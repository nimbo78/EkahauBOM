"""Tests for Batch API endpoints."""

from __future__ import annotations

import io
import json
import zipfile
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import BatchStatus, ProcessingStatus, ProjectMetadata
from app.services.batch_service import batch_service
from app.services.index import index_service
from app.services.storage_service import StorageService

client = TestClient(app)


@pytest.fixture
def temp_storage(tmp_path, monkeypatch):
    """Create temporary storage service and patch it in the app."""
    from app.services.storage.local import LocalStorage

    # Create storage with temp backend
    storage = StorageService()
    temp_backend = LocalStorage(base_dir=tmp_path / "projects")
    storage.backend = temp_backend
    storage.base_dir = tmp_path / "projects"

    # Patch the storage service
    monkeypatch.setattr("app.api.batches.storage_service", storage)
    monkeypatch.setattr("app.services.batch_service.StorageService", lambda: storage)

    # Update batch_service instance
    batch_service.storage = storage

    # Clear index
    index_service._projects = {}

    yield storage

    # Cleanup
    index_service._projects = {}


@pytest.fixture
def admin_headers():
    """Get admin authentication headers."""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "EkahauAdmin"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data, f"No access_token in response: {data}"
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_esx_file():
    """Create a sample .esx file in memory."""
    esx_buffer = io.BytesIO()
    with zipfile.ZipFile(esx_buffer, "w") as zf:
        # Add project.json
        project_data = {
            "project": {"name": "Test Project"},
            "accessPoints": [{"id": 1, "name": "AP1"}],
        }
        zf.writestr("project.json", json.dumps(project_data))

    esx_buffer.seek(0)
    return esx_buffer


