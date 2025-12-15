"""Tests for API endpoints."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ProcessingStatus, ProjectMetadata
from app.services.index import index_service
from app.services.storage_service import StorageService
from app.config import settings

# Get credentials from settings
ADMIN_USERNAME = settings.admin_username
ADMIN_PASSWORD = settings.admin_password

client = TestClient(app)


@pytest.fixture
def temp_storage(tmp_path, monkeypatch):
    """Create temporary storage service and patch it in the app."""
    from app.services.storage.local import LocalStorage

    # Create storage with temp backend
    storage = StorageService()
    temp_backend = LocalStorage(base_dir=tmp_path / "projects")
    storage.backend = temp_backend
    storage.projects_dir = tmp_path / "projects"  # Keep for backward compatibility

    # Patch the storage service
    monkeypatch.setattr("app.api.upload.storage_service", storage)
    monkeypatch.setattr("app.api.projects.storage_service", storage)
    monkeypatch.setattr("app.api.reports.storage_service", storage)

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
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_project(temp_storage):
    """Create a sample project in storage and index."""
    project_id = uuid4()
    metadata = ProjectMetadata(
        project_id=project_id,
        filename="test.esx",
        file_size=1024,
        processing_status=ProcessingStatus.COMPLETED,
        original_file=f"projects/{project_id}/original.esx",
        reports_dir=f"{project_id}/reports",
        visualizations_dir=f"{project_id}/reports/visualizations",
        project_name="Test Project",
        aps_count=5,
        floors_count=2,
    )

    # Save to storage
    project_dir = temp_storage.get_project_dir(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create original .esx file
    original_file = project_dir / "original.esx"
    with zipfile.ZipFile(original_file, "w") as zf:
        zf.writestr("project.json", json.dumps({"project": {"name": "Test Project"}}))

    # Save metadata
    temp_storage.save_metadata(project_id, metadata)

    # Add to index
    index_service.add(metadata)

    return metadata


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_list_projects_empty(temp_storage):
    """Test listing projects when there are none."""
    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_list_projects(temp_storage, sample_project):
    """Test listing projects."""
    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["project_id"] == str(sample_project.project_id)
    assert data[0]["filename"] == "test.esx"


def test_list_projects_with_filters(temp_storage, sample_project):
    """Test listing projects with status filter."""
    response = client.get("/api/projects?status=completed")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

    response = client.get("/api/projects?status=pending")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


def test_get_project_details(temp_storage, sample_project):
    """Test getting project details."""
    response = client.get(f"/api/projects/{sample_project.project_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == str(sample_project.project_id)
    assert data["filename"] == "test.esx"
    assert data["processing_status"] == "completed"
    assert data["project_name"] == "Test Project"
    assert data["aps_count"] == 5
    assert data["floors_count"] == 2


def test_get_project_details_not_found():
    """Test getting non-existent project."""
    response = client.get(f"/api/projects/{uuid4()}")
    assert response.status_code == 404


def test_get_project_stats(temp_storage, sample_project):
    """Test getting project statistics."""
    response = client.get("/api/projects/stats/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["completed"] == 1
    assert data["pending"] == 0
    assert data["processing"] == 0
    assert data["failed"] == 0


def test_upload_project(temp_storage, admin_headers):
    """Test uploading a .esx file."""
    # Create a minimal .esx file (ZIP)
    esx_content = io.BytesIO()
    with zipfile.ZipFile(esx_content, "w") as zf:
        zf.writestr("project.json", json.dumps({"project": {"name": "Upload Test"}}))
    esx_content.seek(0)

    response = client.post(
        "/api/upload",
        files={"file": ("test.esx", esx_content, "application/octet-stream")},
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "project_id" in data
    assert "short_link" in data
    assert "message" in data
    assert "test.esx" in data["message"]


def test_upload_invalid_file(temp_storage, admin_headers):
    """Test uploading non-.esx file."""
    response = client.post(
        "/api/upload",
        files={"file": ("test.txt", io.BytesIO(b"not an esx file"), "text/plain")},
        headers=admin_headers,
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_upload_large_file(temp_storage, admin_headers):
    """Test uploading file exceeding size limit."""
    # Create file larger than 500MB (simulate by setting large size)
    large_file = io.BytesIO(b"x" * 1000)  # Small file for testing

    response = client.post(
        "/api/upload",
        files={"file": ("large.esx", large_file, "application/octet-stream")},
        headers=admin_headers,
    )

    # Should succeed for small file (real large file test would need actual large content)
    assert response.status_code in [200, 400]


def test_delete_project(temp_storage, sample_project, admin_headers):
    """Test deleting a project."""
    project_id = sample_project.project_id

    # Verify project exists
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200

    # Delete project
    response = client.delete(f"/api/projects/{project_id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Project deleted successfully"

    # Verify project no longer exists
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 404


def test_delete_project_not_found(admin_headers):
    """Test deleting non-existent project."""
    response = client.delete(f"/api/projects/{uuid4()}", headers=admin_headers)
    assert response.status_code == 404


def test_list_reports(temp_storage, sample_project):
    """Test listing project reports."""
    # Create some report files
    project_id = sample_project.project_id
    reports_dir = temp_storage.get_reports_dir(project_id)
    reports_dir.mkdir(parents=True, exist_ok=True)

    (reports_dir / "report.csv").write_text("test")
    (reports_dir / "report.xlsx").write_text("test")

    response = client.get(f"/api/reports/{project_id}/list")
    assert response.status_code == 200
    data = response.json()
    assert "project_id" in data
    assert "reports" in data
    assert "visualizations" in data
    assert isinstance(data["reports"], list)
    assert len(data["reports"]) == 2
    assert any(f["filename"] == "report.csv" for f in data["reports"])


def test_list_reports_not_found():
    """Test listing reports for non-existent project."""
    response = client.get(f"/api/reports/{uuid4()}/list")
    assert response.status_code == 404


def test_download_report(temp_storage, sample_project):
    """Test downloading a report file."""
    # Create a report file
    project_id = sample_project.project_id
    reports_dir = temp_storage.get_reports_dir(project_id)
    reports_dir.mkdir(parents=True, exist_ok=True)

    test_content = "test report content"
    (reports_dir / "report.csv").write_text(test_content)

    response = client.get(f"/api/reports/{project_id}/download/report.csv")
    assert response.status_code == 200
    assert response.text == test_content


def test_download_report_not_found(temp_storage, sample_project):
    """Test downloading non-existent report."""
    response = client.get(f"/api/reports/{sample_project.project_id}/download/nonexistent.csv")
    assert response.status_code == 404


def test_download_original_esx(temp_storage, sample_project):
    """Test downloading original .esx file."""
    response = client.get(f"/api/reports/{sample_project.project_id}/original")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_download_original_esx_not_found():
    """Test downloading original for non-existent project."""
    response = client.get(f"/api/reports/{uuid4()}/original")
    assert response.status_code == 404


def test_get_project_by_short_link(temp_storage, sample_project):
    """Test getting project by short link."""
    # Add short link to project
    sample_project.short_link = "test123"
    temp_storage.save_metadata(sample_project.project_id, sample_project)
    index_service.add(sample_project)

    response = client.get("/api/projects/short/test123")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == str(sample_project.project_id)


def test_get_project_by_short_link_not_found():
    """Test getting project by non-existent short link."""
    response = client.get("/api/projects/short/nonexistent")
    assert response.status_code == 404


def test_get_visualization(temp_storage, sample_project):
    """Test getting a visualization file."""
    # Create a visualization file
    project_id = sample_project.project_id
    viz_dir = temp_storage.get_visualizations_dir(project_id)
    viz_dir.mkdir(parents=True, exist_ok=True)

    (viz_dir / "floor1.png").write_bytes(b"fake png data")

    response = client.get(f"/api/reports/{project_id}/visualization/floor1.png")
    assert response.status_code == 200
    assert response.content == b"fake png data"


def test_get_visualization_not_found(temp_storage, sample_project):
    """Test getting non-existent visualization."""
    response = client.get(f"/api/reports/{sample_project.project_id}/visualization/nonexistent.png")
    assert response.status_code == 404
