from fastapi import APIRouter, HTTPException, status, Query
from typing import Annotated
import googlemaps

from app.models import Direction
from app.services import direction_service

router = APIRouter(prefix="/api/directions", tags=["directions"])

@router.get("/", response_model=Direction)
async def get_direction_endpoint(
    origin: Annotated[str, Query(alias="from", description="Starting location")],
    destination: Annotated[str, Query(alias="to", description="Ending location")]
):
    """Get direction information between origin and destination"""
    try:
        direction = await direction_service.get_direction(origin, destination)
        return direction

    except (ValueError, googlemaps.exceptions.ApiError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google Maps API error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )