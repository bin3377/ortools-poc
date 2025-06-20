from fastapi import APIRouter, HTTPException, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
import os
import googlemaps
from dotenv import load_dotenv

from app.database import get_database
from app.models import Direction
from app.crud import DirectionCRUD

load_dotenv()

router = APIRouter(prefix="/api/directions", tags=["directions"])

async def get_direction_crud(db: AsyncIOMotorDatabase = Depends(get_database)) -> DirectionCRUD:
    return DirectionCRUD(db)

@router.get("/{origin}/{destination}", response_model=Direction)
async def get_direction(
    origin: str,
    destination: str,
    crud: DirectionCRUD = Depends(get_direction_crud)
):
    """Get direction information between origin and destination"""
    try:
        # Try to get from cache first
        cached_direction = await crud.get_direction(origin, destination)
        if cached_direction:
            return Direction(**cached_direction)

        # If not in cache, call Google Maps API
        gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
        directions = gmaps.directions(origin, destination, mode="driving")

        if not directions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No route found between the specified locations"
            )

        leg = directions[0]["legs"][0]
        direction_data = {
            "distance_in_meter": leg["distance"]["value"],
            "duration_in_seconds": leg["duration"]["value"],
        }

        # Save to cache
        await crud.create_direction(origin, destination, direction_data)

        return Direction(**direction_data)

    except googlemaps.exceptions.ApiError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google Maps API error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )