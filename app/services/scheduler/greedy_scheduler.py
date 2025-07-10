from datetime import datetime, timedelta
from typing import Dict, List, Optional

from nanoid import generate

from app.internal.timeaddr import get_date_object, to_12hr, to_24hr
from app.models.direction import Direction
from app.models.inout import Booking, Trip
from app.models.mobility_assistance import MobilityAssistanceType
from app.services.direction import get_direction
from app.services.scheduler import Scheduler, SchedulerContext, Shuttle


class TripInfo:
    """Trip information for scheduling"""

    def __init__(
        self,
        context: SchedulerContext,
        booking: Booking,
        pickup_time: datetime,
        direction: Direction,
    ):
        self.context = context
        self.booking = booking

        self.pickup_address = booking.pickup_address
        self.dropoff_address = booking.dropoff_address

        # Passenger ID or full name if empty
        self.passenger = (
            booking.passenger_id
            if booking.passenger_id
            else f"{booking.passenger_firstname} {booking.passenger_lastname}"
        )

        # Parse mobility assistance
        self.assistance = MobilityAssistanceType.from_strings(
            *booking.mobility_assistance
        )

        self.pickup_time = pickup_time
        self.distance_in_meter = direction.distance_in_meter
        self.duration_in_sec = direction.duration_in_sec

        # Flags and calculated times
        self.is_last = False
        self.adjusted_pickup_time: Optional[datetime] = None
        self.earliest_arrival_time: Optional[datetime] = None

        # Update booking with travel info
        booking.travel_distance = direction.distance_in_meter
        booking.travel_time = direction.duration_in_sec

    @classmethod
    async def create(cls, context: SchedulerContext, booking: Booking) -> "TripInfo":
        """Create TripInfo with async direction lookup"""
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

        return cls(context, booking, pickup_time, direction)

    def short(self) -> str:
        """Short string representation for debugging"""

        def short_addr(addr: str) -> str:
            return addr.split(",")[0]

        book = f"{self.booking.booking_id} {self.booking.pickup_time}"
        name = f"{self.booking.passenger_firstname[0] if self.booking.passenger_firstname else ''}.{self.booking.passenger_lastname[0] if self.booking.passenger_lastname else ''}[{self.assistance.ljust(7)}]"
        addr = f"{short_addr(self.pickup_address)}-{short_addr(self.dropoff_address)}"

        if self.adjusted_pickup_time:
            time_str = f"({to_12hr(self.earliest_arrival_time)}){to_12hr(self.adjusted_pickup_time)}-{to_12hr(self.dropoff_time())} "
        else:
            time_str = " "

        last_str = "[L]" if self.is_last else ""
        return f"{book} {name}: {time_str}{addr}{last_str}"

    def latest_pickup_time(self) -> datetime:
        """Latest allowable pickup time"""
        if self.is_last:
            # For last trip (return), we can delay with configured value
            return self.pickup_time + timedelta(
                seconds=self.context.after_pickup_in_sec()
            )
        else:
            return self.pickup_time

    def dropoff_time(self) -> datetime:
        """Calculated dropoff time"""
        base_time = (
            self.adjusted_pickup_time if self.adjusted_pickup_time else self.pickup_time
        )
        return base_time + timedelta(seconds=self.duration_in_sec)

    def finish_time(self) -> datetime:
        """Time when trip is completely finished (including unloading)"""
        return self.dropoff_time() + timedelta(
            seconds=self.context.dropoff_unloading_in_sec()
        )

    def to_trip(self) -> Trip:
        """Convert to Trip model"""
        booking = self.booking

        # Clear irrelevant fields
        booking.actual_dropoff_time = None
        booking.actual_pickup_time = None
        booking.driver_arrival_time = None
        booking.driver_enroute_time = None

        # Set scheduled times
        booking.scheduled_pickup_time = to_24hr(
            self.adjusted_pickup_time or self.pickup_time
        )
        booking.scheduled_dropoff_time = to_24hr(self.dropoff_time())

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
            first_pickup_time=to_12hr(self.adjusted_pickup_time or self.pickup_time),
            last_dropoff_time=to_12hr(self.dropoff_time()),
            notes=booking.admin_note,
            number_of_passengers=1 + booking.additional_passenger,
            trip_complete=booking.trip_complete,
            short=self.short(),
        )


