from datetime import datetime, timezone
from typing import List, Optional

from nanoid import generate
from pydantic import BaseModel, Field
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError

from app.models.mobility_assistance import MobilityAssistanceType


class Vehicle(BaseModel):
    id: str = Field(default_factory=lambda: generate(size=10))
    name: str = Field(..., min_length=1, max_length=100)
    mobility_assistance: List[MobilityAssistanceType] = Field(..., default_factory=list)


class Program(BaseModel):
    id: str = Field(default_factory=lambda: generate(size=10))
    name: str = Field(..., min_length=1, max_length=100)
    vehicles: List[Vehicle] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ProgramCRUD:
    def __init__(self, database: AsyncMongoClient):
        self.collection = database["programs"]

    async def create_program(self, program: Program) -> Program:
        """Create a new program"""
        try:
            await self.collection.insert_one(program.model_dump())
            created_program = await self.collection.find_one({"id": program.id})
            return Program(**created_program)
        except DuplicateKeyError:
            raise ValueError("Program name already exists")

    async def get_programs(self) -> List[Program]:
        """Get all programs"""
        cursor = self.collection.find({}).sort("created_at", -1)
        programs = []
        async for program_dict in cursor:
            programs.append(Program(**program_dict))
        return programs

    async def get_program_by_id(self, id: str) -> Optional[Program]:
        """Get a program by ID"""
        program_dict = await self.collection.find_one({"id": id})
        if program_dict:
            return Program(**program_dict)
        return None

    async def delete_program(self, id: str) -> bool:
        """Delete a program"""
        result = await self.collection.delete_one({"id": id})
        return result.deleted_count == 1

    async def update_program(
        self, id: str, program_update: Program
    ) -> Optional[Program]:
        """Update a program"""
        program = await self.get_program_by_id(id)
        if not program:
            return None

        update_dict = {"updated_at": datetime.now(timezone.utc)}

        # Only update fields that are provided
        if program_update.name is not None:
            update_dict["name"] = program_update.name
        if program_update.vehicles is not None:
            update_dict["vehicles"] = [
                vehicle.model_dump() for vehicle in program_update.vehicles
            ]

        try:
            result = await self.collection.update_one({"id": id}, {"$set": update_dict})

            if result.modified_count == 1:
                updated_program = await self.collection.find_one({"id": id})
                return Program(**updated_program)
            return None
        except DuplicateKeyError:
            raise ValueError("Program name already exists")

    async def add_vehicle_to_program(
        self, program_id: str, vehicle: Vehicle
    ) -> Optional[Program]:
        """Add a vehicle to a program"""
        program = await self.get_program_by_id(program_id)
        if not program:
            return None

        vehicle_dict = vehicle.model_dump()

        result = await self.collection.update_one(
            {"id": program_id},
            {
                "$push": {"vehicles": vehicle_dict},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )

        if result.modified_count == 1:
            updated_program = await self.collection.find_one({"id": program_id})
            return Program(**updated_program)
        return None

    async def delete_vehicle_from_program(
        self, program_id: str, vehicle_id: str
    ) -> Optional[Program]:
        """Delete a vehicle from a program"""
        program = await self.get_program_by_id(program_id)
        if not program:
            return None

        result = await self.collection.update_one(
            {"id": program_id},
            {
                "$pull": {"vehicles": {"id": vehicle_id}},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )

        if result.modified_count == 1:
            updated_program = await self.collection.find_one({"id": program_id})
            return Program(**updated_program)
        return None

    async def update_vehicle_in_program(
        self, program_id: str, vehicle_id: str, vehicle_update: Vehicle
    ) -> Optional[Program]:
        """Update a vehicle in a program"""
        program = await self.get_program_by_id(program_id)
        if not program:
            return None

        vehicle_update_dict = vehicle_update.model_dump()

        result = await self.collection.update_one(
            {"id": program_id, "vehicles.id": vehicle_id},
            {
                "$set": {
                    "vehicles.$": vehicle_update_dict,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        if result.modified_count == 1:
            updated_program = await self.collection.find_one({"id": program_id})
            return Program(**updated_program)
        return None
