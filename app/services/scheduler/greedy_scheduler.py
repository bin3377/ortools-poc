from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.internal.timeaddr import to_12hr
from app.services.direction import get_direction
from app.services.scheduler import Scheduler, Shuttle, TripInfo


class ShuttleInfo:
    """Shuttle information for scheduling"""

    def __init__(self, idx: int, first_trip: TripInfo):
        self.idx = idx
        self.trips: List[TripInfo] = [first_trip]

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
        return Shuttle(trips=trips, shuttle_name=self.name())


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
                passenger_trip_list[0].is_last = True

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
                # First trip of the vehicle
                if trip.is_last:
                    trip.earliest_arrival_time = trip.pickup_time
                else:
                    trip.earliest_arrival_time = trip.pickup_time - timedelta(
                        seconds=self.context.before_pickup_in_sec()
                    )
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
