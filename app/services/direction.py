import os
from datetime import datetime
from typing import Optional

import googlemaps
from dotenv import load_dotenv

from app.models.direction import Direction
from app.services.database import get_direction_crud

load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


async def get_direction(
    origin: str, destination: str, departure_time: Optional[datetime] = None
) -> Direction:
    """
    Convenience function to get direction between two locations.

    Args:
        origin: Starting location
        destination: Ending location

    Returns:
        Direction: Direction object with distance, duration

    Raises:
        ValueError: If no route is found
        googlemaps.exceptions.ApiError: If Google Maps API error occurs
    """
    # Try to get from cache first
    crud = await get_direction_crud()
    cached_direction = await crud.get_direction(origin, destination)
    if cached_direction:
        return Direction(**cached_direction)

    # If not in cache, call Google Maps API
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    directions = gmaps.directions(
        origin, destination, mode="driving", departure_time=departure_time
    )

    if not directions:
        raise ValueError("No route found between the specified locations")

    leg = directions[0]["legs"][0]
    direction_data = {
        "distance_in_meter": leg["distance"]["value"],
        "duration_in_sec": leg["duration"]["value"],
        "raw_response": directions,  # Store the full directions response as dict
    }

    # Save to cache
    await crud.create_direction(origin, destination, direction_data)

    return Direction(**direction_data)
