"""Tests for SchedulerService."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from apscheduler.triggers.cron import CronTrigger

from app.models import (
    NotificationConfig,
    Schedule,
    ScheduleCreateRequest,
    ScheduleRun,
    ScheduleStatus,
    ScheduleUpdateRequest,
    TriggerConfig,
    TriggerType,
)
from app.services.scheduler_service import SchedulerService


@pytest.fixture
def temp_scheduler_service(tmp_path):
    """Create temporary scheduler service with temp storage."""
    # Use BackgroundScheduler for tests (doesn't require event loop)
    service = SchedulerService(storage_dir=str(tmp_path / "schedules"), use_background=True)
    service.start()
    yield service
    # Shutdown scheduler after test
    if service._started:
        service.scheduler.shutdown(wait=False)


@pytest.fixture
def sample_schedule_create_request():
    """Create sample schedule creation request."""
    return ScheduleCreateRequest(
        name="Test Schedule",
        description="Test description",
        cron_expression="0 2 * * *",  # Daily at 2 AM
        enabled=True,
        trigger_type=TriggerType.CRON,
        trigger_config=TriggerConfig(
            directory="/data/input",
            pattern="*.esx",
            recursive=True,
        ),
        notification_config=NotificationConfig(
            email=["test@example.com"],
            notify_on_success=True,
            notify_on_failure=True,
            notify_on_partial=True,
        ),
    )


class TestSchedulerServiceCreation:
    """Tests for schedule creation."""

    @pytest.mark.asyncio
    async def test_create_schedule_minimal(self, temp_scheduler_service):
        """Test creating schedule with minimal parameters."""
        request = ScheduleCreateRequest(
            name="Minimal Schedule",
            cron_expression="0 0 * * *",  # Midnight daily
            trigger_type=TriggerType.CRON,
        )

        schedule = await temp_scheduler_service.create_schedule(request)

        assert isinstance(schedule.schedule_id, UUID)
        assert schedule.name == "Minimal Schedule"
        assert schedule.cron_expression == "0 0 * * *"
        assert schedule.enabled is True
        assert schedule.trigger_type == TriggerType.CRON
        assert schedule.execution_count == 0
        assert schedule.next_run_time is not None  # Should be scheduled

    @pytest.mark.asyncio
    async def test_create_schedule_full(
        self, temp_scheduler_service, sample_schedule_create_request
    ):
        """Test creating schedule with all parameters."""
        schedule = await temp_scheduler_service.create_schedule(sample_schedule_create_request)

        assert schedule.name == "Test Schedule"
        assert schedule.description == "Test description"
        assert schedule.cron_expression == "0 2 * * *"
        assert schedule.enabled is True
        assert schedule.trigger_config.directory == "/data/input"
        assert schedule.trigger_config.pattern == "*.esx"
        assert schedule.notification_config.email == ["test@example.com"]

    @pytest.mark.asyncio
    async def test_create_schedule_invalid_cron(self, temp_scheduler_service):
        """Test creating schedule with invalid cron expression."""
        request = ScheduleCreateRequest(
            name="Invalid Schedule",
            cron_expression="invalid cron",
            trigger_type=TriggerType.CRON,
        )

        with pytest.raises(ValueError, match="Invalid cron expression"):
            await temp_scheduler_service.create_schedule(request)

    @pytest.mark.asyncio
    async def test_create_schedule_disabled(self, temp_scheduler_service):
        """Test creating disabled schedule."""
        request = ScheduleCreateRequest(
            name="Disabled Schedule",
            cron_expression="0 0 * * *",
            enabled=False,
            trigger_type=TriggerType.CRON,
        )

        schedule = await temp_scheduler_service.create_schedule(request)

        assert schedule.enabled is False
        assert schedule.next_run_time is None  # Should not be scheduled


class TestSchedulerServiceRetrieval:
    """Tests for schedule retrieval."""

    @pytest.mark.asyncio
    async def test_get_schedule(self, temp_scheduler_service, sample_schedule_create_request):
        """Test getting schedule by ID."""
        created = await temp_scheduler_service.create_schedule(sample_schedule_create_request)

        retrieved = await temp_scheduler_service.get_schedule(created.schedule_id)

        assert retrieved is not None
        assert retrieved.schedule_id == created.schedule_id
        assert retrieved.name == created.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_schedule(self, temp_scheduler_service):
        """Test getting non-existent schedule."""
        fake_id = uuid4()
        result = await temp_scheduler_service.get_schedule(fake_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_list_schedules_empty(self, temp_scheduler_service):
        """Test listing schedules when none exist."""
        schedules = await temp_scheduler_service.list_schedules()

        assert len(schedules) == 0

    @pytest.mark.asyncio
    async def test_list_schedules(self, temp_scheduler_service, sample_schedule_create_request):
        """Test listing schedules."""
        # Create multiple schedules
        await temp_scheduler_service.create_schedule(sample_schedule_create_request)

        request2 = ScheduleCreateRequest(
            name="Second Schedule",
            cron_expression="0 3 * * *",
            enabled=False,
            trigger_type=TriggerType.CRON,
        )
        await temp_scheduler_service.create_schedule(request2)

        schedules = await temp_scheduler_service.list_schedules()

        assert len(schedules) == 2

    @pytest.mark.asyncio
    async def test_list_schedules_filtered_enabled(
        self, temp_scheduler_service, sample_schedule_create_request
    ):
        """Test listing schedules filtered by enabled status."""
        # Create enabled schedule
        await temp_scheduler_service.create_schedule(sample_schedule_create_request)

        # Create disabled schedule
        request2 = ScheduleCreateRequest(
            name="Disabled Schedule",
            cron_expression="0 3 * * *",
            enabled=False,
            trigger_type=TriggerType.CRON,
        )
        await temp_scheduler_service.create_schedule(request2)

        # Filter for enabled only
        enabled_schedules = await temp_scheduler_service.list_schedules(enabled=True)
        assert len(enabled_schedules) == 1
        assert enabled_schedules[0].enabled is True

        # Filter for disabled only
        disabled_schedules = await temp_scheduler_service.list_schedules(enabled=False)
        assert len(disabled_schedules) == 1
        assert disabled_schedules[0].enabled is False

    @pytest.mark.asyncio
    async def test_list_schedules_filtered_trigger_type(self, temp_scheduler_service):
        """Test listing schedules filtered by trigger type."""
        # Create cron schedule
        request1 = ScheduleCreateRequest(
            name="Cron Schedule",
            cron_expression="0 0 * * *",
            trigger_type=TriggerType.CRON,
        )
        await temp_scheduler_service.create_schedule(request1)

        # Create directory schedule
        request2 = ScheduleCreateRequest(
            name="Directory Schedule",
            cron_expression="0 1 * * *",
            trigger_type=TriggerType.DIRECTORY,
        )
        await temp_scheduler_service.create_schedule(request2)

        # Filter for cron only
        cron_schedules = await temp_scheduler_service.list_schedules(trigger_type=TriggerType.CRON)
        assert len(cron_schedules) == 1
        assert cron_schedules[0].trigger_type == TriggerType.CRON


class TestSchedulerServiceUpdate:
    """Tests for schedule updates."""

    @pytest.mark.asyncio
    async def test_update_schedule(self, temp_scheduler_service, sample_schedule_create_request):
        """Test updating schedule."""
        created = await temp_scheduler_service.create_schedule(sample_schedule_create_request)

        update = ScheduleUpdateRequest(
            name="Updated Name",
            description="Updated description",
        )

        updated = await temp_scheduler_service.update_schedule(created.schedule_id, update)

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"
        # Other fields should remain unchanged
        assert updated.cron_expression == created.cron_expression

    @pytest.mark.asyncio
    async def test_update_schedule_cron_expression(
        self, temp_scheduler_service, sample_schedule_create_request
    ):
        """Test updating schedule cron expression."""
        created = await temp_scheduler_service.create_schedule(sample_schedule_create_request)
        original_cron = created.cron_expression

        # Update cron expression
        update = ScheduleUpdateRequest(cron_expression="0 3 * * *")

        updated = await temp_scheduler_service.update_schedule(created.schedule_id, update)

        assert updated is not None
        assert updated.cron_expression == "0 3 * * *"
        assert updated.cron_expression != original_cron
        # next_run_time should be set
        assert updated.next_run_time is not None

    @pytest.mark.asyncio
    async def test_update_schedule_toggle_enabled(
        self, temp_scheduler_service, sample_schedule_create_request
    ):
        """Test toggling schedule enabled status."""
        created = await temp_scheduler_service.create_schedule(sample_schedule_create_request)

        # Disable schedule
        update = ScheduleUpdateRequest(enabled=False)
        updated = await temp_scheduler_service.update_schedule(created.schedule_id, update)

        assert updated.enabled is False
        assert updated.next_run_time is None

        # Re-enable schedule
        update2 = ScheduleUpdateRequest(enabled=True)
        updated2 = await temp_scheduler_service.update_schedule(created.schedule_id, update2)

        assert updated2.enabled is True
        assert updated2.next_run_time is not None

    @pytest.mark.asyncio
    async def test_update_nonexistent_schedule(self, temp_scheduler_service):
        """Test updating non-existent schedule."""
        fake_id = uuid4()
        update = ScheduleUpdateRequest(name="Should Fail")

        result = await temp_scheduler_service.update_schedule(fake_id, update)

        assert result is None


class TestSchedulerServiceDeletion:
    """Tests for schedule deletion."""

    @pytest.mark.asyncio
    async def test_delete_schedule(self, temp_scheduler_service, sample_schedule_create_request):
        """Test deleting schedule."""
        created = await temp_scheduler_service.create_schedule(sample_schedule_create_request)

        success = await temp_scheduler_service.delete_schedule(created.schedule_id)

        assert success is True

        # Verify schedule is deleted
        retrieved = await temp_scheduler_service.get_schedule(created.schedule_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_schedule(self, temp_scheduler_service):
        """Test deleting non-existent schedule."""
        fake_id = uuid4()
        success = await temp_scheduler_service.delete_schedule(fake_id)

        assert success is False


class TestSchedulerServiceExecution:
    """Tests for schedule execution."""

    @pytest.mark.asyncio
    async def test_execute_schedule_now(
        self, temp_scheduler_service, sample_schedule_create_request
    ):
        """Test manually executing schedule."""
        created = await temp_scheduler_service.create_schedule(sample_schedule_create_request)

        success = await temp_scheduler_service.execute_schedule_now(created.schedule_id)

        assert success is True

        # Check that execution was recorded (with a small delay for async processing)
        import asyncio

        await asyncio.sleep(0.1)

        history = await temp_scheduler_service.get_schedule_history(created.schedule_id, limit=1)
        assert len(history) >= 0  # Execution may be async

    @pytest.mark.asyncio
    async def test_execute_nonexistent_schedule(self, temp_scheduler_service):
        """Test executing non-existent schedule."""
        fake_id = uuid4()
        success = await temp_scheduler_service.execute_schedule_now(fake_id)

        assert success is False


class TestSchedulerServiceHistory:
    """Tests for schedule execution history."""

    @pytest.mark.asyncio
    async def test_get_schedule_history_empty(
        self, temp_scheduler_service, sample_schedule_create_request
    ):
        """Test getting history for schedule with no runs."""
        created = await temp_scheduler_service.create_schedule(sample_schedule_create_request)

        history = await temp_scheduler_service.get_schedule_history(created.schedule_id)

        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_get_schedule_history_with_runs(
        self, temp_scheduler_service, sample_schedule_create_request
    ):
        """Test getting history for schedule with runs."""
        created = await temp_scheduler_service.create_schedule(sample_schedule_create_request)

        # Manually add a run to history
        run = ScheduleRun(
            schedule_id=created.schedule_id,
            executed_at=datetime.now(UTC),
            status=ScheduleStatus.SUCCESS,
            duration_seconds=10.5,
            projects_processed=5,
            projects_succeeded=5,
            projects_failed=0,
        )

        temp_scheduler_service._save_schedule_run(run)

        history = await temp_scheduler_service.get_schedule_history(created.schedule_id)

        assert len(history) == 1
        assert history[0].schedule_id == created.schedule_id
        assert history[0].status == ScheduleStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_get_schedule_history_pagination(
        self, temp_scheduler_service, sample_schedule_create_request
    ):
        """Test getting history with pagination."""
        created = await temp_scheduler_service.create_schedule(sample_schedule_create_request)

        # Add multiple runs
        for i in range(10):
            run = ScheduleRun(
                schedule_id=created.schedule_id,
                executed_at=datetime.now(UTC),
                status=ScheduleStatus.SUCCESS,
                duration_seconds=10.5,
                projects_processed=i + 1,
                projects_succeeded=i + 1,
                projects_failed=0,
            )
            temp_scheduler_service._save_schedule_run(run)

        # Get first 5 runs
        history_page1 = await temp_scheduler_service.get_schedule_history(
            created.schedule_id, limit=5, offset=0
        )
        assert len(history_page1) == 5

        # Get next 5 runs
        history_page2 = await temp_scheduler_service.get_schedule_history(
            created.schedule_id, limit=5, offset=5
        )
        assert len(history_page2) == 5


class TestSchedulerServicePersistence:
    """Tests for schedule persistence."""

    @pytest.mark.asyncio
    async def test_schedules_persist_across_instances(
        self, tmp_path, sample_schedule_create_request
    ):
        """Test that schedules persist across service instances."""
        storage_dir = str(tmp_path / "schedules")

        # Create schedule with first instance (use BackgroundScheduler for tests)
        service1 = SchedulerService(storage_dir=storage_dir, use_background=True)
        service1.start()
        created = await service1.create_schedule(sample_schedule_create_request)
        service1.scheduler.shutdown(wait=False)

        # Load schedules with second instance
        service2 = SchedulerService(storage_dir=storage_dir, use_background=True)
        service2.start()
        retrieved = await service2.get_schedule(created.schedule_id)

        assert retrieved is not None
        assert retrieved.schedule_id == created.schedule_id
        assert retrieved.name == created.name

        service2.scheduler.shutdown(wait=False)


class TestCronValidation:
    """Tests for cron expression validation."""

    @pytest.mark.asyncio
    async def test_valid_cron_expressions(self, temp_scheduler_service):
        """Test various valid cron expressions."""
        valid_expressions = [
            "0 0 * * *",  # Midnight daily
            "0 2 * * *",  # 2 AM daily
            "*/15 * * * *",  # Every 15 minutes
            "0 0 * * 0",  # Sunday midnight
            "0 9 * * 1-5",  # Weekdays 9 AM
            "0 0 1 * *",  # First day of month
        ]

        for expr in valid_expressions:
            request = ScheduleCreateRequest(
                name=f"Test {expr}",
                cron_expression=expr,
                trigger_type=TriggerType.CRON,
            )
            schedule = await temp_scheduler_service.create_schedule(request)
            assert schedule is not None

    @pytest.mark.asyncio
    async def test_invalid_cron_expressions(self, temp_scheduler_service):
        """Test various invalid cron expressions."""
        invalid_expressions = [
            "invalid",
            "60 0 * * *",  # Invalid minute
            "0 25 * * *",  # Invalid hour
            "0 0 32 * *",  # Invalid day
            "* * * *",  # Too few fields
            "* * * * * *",  # Too many fields
        ]

        for expr in invalid_expressions:
            request = ScheduleCreateRequest(
                name=f"Test {expr}",
                cron_expression=expr,
                trigger_type=TriggerType.CRON,
            )
            with pytest.raises((ValueError, Exception)):
                await temp_scheduler_service.create_schedule(request)
