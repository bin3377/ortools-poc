"""
Direction service for handling direction-related operations.
This service can be reused across different parts of the application.
"""

import os
import googlemaps
from dotenv import load_dotenv

from app.models import Direction
from app.crud import DirectionCRUD
from app.database import get_database

load_dotenv()

async def get_direction(origin: str, destination: str) -> Direction:
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
    # Get database connection
    db = await get_database()
    crud = DirectionCRUD(db)
    
    # Try to get from cache first
    cached_direction = await crud.get_direction(origin, destination)
    if cached_direction:
        return Direction(**cached_direction)

    # If not in cache, call Google Maps API
    gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
    directions = gmaps.directions(origin, destination, mode="driving")
    
    if not directions:
        raise ValueError("No route found between the specified locations")

    leg = directions[0]["legs"][0]
    direction_data = {
        "distance_in_meter": leg["distance"]["value"],
        "duration_in_seconds": leg["duration"]["value"],
        "raw_response": directions,  # Store the full directions response as dict
    }

    # Save to cache
    await crud.create_direction(origin, destination, direction_data)
    
    return Direction(**direction_data)
