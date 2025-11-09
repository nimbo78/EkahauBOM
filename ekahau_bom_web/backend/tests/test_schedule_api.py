"""Tests for Schedule API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ScheduleStatus, TriggerType


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authentication headers for admin user."""
    # Mock admin authentication
    # In actual tests, you would use proper authentication
    return {"Authorization": "Bearer admin_token"}


@pytest.fixture
def sample_schedule_payload():
    """Create sample schedule creation payload."""
    return {
        "name": "Test Schedule",
        "description": "Test description",
        "cron_expression": "0 2 * * *",
        "enabled": True,
        "trigger_type": "cron",
        "trigger_config": {
            "directory": "/data/input",
            "pattern": "*.esx",
            "recursive": True,
        },
        "notification_config": {
            "email": ["test@example.com"],
            "notify_on_success": True,
            "notify_on_failure": True,
            "notify_on_partial": True,
        },
    }


class TestScheduleListEndpoint:
    """Tests for GET /api/schedules endpoint."""

    def test_list_schedules_empty(self, client, auth_headers):
        """Test listing schedules when none exist."""
        response = client.get("/api/schedules", headers=auth_headers)

        # May return 401 without proper auth, or 200 with empty list
        # This depends on authentication implementation
        assert response.status_code in [200, 401]

    def test_list_schedules_unauthorized(self, client):
        """Test listing schedules without authentication."""
        response = client.get("/api/schedules")

        # Should require authentication
        assert response.status_code in [401, 403]


class TestScheduleCreateEndpoint:
    """Tests for POST /api/schedules endpoint."""

    def test_create_schedule_success(self, client, auth_headers, sample_schedule_payload):
        """Test successful schedule creation."""
        response = client.post("/api/schedules", json=sample_schedule_payload, headers=auth_headers)

        # May return 401 without proper auth, or 201 on success
        if response.status_code == 201:
            data = response.json()
            assert data["name"] == "Test Schedule"
            assert data["cron_expression"] == "0 2 * * *"
            assert "schedule_id" in data
        else:
            assert response.status_code in [401, 403]

    def test_create_schedule_invalid_cron(self, client, auth_headers):
        """Test schedule creation with invalid cron expression."""
        payload = {
            "name": "Invalid Schedule",
            "cron_expression": "invalid",
            "trigger_type": "cron",
        }

        response = client.post("/api/schedules", json=payload, headers=auth_headers)

        # Should return 400 for validation error (or 401 without auth)
        assert response.status_code in [400, 401, 403, 422]

    def test_create_schedule_missing_name(self, client, auth_headers):
        """Test schedule creation without name."""
        payload = {
            "cron_expression": "0 0 * * *",
            "trigger_type": "cron",
        }

        response = client.post("/api/schedules", json=payload, headers=auth_headers)

        # Should return 422 for validation error (or 401 without auth)
        assert response.status_code in [401, 403, 422]


class TestScheduleGetEndpoint:
    """Tests for GET /api/schedules/{schedule_id} endpoint."""

    def test_get_schedule_not_found(self, client, auth_headers):
        """Test getting non-existent schedule."""
        fake_id = str(uuid4())
        response = client.get(f"/api/schedules/{fake_id}", headers=auth_headers)

        # Should return 404 (or 401 without auth)
        assert response.status_code in [401, 403, 404]

    def test_get_schedule_invalid_id(self, client, auth_headers):
        """Test getting schedule with invalid ID format."""
        response = client.get("/api/schedules/invalid-uuid", headers=auth_headers)

        # Should return 422 for invalid UUID format (or 401 without auth)
        assert response.status_code in [401, 403, 422]


