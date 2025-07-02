from fastapi import APIRouter, HTTPException, status

from app.models.inout import ScheduleRequest, ScheduleResponse
from app.services.schedule import schedule

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_200_OK)
async def create_task(request: ScheduleRequest):
    """Schedule trips syncronously."""
    try:
        return await schedule(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
