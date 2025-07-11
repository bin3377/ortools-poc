from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ortools.sat.python import cp_model

from app.internal.timeaddr import get_date_object, to_12hr, to_24hr
from app.models.inout import Booking, Trip
from app.models.program import Vehicle
from app.services.database import get_program_crud
from app.services.direction import get_direction
from app.services.scheduler import Scheduler, SchedulerContext, Shuttle


class BookingInfo:
    def __init__(
        self,
        booking: Booking,
        from_time_in_minutes: int,
        duration_in_minutes: int,
    ):
        self.booking = booking
        self.from_time_in_minutes = from_time_in_minutes
        self.duration_in_minutes = duration_in_minutes

    @classmethod
    async def create(cls, context: SchedulerContext, booking: Booking) -> "BookingInfo":
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

        return cls(
            booking,
            context.datetime_to_minutes(pickup_time),
            direction.duration_in_sec // 60,
        )


class ORToolsScheduler(Scheduler):
    """OR-Tools based scheduler implementation"""

    def __init__(self, request):
        super().__init__(request)
        self.bookings: List[BookingInfo] = []
        self.vehicles: List[Vehicle] = []

    async def _calculate(self) -> List[Shuttle]:
        """Calculate the scheduling plan using OR-Tools"""
        # Load vehicles
        self.vehicles = await self._load_vehicles(self.request.program_id)

        # Convert bookings to bookinginfo
        for booking in self.request.bookings:
            bi = await BookingInfo.create(self.context, booking)
            self.bookings.append(bi)

        # Create OR-Tools model
        model = cp_model.CpModel()

        num_vehicles = len(self.vehicles)
        num_bookings = len(self.bookings)

        self.context.debug(
            f"OR-Tools model: {num_vehicles} vehicles, {num_bookings} bookings"
        )

        # boolvar assignments[i][j] means vehicle i is assigned to booking j
        assignments = {}
        for i in range(num_vehicles):
            for j in range(num_bookings):
                assignments[i, j] = model.NewBoolVar(f"vehicle_{i}_booking_{j}")

        # intvar times[i][j] means vehicle i starts booking j at times[i][j] (in minutes)
        times = {}
        for i in range(num_vehicles):
            for j in range(num_bookings):
                times[i, j] = model.NewIntVar(
                    0, 24 * 60, f"time_vehicle_{i}_booking_{j}"
                )

        await self._add_constraints(model, assignments, times)
        await self._add_objectives(model, assignments)

        # Solve the model
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 600.0  # 10 minute timeout

        status = solver.Solve(model)

        match status:
            case cp_model.OPTIMAL:
                self.context.debug("OR-Tools solver: OPTIMAL")
            case cp_model.FEASIBLE:
                self.context.debug("OR-Tools solver: FEASIBLE")
            case cp_model.INFEASIBLE:
                self.context.debug("OR-Tools solver: INFEASIBLE")
                raise ValueError("OR-Tools solver failed with status: INFEASIBLE")
            case cp_model.MODEL_INVALID:
                self.context.debug("OR-Tools solver: MODEL_INVALID")
                self.context.debug(model.validate())
                raise ValueError("OR-Tools solver failed with status: MODEL_INVALID")
            case cp_model.UNKNOWN:
                self.context.debug("OR-Tools solver: UNKNOWN")
                raise ValueError("OR-Tools solver failed with status: UNKNOWN")
            case _:
                self.context.debug(f"OR-Tools solver: {status}")
                raise ValueError(f"OR-Tools solver failed with status: {status}")

        return self._extract_solution(solver, assignments, times)

    async def _load_vehicles(self, program_id: str):
        """Load actual vehicles from the database based on program_id"""
        crud = await get_program_crud()
        program = await crud.get_program_by_id(program_id)
        return program.vehicles

    async def _add_constraints(
        self,
        model: cp_model.CpModel,
        assignments: Dict,
        times: Dict,
    ):
        """Add constraints to the OR-Tools model"""

        num_vehicles = len(self.vehicles)
        num_bookings = len(self.bookings)

        # Each booking must be assigned to exactly one vehicle
        for j in range(num_bookings):
            model.Add(sum(assignments[i, j] for i in range(num_vehicles)) == 1)

        # Mobility assistance compatibility
        for i in range(num_vehicles):
            for j in range(num_bookings):
                # if vehicle i is assigned to booking j, then the mobility assistance must be compatible
                model.Add(
                    self.vehicles[i].assistance.compatible(
                        self.bookings[j].booking.assistance()
                    )
                ).OnlyEnforceIf(assignments[i, j])

        # Times within pickup time window
        for i in range(num_vehicles):
            for j in range(num_bookings):
                # if vehicle i is assigned to booking j, then the start time must be within the pickup time window
                model.Add(
                    times[i, j] <= self.bookings[j].from_time_in_minutes
                ).OnlyEnforceIf(assignments[i, j])
                # model.Add(
                #     times[i, j]
                #     >= self.bookings[j].from_time_in_minutes
                #     + self.context.before_pickup_in_sec() // 60
                # ).OnlyEnforceIf(assignments[i, j])

        # No overlap between bookings assigned to the same vehicle
        for i in range(num_vehicles):
            for j in range(num_bookings):
                for k in range(num_bookings):
                    if (
                        j != k
                        and self.bookings[j].from_time_in_minutes
                        >= self.bookings[k].from_time_in_minutes
                    ):
                        connection = await get_direction(
                            self.bookings[j].booking.dropoff_address,
                            self.bookings[k].booking.pickup_address,
                        )
                        # if vehicle i is assigned to both booking j and k, then the start time of j must be after the end time of k
                        model.Add(
                            times[i, j]
                            >= times[i, k]
                            + self.bookings[k].duration_in_minutes
                            + self.context.dropoff_unloading_in_sec() // 60
                            + connection.duration_in_sec // 60
                        ).OnlyEnforceIf(assignments[i, j]).OnlyEnforceIf(
                            assignments[i, k]
                        )

        # Same passenger preference constraint
        if self.request.optimization.chain_bookings_for_same_passenger:
            for i in range(num_vehicles):
                for j in range(num_bookings):
                    for k in range(num_bookings):
                        if (
                            j != k
                            and self.bookings[j].booking.passenger()
                            == self.bookings[k].booking.passenger()
                        ):
                            model.Add(assignments[i, j] == assignments[i, k])

    async def _add_objectives(
        self,
        model: cp_model.CpModel,
        assignments: Dict,
    ):
        """Add objectives to the OR-Tools model"""

        num_vehicles = len(self.vehicles)
        num_bookings = len(self.bookings)
        objectives = []

        # Minimize number of vehicles used
        if self.request.optimization.minimize_vehicles:
            # boolvar vehicle_used[i] means vehicle i is used
            vehicle_used = {}
            for i in range(num_vehicles):
                vehicle_used[i] = model.NewBoolVar(f"vehicle_used_{i}")

            # mark vehicle used if assigned to any trip
            for i in range(num_vehicles):
                for j in range(num_bookings):
                    model.Add(vehicle_used[i] >= assignments[i, j])

            objectives.append(
                sum(vehicle_used) * 1000
            )  # High weight for vehicle minimization

        # Set the objective
        if objectives:
            model.Minimize(sum(objectives))

    def _extract_solution(
        self,
        solver: cp_model.CpSolver,
        assignments: Dict,
        times: Dict,
    ) -> List[Shuttle]:
        """Extract solution from the solver"""

        num_vehicles = len(self.vehicles)
        num_bookings = len(self.bookings)

        # Convert to shuttles
        shuttles = []
        for i in range(num_vehicles):
            vehicle_trips = []  # trips assigned to vehicle i
            for j in range(num_bookings):
                if solver.Value(assignments[i, j]):
                    start_time_in_minutes = solver.Value(times[i, j])
                    trip = self._convert_to_trip(
                        self.bookings[j], start_time_in_minutes
                    )
                    vehicle_trips.append(trip)

            if vehicle_trips:
                shuttles.append(
                    self._convert_to_shuttle(self.vehicles[i], vehicle_trips)
                )

        return shuttles

    def _convert_to_shuttle(self, vehicle: Vehicle, trips: List[Trip]) -> Shuttle:
        """Convert to Shuttle model"""

        return Shuttle(
            trips=trips,
            shuttle_name=vehicle.name,
            shuttle_id=vehicle.id,
            shuttle_wheelchair=vehicle.assistance.value,
        )

    def _convert_to_trip(
        self,
        booking_info: BookingInfo,
        start_time_in_minutes: int,
    ) -> Trip:
        """Convert to Trip model"""
        booking = booking_info.booking

        # Clear irrelevant fields
        booking.actual_dropoff_time = None
        booking.actual_pickup_time = None
        booking.driver_arrival_time = None
        booking.driver_enroute_time = None

        # Set scheduled times
        scheduled_pickup_time = self.context.minutes_to_datetime(start_time_in_minutes)
        booking.scheduled_pickup_time = to_24hr(scheduled_pickup_time)
        scheduled_dropoff_time = self.context.minutes_to_datetime(
            start_time_in_minutes + booking_info.duration_in_minutes
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
            number_of_passengers=1 + booking.additional_passenger,
            trip_complete=booking.trip_complete,
        )
