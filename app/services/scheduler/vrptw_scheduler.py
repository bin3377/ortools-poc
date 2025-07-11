from typing import Dict, List, Optional, Tuple

import numpy as np
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.internal.timeaddr import get_date_object, to_12hr, to_24hr
from app.models.inout import Booking, Trip
from app.models.program import Vehicle
from app.services.database import get_program_crud
from app.services.direction import get_direction
from app.services.scheduler import Scheduler, SchedulerContext, Shuttle


class VRPTWNode:
    """Node for VRPTW representing pickup and dropoff locations"""

    def __init__(
        self,
        node_id: int,
        address: str,
        time_window: Tuple[int, int],
        service_time: int = 0,
        demand: int = 0,
    ):
        self.node_id = node_id
        self.address = address
        self.time_window = time_window  # (earliest, latest) in minutes
        self.service_time = service_time  # time to serve this node in minutes
        self.demand = demand  # passenger demand
        self.booking_info: Optional["BookingInfo"] = None
        self.is_depot = False
        self.is_pickup = False
        self.is_dropoff = False


class BookingInfo:
    """Enhanced booking info for VRPTW"""

    def __init__(
        self,
        booking: Booking,
        pickup_node: VRPTWNode,
        dropoff_node: VRPTWNode,
        duration_in_minutes: int,
    ):
        self.booking = booking
        self.pickup_node = pickup_node
        self.dropoff_node = dropoff_node
        self.duration_in_minutes = duration_in_minutes

        # Link nodes to booking
        pickup_node.booking_info = self
        dropoff_node.booking_info = self
        pickup_node.is_pickup = True
        dropoff_node.is_dropoff = True

    @classmethod
    async def create(
        cls,
        context: SchedulerContext,
        booking: Booking,
        pickup_node_id: int,
        dropoff_node_id: int,
    ) -> "BookingInfo":
        """Create BookingInfo with pickup and dropoff nodes"""
        pickup_time = get_date_object(
            context.date_str(), booking.pickup_time, booking.pickup_address
        )
        direction = await get_direction(
            booking.pickup_address, booking.dropoff_address, pickup_time
        )

        if direction is None:
            raise ValueError(
                f"No routes found for the given query from {booking.pickup_address} to {booking.dropoff_address}."
            )

        # Convert pickup time to minutes and create time windows
        pickup_time_minutes = context.datetime_to_minutes(pickup_time)
        earliest_pickup = pickup_time_minutes - (context.before_pickup_in_sec() // 60)
        latest_pickup = pickup_time_minutes + (context.after_pickup_in_sec() // 60)

        # Create pickup node
        pickup_node = VRPTWNode(
            node_id=pickup_node_id,
            address=booking.pickup_address,
            time_window=(earliest_pickup, latest_pickup),
            service_time=context.before_pickup_in_sec() // 60,  # pickup loading time
            demand=booking.total_seats(),
        )

        # Create dropoff node
        trip_duration = direction.duration_in_sec // 60
        dropoff_time_minutes = pickup_time_minutes + trip_duration
        dropoff_node = VRPTWNode(
            node_id=dropoff_node_id,
            address=booking.dropoff_address,
            time_window=(
                dropoff_time_minutes,
                dropoff_time_minutes + 60,
            ),  # 1 hour window
            service_time=context.dropoff_unloading_in_sec()
            // 60,  # dropoff unloading time
            demand=-booking.total_seats(),  # negative demand for dropoff
        )

        return cls(booking, pickup_node, dropoff_node, trip_duration)


class VRPTWScheduler(Scheduler):
    """VRPTW-based scheduler implementation using OR-Tools routing"""

    def __init__(self, request):
        super().__init__(request)
        self.bookings: List[BookingInfo] = []
        self.vehicles: List[Vehicle] = []
        self.nodes: List[VRPTWNode] = []
        self.distance_matrix: List[List[int]] = []
        self.time_matrix: List[List[int]] = []

    async def _calculate(self) -> List[Shuttle]:
        """Calculate the scheduling plan using VRPTW"""
        # Load vehicles
        self.vehicles = await self._load_vehicles(self.request.program_id)

        if not self.vehicles:
            raise ValueError("No vehicles available for scheduling")

        # Create nodes and bookings
        await self._create_nodes_and_bookings()

        if not self.bookings:
            return []

        # Build distance and time matrices
        await self._build_matrices()
        self.context.debug("Distance matrix:")
        self.context.debug(np.shape(self.distance_matrix))
        self.context.debug("Time matrix:")
        self.context.debug(np.shape(self.time_matrix))

        # Create and solve VRPTW model
        return await self._solve_vrptw()

    async def _load_vehicles(self, program_id: str) -> List[Vehicle]:
        """Load actual vehicles from the database based on program_id"""
        crud = await get_program_crud()
        program = await crud.get_program_by_id(program_id)
        return program.vehicles

    async def _create_nodes_and_bookings(self):
        """Create nodes and booking info for VRPTW"""
        # Create depot node (first booking's pickup address as depot)
        if self.request.bookings:
            depot_address = self.request.bookings[0].pickup_address
            depot_node = VRPTWNode(
                node_id=0,
                address=depot_address,
                time_window=(0, 24 * 60),  # 24 hour window
                service_time=0,
                demand=0,
            )
            depot_node.is_depot = True
            self.nodes.append(depot_node)

        # Create pickup and dropoff nodes for each booking
        node_id = 1
        for booking in self.request.bookings:
            pickup_node_id = node_id
            dropoff_node_id = node_id + 1

            booking_info = await BookingInfo.create(
                self.context, booking, pickup_node_id, dropoff_node_id
            )
            self.bookings.append(booking_info)

            self.nodes.append(booking_info.pickup_node)
            self.nodes.append(booking_info.dropoff_node)

            node_id += 2

    async def _build_matrices(self):
        """Build distance and time matrices between all nodes"""
        num_nodes = len(self.nodes)
        self.distance_matrix = [[0 for _ in range(num_nodes)] for _ in range(num_nodes)]
        self.time_matrix = [[0 for _ in range(num_nodes)] for _ in range(num_nodes)]

        # Calculate distances and times between all pairs of nodes
        for i in range(num_nodes):
            for j in range(num_nodes):
                if i == j:
                    self.distance_matrix[i][j] = 0
                    self.time_matrix[i][j] = 0
                else:
                    # Get direction between nodes
                    direction = await get_direction(
                        self.nodes[i].address, self.nodes[j].address
                    )

                    if direction:
                        # Convert to appropriate units
                        self.distance_matrix[i][j] = int(direction.distance_in_meter)
                        self.time_matrix[i][j] = (
                            direction.duration_in_sec // 60
                        )  # minutes
                    else:
                        # Use large penalty for unreachable nodes
                        self.distance_matrix[i][j] = 999999
                        self.time_matrix[i][j] = 999999

    async def _solve_vrptw(self) -> List[Shuttle]:
        """Solve VRPTW using OR-Tools routing"""
        # Create routing index manager
        manager = pywrapcp.RoutingIndexManager(
            len(self.nodes),
            len(self.vehicles),
            0,  # depot is node 0
        )

        # Create routing model
        routing = pywrapcp.RoutingModel(manager)

        # Add distance callback
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return self.distance_matrix[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Add time callback
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return self.time_matrix[from_node][to_node]

        time_callback_index = routing.RegisterTransitCallback(time_callback)

        # Add time window constraints
        time_dimension_name = "Time"
        routing.AddDimension(
            time_callback_index,
            30,  # slack time (30 minutes)
            24 * 60,  # maximum time (24 hours)
            False,  # Don't force start cumul to zero
            time_dimension_name,
        )
        time_dimension = routing.GetDimensionOrDie(time_dimension_name)

        # Add time windows for each node
        for node_idx, node in enumerate(self.nodes):
            if node_idx == 0:  # depot
                time_dimension.SetCumulVarSoftLowerBound(
                    manager.NodeToIndex(node_idx), 0, 0
                )
                time_dimension.SetCumulVarSoftUpperBound(
                    manager.NodeToIndex(node_idx), 24 * 60, 0
                )
            else:
                index = manager.NodeToIndex(node_idx)
                time_dimension.SetCumulVarSoftLowerBound(
                    index, node.time_window[0], 1000
                )
                time_dimension.SetCumulVarSoftUpperBound(
                    index, node.time_window[1], 1000
                )

        # Add vehicle capacity constraints if multi-loading is enabled
        if (
            self.request.optimization
            and self.request.optimization.multi_load_passengers
        ):

            def demand_callback(from_index):
                from_node = manager.IndexToNode(from_index)
                return self.nodes[from_node].demand

            demand_callback_index = routing.RegisterUnaryTransitCallback(
                demand_callback
            )
            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index,
                0,  # null capacity slack
                [
                    vehicle.seats for vehicle in self.vehicles
                ],  # vehicle maximum capacities
                True,  # start cumul to zero
                "Capacity",
            )

        # Add pickup and delivery constraints
        for booking_info in self.bookings:
            pickup_index = manager.NodeToIndex(booking_info.pickup_node.node_id)
            dropoff_index = manager.NodeToIndex(booking_info.dropoff_node.node_id)

            # Same vehicle must handle pickup and dropoff
            routing.AddPickupAndDelivery(pickup_index, dropoff_index)

            # Pickup must come before dropoff
            routing.solver().Add(
                routing.VehicleVar(pickup_index) == routing.VehicleVar(dropoff_index)
            )
            routing.solver().Add(
                time_dimension.CumulVar(pickup_index)
                <= time_dimension.CumulVar(dropoff_index)
            )

        # Add same passenger constraints
        if (
            self.request.optimization
            and self.request.optimization.chain_bookings_for_same_passenger
        ):
            passenger_bookings = {}
            for booking_info in self.bookings:
                passenger = booking_info.booking.passenger()
                if passenger not in passenger_bookings:
                    passenger_bookings[passenger] = []
                passenger_bookings[passenger].append(booking_info)

            # Force same vehicle for same passenger
            for passenger_booking_list in passenger_bookings.values():
                if len(passenger_booking_list) > 1:
                    for i in range(len(passenger_booking_list) - 1):
                        pickup_index_1 = manager.NodeToIndex(
                            passenger_booking_list[i].pickup_node.node_id
                        )
                        pickup_index_2 = manager.NodeToIndex(
                            passenger_booking_list[i + 1].pickup_node.node_id
                        )
                        routing.solver().Add(
                            routing.VehicleVar(pickup_index_1)
                            == routing.VehicleVar(pickup_index_2)
                        )

        # Set search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.FromSeconds(60)

        # Solve
        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            return self._extract_solution(manager, routing, solution)
        else:
            self.context.debug("VRPTW solver failed to find solution")
            raise ValueError("VRPTW solver failed to find solution")

    def _extract_solution(self, manager, routing, solution) -> List[Shuttle]:
        """Extract solution from VRPTW solver"""
        shuttles = []

        for vehicle_id in range(len(self.vehicles)):
            vehicle = self.vehicles[vehicle_id]
            vehicle_trips = []

            index = routing.Start(vehicle_id)
            route_nodes = []

            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route_nodes.append(node_index)
                index = solution.Value(routing.NextVar(index))

            # Convert route nodes to trips
            current_booking = None
            for node_index in route_nodes:
                if node_index == 0:  # depot
                    continue

                node = self.nodes[node_index]
                if node.is_pickup:
                    current_booking = node.booking_info
                elif node.is_dropoff and current_booking:
                    # Create trip for this booking
                    trip = self._convert_to_trip(
                        current_booking, solution, manager, routing, vehicle_id
                    )
                    if trip:
                        vehicle_trips.append(trip)
                    current_booking = None

            if vehicle_trips:
                shuttle = self._convert_to_shuttle(vehicle, vehicle_trips)
                shuttles.append(shuttle)

        return shuttles

    def _convert_to_trip(
        self, booking_info: BookingInfo, solution, manager, routing, vehicle_id
    ) -> Optional[Trip]:
        """Convert booking info to Trip model"""
        booking = booking_info.booking

        # Get pickup time from solution
        pickup_index = manager.NodeToIndex(booking_info.pickup_node.node_id)
        time_dimension = routing.GetDimensionOrDie("Time")
        pickup_time_minutes = solution.Value(time_dimension.CumulVar(pickup_index))

        # Clear irrelevant fields
        booking.actual_dropoff_time = None
        booking.actual_pickup_time = None
        booking.driver_arrival_time = None
        booking.driver_enroute_time = None

        # Set scheduled times
        scheduled_pickup_time = self.context.minutes_to_datetime(pickup_time_minutes)
        booking.scheduled_pickup_time = to_24hr(scheduled_pickup_time)

        scheduled_dropoff_time = self.context.minutes_to_datetime(
            pickup_time_minutes + booking_info.duration_in_minutes
        )
        booking.scheduled_dropoff_time = to_24hr(scheduled_dropoff_time)

        return Trip(
            bookings=[booking],
            trip_id=booking.trip_id,
            program_id=booking.program_id,
            program_name=booking.program_name,
            program_timezone=booking.program_timezone,
            first_pickup_address=booking.pickup_address,
            first_pickup_latitude=booking.pickup_latitude,
            first_pickup_longitude=booking.pickup_longitude,
            last_dropoff_address=booking.dropoff_address,
            last_dropoff_latitude=booking.dropoff_latitude,
            last_dropoff_longitude=booking.dropoff_longitude,
            first_pickup_time=to_12hr(scheduled_pickup_time),
            last_dropoff_time=to_12hr(scheduled_dropoff_time),
            notes=booking.admin_note,
            number_of_passengers=booking.total_seats(),
            trip_complete=booking.trip_complete,
        )

    def _convert_to_shuttle(self, vehicle: Vehicle, trips: List[Trip]) -> Shuttle:
        """Convert to Shuttle model"""
        return Shuttle(
            trips=trips,
            shuttle_name=vehicle.name,
            shuttle_id=vehicle.id,
            shuttle_wheelchair=vehicle.assistance.value,
        )
