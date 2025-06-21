from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Annotated
import googlemaps

from pymongo import AsyncMongoClient

from app.internal.models import Direction
from app.internal.direction import get_direction
from app.internal.crud import DirectionCRUD
from app.internal.database import get_database

router = APIRouter(prefix="/api/directions", tags=["directions"])


async def get_direction_crud(
    db: AsyncMongoClient = Depends(get_database),
) -> DirectionCRUD:
    return DirectionCRUD(db)


@router.get("/", response_model=Direction)
async def get_direction_endpoint(
    origin: Annotated[str, Query(alias="from", description="Starting location")],
    destination: Annotated[str, Query(alias="to", description="Ending location")],
    crud: DirectionCRUD = Depends(get_direction_crud),
):
    """Get direction information between origin and destination"""
    try:
        return await get_direction(crud, origin, destination)

    except (ValueError, googlemaps.exceptions.ApiError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google Maps API error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )
