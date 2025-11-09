"""Schedule API endpoints for automated batch processing."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import verify_admin
from app.models import (
    Schedule,
    ScheduleCreateRequest,
    ScheduleListItem,
    ScheduleRun,
    ScheduleUpdateRequest,
    TriggerType,
)
from app.services.scheduler_service import scheduler_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=list[ScheduleListItem])
async def list_schedules(
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    trigger_type: Optional[TriggerType] = Query(None, description="Filter by trigger type"),
    _admin: dict = Depends(verify_admin),
) -> list[ScheduleListItem]:
    """
    List all schedules.

    Args:
        enabled: Filter by enabled status (optional)
        trigger_type: Filter by trigger type (optional)

    Returns:
        List of schedule items
    """
    try:
        schedules = await scheduler_service.list_schedules(
            enabled=enabled,
            trigger_type=trigger_type,
        )

        logger.info(f"Listed {len(schedules)} schedules")
        return schedules

    except Exception as e:
        logger.error(f"Failed to list schedules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list schedules: {e}")


@router.get("/{schedule_id}", response_model=Schedule)
async def get_schedule(
    schedule_id: UUID,
    _admin: dict = Depends(verify_admin),
) -> Schedule:
    """
    Get schedule by ID.

    Args:
        schedule_id: Schedule UUID

    Returns:
        Schedule details

    Raises:
        404: Schedule not found
    """
    try:
        schedule = await scheduler_service.get_schedule(schedule_id)

        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        logger.info(f"Retrieved schedule {schedule_id}")
        return schedule

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {e}")


@router.post("", response_model=Schedule, status_code=201)
async def create_schedule(
    request: ScheduleCreateRequest,
    _admin: dict = Depends(verify_admin),
) -> Schedule:
    """
    Create a new schedule.

    Args:
        request: Schedule creation request

    Returns:
        Created schedule

    Raises:
        400: Invalid cron expression
    """
    try:
        schedule = await scheduler_service.create_schedule(request)

        logger.info(f"Created schedule '{schedule.name}' (ID: {schedule.schedule_id})")
        return schedule

    except ValueError as e:
        logger.warning(f"Invalid schedule request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {e}")


@router.put("/{schedule_id}", response_model=Schedule)
async def update_schedule(
    schedule_id: UUID,
    request: ScheduleUpdateRequest,
    _admin: dict = Depends(verify_admin),
) -> Schedule:
    """
    Update an existing schedule.

    Args:
        schedule_id: Schedule UUID
        request: Schedule update request

    Returns:
        Updated schedule

    Raises:
        404: Schedule not found
        400: Invalid cron expression
    """
    try:
        schedule = await scheduler_service.update_schedule(schedule_id, request)

        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        logger.info(f"Updated schedule {schedule_id}")
        return schedule

    except ValueError as e:
        logger.warning(f"Invalid schedule update: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {e}")


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: UUID,
    _admin: dict = Depends(verify_admin),
) -> None:
    """
    Delete a schedule.

    Args:
        schedule_id: Schedule UUID

    Raises:
        404: Schedule not found
    """
    try:
        success = await scheduler_service.delete_schedule(schedule_id)

        if not success:
            raise HTTPException(status_code=404, detail="Schedule not found")

        logger.info(f"Deleted schedule {schedule_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {e}")


@router.post("/{schedule_id}/run", status_code=202)
async def run_schedule(
    schedule_id: UUID,
    _admin: dict = Depends(verify_admin),
) -> dict:
    """
    Manually trigger schedule execution.

    Args:
        schedule_id: Schedule UUID

    Returns:
        Execution confirmation

    Raises:
        404: Schedule not found
    """
    try:
        success = await scheduler_service.execute_schedule_now(schedule_id)

        if not success:
            raise HTTPException(status_code=404, detail="Schedule not found")

        logger.info(f"Manually triggered schedule {schedule_id}")
        return {
            "message": "Schedule execution triggered",
            "schedule_id": str(schedule_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run schedule: {e}")


@router.get("/{schedule_id}/history", response_model=list[ScheduleRun])
async def get_schedule_history(
    schedule_id: UUID,
    limit: int = Query(50, ge=1, le=100, description="Number of runs to return"),
    offset: int = Query(0, ge=0, description="Number of runs to skip"),
    _admin: dict = Depends(verify_admin),
) -> list[ScheduleRun]:
    """
    Get execution history for a schedule.

    Args:
        schedule_id: Schedule UUID
        limit: Number of runs to return (1-100, default: 50)
        offset: Number of runs to skip (default: 0)

    Returns:
        List of schedule runs
    """
    try:
        history = await scheduler_service.get_schedule_history(
            schedule_id,
            limit=limit,
            offset=offset,
        )

        logger.info(f"Retrieved {len(history)} history entries for schedule {schedule_id}")
        return history

    except Exception as e:
        logger.error(f"Failed to get schedule history {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {e}")
