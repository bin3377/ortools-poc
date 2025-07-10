from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.models.mobility_assistance import MobilityAssistanceType


class Booking(BaseModel):
    """Booking model representing a ride booking"""

    booking_id: str
    passenger_id: str
    passenger_firstname: str
    passenger_lastname: str
    additional_passenger: int
    mobility_assistance: List[str]
    program_name: str
    pickup_time: str  # HH:mm format
    pickup_address: str
    dropoff_address: str
    ride_status: int

    # Optional fields
    passenger_phone: Optional[str] = None
    pickup_address_id: Optional[str] = None
    pickup_latitude: Optional[float] = None
    pickup_longitude: Optional[float] = None
    pickup_account_id: Optional[str] = None
    dropoff_address_id: Optional[str] = None
    dropoff_latitude: Optional[float] = None
    dropoff_longitude: Optional[float] = None
    dropoff_account_id: Optional[str] = None

    scheduled_pickup_time: Optional[str] = None  # h:mm AM/PM
    scheduled_dropoff_time: Optional[str] = None  # h:mm AM/PM
    actual_pickup_time: Optional[str] = None  # h:mm AM/PM
    actual_dropoff_time: Optional[str] = None  # h:mm AM/PM
    driver_arrival_time: Optional[str] = None  # h:mm AM/PM
    driver_enroute_time: Optional[str] = None  # h:mm AM/PM

    travel_time: Optional[int] = None
    travel_distance: Optional[float] = None
    ride_fee: Optional[float] = None
    total_addl_fee_usd_cents: Optional[int] = None
    payment: Optional[str] = None
    insurance_account_id: Optional[str] = None
    payment_complete: Optional[bool] = None
    admin_note: Optional[str] = None
    trip_id: Optional[str] = None
    trip_complete: Optional[bool] = None
    program_id: Optional[str] = None
    program_timezone: Optional[str] = None
    driver_note: Optional[str] = None
    office_note: Optional[str] = None
    flag: Optional[bool] = None
    willcall_call_time: Optional[Any] = None
    total_seat_count: Optional[int] = None

    def assistance(self) -> MobilityAssistanceType:
        """Get mobility assistance type"""
        return MobilityAssistanceType.from_strings(*self.mobility_assistance)

    def short(self) -> str:
        """Short string representation for debugging"""

        def passenger() -> str:
            return f"{self.passenger_firstname[0] if self.passenger_firstname else ''}.{self.passenger_lastname[0] if self.passenger_lastname else ''}"

        def addr(addr: str) -> str:
            return addr.split(",")[0]

        return f"B-{self.booking_id} {passenger()} {self.pickup_time} {addr(self.pickup_address)}-{addr(self.dropoff_address)} [{self.assistance().value}]"


class Trip(BaseModel):
    """Trip model representing a scheduled trip"""

    trip_id: Optional[str] = None
    program_id: Optional[str] = None
    program_name: str
    program_timezone: Optional[str] = None
    first_pickup_time: str
    last_dropoff_time: str
    driver_id: Optional[str] = None
    driver_firstname: Optional[str] = None
    driver_lastname: Optional[str] = None
    driver_team_id: Optional[str] = None
    driver_team_name: Optional[str] = None
    driver_team: Optional[str] = None
    driver_action: Optional[str] = None
    drivershifts: Optional[List[Any]] = None
    first_pickup_address: str
    first_pickup_latitude: Optional[float] = None
    first_pickup_longitude: Optional[float] = None
    last_dropoff_address: str
    last_dropoff_latitude: Optional[float] = None
    last_dropoff_longitude: Optional[float] = None
    notes: Optional[str] = None
    number_of_passengers: int
    trip_complete: Optional[bool] = None
    bookings: List[Booking]

    def assistance(self) -> MobilityAssistanceType:
        """Get mobility assistance type"""
        return MobilityAssistanceType.from_multiple(
            *[booking.assistance() for booking in self.bookings]
        )

    def short(self) -> str:
        """Short string representation for debugging"""
        bookings = "\n    ".join([booking.short() for booking in self.bookings])
        return f"T-{self.trip_id} {self.first_pickup_time}-{self.last_dropoff_time} [{self.assistance().value}]\n    {bookings}"


class Shuttle(BaseModel):
    """Shuttle model representing a vehicle with assigned trips"""

    shuttle_name: str
    shuttle_id: Optional[str] = None
    shuttle_make: Optional[str] = None
    shuttle_model: Optional[str] = None
    shuttle_color: Optional[str] = None
    shuttle_license_plate: Optional[str] = None
    shuttle_wheelchair: Optional[str] = None

    driver_id: Optional[str] = None
    driver_firstname: Optional[str] = None
    driver_lastname: Optional[str] = None
    driver_team_id: Optional[str] = None
    driver_team_name: Optional[str] = None
    driver_team: Optional[str] = None

    trips: List[Trip]

    def assistance(self) -> MobilityAssistanceType:
        """Get mobility assistance type"""
        if not self.shuttle_wheelchair:
            return MobilityAssistanceType.AMBULATORY
        return MobilityAssistanceType.from_string(self.shuttle_wheelchair)

    def short(self) -> str:
        """Short string representation for debugging"""
        trips = "\n  ".join([trip.short() for trip in self.trips])
        return f"S-{self.shuttle_id or ''} {self.shuttle_name} [{self.assistance().value}]\n  {trips}"


class Optimization(BaseModel):
    """Objectives model representing the optimization objectives"""

    # constraints
    chain_bookings_for_same_passenger: bool = Field(default=True)

    # objectives
    minimize_vehicles: bool = Field(default=True)
    minimize_total_duration: bool = Field(default=False)


class ScheduleRequest(BaseModel):
    """Schedule request model"""

    date: str  # "Month Day, Year" format
    debug: Optional[bool] = None

    before_pickup_time: Optional[int] = None  # seconds
    after_pickup_time: Optional[int] = None  # seconds
    pickup_loading_time: Optional[int] = None  # seconds
    dropoff_unloading_time: Optional[int] = None  # seconds
    bookings: List[Booking] = Field(default_factory=list)

    optimization: Optional[Optimization] = None
    program_name: Optional[str] = None


class ScheduleResultData(BaseModel):
    """Schedule result data"""

    vehicle_trip_list: List[Shuttle]


class ScheduleResult(BaseModel):
    """Auto scheduling result"""

    status: str
    error_code: int
    message: str
    data: ScheduleResultData


class ScheduleResponse(BaseModel):
    """Auto scheduling response"""

    result: ScheduleResult
