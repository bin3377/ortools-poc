from fastapi import APIRouter, Depends, HTTPException, status

from app.models.task import CreateTaskResponse, ScheduleRequest, Task, TaskCRUD
from app.services.database import get_task_crud

router = APIRouter(prefix="/api/task", tags=["task"])


@router.get("/{task_id}", response_model=Task)
async def get_task(id: str, crud: TaskCRUD = Depends(get_task_crud)):
    """Get a task by ID"""
    task = await crud.get_task(id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


@router.post(
    "/", response_model=CreateTaskResponse, status_code=status.HTTP_201_CREATED
)
async def create_task(
    request: ScheduleRequest, crud: TaskCRUD = Depends(get_task_crud)
):
    """Create a new task"""
    try:
        created_task = await crud.create_task(request)
        return created_task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
