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
