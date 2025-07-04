from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.program import Program, ProgramCRUD, Vehicle
from app.services.database import get_program_crud

router = APIRouter(prefix="/api/program", tags=["program"])


@router.get("/", response_model=List[Program])
async def get_programs(crud: ProgramCRUD = Depends(get_program_crud)):
    """Get all programs"""
    programs = await crud.get_programs()
    return programs


@router.get("/{program_id}", response_model=Program)
async def get_program(program_id: str, crud: ProgramCRUD = Depends(get_program_crud)):
    """Get a program by ID"""
    program = await crud.get_program_by_id(program_id)
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    return program


@router.post("/", response_model=Program, status_code=status.HTTP_201_CREATED)
async def create_program(
    program: Program, crud: ProgramCRUD = Depends(get_program_crud)
):
    """Create a new program"""
    try:
        created_program = await crud.create_program(program)
        return created_program
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{program_id}", response_model=Program)
async def update_program(
    program_id: str,
    program_update: Program,
    crud: ProgramCRUD = Depends(get_program_crud),
):
    """Update a program"""
    try:
        updated_program = await crud.update_program(program_id, program_update)
        if not updated_program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Program not found",
            )

        return updated_program
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{program_id}")
async def delete_program(
    program_id: str, crud: ProgramCRUD = Depends(get_program_crud)
):
    """Delete a program"""
    program = await crud.get_program_by_id(program_id)
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    deleted = await crud.delete_program(program_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete program",
        )

    return {"message": "Program deleted successfully"}


@router.post(
    "/{program_id}/vehicles",
    response_model=Program,
    status_code=status.HTTP_201_CREATED,
)
async def add_vehicle_to_program(
    program_id: str, vehicle: Vehicle, crud: ProgramCRUD = Depends(get_program_crud)
):
    """Add a vehicle to a program"""
    # Check if program exists
    existing_program = await crud.get_program_by_id(program_id)
    if not existing_program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    updated_program = await crud.add_vehicle_to_program(program_id, vehicle)
    if not updated_program:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add vehicle to program",
        )

    return updated_program


@router.put("/{program_id}/vehicles/{vehicle_id}", response_model=Program)
async def update_vehicle_in_program(
    program_id: str,
    vehicle_id: str,
    vehicle_update: Vehicle,
    crud: ProgramCRUD = Depends(get_program_crud),
):
    """Update a vehicle in a program"""
    # Check if program exists
    existing_program = await crud.get_program_by_id(program_id)
    if not existing_program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    # Check if vehicle exists in program
    vehicle_exists = any(v.id == vehicle_id for v in existing_program.vehicles)
    if not vehicle_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    updated_program = await crud.update_vehicle_in_program(
        program_id, vehicle_id, vehicle_update
    )
    if not updated_program:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update vehicle",
        )

    return updated_program


@router.delete("/{program_id}/vehicles/{vehicle_id}", response_model=Program)
async def delete_vehicle_from_program(
    program_id: str, vehicle_id: str, crud: ProgramCRUD = Depends(get_program_crud)
):
    """Delete a vehicle from a program"""
    # Check if program exists
    existing_program = await crud.get_program_by_id(program_id)
    if not existing_program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    # Check if vehicle exists in program
    vehicle_exists = any(v.id == vehicle_id for v in existing_program.vehicles)
    if not vehicle_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    updated_program = await crud.delete_vehicle_from_program(program_id, vehicle_id)
    if not updated_program:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete vehicle",
        )

    return updated_program
