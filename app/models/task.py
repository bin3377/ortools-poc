from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from nanoid import generate
from pydantic import BaseModel, Field

from app.models.inout import ScheduleRequest, ScheduleResponse


class TaskStatus(str, Enum):
    """Task status enumeration"""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Task(BaseModel):
    """Base task model"""

    id: str = Field(
        default_factory=lambda: generate(
            alphabet="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            size=10,
        )
    )
    request: ScheduleRequest
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = None
    response: Optional[ScheduleResponse] = None


class CreateTaskResponse(BaseModel):
    """Task creation response"""

    id: str


class TaskCRUD:
    def __init__(self, database):
        self.collection = database["tasks"]

    async def create_task(self, request: ScheduleRequest) -> CreateTaskResponse:
        """Create a new task"""
        task = Task(
            request=request,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await self.collection.insert_one(task.model_dump())
        return CreateTaskResponse(id=task.id)

    async def get_task(self, id: str) -> Optional[Task]:
        """Get a task by ID"""
        task_dict = await self.collection.find_one({"id": id})
        if task_dict:
            return Task(**task_dict)
        return None

    async def get_pending_tasks(self, limit: int = 10) -> List[str]:
        """Get pending tasks and mark them as processing"""

        # Find pending tasks
        pending_docs = (
            await self.collection.find({"status": TaskStatus.PENDING.value})
            .limit(limit)
            .to_list(length=limit)
        )

        if not pending_docs:
            return []

        # Extract IDs
        ids = [doc["id"] for doc in pending_docs]

        # Mark as processing
        await self.collection.update_many(
            {"id": {"$in": ids}}, {"$set": {"status": TaskStatus.PROCESSING.value}}
        )

        return ids

    async def update_task(
        self,
        id: str,
        status: TaskStatus,
        response: Optional[ScheduleResponse] = None,
        error_message: Optional[str] = None,
    ):
        """Update task status and optional response/error"""

        update_data = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }

        if response:
            update_data["response"] = response.model_dump()

        if error_message:
            update_data["error_message"] = error_message

        await self.collection.update_one({"id": id}, {"$set": update_data})
