"""Scheduler service for automated batch processing."""

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from app.models import (
    ProcessingRequest,
    Schedule,
    ScheduleCreateRequest,
    ScheduleListItem,
    ScheduleRun,
    ScheduleStatus,
    ScheduleUpdateRequest,
    TriggerType,
)

if TYPE_CHECKING:
    from app.services.batch_service import BatchService
    from app.services.storage_service import StorageService
    from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled batch processing jobs using APScheduler."""

    def __init__(self, storage_dir: str = "data/schedules", use_background: bool = False):
        """
        Initialize the scheduler service.

        Args:
            storage_dir: Directory for storing schedule metadata and history
            use_background: Use BackgroundScheduler instead of AsyncIOScheduler (for tests)
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.schedules_file = self.storage_dir / "schedules.json"
        self.history_dir = self.storage_dir / "history"
        self.history_dir.mkdir(exist_ok=True)

        # Services will be injected later via set_services()
        self._batch_service: Optional["BatchService"] = None
        self._storage_service: Optional["StorageService"] = None
        self._notification_service: Optional["NotificationService"] = None

        # In-memory cache of schedules
        self._schedules: dict[UUID, Schedule] = {}

        # Initialize APScheduler (but don't start yet - no event loop for AsyncIO)
        jobstores = {"default": MemoryJobStore()}
        self._use_background = use_background
        if use_background:
            self.scheduler = BackgroundScheduler(jobstores=jobstores, timezone="UTC")
        else:
            self.scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="UTC")
        self._started = False

        logger.info(
            f"SchedulerService initialized (not started yet, "
            f"scheduler_type={'Background' if use_background else 'AsyncIO'})"
        )

    def start(self) -> None:
        """Start the scheduler. Call this after event loop is running (for AsyncIO)."""
        if self._started:
            return

        self.scheduler.start()
        self._started = True

        # Load existing schedules and add to scheduler
        self._load_schedules()

        logger.info("Scheduler started")

    def set_services(
        self,
        batch_service: "BatchService",
        storage_service: "StorageService",
        notification_service: "NotificationService",
    ) -> None:
        """
        Inject required services for batch processing.

        Args:
            batch_service: Service for batch operations
            storage_service: Service for file storage
            notification_service: Service for notifications
        """
        self._batch_service = batch_service
        self._storage_service = storage_service
        self._notification_service = notification_service
        logger.info("SchedulerService: Services injected")

    def _load_schedules(self) -> None:
        """Load existing schedules from disk and add them to the scheduler."""
        if not self.schedules_file.exists():
            logger.info("No existing schedules found")
            return

        try:
            with open(self.schedules_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for s in data.get("schedules", []):
                schedule = Schedule(**s)
                self._schedules[schedule.schedule_id] = schedule

            logger.info(f"Loaded {len(self._schedules)} schedules from disk")

            # Add enabled schedules to APScheduler
            for schedule in self._schedules.values():
                if schedule.enabled:
                    self._add_job_to_scheduler(schedule)

        except Exception as e:
            logger.error(f"Failed to load schedules: {e}")

    def _save_schedules(self) -> None:
        """Save all schedules to disk."""
        try:
            data = {
                "schedules": [s.model_dump(mode="json") for s in self._schedules.values()],
                "updated_at": datetime.now(UTC).isoformat(),
            }

            with open(self.schedules_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved {len(self._schedules)} schedules to disk")

        except Exception as e:
            logger.error(f"Failed to save schedules: {e}")

    def _get_all_schedules(self) -> dict[UUID, Schedule]:
        """Get all schedules from in-memory cache."""
        return self._schedules

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

            # Update next run time (handle different APScheduler versions)
            job = self.scheduler.get_job(str(schedule.schedule_id))
            if job:
                # APScheduler 3.x uses next_run_time attribute
                next_run = getattr(job, "next_run_time", None)
                if next_run:
                    schedule.next_run_time = next_run

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
        Execute a scheduled job - scan directory, create batch, and process files.

        Args:
            schedule_id: Schedule ID to execute
        """
        schedules = self._get_all_schedules()
        schedule = schedules.get(schedule_id)

        if not schedule:
            logger.error(f"Schedule {schedule_id} not found")
            return

        logger.info(f"Executing schedule '{schedule.name}' (ID: {schedule_id})")

        # Check if services are available
        if not self._batch_service or not self._storage_service:
            logger.error("SchedulerService: Services not injected, cannot execute schedule")
            return

        # Record execution start
        run_start = datetime.now(UTC)
        run = ScheduleRun(
            schedule_id=schedule_id,
            executed_at=run_start,
            status=ScheduleStatus.RUNNING,
        )

        batch_metadata = None

        try:
            # Step 1: Scan directory for .esx files
            trigger_config = schedule.trigger_config
            directory = trigger_config.directory

            if not directory:
                raise ValueError("No directory configured in trigger_config")

            dir_path = Path(directory)
            if not dir_path.exists():
                raise FileNotFoundError(f"Directory not found: {directory}")

            # Find matching files
            pattern = trigger_config.pattern or "*.esx"
            if trigger_config.recursive:
                matching_files = list(dir_path.rglob(pattern))
            else:
                matching_files = list(dir_path.glob(pattern))

            run.files_found = len(matching_files)
            logger.info(
                f"Schedule '{schedule.name}': Found {len(matching_files)} files matching '{pattern}'"
            )

            if not matching_files:
                logger.info(f"Schedule '{schedule.name}': No files found, nothing to process")
                run.status = ScheduleStatus.SUCCESS
                run.duration_seconds = (datetime.now(UTC) - run_start).total_seconds()
                self._save_schedule_run(run)
                return

            # Step 2: Get processing options from template or defaults
            processing_options = None
            if trigger_config.batch_template_id:
                # Load template and use its processing options
                from app.services.template_service import template_service

                template = await template_service.get_template(trigger_config.batch_template_id)
                if template:
                    processing_options = template.processing_options
                    logger.info(f"Using template '{template.name}' for processing")

            if not processing_options:
                # Use default processing options
                processing_options = ProcessingRequest(
                    output_formats=["csv", "excel", "html", "json"],
                    visualize_floor_plans=True,
                    show_azimuth_arrows=True,
                    ap_opacity=0.6,
                )

            # Step 3: Create batch
            batch_name = f"Scheduled: {schedule.name} - {run_start.strftime('%Y-%m-%d %H:%M')}"
            batch_metadata = self._batch_service.create_batch(
                batch_name=batch_name,
                processing_options=processing_options,
                parallel_workers=1,
            )
            run.batch_id = batch_metadata.batch_id
            schedule.last_batch_id = batch_metadata.batch_id

            logger.info(f"Schedule '{schedule.name}': Created batch {batch_metadata.batch_id}")

            # Step 4: Add files to batch
            files_added = 0
            for file_path in matching_files:
                try:
                    with open(file_path, "rb") as f:
                        file_content = f.read()

                    project_metadata = self._storage_service.save_uploaded_file(
                        filename=file_path.name,
                        file_content=file_content,
                        project_name=file_path.stem,
                        short_link_days=(
                            processing_options.short_link_days
                            if processing_options.create_short_link
                            else None
                        ),
                    )

                    self._batch_service.add_project_to_batch(
                        batch_metadata.batch_id, project_metadata.project_id
                    )
                    files_added += 1
                    logger.debug(f"Added file to batch: {file_path.name}")

                except Exception as e:
                    logger.error(f"Error adding file {file_path}: {e}")
                    continue

            run.files_processed = files_added
            logger.info(f"Schedule '{schedule.name}': Added {files_added} files to batch")

            if files_added == 0:
                raise ValueError("No files could be added to batch")

            # Step 5: Process batch
            logger.info(f"Schedule '{schedule.name}': Starting batch processing")
            batch_metadata = await self._batch_service.process_batch(batch_metadata.batch_id)

            # Step 6: Update run statistics from batch results
            run.projects_processed = batch_metadata.statistics.total_projects
            run.projects_succeeded = batch_metadata.statistics.successful_projects
            run.projects_failed = batch_metadata.statistics.failed_projects

            # Determine final status
            if run.projects_failed == 0:
                run.status = ScheduleStatus.SUCCESS
            elif run.projects_succeeded == 0:
                run.status = ScheduleStatus.FAILED
            else:
                run.status = ScheduleStatus.PARTIAL

            run.duration_seconds = (datetime.now(UTC) - run_start).total_seconds()

            # Update schedule metadata
            schedule.last_run_time = run_start
            schedule.last_run_status = run.status
            schedule.execution_count += 1

            logger.info(
                f"Schedule '{schedule.name}' completed: {run.projects_succeeded}/{run.projects_processed} "
                f"projects succeeded in {run.duration_seconds:.2f}s"
            )

        except Exception as e:
            logger.error(f"Schedule execution failed for '{schedule.name}': {e}", exc_info=True)

            run.status = ScheduleStatus.FAILED
            run.error_message = str(e)
            run.duration_seconds = (datetime.now(UTC) - run_start).total_seconds()

            schedule.last_run_time = run_start
            schedule.last_run_status = ScheduleStatus.FAILED

        finally:
            # Save schedule history
            self._save_schedule_run(run)

            # Save updated schedule
            schedules[schedule_id] = schedule
            self._save_schedules()

            # Step 7: Send notifications
            if self._notification_service:
                try:
                    await self._notification_service.notify_schedule_completed(
                        schedule=schedule,
                        run=run,
                        batch=batch_metadata,
                    )
                except Exception as e:
                    logger.error(f"Failed to send notifications: {e}")

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
                if job:
                    next_run = getattr(job, "next_run_time", None)
                    if next_run:
                        schedule.next_run_time = next_run

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
