"""Notification service for email, webhook, and Slack notifications."""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib
import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings
from app.models import BatchMetadata, Schedule, ScheduleRun, ScheduleStatus

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications via email, webhook, and Slack."""

    def __init__(self, template_dir: str = "app/templates/emails"):
        """
        Initialize the notification service.

        Args:
            template_dir: Directory containing email templates
        """
        # Setup Jinja2 for email templates
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

        logger.info("NotificationService initialized")

    async def send_email(
        self,
        to: list[str],
        subject: str,
        template: str,
        context: dict,
        from_email: Optional[str] = None,
    ) -> bool:
        """
        Send email notification.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            template: Template name (e.g., "batch_completed.html")
            context: Template context variables
            from_email: Sender email (defaults to settings.smtp_from_email)

        Returns:
            True if sent successfully, False otherwise
        """
        if not to:
            logger.warning("No recipients specified for email")
            return False

        # Check if SMTP is configured
        if not settings.smtp_host or not settings.smtp_username:
            logger.warning("SMTP not configured, skipping email notification")
            return False

        try:
            # Render email template
            email_template = self.jinja_env.get_template(template)
            html_body = email_template.render(**context)

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email or settings.smtp_from_email
            msg["To"] = ", ".join(to)

            # Attach HTML body
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)

            # Send email
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                use_tls=settings.smtp_use_tls,
            )

            logger.info(f"Email sent to {len(to)} recipient(s): {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def send_webhook(self, url: str, payload: dict) -> bool:
        """
        Send webhook notification via HTTP POST.

        Args:
            url: Webhook URL
            payload: JSON payload to send

        Returns:
            True if sent successfully, False otherwise
        """
        if not url:
            logger.warning("No webhook URL specified")
            return False

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

            logger.info(f"Webhook sent to {url} (status: {response.status_code})")
            return True

        except Exception as e:
            logger.error(f"Failed to send webhook to {url}: {e}")
            return False

    async def send_slack(
        self, webhook_url: str, message: str, blocks: Optional[list[dict]] = None
    ) -> bool:
        """
        Send Slack notification via incoming webhook.

        Args:
            webhook_url: Slack incoming webhook URL
            message: Message text (fallback)
            blocks: Slack block kit blocks (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        if not webhook_url:
            logger.warning("No Slack webhook URL specified")
            return False

        try:
            payload = {"text": message}

            if blocks:
                payload["blocks"] = blocks

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()

            logger.info(f"Slack notification sent (status: {response.status_code})")
            return True

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    async def notify_schedule_completed(
        self,
        schedule: Schedule,
        run: ScheduleRun,
        batch: Optional[BatchMetadata] = None,
    ) -> None:
        """
        Send notifications when a schedule execution completes.

        Args:
            schedule: Schedule that was executed
            run: Schedule run details
            batch: Batch metadata (if batch was created)
        """
        # Check if notifications should be sent
        if (
            run.status == ScheduleStatus.SUCCESS
            and not schedule.notification_config.notify_on_success
        ):
            return
        if (
            run.status == ScheduleStatus.FAILED
            and not schedule.notification_config.notify_on_failure
        ):
            return
        if (
            run.status == ScheduleStatus.PARTIAL
            and not schedule.notification_config.notify_on_partial
        ):
            return

        # Prepare context
        context = {
            "schedule_name": schedule.name,
            "schedule_description": schedule.description,
            "status": run.status.value,
            "executed_at": run.executed_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "duration": f"{run.duration_seconds:.2f}s",
            "projects_processed": run.projects_processed,
            "projects_succeeded": run.projects_succeeded,
            "projects_failed": run.projects_failed,
            "error_message": run.error_message,
            "batch_id": str(run.batch_id) if run.batch_id else None,
        }

        # Email notification
        if schedule.notification_config.email:
            template = self._get_email_template(run.status)
            subject = self._get_email_subject(schedule.name, run.status)

            await self.send_email(
                to=schedule.notification_config.email,
                subject=subject,
                template=template,
                context=context,
            )

        # Webhook notification
        if schedule.notification_config.webhook_url:
            payload = {
                "event": "schedule_completed",
                "schedule_id": str(schedule.schedule_id),
                "schedule_name": schedule.name,
                "run_id": str(run.run_id),
                "status": run.status.value,
                "executed_at": run.executed_at.isoformat(),
                "duration_seconds": run.duration_seconds,
                "batch_id": str(run.batch_id) if run.batch_id else None,
                "statistics": {
                    "projects_processed": run.projects_processed,
                    "projects_succeeded": run.projects_succeeded,
                    "projects_failed": run.projects_failed,
                },
            }

            if run.error_message:
                payload["error_message"] = run.error_message

            await self.send_webhook(schedule.notification_config.webhook_url, payload)

        # Slack notification
        if schedule.notification_config.slack_webhook:
            message = self._format_slack_message(schedule.name, run)
            blocks = self._format_slack_blocks(schedule.name, run)

            await self.send_slack(schedule.notification_config.slack_webhook, message, blocks)

    def _get_email_template(self, status: ScheduleStatus) -> str:
        """Get email template name based on status."""
        if status == ScheduleStatus.SUCCESS:
            return "schedule_completed.html"
        elif status == ScheduleStatus.FAILED:
            return "schedule_failed.html"
        elif status == ScheduleStatus.PARTIAL:
            return "schedule_partial.html"
        else:
            return "schedule_completed.html"

    def _get_email_subject(self, schedule_name: str, status: ScheduleStatus) -> str:
        """Get email subject based on status."""
        if status == ScheduleStatus.SUCCESS:
            return f"✅ Schedule '{schedule_name}' completed successfully"
        elif status == ScheduleStatus.FAILED:
            return f"❌ Schedule '{schedule_name}' failed"
        elif status == ScheduleStatus.PARTIAL:
            return f"⚠️ Schedule '{schedule_name}' completed with errors"
        else:
            return f"Schedule '{schedule_name}' executed"

    def _format_slack_message(self, schedule_name: str, run: ScheduleRun) -> str:
        """Format Slack message text."""
        status_emoji = {
            ScheduleStatus.SUCCESS: "✅",
            ScheduleStatus.FAILED: "❌",
            ScheduleStatus.PARTIAL: "⚠️",
            ScheduleStatus.RUNNING: "⏳",
        }.get(run.status, "ℹ️")

        message = f"{status_emoji} Schedule '{schedule_name}' {run.status.value}\n"
        message += f"Duration: {run.duration_seconds:.2f}s\n"
        message += f"Projects: {run.projects_succeeded}/{run.projects_processed} succeeded"

        if run.projects_failed > 0:
            message += f", {run.projects_failed} failed"

        return message

    def _format_slack_blocks(self, schedule_name: str, run: ScheduleRun) -> list[dict]:
        """Format Slack block kit blocks."""
        status_emoji = {
            ScheduleStatus.SUCCESS: "✅",
            ScheduleStatus.FAILED: "❌",
            ScheduleStatus.PARTIAL: "⚠️",
            ScheduleStatus.RUNNING: "⏳",
        }.get(run.status, "ℹ️")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} Schedule Execution: {schedule_name}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Status:*\n{run.status.value}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Duration:*\n{run.duration_seconds:.2f}s",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Projects Processed:*\n{run.projects_processed}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Success Rate:*\n{run.projects_succeeded}/{run.projects_processed}",
                    },
                ],
            },
        ]

        # Add error section if failed
        if run.error_message:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Error:*\n```{run.error_message}```",
                    },
                }
            )

        # Add batch link if available
        if run.batch_id:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Batch ID:*\n`{run.batch_id}`",
                    },
                }
            )

        blocks.append({"type": "divider"})

        return blocks


# Singleton instance
notification_service = NotificationService()
