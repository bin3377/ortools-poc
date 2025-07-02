import os
from datetime import datetime, timedelta
from typing import List, Optional

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
from app.models.mobility_assistance import MobilityAssistanceType
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


class BookingInfo:
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
    async def create(cls, context: SchedulerContext, booking: Booking) -> "BookingInfo":
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

    def __init__(self, idx: int, first_trip: BookingInfo):
        self.idx = idx
        self.trips: List[BookingInfo] = [first_trip]

    def name(self) -> str:
        """Generate vehicle name based on index and mobility assistance codes"""
        for trip in self.trips:
            return f"{self.idx}{trip.assistance.value}"

    def add_trip(self, next_trip: BookingInfo):
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

    async def schedule(self) -> ScheduleResponse:
        """Schedule trips for a given request"""

        plan = await self._calculate()
        # Debug output
        self.context.debug(self._get_text_plan(plan))

        return self._get_response(plan)

    async def _calculate(self) -> List[PlanInfo]:
        pass

    async def _get_trips_from_bookings(
        self, bookings: List[Booking]
    ) -> List[BookingInfo]:
        """Convert bookings to trip info objects"""
        trips = []
        for booking in bookings:
            trip = await BookingInfo.create(self.context, booking)
            trips.append(trip)
        return trips

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