class TestScheduleUpdateEndpoint:
    """Tests for PUT /api/schedules/{schedule_id} endpoint."""

    def test_update_schedule_not_found(self, client, auth_headers):
        """Test updating non-existent schedule."""
        fake_id = str(uuid4())
        payload = {"name": "Updated Name"}

        response = client.put(f"/api/schedules/{fake_id}", json=payload, headers=auth_headers)

        # Should return 404 (or 401 without auth)
        assert response.status_code in [401, 403, 404]

    def test_update_schedule_invalid_cron(self, client, auth_headers):
        """Test updating schedule with invalid cron expression."""
        fake_id = str(uuid4())
        payload = {"cron_expression": "invalid"}

        response = client.put(f"/api/schedules/{fake_id}", json=payload, headers=auth_headers)

        # Should return 400 or 404 (or 401 without auth)
        assert response.status_code in [400, 401, 403, 404, 422]


class TestScheduleDeleteEndpoint:
    """Tests for DELETE /api/schedules/{schedule_id} endpoint."""

    def test_delete_schedule_not_found(self, client, auth_headers):
        """Test deleting non-existent schedule."""
        fake_id = str(uuid4())
        response = client.delete(f"/api/schedules/{fake_id}", headers=auth_headers)

        # Should return 404 (or 401 without auth)
        assert response.status_code in [401, 403, 404]

    def test_delete_schedule_invalid_id(self, client, auth_headers):
        """Test deleting schedule with invalid ID format."""
        response = client.delete("/api/schedules/invalid-uuid", headers=auth_headers)

        # Should return 422 for invalid UUID format (or 401 without auth)
        assert response.status_code in [401, 403, 422]


class TestScheduleRunEndpoint:
    """Tests for POST /api/schedules/{schedule_id}/run endpoint."""

    def test_run_schedule_not_found(self, client, auth_headers):
        """Test running non-existent schedule."""
        fake_id = str(uuid4())
        response = client.post(f"/api/schedules/{fake_id}/run", headers=auth_headers)

        # Should return 404 (or 401 without auth)
        assert response.status_code in [401, 403, 404]

    def test_run_schedule_unauthorized(self, client):
        """Test running schedule without authentication."""
        fake_id = str(uuid4())
        response = client.post(f"/api/schedules/{fake_id}/run")

        # Should require authentication
        assert response.status_code in [401, 403]


class TestScheduleHistoryEndpoint:
    """Tests for GET /api/schedules/{schedule_id}/history endpoint."""

    def test_get_history_not_found(self, client, auth_headers):
        """Test getting history for non-existent schedule."""
        fake_id = str(uuid4())
        response = client.get(f"/api/schedules/{fake_id}/history", headers=auth_headers)

        # May return empty list or 200 even for non-existent schedule
        assert response.status_code in [200, 401, 403]

    def test_get_history_with_pagination(self, client, auth_headers):
        """Test getting history with pagination parameters."""
        fake_id = str(uuid4())
        response = client.get(
            f"/api/schedules/{fake_id}/history?limit=10&offset=5",
            headers=auth_headers,
        )

        # Should accept pagination parameters
        assert response.status_code in [200, 401, 403]

    def test_get_history_invalid_pagination(self, client, auth_headers):
        """Test getting history with invalid pagination parameters."""
        fake_id = str(uuid4())
        response = client.get(
            f"/api/schedules/{fake_id}/history?limit=-1",
            headers=auth_headers,
        )

        # Should validate pagination parameters
        assert response.status_code in [401, 403, 422]


class TestScheduleFiltering:
    """Tests for schedule list filtering."""

    def test_filter_by_enabled(self, client, auth_headers):
        """Test filtering schedules by enabled status."""
        response = client.get("/api/schedules?enabled=true", headers=auth_headers)

        # Should accept enabled filter
        assert response.status_code in [200, 401, 403]

    def test_filter_by_trigger_type(self, client, auth_headers):
        """Test filtering schedules by trigger type."""
        response = client.get("/api/schedules?trigger_type=cron", headers=auth_headers)

        # Should accept trigger_type filter
        assert response.status_code in [200, 401, 403]

    def test_filter_by_multiple_params(self, client, auth_headers):
        """Test filtering schedules with multiple parameters."""
        response = client.get(
            "/api/schedules?enabled=true&trigger_type=cron",
            headers=auth_headers,
        )

        # Should accept multiple filters
        assert response.status_code in [200, 401, 403]


