"""Tests for Template API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Test credentials
ADMIN_TOKEN = None


@pytest.fixture(scope="module", autouse=True)
def setup_admin_auth():
    """Get admin token for authenticated requests."""
    global ADMIN_TOKEN
    response = client.post("/api/auth/login", json={"username": "admin", "password": "EkahauAdmin"})
    assert response.status_code == 200
    ADMIN_TOKEN = response.json()["access_token"]


@pytest.fixture
def admin_headers():
    """Provide authentication headers."""
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


class TestTemplateListEndpoint:
    """Tests for GET /templates."""

    def test_list_templates_includes_predefined(self):
        """Test that predefined templates are loaded on startup."""
        response = client.get("/api/templates")
        assert response.status_code == 200
        templates = response.json()
        assert isinstance(templates, list)
        assert len(templates) >= 3  # At least 3 predefined templates

        # Check predefined templates exist
        template_names = [t["name"] for t in templates]
        assert "CSV Only" in template_names
        assert "Full Reports" in template_names
        assert "Quick Processing" in template_names

    def test_list_templates_exclude_system(self):
        """Test listing templates without system templates."""
        response = client.get("/api/templates", params={"include_system": False})
        assert response.status_code == 200
        templates = response.json()
        assert isinstance(templates, list)
        # All should be user templates
        for template in templates:
            assert not template["is_system"]


class TestTemplateGetEndpoint:
    """Tests for GET /templates/{template_id}."""

    def test_get_template_success(self):
        """Test getting a specific template."""
        # First list to get an ID
        response = client.get("/api/templates")
        templates = response.json()
        assert len(templates) > 0

        template_id = templates[0]["template_id"]

        # Get specific template
        response = client.get(f"/api/templates/{template_id}")
        assert response.status_code == 200
        template = response.json()
        assert template["template_id"] == template_id
        assert "processing_options" in template
        assert "parallel_workers" in template

    def test_get_template_not_found(self):
        """Test getting non-existent template."""
        response = client.get("/api/templates/00000000-0000-0000-0000-999999999999")
        assert response.status_code == 404


class TestTemplateCreateEndpoint:
    """Tests for POST /templates."""

    def test_create_template_success(self, admin_headers):
        """Test creating a new template."""
        request = {
            "name": "Test Template",
            "description": "A test template",
            "processing_options": {
                "group_by": "vendor",
                "output_formats": ["csv", "excel"],
                "visualize_floor_plans": True,
                "show_azimuth_arrows": False,
            },
            "parallel_workers": 4,
        }

        response = client.post("/api/templates", json=request, headers=admin_headers)
        assert response.status_code == 200
        template = response.json()
        assert template["name"] == "Test Template"
        assert template["description"] == "A test template"
        assert template["parallel_workers"] == 4
        assert not template["is_system"]  # User templates are never system
        assert template["usage_count"] == 0

        # Cleanup
        template_id = template["template_id"]
        client.delete(f"/api/templates/{template_id}", headers=admin_headers)

    def test_create_template_without_auth(self):
        """Test creating template without authentication."""
        request = {
            "name": "Unauthorized Template",
            "processing_options": {},
            "parallel_workers": 1,
        }

        response = client.post("/api/templates", json=request)
        assert response.status_code == 403  # Forbidden (no auth header)


class TestTemplateUpdateEndpoint:
    """Tests for PUT /templates/{template_id}."""

    def test_update_template_success(self, admin_headers):
        """Test updating a user template."""
        # Create a template first
        create_request = {
            "name": "Template to Update",
            "processing_options": {},
            "parallel_workers": 1,
        }
        create_response = client.post("/api/templates", json=create_request, headers=admin_headers)
        template_id = create_response.json()["template_id"]

        # Update it
        update_request = {
            "name": "Updated Template Name",
            "description": "New description",
            "parallel_workers": 8,
        }
        response = client.put(
            f"/api/templates/{template_id}", json=update_request, headers=admin_headers
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["name"] == "Updated Template Name"
        assert updated["description"] == "New description"
        assert updated["parallel_workers"] == 8

        # Cleanup
        client.delete(f"/api/templates/{template_id}", headers=admin_headers)

    def test_update_system_template_fails(self, admin_headers):
        """Test that system templates cannot be updated."""
        # Try to update the "CSV Only" system template
        system_template_id = "00000000-0000-0000-0000-000000000001"

        update_request = {"name": "Modified System Template"}
        response = client.put(
            f"/api/templates/{system_template_id}", json=update_request, headers=admin_headers
        )
        assert response.status_code == 400
        assert "system" in response.json()["detail"].lower()


class TestTemplateDeleteEndpoint:
    """Tests for DELETE /templates/{template_id}."""

    def test_delete_template_success(self, admin_headers):
        """Test deleting a user template."""
        # Create a template first
        create_request = {
            "name": "Template to Delete",
            "processing_options": {},
            "parallel_workers": 1,
        }
        create_response = client.post("/api/templates", json=create_request, headers=admin_headers)
        template_id = create_response.json()["template_id"]

        # Delete it
        response = client.delete(f"/api/templates/{template_id}", headers=admin_headers)
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # Verify it's gone
        get_response = client.get(f"/api/templates/{template_id}")
        assert get_response.status_code == 404

    def test_delete_system_template_fails(self, admin_headers):
        """Test that system templates cannot be deleted."""
        # Try to delete the "CSV Only" system template
        system_template_id = "00000000-0000-0000-0000-000000000001"

        response = client.delete(f"/api/templates/{system_template_id}", headers=admin_headers)
        assert response.status_code == 400
        assert "system" in response.json()["detail"].lower()

    def test_delete_template_not_found(self, admin_headers):
        """Test deleting non-existent template."""
        response = client.delete(
            "/api/templates/00000000-0000-0000-0000-999999999999", headers=admin_headers
        )
        assert response.status_code == 404
