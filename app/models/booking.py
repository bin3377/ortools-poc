from typing import Any, List, Optional

from pydantic import BaseModel


class BookingBase(BaseModel):
    booking_id: str
    mobility_assistance: List[str]
    program_name: str
    pickup_address: str
    dropoff_address: str


class Booking(BookingBase):
    """Booking model representing a ride booking"""

    passenger_id: str
    passenger_firstname: str
    passenger_lastname: str
    additional_passenger: int

    pickup_time: str  # HH:mm format
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
