"""Scheduler service for automated batch processing."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from app.models import (
    Schedule,
    ScheduleCreateRequest,
    ScheduleListItem,
    ScheduleRun,
    ScheduleStatus,
    ScheduleUpdateRequest,
    TriggerType,
)

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled batch processing jobs using APScheduler."""

    def __init__(self, storage_dir: str = "data/schedules"):
        """
        Initialize the scheduler service.

        Args:
            storage_dir: Directory for storing schedule metadata and history
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.schedules_file = self.storage_dir / "schedules.json"
        self.history_dir = self.storage_dir / "history"
        self.history_dir.mkdir(exist_ok=True)

        # Initialize APScheduler
        jobstores = {"default": MemoryJobStore()}
        self.scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="UTC")
        self.scheduler.start()

        # Load existing schedules
        self._load_schedules()

        logger.info("SchedulerService initialized")

    def _load_schedules(self) -> None:
        """Load existing schedules from disk and add them to the scheduler."""
        if not self.schedules_file.exists():
            logger.info("No existing schedules found")
            return

        try:
            with open(self.schedules_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            schedules = [Schedule(**s) for s in data.get("schedules", [])]
            logger.info(f"Loaded {len(schedules)} schedules from disk")

            # Add enabled schedules to APScheduler
            for schedule in schedules:
                if schedule.enabled:
                    self._add_job_to_scheduler(schedule)

        except Exception as e:
            logger.error(f"Failed to load schedules: {e}")

    def _save_schedules(self) -> None:
        """Save all schedules to disk."""
        try:
            schedules = list(self._get_all_schedules().values())
            data = {
                "schedules": [s.model_dump(mode="json") for s in schedules],
                "updated_at": datetime.now(UTC).isoformat(),
            }

            with open(self.schedules_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved {len(schedules)} schedules to disk")

        except Exception as e:
            logger.error(f"Failed to save schedules: {e}")

    def _get_all_schedules(self) -> dict[UUID, Schedule]:
        """Get all schedules from memory."""
        # In production, this would load from database
        # For now, we load from file each time
        if not self.schedules_file.exists():
            return {}

        try:
            with open(self.schedules_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            schedules = {UUID(s["schedule_id"]): Schedule(**s) for s in data.get("schedules", [])}
            return schedules

        except Exception as e:
            logger.error(f"Failed to load schedules: {e}")
            return {}

    def _add_job_to_scheduler(self, schedule: Schedule) -> None:
        """
        Add a schedule as a job to APScheduler.

        Args:
            schedule: Schedule to add
        """
        try:
            # Parse cron expression
            trigger = CronTrigger.from_crontab(schedule.cron_expression, timezone="UTC")

            # Add job to scheduler
            self.scheduler.add_job(
                func=self._execute_schedule,
                trigger=trigger,
                args=[schedule.schedule_id],
                id=str(schedule.schedule_id),
                name=schedule.name,
                replace_existing=True,
            )

            # Update next run time
            job = self.scheduler.get_job(str(schedule.schedule_id))
            if job and job.next_run_time:
                schedule.next_run_time = job.next_run_time

            logger.info(
                f"Added job for schedule '{schedule.name}' (ID: {schedule.schedule_id}), "
                f"next run: {schedule.next_run_time}"
            )

        except Exception as e:
            logger.error(f"Failed to add job for schedule {schedule.schedule_id}: {e}")
            raise

    def _remove_job_from_scheduler(self, schedule_id: UUID) -> None:
        """
        Remove a job from APScheduler.

        Args:
            schedule_id: Schedule ID to remove
        """
        try:
            self.scheduler.remove_job(str(schedule_id))
            logger.info(f"Removed job for schedule {schedule_id}")
        except Exception as e:
            logger.warning(f"Failed to remove job {schedule_id}: {e}")

    async def _execute_schedule(self, schedule_id: UUID) -> None:
        """
        Execute a scheduled job.

        Args:
            schedule_id: Schedule ID to execute
        """
        schedules = self._get_all_schedules()
        schedule = schedules.get(schedule_id)

        if not schedule:
            logger.error(f"Schedule {schedule_id} not found")
            return

        logger.info(f"Executing schedule '{schedule.name}' (ID: {schedule_id})")

        # Record execution start
        run_start = datetime.now(UTC)
        run = ScheduleRun(
            schedule_id=schedule_id,
            executed_at=run_start,
            status=ScheduleStatus.RUNNING,
        )

        try:
            # TODO: Implement actual batch processing execution
            # For now, just log the execution
            logger.info(
                f"Schedule execution for '{schedule.name}' - TODO: implement batch processing"
            )

            # Update run status
            run.status = ScheduleStatus.SUCCESS
            run.duration_seconds = (datetime.now(UTC) - run_start).total_seconds()

            # Update schedule metadata
            schedule.last_run_time = run_start
            schedule.last_run_status = ScheduleStatus.SUCCESS
            schedule.execution_count += 1

            # Save schedule history
            self._save_schedule_run(run)

            # Save updated schedule
            schedules[schedule_id] = schedule
            self._save_schedules()

            logger.info(
                f"Schedule '{schedule.name}' executed successfully in {run.duration_seconds:.2f}s"
            )

        except Exception as e:
            logger.error(f"Schedule execution failed for '{schedule.name}': {e}")

            # Update run status
            run.status = ScheduleStatus.FAILED
            run.error_message = str(e)
            run.duration_seconds = (datetime.now(UTC) - run_start).total_seconds()

            # Update schedule metadata
            schedule.last_run_time = run_start
            schedule.last_run_status = ScheduleStatus.FAILED

            # Save schedule history
            self._save_schedule_run(run)

            # Save updated schedule
            schedules[schedule_id] = schedule
            self._save_schedules()

    def _save_schedule_run(self, run: ScheduleRun) -> None:
        """
        Save schedule execution history.

        Args:
            run: Schedule run to save
        """
        try:
            # Create history file for this schedule
            history_file = self.history_dir / f"{run.schedule_id}.json"

            # Load existing history
            history = []
            if history_file.exists():
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)

            # Add new run (keep last 100 runs)
            history.insert(0, run.model_dump(mode="json"))
            history = history[:100]

            # Save history
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to save schedule run history: {e}")

    async def create_schedule(self, request: ScheduleCreateRequest) -> Schedule:
        """
        Create a new schedule.

        Args:
            request: Schedule creation request

        Returns:
            Created schedule

        Raises:
            ValueError: If cron expression is invalid
        """
        # Validate cron expression
        try:
            CronTrigger.from_crontab(request.cron_expression)
        except Exception as e:
            raise ValueError(f"Invalid cron expression: {e}")

        # Create schedule
        schedule = Schedule(
            name=request.name,
            description=request.description,
            cron_expression=request.cron_expression,
            enabled=request.enabled,
            trigger_type=request.trigger_type,
            trigger_config=request.trigger_config,
            notification_config=request.notification_config,
        )

        # Add to scheduler if enabled
        if schedule.enabled:
            self._add_job_to_scheduler(schedule)

        # Save to disk
        schedules = self._get_all_schedules()
        schedules[schedule.schedule_id] = schedule
        self._save_schedules()

        logger.info(f"Created schedule '{schedule.name}' (ID: {schedule.schedule_id})")

        return schedule

    async def get_schedule(self, schedule_id: UUID) -> Optional[Schedule]:
        """
        Get schedule by ID.

        Args:
            schedule_id: Schedule ID

        Returns:
            Schedule or None if not found
        """
        schedules = self._get_all_schedules()
        return schedules.get(schedule_id)

    async def list_schedules(
        self,
        enabled: Optional[bool] = None,
        trigger_type: Optional[TriggerType] = None,
    ) -> list[ScheduleListItem]:
        """
        List all schedules.

        Args:
            enabled: Filter by enabled status
            trigger_type: Filter by trigger type

        Returns:
            List of schedule items
        """
        schedules = self._get_all_schedules()

        # Filter schedules
        filtered = []
        for schedule in schedules.values():
            if enabled is not None and schedule.enabled != enabled:
                continue
            if trigger_type is not None and schedule.trigger_type != trigger_type:
                continue

            # Update next run time from scheduler
            if schedule.enabled:
                job = self.scheduler.get_job(str(schedule.schedule_id))
                if job and job.next_run_time:
                    schedule.next_run_time = job.next_run_time

            filtered.append(
                ScheduleListItem(
                    schedule_id=schedule.schedule_id,
                    name=schedule.name,
                    description=schedule.description,
                    cron_expression=schedule.cron_expression,
                    enabled=schedule.enabled,
                    trigger_type=schedule.trigger_type,
                    next_run_time=schedule.next_run_time,
                    last_run_time=schedule.last_run_time,
                    last_run_status=schedule.last_run_status,
                    execution_count=schedule.execution_count,
                )
            )

        # Sort by next run time (enabled schedules first)
        filtered.sort(
            key=lambda x: (not x.enabled, x.next_run_time or datetime.max.replace(tzinfo=UTC))
        )

        return filtered

    async def update_schedule(
        self, schedule_id: UUID, request: ScheduleUpdateRequest
    ) -> Optional[Schedule]:
        """
        Update an existing schedule.

        Args:
            schedule_id: Schedule ID
            request: Schedule update request

        Returns:
            Updated schedule or None if not found

        Raises:
            ValueError: If cron expression is invalid
        """
        schedules = self._get_all_schedules()
        schedule = schedules.get(schedule_id)

        if not schedule:
            return None

        # Validate cron expression if changed
        if request.cron_expression and request.cron_expression != schedule.cron_expression:
            try:
                CronTrigger.from_crontab(request.cron_expression)
            except Exception as e:
                raise ValueError(f"Invalid cron expression: {e}")

        # Update fields
        if request.name is not None:
            schedule.name = request.name
        if request.description is not None:
            schedule.description = request.description
        if request.cron_expression is not None:
            schedule.cron_expression = request.cron_expression
        if request.trigger_type is not None:
            schedule.trigger_type = request.trigger_type
        if request.trigger_config is not None:
            schedule.trigger_config = request.trigger_config
        if request.notification_config is not None:
            schedule.notification_config = request.notification_config

        # Handle enabled status change
        if request.enabled is not None and request.enabled != schedule.enabled:
            schedule.enabled = request.enabled

            if schedule.enabled:
                # Add to scheduler
                self._add_job_to_scheduler(schedule)
            else:
                # Remove from scheduler
                self._remove_job_from_scheduler(schedule_id)
                schedule.next_run_time = None

        elif schedule.enabled:
            # Reschedule if cron expression changed
            self._remove_job_from_scheduler(schedule_id)
            self._add_job_to_scheduler(schedule)

        schedule.updated_at = datetime.now(UTC)

        # Save to disk
        schedules[schedule_id] = schedule
        self._save_schedules()

        logger.info(f"Updated schedule '{schedule.name}' (ID: {schedule_id})")

        return schedule

    async def delete_schedule(self, schedule_id: UUID) -> bool:
        """
        Delete a schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            True if deleted, False if not found
        """
        schedules = self._get_all_schedules()

        if schedule_id not in schedules:
            return False

        # Remove from scheduler
        self._remove_job_from_scheduler(schedule_id)

        # Remove from storage
        del schedules[schedule_id]
        self._save_schedules()

        # Remove history file
        history_file = self.history_dir / f"{schedule_id}.json"
        if history_file.exists():
            history_file.unlink()

        logger.info(f"Deleted schedule {schedule_id}")

        return True

    async def execute_schedule_now(self, schedule_id: UUID) -> bool:
        """
        Manually trigger schedule execution.

        Args:
            schedule_id: Schedule ID

        Returns:
            True if scheduled, False if not found
        """
        schedules = self._get_all_schedules()

        if schedule_id not in schedules:
            return False

        # Execute immediately
        await self._execute_schedule(schedule_id)

        return True

    async def get_schedule_history(
        self, schedule_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[ScheduleRun]:
        """
        Get execution history for a schedule.

        Args:
            schedule_id: Schedule ID
            limit: Maximum number of runs to return
            offset: Number of runs to skip

        Returns:
            List of schedule runs
        """
        history_file = self.history_dir / f"{schedule_id}.json"

        if not history_file.exists():
            return []

        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)

            # Apply pagination
            paginated = history[offset : offset + limit]

            return [ScheduleRun(**run) for run in paginated]

        except Exception as e:
            logger.error(f"Failed to load schedule history: {e}")
            return []

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        logger.info("Shutting down scheduler")
        self.scheduler.shutdown()


# Singleton instance
scheduler_service = SchedulerService()
