from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from typing_extensions import Annotated
from datetime import datetime
from bson import ObjectId
from pydantic.functional_validators import BeforeValidator

# Represents an ObjectId field in the database.
# It will be represented as a `str` on the model so that it can be serialized to JSON.
PyObjectId = Annotated[str, BeforeValidator(str)]

# Vehicle Models
class VehicleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    mobility_assistance: List[Literal["ambulatory", "wheelchair", "stretcher"]] = Field(...)
    capacity: int = Field(default=1, ge=1, le=50)
    license_plate: Optional[str] = Field(None, max_length=20)

class VehicleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    mobility_assistance: Optional[List[Literal["ambulatory", "wheelchair", "stretcher"]]] = Field(None)
    capacity: Optional[int] = Field(None, ge=1, le=50)
    license_plate: Optional[str] = Field(None, max_length=20)

class Vehicle(VehicleBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "name": "Ambulance 1",
                "mobility_assistance": ["wheelchair", "stretcher"],
                "capacity": 2,
                "license_plate": "AMB001"
            }
        }
    }

# Program Models
class ProgramBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class ProgramCreate(ProgramBase):
    vehicles: List[Vehicle] = Field(default_factory=list)

class ProgramUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    vehicles: Optional[List[Vehicle]] = None

class Program(ProgramBase):
    id: PyObjectId = Field(..., alias="_id")
    vehicles: List[Vehicle] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "name": "Emergency Transport Program",
                "vehicles": [
                    {
                        "id": "507f1f77bcf86cd799439012",
                        "name": "Ambulance 1",
                        "mobility_assistance": ["wheelchair", "stretcher"],
                        "capacity": 2,
                        "license_plate": "AMB001"
                    }
                ],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    }

# Direction Models
class Direction(BaseModel):
    distance_in_meter: int
    duration_in_seconds: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "distance_in_meter": 15420,
                "duration_in_seconds": 1200
            }
        }
    }