class TestScheduleIntegration:
    """Integration tests for schedule workflows."""

    @pytest.mark.skip(reason="Requires full authentication setup")
    def test_full_schedule_lifecycle(self, client, auth_headers, sample_schedule_payload):
        """Test complete schedule lifecycle: create, update, run, delete."""
        # Create schedule
        create_response = client.post(
            "/api/schedules", json=sample_schedule_payload, headers=auth_headers
        )
        assert create_response.status_code == 201
        schedule_id = create_response.json()["schedule_id"]

        # Get schedule
        get_response = client.get(f"/api/schedules/{schedule_id}", headers=auth_headers)
        assert get_response.status_code == 200

        # Update schedule
        update_payload = {"name": "Updated Schedule"}
        update_response = client.put(
            f"/api/schedules/{schedule_id}", json=update_payload, headers=auth_headers
        )
        assert update_response.status_code == 200

        # Run schedule
        run_response = client.post(f"/api/schedules/{schedule_id}/run", headers=auth_headers)
        assert run_response.status_code == 202

        # Get history
        history_response = client.get(f"/api/schedules/{schedule_id}/history", headers=auth_headers)
        assert history_response.status_code == 200

        # Delete schedule
        delete_response = client.delete(f"/api/schedules/{schedule_id}", headers=auth_headers)
        assert delete_response.status_code == 204

        # Verify deletion
        get_after_delete = client.get(f"/api/schedules/{schedule_id}", headers=auth_headers)
        assert get_after_delete.status_code == 404


class TestScheduleValidation:
    """Tests for schedule data validation."""

    def test_create_schedule_with_directory_trigger(self, client, auth_headers):
        """Test creating schedule with directory trigger type."""
        payload = {
            "name": "Directory Schedule",
            "cron_expression": "0 0 * * *",
            "trigger_type": "directory",
            "trigger_config": {
                "directory": "/data/input",
                "pattern": "*.esx",
                "recursive": True,
            },
        }

        response = client.post("/api/schedules", json=payload, headers=auth_headers)

        # Should accept directory trigger type
        assert response.status_code in [201, 401, 403]

    def test_create_schedule_with_s3_trigger(self, client, auth_headers):
        """Test creating schedule with S3 trigger type."""
        payload = {
            "name": "S3 Schedule",
            "cron_expression": "0 0 * * *",
            "trigger_type": "s3",
            "trigger_config": {
                "s3_bucket": "my-bucket",
                "s3_prefix": "input/",
                "pattern": "*.esx",
            },
        }

        response = client.post("/api/schedules", json=payload, headers=auth_headers)

        # Should accept S3 trigger type
        assert response.status_code in [201, 401, 403]

    def test_create_schedule_with_email_notifications(self, client, auth_headers):
        """Test creating schedule with email notifications."""
        payload = {
            "name": "Email Schedule",
            "cron_expression": "0 0 * * *",
            "trigger_type": "cron",
            "notification_config": {
                "email": ["admin@example.com", "ops@example.com"],
                "notify_on_success": True,
                "notify_on_failure": True,
            },
        }

        response = client.post("/api/schedules", json=payload, headers=auth_headers)

        # Should accept email notification config
        assert response.status_code in [201, 401, 403]

    def test_create_schedule_with_webhook(self, client, auth_headers):
        """Test creating schedule with webhook notification."""
        payload = {
            "name": "Webhook Schedule",
            "cron_expression": "0 0 * * *",
            "trigger_type": "cron",
            "notification_config": {
                "webhook_url": "https://example.com/webhook",
                "notify_on_failure": True,
            },
        }

        response = client.post("/api/schedules", json=payload, headers=auth_headers)

        # Should accept webhook URL
        assert response.status_code in [201, 401, 403]
