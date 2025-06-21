from typing import List, Optional
from bson import ObjectId
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone

from app.internal.models import Program, ProgramCreate, ProgramUpdate, Vehicle, VehicleUpdate

class DirectionCRUD:
    def __init__(self, database):
        self.collection = database["directions"]

    def generate_key(self, origin: str, destination: str) -> str:
        return f"{origin}|{destination}"

    async def get_direction(self, origin: str, destination: str) -> Optional[dict]:
        """Get a direction by origin and destination"""
        doc = await self.collection.find_one({"key": self.generate_key(origin, destination)})
        if doc:
            # Return only the direction data, not the full document
            return {
                "distance_in_meter": doc.get("distance_in_meter"),
                "duration_in_seconds": doc.get("duration_in_seconds"),
            }
        return None

    async def create_direction(self, origin: str, destination: str, data: dict) -> Optional[dict]:
        """Create a new direction"""
        key = self.generate_key(origin, destination)
        doc = {
            "key": key,
            "distance_in_meter": data["distance_in_meter"],
            "duration_in_seconds": data["duration_in_seconds"],
            "created_at": datetime.now(timezone.utc),
        }

        # Use upsert to update if exists or create if not
        await self.collection.update_one(
            {"key": key},
            {"$set": doc},
            upsert=True
        )

        return data

class ProgramCRUD:
    def __init__(self, database: AsyncMongoClient):
        self.collection = database["programs"]

    async def create_program(self, program: ProgramCreate) -> Program:
        """Create a new program"""
        program_dict = {
            "name": program.name,
            "vehicles": [vehicle.model_dump() for vehicle in program.vehicles],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Ensure each vehicle has an id
        for vehicle in program_dict["vehicles"]:
            if "id" not in vehicle:
                vehicle["id"] = str(ObjectId())
        
        try:
            result = await self.collection.insert_one(program_dict)
            created_program = await self.collection.find_one({"_id": result.inserted_id})
            return Program(**created_program)
        except DuplicateKeyError:
            raise ValueError("Program name already exists")

    async def get_programs(self) -> List[Program]:
        """Get all programs"""
        cursor = self.collection.find({}).sort("created_at", -1)
        programs = []
        async for program_dict in cursor:
            programs.append(Program(**program_dict))
            print(Program(**program_dict))
        return programs

    async def get_program_by_id(self, program_id: str) -> Optional[Program]:
        """Get a program by ID"""
        if not ObjectId.is_valid(program_id):
            return None
        
        program_dict = await self.collection.find_one({"_id": ObjectId(program_id)})
        if program_dict:
            return Program(**program_dict)
        return None

    async def update_program(self, program_id: str, program_update: ProgramUpdate) -> Optional[Program]:
        """Update a program"""
        if not ObjectId.is_valid(program_id):
            return None

        update_dict = {"updated_at": datetime.now(timezone.utc)}
        
        # Only update fields that are provided
        if program_update.name is not None:
            update_dict["name"] = program_update.name
        if program_update.vehicles is not None:
            update_dict["vehicles"] = [vehicle.model_dump() for vehicle in program_update.vehicles]

        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(program_id)},
                {"$set": update_dict}
            )
            
            if result.modified_count == 1:
                updated_program = await self.collection.find_one({"_id": ObjectId(program_id)})
                return Program(**updated_program)
            return None
        except DuplicateKeyError:
            raise ValueError("Program name already exists")

    async def delete_program(self, program_id: str) -> bool:
        """Delete a program"""
        if not ObjectId.is_valid(program_id):
            return False

        result = await self.collection.delete_one({"_id": ObjectId(program_id)})
        return result.deleted_count == 1

    async def add_vehicle_to_program(self, program_id: str, vehicle: Vehicle) -> Optional[Program]:
        """Add a vehicle to a program"""
        if not ObjectId.is_valid(program_id):
            print("Invalid program ID")
            return None

        vehicle_dict = vehicle.model_dump()
        vehicle_dict["id"] = str(ObjectId())

        result = await self.collection.update_one(
            {"_id": ObjectId(program_id)},
            {
                "$push": {"vehicles": vehicle_dict},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )

        if result.modified_count == 1:
            updated_program = await self.collection.find_one({"_id": ObjectId(program_id)})
            return Program(**updated_program)
        return None

    async def update_vehicle_in_program(self, program_id: str, vehicle_id: str, vehicle_update: VehicleUpdate) -> Optional[Program]:
        """Update a vehicle in a program"""
        if not ObjectId.is_valid(program_id):
            print("Invalid program ID")
            return None

        # Build update fields for the vehicle
        update_fields = {}
        if vehicle_update.name is not None:
            update_fields["vehicles.$.name"] = vehicle_update.name
        if vehicle_update.mobility_assistance is not None:
            update_fields["vehicles.$.mobility_assistance"] = vehicle_update.mobility_assistance
        if vehicle_update.capacity is not None:
            update_fields["vehicles.$.capacity"] = vehicle_update.capacity
        if vehicle_update.license_plate is not None:
            update_fields["vehicles.$.license_plate"] = vehicle_update.license_plate
        
        update_fields["updated_at"] = datetime.now(timezone.utc)

        result = await self.collection.update_one(
            {
                "_id": ObjectId(program_id),
                "vehicles.id": vehicle_id
            },
            {"$set": update_fields}
        )

        if result.modified_count == 1:
            updated_program = await self.collection.find_one({"_id": ObjectId(program_id)})
            return Program(**updated_program)
        return None

    async def delete_vehicle_from_program(self, program_id: str, vehicle_id: str) -> Optional[Program]:
        """Delete a vehicle from a program"""
        if not ObjectId.is_valid(program_id):
            return None

        result = await self.collection.update_one(
            {"_id": ObjectId(program_id)},
            {
                "$pull": {"vehicles": {"id": vehicle_id}},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )

        if result.modified_count == 1:
            updated_program = await self.collection.find_one({"_id": ObjectId(program_id)})
            return Program(**updated_program)
        return None