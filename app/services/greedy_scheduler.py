import os
from datetime import datetime, timedelta
from enum import IntFlag
from typing import Dict, List, Optional

from dotenv import load_dotenv

from app.internal.timeaddr import get_date_object, to_12hr, to_24hr
from app.models.direction import Direction
from app.models.inout import (
    Booking,
    Plan,
    ScheduleRequest,
    ScheduleResponse,
    ScheduleResult,
    ScheduleResultData,
    Trip,
)
from app.services.direction import get_direction

load_dotenv()
DEBUG_MODE = os.getenv("DEBUG_MODE", "true") == "true"
DEFAULT_BEFORE_PICKUP_TIME = int(
    os.getenv("DEFAULT_BEFORE_PICKUP_TIME", "300")
)  # 5 minutes
DEFAULT_AFTER_PICKUP_TIME = int(
    os.getenv("DEFAULT_AFTER_PICKUP_TIME", "300")
)  # 5 minutes
DEFAULT_DROPOFF_UNLOADING_TIME = int(
    os.getenv("DEFAULT_DROPOFF_UNLOADING_TIME", "300")
)  # 5 minutes


class MobilityAssistance(IntFlag):
    """Mobility assistance flags"""

    NONE = 0
    AMBULATORY = 1 << 0  # 1
    WHEELCHAIR = 1 << 1  # 2
    STRETCHER = 1 << 4  # 16
    ALL = ~(~0 << 8)  # 255


def parse_mobility_assistance(*args: str) -> MobilityAssistance:
    """Parse mobility assistance from strings"""

    def parse_single(s: str) -> MobilityAssistance:
        s_upper = s.upper()
        if s_upper == "STRETCHER":
            return MobilityAssistance.STRETCHER
        elif s_upper == "WHEELCHAIR":
            return MobilityAssistance.WHEELCHAIR
        else:
            return MobilityAssistance.AMBULATORY

    if not args:
        return MobilityAssistance.AMBULATORY

    result = MobilityAssistance.NONE
    for arg in args:
        result |= parse_single(arg)
    return result


def get_priority_from_mobility_assistance(ma: MobilityAssistance) -> int:
    """Get priority from mobility assistance (0=highest, 2=lowest)"""
    if ma & MobilityAssistance.STRETCHER:
        return 0
    if ma & MobilityAssistance.WHEELCHAIR:
        return 1
    return 2


def code_mobility_assistance(ma: MobilityAssistance) -> str:
    """Get code string from mobility assistance"""
    code = ""
    if ma & MobilityAssistance.STRETCHER:
        code += "GUR"
    if ma & MobilityAssistance.WHEELCHAIR:
        code += "WC"
    else:
        code += "AMBI"
    return code


class SchedulerContext:
    """Scheduler context containing configuration and request data"""

    def __init__(self, request: ScheduleRequest):
        self.request = request

    def date_str(self) -> str:
        return self.request.date

    def is_debug(self) -> bool:
        return self.request.debug or DEBUG_MODE

    def debug(self, *args):
        if self.is_debug():
            print("DEBUG:", *args)

    def assert_condition(self, condition: bool, message: str):
        if not condition:
            print("ERROR:", message)
            if self.is_debug():
                raise AssertionError(message)

    def before_pickup_in_sec(self) -> int:
        """Driver can arrive earlier for outgoing trip (in seconds)"""
        return self.request.before_pickup_time or DEFAULT_BEFORE_PICKUP_TIME

    def after_pickup_in_sec(self) -> int:
        """Driver can arrive later for returning trip (in seconds)"""
        return self.request.after_pickup_time or DEFAULT_AFTER_PICKUP_TIME

    def dropoff_unloading_in_sec(self) -> int:
        """Extra time for dropoff unloading (in seconds)"""
        return self.request.dropoff_unloading_time or DEFAULT_DROPOFF_UNLOADING_TIME


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
        self.assistance = parse_mobility_assistance(*booking.mobility_assistance)

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
        name = f"{self.booking.passenger_firstname[0] if self.booking.passenger_firstname else ''}.{self.booking.passenger_lastname[0] if self.booking.passenger_lastname else ''}[{code_mobility_assistance(self.assistance).ljust(7)}]"
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
        booking.scheduled_pickup_time = to_24hr(self.adjusted_pickup_time)
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
            first_pickup_time=to_12hr(self.adjusted_pickup_time),
            last_dropoff_time=to_12hr(self.dropoff_time()),
            notes=booking.admin_note,
            number_of_passengers=1 + booking.additional_passenger,
            trip_complete=booking.trip_complete,
        )


class PlanInfo:
    """Plan information for scheduling"""

    def __init__(self, idx: int, first_trip: TripInfo):
        self.idx = idx
        self.trips: List[TripInfo] = [first_trip]

    def name(self) -> str:
        """Generate vehicle name based on index and mobility assistance codes"""
        # Combine all mobility assistance flags from trips
        combined_assistance = MobilityAssistance.NONE
        for trip in self.trips:
            combined_assistance |= trip.assistance

        code = code_mobility_assistance(combined_assistance)
        return f"{self.idx}{code}"

    def add_trip(self, next_trip: TripInfo):
        """Add a trip to this vehicle"""
        self.trips.append(next_trip)

    def to_plan(self) -> Plan:
        """Convert to Plan model"""
        trips = [trip.to_trip() for trip in self.trips]
        return Plan(trips=trips, shuttle_name=self.name())