@pytest.fixture
def sample_batch(temp_storage, admin_headers, sample_esx_file):
    """Create a sample batch with uploaded files."""
    # Create two test files
    files = [
        ("files", ("test1.esx", io.BytesIO(sample_esx_file.read()), "application/octet-stream")),
        ("files", ("test2.esx", io.BytesIO(sample_esx_file.read()), "application/octet-stream")),
    ]

    response = client.post(
        "/api/batches/upload",
        files=files,
        data={"batch_name": "Test Batch", "parallel_workers": "2"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    return response.json()


class TestBatchUploadEndpoint:
    """Tests for POST /batches/upload."""

    def test_upload_batch_success(self, temp_storage, admin_headers, sample_esx_file):
        """Test successful batch upload."""
        files = [
            (
                "files",
                ("test1.esx", io.BytesIO(sample_esx_file.read()), "application/octet-stream"),
            ),
            (
                "files",
                ("test2.esx", io.BytesIO(sample_esx_file.read()), "application/octet-stream"),
            ),
        ]

        response = client.post(
            "/api/batches/upload",
            files=files,
            data={"batch_name": "My Batch", "parallel_workers": "2"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "batch_id" in data
        assert data["files_count"] == 2
        assert len(data["files_uploaded"]) == 2
        assert len(data["files_failed"]) == 0
        assert "test1.esx" in data["files_uploaded"]
        assert "test2.esx" in data["files_uploaded"]

    def test_upload_batch_without_auth(self, temp_storage, sample_esx_file):
        """Test batch upload without authentication fails."""
        files = [
            ("files", ("test.esx", sample_esx_file, "application/octet-stream")),
        ]

        response = client.post(
            "/api/batches/upload",
            files=files,
            data={"batch_name": "Test Batch"},
        )

        # FastAPI returns 403 when no credentials provided
        assert response.status_code == 403

    def test_upload_batch_no_files(self, temp_storage, admin_headers):
        """Test batch upload with no files fails."""
        response = client.post(
            "/api/batches/upload",
            files=[],
            data={"batch_name": "Test Batch"},
            headers=admin_headers,
        )

        # FastAPI returns 422 for validation errors
        assert response.status_code == 422

    def test_upload_batch_invalid_workers(self, temp_storage, admin_headers, sample_esx_file):
        """Test batch upload with invalid parallel_workers."""
        files = [
            ("files", ("test.esx", sample_esx_file, "application/octet-stream")),
        ]

        response = client.post(
            "/api/batches/upload",
            files=files,
            data={"parallel_workers": "10"},  # Max is 8
            headers=admin_headers,
        )

        assert response.status_code == 400
        assert "parallel_workers must be between 1 and 8" in response.json()["detail"]

    def test_upload_batch_with_invalid_file_extension(self, temp_storage, admin_headers):
        """Test batch upload with invalid file extension."""
        files = [
            ("files", ("test.txt", io.BytesIO(b"test content"), "text/plain")),
        ]

        response = client.post(
            "/api/batches/upload",
            files=files,
            data={"batch_name": "Test Batch"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["files_failed"]) == 1
        assert "test.txt" in data["files_failed"]

    def test_upload_batch_with_processing_options(
        self, temp_storage, admin_headers, sample_esx_file
    ):
        """Test batch upload with processing options."""
        files = [
            ("files", ("test.esx", sample_esx_file, "application/octet-stream")),
        ]

        processing_options = {
            "group_by": "floor",
            "output_formats": ["csv", "excel"],
            "visualize_floor_plans": True,
        }

        response = client.post(
            "/api/batches/upload",
            files=files,
            data={
                "batch_name": "Test Batch",
                "processing_options": json.dumps(processing_options),
            },
            headers=admin_headers,
        )

        assert response.status_code == 200


class TestListBatchesEndpoint:
    """Tests for GET /batches."""

    def test_list_batches_empty(self, temp_storage):
        """Test listing batches when none exist."""
        response = client.get("/api/batches")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_batches_single(self, temp_storage, sample_batch):
        """Test listing single batch."""
        response = client.get("/api/batches")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["batch_id"] == sample_batch["batch_id"]
        assert data[0]["total_projects"] == 2

    def test_list_batches_with_status_filter(self, temp_storage, sample_batch):
        """Test listing batches with status filter."""
        # Get all batches to see actual status
        response = client.get("/api/batches")
        assert response.status_code == 200
        all_batches = response.json()
        assert len(all_batches) >= 1

        # Get the actual status of the sample batch (might be processing, completed, or failed)
        sample_status = all_batches[0]["status"] if all_batches else None

        # Filter by the actual status
        if sample_status:
            response = client.get(f"/api/batches?status={sample_status}")
            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1

    def test_list_batches_with_limit(self, temp_storage, admin_headers, sample_esx_file):
        """Test listing batches with limit."""
        # Create multiple batches
        for i in range(3):
            files = [
                (
                    "files",
                    (
                        f"test{i}.esx",
                        io.BytesIO(sample_esx_file.read()),
                        "application/octet-stream",
                    ),
                ),
            ]
            client.post(
                "/api/batches/upload",
                files=files,
                data={"batch_name": f"Batch {i}"},
                headers=admin_headers,
            )

        # List with limit
        response = client.get("/api/batches?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestGetBatchEndpoint:
    """Tests for GET /batches/{batch_id}."""

    def test_get_batch_success(self, temp_storage, sample_batch):
        """Test getting batch details."""
        batch_id = sample_batch["batch_id"]
        response = client.get(f"/api/batches/{batch_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == batch_id
        assert "statistics" in data
        assert "project_statuses" in data

    def test_get_batch_not_found(self, temp_storage):
        """Test getting non-existent batch."""
        fake_id = str(uuid4())
        response = client.get(f"/api/batches/{fake_id}")

        assert response.status_code == 404


class TestProcessBatchEndpoint:
    """Tests for POST /batches/{batch_id}/process."""

    def test_process_batch_success(self, temp_storage, sample_batch, admin_headers):
        """Test starting batch processing."""
        batch_id = sample_batch["batch_id"]
        response = client.post(f"/api/batches/{batch_id}/process", headers=admin_headers)

        # Should accept the request
        assert response.status_code in [200, 409]  # 409 if already processing

    def test_process_batch_without_auth(self, temp_storage, sample_batch):
        """Test processing batch without authentication fails."""
        batch_id = sample_batch["batch_id"]
        response = client.post(f"/api/batches/{batch_id}/process")

        # FastAPI returns 403 when no credentials provided
        assert response.status_code == 403

    def test_process_batch_not_found(self, temp_storage, admin_headers):
        """Test processing non-existent batch."""
        fake_id = str(uuid4())
        response = client.post(f"/api/batches/{fake_id}/process", headers=admin_headers)

        assert response.status_code == 404


class TestGetBatchStatusEndpoint:
    """Tests for GET /batches/{batch_id}/status."""

    def test_get_batch_status_success(self, temp_storage, sample_batch):
        """Test getting batch status."""
        batch_id = sample_batch["batch_id"]
        response = client.get(f"/api/batches/{batch_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert "batch_id" in data
        assert "status" in data
        assert "total_projects" in data
        assert "completed_projects" in data
        assert "failed_projects" in data
        assert "statistics" in data

    def test_get_batch_status_not_found(self, temp_storage):
        """Test getting status of non-existent batch."""
        fake_id = str(uuid4())
        response = client.get(f"/api/batches/{fake_id}/status")

        assert response.status_code == 404


class TestDeleteBatchEndpoint:
    """Tests for DELETE /batches/{batch_id}."""

    def test_delete_batch_success(self, temp_storage, sample_batch, admin_headers):
        """Test deleting batch."""
        batch_id = sample_batch["batch_id"]

        # Verify batch exists
        response = client.get(f"/api/batches/{batch_id}")
        assert response.status_code == 200

        # Delete batch
        response = client.delete(f"/api/batches/{batch_id}", headers=admin_headers)
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify batch is gone
        response = client.get(f"/api/batches/{batch_id}")
        assert response.status_code == 404

    def test_delete_batch_without_auth(self, temp_storage, sample_batch):
        """Test deleting batch without authentication fails."""
        batch_id = sample_batch["batch_id"]
        response = client.delete(f"/api/batches/{batch_id}")

        # FastAPI returns 403 when no credentials provided
        assert response.status_code == 403

    def test_delete_batch_not_found(self, temp_storage, admin_headers):
        """Test deleting non-existent batch."""
        fake_id = str(uuid4())
        response = client.delete(f"/api/batches/{fake_id}", headers=admin_headers)

        assert response.status_code == 404


class TestBatchEndToEnd:
    """End-to-end tests for batch processing workflow."""

    def test_complete_batch_workflow(self, temp_storage, admin_headers, sample_esx_file):
        """Test complete batch workflow: upload -> list -> get -> delete."""
        # 1. Upload batch
        files = [
            (
                "files",
                ("test1.esx", io.BytesIO(sample_esx_file.read()), "application/octet-stream"),
            ),
            (
                "files",
                ("test2.esx", io.BytesIO(sample_esx_file.read()), "application/octet-stream"),
            ),
        ]

        upload_response = client.post(
            "/api/batches/upload",
            files=files,
            data={"batch_name": "E2E Test Batch", "parallel_workers": "2"},
            headers=admin_headers,
        )
        assert upload_response.status_code == 200
        batch_id = upload_response.json()["batch_id"]

        # 2. List batches
        list_response = client.get("/api/batches")
        assert list_response.status_code == 200
        batches = list_response.json()
        assert any(b["batch_id"] == batch_id for b in batches)

        # 3. Get batch details
        get_response = client.get(f"/api/batches/{batch_id}")
        assert get_response.status_code == 200
        batch_data = get_response.json()
        assert batch_data["batch_name"] == "E2E Test Batch"
        assert len(batch_data["project_ids"]) == 2

        # 4. Get batch status
        status_response = client.get(f"/api/batches/{batch_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["total_projects"] == 2

        # 5. Delete batch
        delete_response = client.delete(f"/api/batches/{batch_id}", headers=admin_headers)
        assert delete_response.status_code == 200

        # 6. Verify deletion
        get_deleted_response = client.get(f"/api/batches/{batch_id}")
        assert get_deleted_response.status_code == 404


class TestBatchTagsEndpoints:
    """Tests for batch tags functionality."""

    def test_add_tags_to_batch(self, sample_batch, admin_headers):
        """Test adding tags to a batch."""
        batch_id = sample_batch["batch_id"]

        # Add tags
        response = client.patch(
            f"/api/batches/{batch_id}/tags",
            params={"tags_to_add": ["customer-x", "production", "urgent"]},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == batch_id
        assert set(data["tags"]) == {"customer-x", "production", "urgent"}
        assert "message" in data

    def test_remove_tags_from_batch(self, sample_batch, admin_headers):
        """Test removing tags from a batch."""
        batch_id = sample_batch["batch_id"]

        # First add tags
        client.patch(
            f"/api/batches/{batch_id}/tags",
            params={"tags_to_add": ["tag1", "tag2", "tag3"]},
            headers=admin_headers,
        )

        # Remove one tag
        response = client.patch(
            f"/api/batches/{batch_id}/tags",
            params={"tags_to_remove": ["tag2"]},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert set(data["tags"]) == {"tag1", "tag3"}

    def test_add_and_remove_tags_simultaneously(self, sample_batch, admin_headers):
        """Test adding and removing tags in same request."""
        batch_id = sample_batch["batch_id"]

        # Add initial tags
        client.patch(
            f"/api/batches/{batch_id}/tags",
            params={"tags_to_add": ["tag1", "tag2", "tag3"]},
            headers=admin_headers,
        )

        # Add and remove tags simultaneously
        response = client.patch(
            f"/api/batches/{batch_id}/tags",
            params={"tags_to_add": ["tag4", "tag5"], "tags_to_remove": ["tag2"]},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert set(data["tags"]) == {"tag1", "tag3", "tag4", "tag5"}

    def test_add_duplicate_tag(self, sample_batch, admin_headers):
        """Test that duplicate tags are not added."""
        batch_id = sample_batch["batch_id"]

        # Add tag first time
        client.patch(
            f"/api/batches/{batch_id}/tags",
            params={"tags_to_add": ["duplicate-tag"]},
            headers=admin_headers,
        )

        # Try to add same tag again
        response = client.patch(
            f"/api/batches/{batch_id}/tags",
            params={"tags_to_add": ["duplicate-tag"]},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should still have only one instance of the tag
        assert data["tags"].count("duplicate-tag") == 1

    def test_remove_nonexistent_tag(self, sample_batch, admin_headers):
        """Test removing a tag that doesn't exist (should succeed silently)."""
        batch_id = sample_batch["batch_id"]

        # Remove tag that doesn't exist
        response = client.patch(
            f"/api/batches/{batch_id}/tags",
            params={"tags_to_remove": ["nonexistent-tag"]},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "nonexistent-tag" not in data["tags"]

    def test_filter_batches_by_tags(self, temp_storage, admin_headers, sample_esx_file):
        """Test filtering batches by tags."""
        # Create batch 1 with tags
        files1 = [
            (
                "files",
                ("test1.esx", io.BytesIO(sample_esx_file.read()), "application/octet-stream"),
            ),
        ]
        response1 = client.post(
            "/api/batches/upload",
            files=files1,
            data={"batch_name": "Batch 1"},
            headers=admin_headers,
        )
        batch1_id = response1.json()["batch_id"]
        client.patch(
            f"/api/batches/{batch1_id}/tags",
            params={"tags_to_add": ["production", "customer-a"]},
            headers=admin_headers,
        )

        # Create batch 2 with different tags
        sample_esx_file.seek(0)  # Reset file pointer
        files2 = [
            (
                "files",
                ("test2.esx", io.BytesIO(sample_esx_file.read()), "application/octet-stream"),
            ),
        ]
        response2 = client.post(
            "/api/batches/upload",
            files=files2,
            data={"batch_name": "Batch 2"},
            headers=admin_headers,
        )
        batch2_id = response2.json()["batch_id"]
        client.patch(
            f"/api/batches/{batch2_id}/tags",
            params={"tags_to_add": ["testing", "customer-b"]},
            headers=admin_headers,
        )

        # Filter by "production" tag
        response = client.get("/api/batches", params={"tags": "production"})
        assert response.status_code == 200
        batches = response.json()
        batch_ids = [b["batch_id"] for b in batches]
        assert batch1_id in batch_ids
        assert batch2_id not in batch_ids

        # Filter by multiple tags (must have ALL tags)
        response = client.get("/api/batches", params={"tags": "production,customer-a"})
        assert response.status_code == 200
        batches = response.json()
        batch_ids = [b["batch_id"] for b in batches]
        assert batch1_id in batch_ids
        assert batch2_id not in batch_ids

    def test_tags_persist_across_reload(self, sample_batch, admin_headers):
        """Test that tags persist when batch is reloaded."""
        batch_id = sample_batch["batch_id"]

        # Add tags
        client.patch(
            f"/api/batches/{batch_id}/tags",
            params={"tags_to_add": ["persistent-tag"]},
            headers=admin_headers,
        )

        # Reload batch metadata
        response = client.get(f"/api/batches/{batch_id}")
        assert response.status_code == 200
        batch_data = response.json()
        assert "persistent-tag" in batch_data["tags"]

    def test_tags_included_in_batch_list(self, sample_batch, admin_headers):
        """Test that tags are included in batch list response."""
        batch_id = sample_batch["batch_id"]

        # Add tags
        client.patch(
            f"/api/batches/{batch_id}/tags",
            params={"tags_to_add": ["list-tag"]},
            headers=admin_headers,
        )

        # Get batch list
        response = client.get("/api/batches")
        assert response.status_code == 200
        batches = response.json()

        # Find our batch
        our_batch = next((b for b in batches if b["batch_id"] == batch_id), None)
        assert our_batch is not None
        assert "list-tag" in our_batch["tags"]

    def test_tags_are_sorted(self, sample_batch, admin_headers):
        """Test that tags are returned in sorted order."""
        batch_id = sample_batch["batch_id"]

        # Add tags in random order
        response = client.patch(
            f"/api/batches/{batch_id}/tags",
            params={"tags_to_add": ["zebra", "apple", "mango", "banana"]},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Tags should be sorted alphabetically
        assert data["tags"] == ["apple", "banana", "mango", "zebra"]

    def test_empty_tag_ignored(self, sample_batch, admin_headers):
        """Test that empty tags are ignored."""
        batch_id = sample_batch["batch_id"]

        # Try to add empty tag
        response = client.patch(
            f"/api/batches/{batch_id}/tags",
            params={"tags_to_add": ["valid-tag", "", "  ", "another-valid-tag"]},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "" not in data["tags"]
        assert "  " not in data["tags"]
        assert "valid-tag" in data["tags"]
        assert "another-valid-tag" in data["tags"]


# Test class for Advanced Search and Filtering


class TestBatchAdvancedFiltering:
    """Tests for advanced batch filtering and searching."""

    def test_search_by_batch_name(self, multiple_batches, admin_headers):
        """Test searching batches by name."""
        response = client.get("/api/batches", params={"search": "Batch 1"}, headers=admin_headers)
        assert response.status_code == 200
        batches = response.json()
        # Should find 'Batch 1' and 'Batch 11' (partial match)
        assert len(batches) >= 1
        assert any("Batch 1" in b["batch_name"] or b["batch_name"] is None for b in batches)

    def test_date_range_filter(self, multiple_batches, admin_headers):
        """Test filtering by date range."""
        # Get all batches first
        response_all = client.get("/api/batches", headers=admin_headers)
        all_batches = response_all.json()

        if len(all_batches) > 0:
            # Use first batch date as reference
            ref_date = all_batches[0]["created_date"]

            # Test created_after filter
            response = client.get(
                "/api/batches", params={"created_after": ref_date}, headers=admin_headers
            )
            assert response.status_code == 200
            batches = response.json()
            assert len(batches) >= 1

    def test_project_count_filter(self, multiple_batches, admin_headers):
        """Test filtering by project count."""
        # Filter batches with at least 1 project
        response = client.get("/api/batches", params={"min_projects": 1}, headers=admin_headers)
        assert response.status_code == 200
        batches = response.json()
        for batch in batches:
            assert batch["total_projects"] >= 1

    def test_sort_by_name(self, multiple_batches, admin_headers):
        """Test sorting batches by name."""
        response = client.get(
            "/api/batches", params={"sort_by": "name", "sort_order": "asc"}, headers=admin_headers
        )
        assert response.status_code == 200
        batches = response.json()

        # Check that batches are sorted by name
        if len(batches) > 1:
            for i in range(len(batches) - 1):
                name1 = (batches[i]["batch_name"] or "").lower()
                name2 = (batches[i + 1]["batch_name"] or "").lower()
                assert name1 <= name2

    def test_sort_by_project_count(self, multiple_batches, admin_headers):
        """Test sorting batches by project count."""
        response = client.get(
            "/api/batches",
            params={"sort_by": "project_count", "sort_order": "desc"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        batches = response.json()

        # Check descending order
        if len(batches) > 1:
            for i in range(len(batches) - 1):
                assert batches[i]["total_projects"] >= batches[i + 1]["total_projects"]

    def test_combined_filters(self, multiple_batches, admin_headers):
        """Test combining multiple filters."""
        response = client.get(
            "/api/batches",
            params={"min_projects": 0, "sort_by": "date", "sort_order": "desc"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        batches = response.json()
        assert isinstance(batches, list)

    def test_invalid_sort_by(self, admin_headers):
        """Test invalid sort_by parameter."""
        response = client.get(
            "/api/batches", params={"sort_by": "invalid_field"}, headers=admin_headers
        )
        # Should return 422 Unprocessable Entity due to regex validation
        assert response.status_code == 422

    def test_invalid_date_format(self, admin_headers):
        """Test invalid date format."""
        response = client.get(
            "/api/batches", params={"created_after": "not-a-date"}, headers=admin_headers
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid" in data["detail"] or "date" in data["detail"].lower()

    def test_tags_filter_with_search(self, admin_headers):
        """Test combining tags filter with search."""
        # First create a batch with tags
        batch_response = client.post(
            "/api/batches/upload",
            data={"batch_name": "Tagged Batch", "parallel_workers": "1"},
            files=[],
            headers=admin_headers,
        )
        batch_id = batch_response.json()["batch_id"]

        # Add tags
        client.patch(
            f"/api/batches/{batch_id}/tags",
            params={"tags_to_add": ["important", "production"]},
            headers=admin_headers,
        )

        # Search with tags filter
        response = client.get(
            "/api/batches", params={"tags": "important", "search": "Tagged"}, headers=admin_headers
        )
        assert response.status_code == 200
        batches = response.json()
        assert len(batches) >= 1

        # Cleanup
        client.delete(f"/api/batches/{batch_id}", headers=admin_headers)
