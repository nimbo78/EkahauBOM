"""Tests for advanced batch filtering and search functionality."""

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


class TestBatchAdvancedFiltering:
    """Tests for advanced batch filtering and searching."""

    def test_search_param_accepted(self, admin_headers):
        """Test that search parameter is accepted."""
        response = client.get("/api/batches", params={"search": "test"}, headers=admin_headers)
        assert response.status_code == 200
        batches = response.json()
        assert isinstance(batches, list)

    def test_date_range_filter_accepted(self, admin_headers):
        """Test that date range filters are accepted."""
        response = client.get(
            "/api/batches", params={"created_after": "2025-01-01T00:00:00Z"}, headers=admin_headers
        )
        assert response.status_code == 200
        batches = response.json()
        assert isinstance(batches, list)

    def test_project_count_min_filter(self, admin_headers):
        """Test min_projects filter."""
        response = client.get("/api/batches", params={"min_projects": 0}, headers=admin_headers)
        assert response.status_code == 200
        batches = response.json()
        assert isinstance(batches, list)
        # All batches should have >= 0 projects
        for batch in batches:
            assert batch["total_projects"] >= 0

    def test_project_count_max_filter(self, admin_headers):
        """Test max_projects filter."""
        response = client.get("/api/batches", params={"max_projects": 100}, headers=admin_headers)
        assert response.status_code == 200
        batches = response.json()
        assert isinstance(batches, list)
        # All batches should have <= 100 projects
        for batch in batches:
            assert batch["total_projects"] <= 100

    def test_sort_by_date(self, admin_headers):
        """Test sorting by date."""
        response = client.get(
            "/api/batches", params={"sort_by": "date", "sort_order": "desc"}, headers=admin_headers
        )
        assert response.status_code == 200
        batches = response.json()
        assert isinstance(batches, list)

    def test_sort_by_name(self, admin_headers):
        """Test sorting by name."""
        response = client.get(
            "/api/batches", params={"sort_by": "name", "sort_order": "asc"}, headers=admin_headers
        )
        assert response.status_code == 200
        batches = response.json()
        assert isinstance(batches, list)

    def test_sort_by_project_count(self, admin_headers):
        """Test sorting by project count."""
        response = client.get(
            "/api/batches",
            params={"sort_by": "project_count", "sort_order": "desc"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        batches = response.json()
        assert isinstance(batches, list)

    def test_sort_by_success_rate(self, admin_headers):
        """Test sorting by success rate."""
        response = client.get(
            "/api/batches",
            params={"sort_by": "success_rate", "sort_order": "desc"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        batches = response.json()
        assert isinstance(batches, list)

    def test_combined_filters(self, admin_headers):
        """Test combining multiple filters."""
        response = client.get(
            "/api/batches",
            params={"min_projects": 0, "max_projects": 50, "sort_by": "date", "sort_order": "desc"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        batches = response.json()
        assert isinstance(batches, list)
        # Verify combined filters work
        for batch in batches:
            assert 0 <= batch["total_projects"] <= 50

    def test_invalid_sort_by(self, admin_headers):
        """Test invalid sort_by parameter."""
        response = client.get(
            "/api/batches", params={"sort_by": "invalid_field"}, headers=admin_headers
        )
        # Should return 422 Unprocessable Entity due to pattern validation
        assert response.status_code == 422

    def test_invalid_sort_order(self, admin_headers):
        """Test invalid sort_order parameter."""
        response = client.get(
            "/api/batches", params={"sort_order": "invalid"}, headers=admin_headers
        )
        # Should return 422 Unprocessable Entity
        assert response.status_code == 422

    def test_invalid_date_format(self, admin_headers):
        """Test invalid date format."""
        response = client.get(
            "/api/batches", params={"created_after": "not-a-date"}, headers=admin_headers
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid" in data["detail"] or "date" in data["detail"].lower()

    def test_negative_project_count(self, admin_headers):
        """Test negative project count is rejected."""
        response = client.get("/api/batches", params={"min_projects": -1}, headers=admin_headers)
        # Should return 422 due to ge=0 validation
        assert response.status_code == 422

    def test_tags_filter_with_multiple_tags(self, admin_headers):
        """Test filtering by multiple tags."""
        response = client.get("/api/batches", params={"tags": "tag1,tag2"}, headers=admin_headers)
        assert response.status_code == 200
        batches = response.json()
        assert isinstance(batches, list)

    def test_limit_parameter(self, admin_headers):
        """Test limit parameter."""
        response = client.get("/api/batches", params={"limit": 5}, headers=admin_headers)
        assert response.status_code == 200
        batches = response.json()
        assert isinstance(batches, list)
        # Should return at most 5 batches
        assert len(batches) <= 5

    def test_all_filters_combined(self, admin_headers):
        """Test all filter parameters together."""
        response = client.get(
            "/api/batches",
            params={
                "search": "test",
                "tags": "important",
                "min_projects": 0,
                "max_projects": 10,
                "sort_by": "name",
                "sort_order": "asc",
                "limit": 10,
            },
            headers=admin_headers,
        )
        assert response.status_code == 200
        batches = response.json()
        assert isinstance(batches, list)
        assert len(batches) <= 10
