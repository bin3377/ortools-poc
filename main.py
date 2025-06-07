from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from scheduler import VehicleScheduler
import uvicorn

app = FastAPI(title="Vehicle Scheduling System")

class Seat(BaseModel):
    regular: int
    wheelchair: int
    stretcher: int

class Vehicle(BaseModel):
    id: str
    seats: Seat
    hourly_rate: float
    start_location: str
    start_time: int  # 24小时制，例如：8表示8:00

class Booking(BaseModel):
    id: str
    pickup_time: int  # 24小时制
    pickup_location: str
    dropoff_location: str
    required_seats: Seat
    unloading_time: int  # 分钟

class ScheduleRequest(BaseModel):
    vehicles: List[Vehicle]
    bookings: List[Booking]

class BookingSchedule(BaseModel):
    booking_id: str
    start_time: int
    pickup_location: str
    dropoff_location: str

class VehicleSchedule(BaseModel):
    vehicle_id: str
    bookings: List[BookingSchedule]

class ScheduleResponse(BaseModel):
    schedules: List[VehicleSchedule]
    total_cost: float
    error: Optional[str] = None

@app.post("/schedule", response_model=ScheduleResponse)
async def create_schedule(request: ScheduleRequest = Body(...)):
    try:
        scheduler = VehicleScheduler()
        result = scheduler.schedule(request.vehicles, request.bookings)
        return ScheduleResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 