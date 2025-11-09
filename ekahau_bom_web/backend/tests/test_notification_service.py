"""Tests for NotificationService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models import (
    NotificationConfig,
    Schedule,
    ScheduleRun,
    ScheduleStatus,
    TriggerType,
)
from app.services.notification_service import NotificationService


@pytest.fixture
def notification_service(tmp_path):
    """Create notification service with temp template directory."""
    # Use actual template directory for testing
    from pathlib import Path

    template_dir = Path(__file__).parent.parent / "app" / "templates" / "emails"
    service = NotificationService(template_dir=str(template_dir))
    return service


@pytest.fixture
def sample_schedule():
    """Create sample schedule."""
    return Schedule(
        schedule_id=uuid4(),
        name="Test Schedule",
        description="Test description",
        cron_expression="0 2 * * *",
        enabled=True,
        trigger_type=TriggerType.CRON,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_schedule_run_success():
    """Create sample successful schedule run."""
    return ScheduleRun(
        schedule_id=uuid4(),
        executed_at=datetime.now(UTC),
        status=ScheduleStatus.SUCCESS,
        duration_seconds=120.5,
        projects_processed=10,
        projects_succeeded=10,
        projects_failed=0,
        files_found=10,
        files_processed=10,
    )


@pytest.fixture
def sample_schedule_run_failed():
    """Create sample failed schedule run."""
    return ScheduleRun(
        schedule_id=uuid4(),
        executed_at=datetime.now(UTC),
        status=ScheduleStatus.FAILED,
        duration_seconds=30.0,
        projects_processed=0,
        projects_succeeded=0,
        projects_failed=0,
        error_message="Connection timeout",
    )


@pytest.fixture
def sample_schedule_run_partial():
    """Create sample partial schedule run."""
    return ScheduleRun(
        schedule_id=uuid4(),
        executed_at=datetime.now(UTC),
        status=ScheduleStatus.PARTIAL,
        duration_seconds=180.0,
        projects_processed=10,
        projects_succeeded=7,
        projects_failed=3,
        error_message="Some projects failed to process",
    )


class TestEmailTemplates:
    """Tests for email template rendering."""

    def test_render_success_template(
        self, notification_service, sample_schedule, sample_schedule_run_success
    ):
        """Test rendering success email template."""
        context = notification_service._build_email_context(
            sample_schedule, sample_schedule_run_success
        )

        template = notification_service.jinja_env.get_template("schedule_completed.html")
        html = template.render(**context)

        assert "Schedule Execution Completed" in html
        assert sample_schedule.name in html
        assert "10" in html  # projects_processed
        assert "success" in html.lower()

    def test_render_failed_template(
        self, notification_service, sample_schedule, sample_schedule_run_failed
    ):
        """Test rendering failed email template."""
        context = notification_service._build_email_context(
            sample_schedule, sample_schedule_run_failed
        )

        template = notification_service.jinja_env.get_template("schedule_failed.html")
        html = template.render(**context)

        assert "Schedule Execution Failed" in html
        assert sample_schedule.name in html
        assert "Connection timeout" in html
        assert "failed" in html.lower()

    def test_render_partial_template(
        self, notification_service, sample_schedule, sample_schedule_run_partial
    ):
        """Test rendering partial success email template."""
        context = notification_service._build_email_context(
            sample_schedule, sample_schedule_run_partial
        )

        template = notification_service.jinja_env.get_template("schedule_partial.html")
        html = template.render(**context)

        assert "Completed with Errors" in html
        assert sample_schedule.name in html
        assert "7" in html  # projects_succeeded
        assert "3" in html  # projects_failed


class TestEmailContextBuilder:
    """Tests for email context building."""

    def test_build_context_success(
        self, notification_service, sample_schedule, sample_schedule_run_success
    ):
        """Test building context for success notification."""
        context = notification_service._build_email_context(
            sample_schedule, sample_schedule_run_success
        )

        assert context["schedule_name"] == sample_schedule.name
        assert context["schedule_description"] == sample_schedule.description
        assert context["status"] == "Success"
        assert context["projects_processed"] == 10
        assert context["projects_succeeded"] == 10
        assert context["projects_failed"] == 0
        assert "2:00" in context["duration"]  # 120.5 seconds = 2 minutes
        assert context["executed_at"] is not None

    def test_build_context_with_batch(
        self, notification_service, sample_schedule, sample_schedule_run_success
    ):
        """Test building context with batch metadata."""
        from app.models import BatchMetadata, BatchStatus

        batch = BatchMetadata(
            batch_id=uuid4(),
            batch_name="Test Batch",
            status=BatchStatus.COMPLETED,
            total_projects=10,
            processed_projects=10,
            created_at=datetime.now(UTC),
        )

        context = notification_service._build_email_context(
            sample_schedule, sample_schedule_run_success, batch
        )

        assert context["batch_id"] == str(batch.batch_id)


class TestEmailSending:
    """Tests for email sending."""

    @pytest.mark.asyncio
    @patch("aiosmtplib.send")
    async def test_send_email_success(
        self, mock_send, notification_service, sample_schedule, sample_schedule_run_success
    ):
        """Test successful email sending."""
        mock_send.return_value = MagicMock()

        # Mock SMTP settings
        with patch("app.services.notification_service.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.smtp_from_email = "noreply@example.com"
            mock_settings.smtp_use_tls = True

            success = await notification_service.send_email(
                to=["test@example.com"],
                subject="Test Subject",
                template="schedule_completed.html",
                context=notification_service._build_email_context(
                    sample_schedule, sample_schedule_run_success
                ),
            )

            assert success is True
            assert mock_send.called

    @pytest.mark.asyncio
    async def test_send_email_no_smtp_config(
        self, notification_service, sample_schedule, sample_schedule_run_success
    ):
        """Test email sending with no SMTP configuration."""
        with patch("app.services.notification_service.settings") as mock_settings:
            mock_settings.smtp_host = ""

            success = await notification_service.send_email(
                to=["test@example.com"],
                subject="Test Subject",
                template="schedule_completed.html",
                context=notification_service._build_email_context(
                    sample_schedule, sample_schedule_run_success
                ),
            )

            assert success is False

    @pytest.mark.asyncio
    @patch("aiosmtplib.send")
    async def test_send_email_smtp_error(
        self, mock_send, notification_service, sample_schedule, sample_schedule_run_success
    ):
        """Test email sending with SMTP error."""
        mock_send.side_effect = Exception("SMTP connection failed")

        with patch("app.services.notification_service.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"

            success = await notification_service.send_email(
                to=["test@example.com"],
                subject="Test Subject",
                template="schedule_completed.html",
                context=notification_service._build_email_context(
                    sample_schedule, sample_schedule_run_success
                ),
            )

            assert success is False


class TestWebhookSending:
    """Tests for webhook sending."""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_send_webhook_success(self, mock_post, notification_service):
        """Test successful webhook sending."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        success = await notification_service.send_webhook(
            url="https://example.com/webhook",
            payload={"test": "data"},
        )

        assert success is True
        assert mock_post.called

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_send_webhook_http_error(self, mock_post, notification_service):
        """Test webhook sending with HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        success = await notification_service.send_webhook(
            url="https://example.com/webhook",
            payload={"test": "data"},
        )

        assert success is False

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_send_webhook_connection_error(self, mock_post, notification_service):
        """Test webhook sending with connection error."""
        mock_post.side_effect = Exception("Connection refused")

        success = await notification_service.send_webhook(
            url="https://example.com/webhook",
            payload={"test": "data"},
        )

        assert success is False


class TestSlackSending:
    """Tests for Slack webhook sending."""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_send_slack_success(self, mock_post, notification_service):
        """Test successful Slack notification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        success = await notification_service.send_slack(
            webhook_url="https://hooks.slack.com/services/test",
            message="Test message",
        )

        assert success is True
        assert mock_post.called

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_send_slack_with_blocks(self, mock_post, notification_service):
        """Test Slack notification with Block Kit formatting."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Schedule Completed*"},
            }
        ]

        success = await notification_service.send_slack(
            webhook_url="https://hooks.slack.com/services/test",
            message="Test message",
            blocks=blocks,
        )

        assert success is True
        # Verify blocks were included in payload
        call_args = mock_post.call_args
        assert call_args[1]["json"]["blocks"] == blocks

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_send_slack_error(self, mock_post, notification_service):
        """Test Slack notification with error."""
        mock_post.side_effect = Exception("Slack API error")

        success = await notification_service.send_slack(
            webhook_url="https://hooks.slack.com/services/test",
            message="Test message",
        )

        assert success is False


class TestScheduleNotifications:
    """Tests for complete schedule notification flow."""

    @pytest.mark.asyncio
    async def test_notify_on_success(
        self, notification_service, sample_schedule, sample_schedule_run_success
    ):
        """Test notification on successful schedule run."""
        sample_schedule.notification_config = NotificationConfig(
            email=["test@example.com"],
            notify_on_success=True,
            notify_on_failure=False,
            notify_on_partial=False,
        )

        with patch.object(notification_service, "send_email", return_value=True) as mock_email:
            await notification_service.notify_schedule_completed(
                sample_schedule, sample_schedule_run_success
            )

            # Verify email was sent
            assert mock_email.called
            call_args = mock_email.call_args
            assert "schedule_completed.html" in call_args[1]["template"]

    @pytest.mark.asyncio
    async def test_notify_on_failure(
        self, notification_service, sample_schedule, sample_schedule_run_failed
    ):
        """Test notification on failed schedule run."""
        sample_schedule.notification_config = NotificationConfig(
            email=["test@example.com"],
            notify_on_success=False,
            notify_on_failure=True,
            notify_on_partial=False,
        )

        with patch.object(notification_service, "send_email", return_value=True) as mock_email:
            await notification_service.notify_schedule_completed(
                sample_schedule, sample_schedule_run_failed
            )

            # Verify email was sent
            assert mock_email.called
            call_args = mock_email.call_args
            assert "schedule_failed.html" in call_args[1]["template"]

    @pytest.mark.asyncio
    async def test_notify_on_partial(
        self, notification_service, sample_schedule, sample_schedule_run_partial
    ):
        """Test notification on partial schedule run."""
        sample_schedule.notification_config = NotificationConfig(
            email=["test@example.com"],
            notify_on_success=False,
            notify_on_failure=False,
            notify_on_partial=True,
        )

        with patch.object(notification_service, "send_email", return_value=True) as mock_email:
            await notification_service.notify_schedule_completed(
                sample_schedule, sample_schedule_run_partial
            )

            # Verify email was sent
            assert mock_email.called
            call_args = mock_email.call_args
            assert "schedule_partial.html" in call_args[1]["template"]

    @pytest.mark.asyncio
    async def test_no_notification_when_disabled(
        self, notification_service, sample_schedule, sample_schedule_run_success
    ):
        """Test that no notification is sent when disabled."""
        sample_schedule.notification_config = NotificationConfig(
            email=["test@example.com"],
            notify_on_success=False,  # Disabled
            notify_on_failure=False,
            notify_on_partial=False,
        )

        with patch.object(notification_service, "send_email", return_value=True) as mock_email:
            await notification_service.notify_schedule_completed(
                sample_schedule, sample_schedule_run_success
            )

            # Verify NO email was sent
            assert not mock_email.called

    @pytest.mark.asyncio
    async def test_multi_channel_notification(
        self, notification_service, sample_schedule, sample_schedule_run_success
    ):
        """Test notification sent to multiple channels."""
        sample_schedule.notification_config = NotificationConfig(
            email=["test@example.com"],
            webhook_url="https://example.com/webhook",
            slack_webhook="https://hooks.slack.com/services/test",
            notify_on_success=True,
        )

        with (
            patch.object(notification_service, "send_email", return_value=True) as mock_email,
            patch.object(notification_service, "send_webhook", return_value=True) as mock_webhook,
            patch.object(notification_service, "send_slack", return_value=True) as mock_slack,
        ):
            await notification_service.notify_schedule_completed(
                sample_schedule, sample_schedule_run_success
            )

            # Verify all channels were notified
            assert mock_email.called
            assert mock_webhook.called
            assert mock_slack.called