class ShuttleInfo:
    """Shuttle information for scheduling"""

    def __init__(self, idx: int, first_trip: TripInfo):
        self.idx = idx
        self.trips: List[TripInfo] = [first_trip]

    def assistance(self) -> MobilityAssistanceType:
        """Get mobility assistance type"""
        return MobilityAssistanceType.from_multiple(
            *[trip.assistance for trip in self.trips]
        )

    def name(self) -> str:
        """Generate vehicle name based on index and mobility assistance codes"""
        for trip in self.trips:
            return f"{self.idx}{trip.assistance.value}"

    def add_trip(self, next_trip: TripInfo):
        """Add a trip to this vehicle"""
        self.trips.append(next_trip)

    def to_shuttle(self) -> Shuttle:
        """Convert to Shuttle model"""
        trips = [trip.to_trip() for trip in self.trips]
        return Shuttle(
            trips=trips,
            shuttle_name=self.name(),
            shuttle_id=generate(
                alphabet="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
                size=10,
            ),
        )


class GreedyScheduler(Scheduler):
    """Main scheduler class"""

    async def _calculate(self) -> List[Shuttle]:
        """Calculate the scheduling plan"""
        # Convert bookings to trips
        all_trips = await self._get_trips_from_bookings(self.request.bookings)

        # Mark last legs for passengers with multiple trips
        self._mark_last_leg(all_trips)

        # Group trips by priority (mobility assistance)
        priority_trips = self._get_priority_trips(all_trips)

        # Schedule trips by priority
        plan: List[ShuttleInfo] = []
        for trips in priority_trips:
            await self._schedule_trips(plan, trips)

        return [shuttle.to_shuttle() for shuttle in plan]

    async def _get_trips_from_bookings(self, bookings: List[Booking]) -> List[TripInfo]:
        """Convert bookings to trip info objects"""
        trips = []
        for booking in bookings:
            trip = await TripInfo.create(self.context, booking)
            trip.earliest_arrival_time = trip.pickup_time - timedelta(
                seconds=self.context.before_pickup_in_sec()
            )
            trips.append(trip)
        return trips

    def _mark_last_leg(self, trips: List[TripInfo]):
        """Mark the last trip for each passenger"""
        # Sort trips by pickup time
        trips.sort(key=lambda t: t.pickup_time)

        # Group trips by passenger (latest first)
        passenger_trips: Dict[str, List[TripInfo]] = {}
        for trip in reversed(trips):
            if trip.passenger not in passenger_trips:
                passenger_trips[trip.passenger] = []
            passenger_trips[trip.passenger].append(trip)

        # Mark last trip for passengers with multiple trips
        for passenger_trip_list in passenger_trips.values():
            if len(passenger_trip_list) > 1:
                passenger_trip_list[-1].is_last = True
                # Last trip of the vehicle
                passenger_trip_list[0].earliest_arrival_time = passenger_trip_list[
                    0
                ].pickup_time

        self.context.debug(f"Converted {len(trips)} trips:")
        for idx, trip in enumerate(trips):
            self.context.debug(idx, trip.short())

    def _get_priority_trips(self, trips: List[TripInfo]) -> List[List[TripInfo]]:
        """Group trips by priority (0=highest, 2=lowest)"""
        priority_trips: List[List[TripInfo]] = [[], [], []]

        for trip in trips:
            priority = trip.assistance.priority()
            priority_trips[priority].append(trip)

        priority_summary = ", ".join(
            f"{idx}: {len(trips)}" for idx, trips in enumerate(priority_trips)
        )
        self.context.debug(f"priority trips: {priority_summary}")

        return priority_trips

    async def _schedule_trips(self, plan: List[ShuttleInfo], trips: List[TripInfo]):
        """Schedule trips to shuttles"""
        for trip in trips:
            self.context.debug(f"[Schedule]: {trip.short()}")

            best_shuttle: Optional[ShuttleInfo] = None
            best_arrival: Optional[datetime] = None

            # Try to fit trip into existing shuttles
            for vehicle in plan:
                arrival = await self._is_trip_fit(vehicle, trip)
                if arrival is None:
                    self.context.debug(f"  [NO]{vehicle.name()}")
                elif best_arrival is None:
                    self.context.debug(f"  [ADD]{vehicle.name()}")
                    best_shuttle = vehicle
                    best_arrival = arrival
                elif self._is_better(arrival, best_arrival, trip):
                    self.context.debug(
                        f"  [REFRESH]{vehicle.name()}: arrival: {to_12hr(arrival)}, current: {to_12hr(best_arrival)}"
                    )
                    best_shuttle = vehicle
                    best_arrival = arrival
                else:
                    self.context.debug(
                        f"  [SKIP]{vehicle.name()}: arrival: {to_12hr(arrival)}, current: {to_12hr(best_arrival)}"
                    )

            if best_shuttle is None:
                # No vehicle can fit this trip, create a new one
                best_shuttle = ShuttleInfo(len(plan) + 1, trip)
                plan.append(best_shuttle)
                self.context.debug(
                    f"[DECISION]new vehicle: {best_shuttle.name()} # {to_12hr(trip.earliest_arrival_time)}"
                )
            else:
                # Add trip to the best vehicle we found
                best_shuttle.add_trip(trip)
                trip.earliest_arrival_time = best_arrival
                self.context.debug(
                    f"[DECISION]add to vehicle: {best_shuttle.name()} # {to_12hr(trip.earliest_arrival_time)}"
                )

            # If actual arrival later than booking, we need to update
            if best_arrival is None or best_arrival < trip.pickup_time:
                trip.adjusted_pickup_time = trip.pickup_time
            else:
                trip.adjusted_pickup_time = best_arrival

    async def _is_trip_fit(
        self, shuttle: ShuttleInfo, next_trip: TripInfo
    ) -> Optional[datetime]:
        """Try to fit next trip into the vehicle, return estimated arrival time if possible"""
        name = shuttle.name()
        self.context.assert_condition(
            len(shuttle.trips) > 0, "only fit non-empty vehicle"
        )

        last_trip = shuttle.trips[-1]

        if last_trip.finish_time() > next_trip.latest_pickup_time():
            self.context.debug(
                f"[NOFIT]{name} - lastFinish: {to_12hr(last_trip.finish_time())}, latestPickup: {to_12hr(next_trip.latest_pickup_time())}"
            )
            return None

        if last_trip.dropoff_address == next_trip.pickup_address:
            self.context.debug(f"[FIT]{name} - same location")
            return last_trip.finish_time()

        # Query time/distance between last dropoff and next pickup
        direction = await get_direction(
            last_trip.dropoff_address, next_trip.pickup_address, last_trip.finish_time()
        )
        if direction is None:
            self.context.debug(
                f"No routes found for the given query from {last_trip.dropoff_address} to {next_trip.pickup_address}; skip."
            )
            return None

        estimated_arrival = last_trip.finish_time() + timedelta(
            seconds=direction.duration_in_sec
        )
        if estimated_arrival > next_trip.latest_pickup_time():
            self.context.debug(
                f"[NOFIT]{name} - estimateArrival: {to_12hr(estimated_arrival)}, latestPickup: {to_12hr(next_trip.latest_pickup_time())}"
            )
            return None

        self.context.debug(
            f"[FIT]{name} - estimateArrival: {to_12hr(estimated_arrival)}, latestPickup: {to_12hr(next_trip.latest_pickup_time())}"
        )
        return estimated_arrival

    def _is_better(self, coming: datetime, current: datetime, trip: TripInfo) -> bool:
        """Compare estimated arrival times; return True if coming is better"""
        if trip.is_last:
            if current > trip.pickup_time:  # We are later than booking time
                return coming < current  # Earlier is always better
            else:
                return coming > current  # Shorter wait is better
        else:  # Outgoing trip
            early_arrival = trip.pickup_time - timedelta(
                seconds=self.context.before_pickup_in_sec()
            )
            if current > early_arrival:  # We cannot make enough early arrival
                return coming < current  # Earlier is always better
            else:
                return coming > current  # Shorter wait is better
