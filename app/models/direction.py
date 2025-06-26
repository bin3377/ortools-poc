from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel


# Direction Models
class Direction(BaseModel):
    distance_in_meter: int
    duration_in_seconds: int

    model_config = {
        "json_schema_extra": {
            "example": {"distance_in_meter": 15420, "duration_in_seconds": 1200}
        }
    }


class DirectionCRUD:
    def __init__(self, database):
        self.collection = database["directions"]

    def generate_key(self, origin: str, destination: str) -> str:
        return f"{origin}|{destination}"

    async def get_direction(self, origin: str, destination: str) -> Optional[dict]:
        """Get a direction by origin and destination"""
        doc = await self.collection.find_one(
            {"key": self.generate_key(origin, destination)}
        )
        if doc:
            # Return only the direction data, not the full document
            return {
                "distance_in_meter": doc.get("distance_in_meter"),
                "duration_in_seconds": doc.get("duration_in_seconds"),
            }
        return None

    async def create_direction(
        self, origin: str, destination: str, data: dict
    ) -> Optional[dict]:
        """Create a new direction"""
        key = self.generate_key(origin, destination)
        doc = {
            "key": key,
            "distance_in_meter": data["distance_in_meter"],
            "duration_in_seconds": data["duration_in_seconds"],
            "created_at": datetime.now(timezone.utc),
        }

        # Use upsert to update if exists or create if not
        await self.collection.update_one({"key": key}, {"$set": doc}, upsert=True)

        return data