class Scheduler:
    """Main scheduler class"""

    def __init__(self, request: ScheduleRequest):
        self.request = request
        self.context = SchedulerContext(request)

    async def calculate(self) -> ScheduleResponse:
        """Calculate the scheduling plan"""
        # Convert bookings to trips
        all_trips = await self._get_trips_from_bookings(self.request.bookings)

        # Mark last legs for passengers with multiple trips
        self._mark_last_leg(all_trips)

        # Group trips by priority (mobility assistance)
        priority_trips = self._get_priority_trips(all_trips)

        # Schedule trips by priority
        plan: List[PlanInfo] = []
        for trips in priority_trips:
            await self._schedule_trips(plan, trips)

        # Debug output
        self.context.debug(self._get_text_plan(plan))

        return self._get_response(plan)

    async def _get_trips_from_bookings(self, bookings: List[Booking]) -> List[TripInfo]:
        """Convert bookings to trip info objects"""
        trips = []
        for booking in bookings:
            trip = await TripInfo.create(self.context, booking)
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
                passenger_trip_list[0].is_last = True

        self.context.debug(f"Converted {len(trips)} trips:")
        for idx, trip in enumerate(trips):
            self.context.debug(idx, trip.short())

    def _get_priority_trips(self, trips: List[TripInfo]) -> List[List[TripInfo]]:
        """Group trips by priority (0=highest, 2=lowest)"""
        priority_trips: List[List[TripInfo]] = [[], [], []]

        for trip in trips:
            priority = get_priority_from_mobility_assistance(trip.assistance)
            priority_trips[priority].append(trip)

        priority_summary = ", ".join(
            f"{idx}: {len(trips)}" for idx, trips in enumerate(priority_trips)
        )
        self.context.debug(f"priority trips: {priority_summary}")

        return priority_trips

    async def _schedule_trips(self, plan: List[PlanInfo], trips: List[TripInfo]):
        """Schedule trips to vehicles"""
        for trip in trips:
            self.context.debug(f"[Schedule]: {trip.short()}")

            best_vehicle: Optional[PlanInfo] = None
            best_arrival: Optional[datetime] = None

            # Try to fit trip into existing vehicles
            for vehicle in plan:
                arrival = await self._is_trip_fit_vehicle(vehicle, trip)
                if arrival is None:
                    self.context.debug(f"  [NO]{vehicle.name()}")
                elif best_arrival is None:
                    self.context.debug(f"  [ADD]{vehicle.name()}")
                    best_vehicle = vehicle
                    best_arrival = arrival
                elif self._is_better(arrival, best_arrival, trip):
                    self.context.debug(
                        f"  [REFRESH]{vehicle.name()}: arrival: {to_12hr(arrival)}, current: {to_12hr(best_arrival)}"
                    )
                    best_vehicle = vehicle
                    best_arrival = arrival
                else:
                    self.context.debug(
                        f"  [SKIP]{vehicle.name()}: arrival: {to_12hr(arrival)}, current: {to_12hr(best_arrival)}"
                    )

            if best_vehicle is None:
                # No vehicle can fit this trip, create a new one
                best_vehicle = PlanInfo(len(plan) + 1, trip)
                plan.append(best_vehicle)
                # First trip of the vehicle
                if trip.is_last:
                    trip.earliest_arrival_time = trip.pickup_time
                else:
                    trip.earliest_arrival_time = trip.pickup_time - timedelta(
                        seconds=self.context.before_pickup_in_sec()
                    )
                self.context.debug(
                    f"[DECISION]new vehicle: {best_vehicle.name()} # {to_12hr(trip.earliest_arrival_time)}"
                )
            else:
                # Add trip to the best vehicle we found
                best_vehicle.add_trip(trip)
                trip.earliest_arrival_time = best_arrival
                self.context.debug(
                    f"[DECISION]add to vehicle: {best_vehicle.name()} # {to_12hr(trip.earliest_arrival_time)}"
                )

            # If actual arrival later than booking, we need to update
            if best_arrival is None or best_arrival < trip.pickup_time:
                trip.adjusted_pickup_time = trip.pickup_time
            else:
                trip.adjusted_pickup_time = best_arrival

    async def _is_trip_fit_vehicle(
        self, vehicle: PlanInfo, next_trip: TripInfo
    ) -> Optional[datetime]:
        """Try to fit next trip into the vehicle, return estimated arrival time if possible"""
        name = vehicle.name()
        self.context.assert_condition(
            len(vehicle.trips) > 0, "only fit non-empty vehicle"
        )

        last_trip = vehicle.trips[-1]

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

    def _get_text_plan(self, plan: List[PlanInfo]) -> str:
        """Generate text representation of the plan for debugging"""
        lines = [
            "=================================================",
            f" Plan of {self.context.date_str()}",
            "======================BEGIN======================",
        ]

        for vehicle in plan:
            lines.append(f"Shuttle = {vehicle.name()}")
            for idx, trip in enumerate(vehicle.trips):
                lines.append(f"{idx} {trip.short()}")

        lines.append("=======================END=======================")
        return "\n".join(lines)

    def _get_response(self, plan: List[PlanInfo]) -> ScheduleResponse:
        """Generate the final response"""
        vehicles = [vehicle.to_plan() for vehicle in plan]

        return ScheduleResponse(
            result=ScheduleResult(
                error_code=0,
                message="Successfully retrieved trips data.",
                status="success",
                data=ScheduleResultData(vehicle_trip_list=vehicles),
            )
        )
