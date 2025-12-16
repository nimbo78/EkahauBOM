"""Tests for Comparison API endpoints."""

from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
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
    storage.projects_dir = tmp_path / "projects"

    # Patch the storage service in all relevant modules
    monkeypatch.setattr("app.api.upload.storage_service", storage)
    monkeypatch.setattr("app.api.projects.storage_service", storage)
    monkeypatch.setattr("app.api.reports.storage_service", storage)
    monkeypatch.setattr("app.api.comparison.storage_service", storage)

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


@pytest.fixture
def sample_project_with_comparison(temp_storage, sample_project):
    """Create a sample project with comparison data."""
    project_id = sample_project.project_id
    project_dir = temp_storage.get_project_dir(project_id)

    # Create comparison directory
    comparison_dir = project_dir / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)

    # Create comparison data
    comparison_data = {
        "project_a_name": "Old Version",
        "project_b_name": "New Version",
        "project_a_filename": "test_old.esx",
        "project_b_filename": "test.esx",
        "comparison_timestamp": datetime.now(UTC).isoformat(),
        "total_changes": 5,
        "has_changes": True,
        "inventory": {
            "old_total_aps": 10,
            "new_total_aps": 12,
            "aps_added": 3,
            "aps_removed": 1,
            "aps_modified": 2,
            "aps_moved": 1,
            "aps_renamed": 0,
            "aps_unchanged": 6,
        },
        "metadata_change": None,
        "ap_changes": [
            {
                "status": "added",
                "ap_name": "AP-NEW-1",
                "floor_name": "Floor 1",
                "old_name": None,
                "new_name": None,
                "distance_moved": None,
                "old_coords": None,
                "new_coords": None,
                "changes": [],
            },
            {
                "status": "removed",
                "ap_name": "AP-OLD-1",
                "floor_name": "Floor 1",
                "old_name": None,
                "new_name": None,
                "distance_moved": None,
                "old_coords": None,
                "new_coords": None,
                "changes": [],
            },
            {
                "status": "modified",
                "ap_name": "AP-1",
                "floor_name": "Floor 1",
                "old_name": None,
                "new_name": None,
                "distance_moved": None,
                "old_coords": None,
                "new_coords": None,
                "changes": [
                    {
                        "field_name": "channel",
                        "category": "radio",
                        "old_value": "36",
                        "new_value": "44",
                    }
                ],
            },
            {
                "status": "moved",
                "ap_name": "AP-2",
                "floor_name": "Floor 2",
                "old_name": None,
                "new_name": None,
                "distance_moved": 2.5,
                "old_coords": [10.0, 20.0],
                "new_coords": [12.0, 21.5],
                "changes": [],
            },
        ],
        "changes_by_floor": {
            "Floor 1": [
                {
                    "status": "added",
                    "ap_name": "AP-NEW-1",
                    "floor_name": "Floor 1",
                    "old_name": None,
                    "new_name": None,
                    "distance_moved": None,
                    "old_coords": None,
                    "new_coords": None,
                    "changes": [],
                },
            ],
            "Floor 2": [
                {
                    "status": "moved",
                    "ap_name": "AP-2",
                    "floor_name": "Floor 2",
                    "old_name": None,
                    "new_name": None,
                    "distance_moved": 2.5,
                    "old_coords": [10.0, 20.0],
                    "new_coords": [12.0, 21.5],
                    "changes": [],
                },
            ],
        },
        "floors": ["Floor 1", "Floor 2"],
        "diff_images": {
            "Floor 1": "diff_floor_1.png",
            "Floor 2": "diff_floor_2.png",
        },
    }

    # Save comparison data
    comparison_file = comparison_dir / "comparison_data.json"
    with open(comparison_file, "w", encoding="utf-8") as f:
        json.dump(comparison_data, f, indent=2, ensure_ascii=False)

    # Create visualization files
    viz_dir = comparison_dir / "visualizations"
    viz_dir.mkdir(parents=True, exist_ok=True)
    (viz_dir / "diff_floor_1.png").write_bytes(b"fake png data for floor 1")
    (viz_dir / "diff_floor_2.png").write_bytes(b"fake png data for floor 2")

    # Create comparison report files
    (comparison_dir / "test_comparison.csv").write_text(
        "AP Name,Status,Floor\nAP-1,modified,Floor 1"
    )
    (comparison_dir / "test_comparison.json").write_text(json.dumps(comparison_data))
    (comparison_dir / "test_comparison.html").write_text(
        "<html><body>Comparison Report</body></html>"
    )

    return sample_project


# ============================================================================
# Test GET /comparison/{project_id}
# ============================================================================


def test_get_comparison(temp_storage, sample_project_with_comparison):
    """Test getting full comparison data."""
    project_id = sample_project_with_comparison.project_id
    response = client.get(f"/api/comparison/{project_id}")

    assert response.status_code == 200
    data = response.json()

    # Check basic fields
    assert data["project_a_name"] == "Old Version"
    assert data["project_b_name"] == "New Version"
    assert data["total_changes"] == 5
    assert data["has_changes"] is True

    # Check inventory
    assert data["inventory"]["old_total_aps"] == 10
    assert data["inventory"]["new_total_aps"] == 12
    assert data["inventory"]["aps_added"] == 3
    assert data["inventory"]["aps_removed"] == 1

    # Check AP changes
    assert len(data["ap_changes"]) == 4
    assert any(c["status"] == "added" for c in data["ap_changes"])
    assert any(c["status"] == "removed" for c in data["ap_changes"])
    assert any(c["status"] == "modified" for c in data["ap_changes"])
    assert any(c["status"] == "moved" for c in data["ap_changes"])

    # Check floors
    assert "Floor 1" in data["floors"]
    assert "Floor 2" in data["floors"]


def test_get_comparison_not_found(temp_storage, sample_project):
    """Test getting comparison for project without comparison data."""
    project_id = sample_project.project_id
    response = client.get(f"/api/comparison/{project_id}")

    assert response.status_code == 404
    assert "No comparison data available" in response.json()["detail"]


def test_get_comparison_project_not_found(temp_storage):
    """Test getting comparison for non-existent project."""
    response = client.get(f"/api/comparison/{uuid4()}")

    assert response.status_code == 404
    assert "Project not found" in response.json()["detail"]


# ============================================================================
# Test GET /comparison/{project_id}/summary
# ============================================================================


def test_get_comparison_summary(temp_storage, sample_project_with_comparison):
    """Test getting comparison summary."""
    project_id = sample_project_with_comparison.project_id
    response = client.get(f"/api/comparison/{project_id}/summary")

    assert response.status_code == 200
    data = response.json()

    assert data["has_comparison"] is True
    assert data["total_changes"] == 5
    assert data["aps_added"] == 3
    assert data["aps_removed"] == 1
    assert data["aps_modified"] == 2
    assert data["aps_moved"] == 1
    assert data["aps_renamed"] == 0
    assert "comparison_timestamp" in data


def test_get_comparison_summary_no_comparison(temp_storage, sample_project):
    """Test getting summary for project without comparison data."""
    project_id = sample_project.project_id
    response = client.get(f"/api/comparison/{project_id}/summary")

    assert response.status_code == 200
    data = response.json()

    assert data["has_comparison"] is False
    assert data.get("total_changes", 0) == 0


def test_get_comparison_summary_project_not_found(temp_storage):
    """Test getting summary for non-existent project."""
    response = client.get(f"/api/comparison/{uuid4()}/summary")

    assert response.status_code == 404


# ============================================================================
# Test GET /comparison/{project_id}/diff/{floor_name}
# ============================================================================


def test_get_diff_image(temp_storage, sample_project_with_comparison):
    """Test getting a diff image for a floor."""
    project_id = sample_project_with_comparison.project_id
    response = client.get(f"/api/comparison/{project_id}/diff/Floor 1")

    assert response.status_code == 200
    assert response.content == b"fake png data for floor 1"
    assert response.headers["content-type"] == "image/png"


def test_get_diff_image_floor_2(temp_storage, sample_project_with_comparison):
    """Test getting a diff image for floor 2."""
    project_id = sample_project_with_comparison.project_id
    response = client.get(f"/api/comparison/{project_id}/diff/Floor 2")

    assert response.status_code == 200
    assert response.content == b"fake png data for floor 2"


def test_get_diff_image_floor_not_found(temp_storage, sample_project_with_comparison):
    """Test getting diff image for non-existent floor."""
    project_id = sample_project_with_comparison.project_id
    response = client.get(f"/api/comparison/{project_id}/diff/NonExistentFloor")

    assert response.status_code == 404
    assert "No diff image for floor" in response.json()["detail"]


def test_get_diff_image_no_comparison(temp_storage, sample_project):
    """Test getting diff image when no comparison exists."""
    project_id = sample_project.project_id
    response = client.get(f"/api/comparison/{project_id}/diff/Floor 1")

    assert response.status_code == 404
    assert "No comparison data available" in response.json()["detail"]


def test_get_diff_image_project_not_found(temp_storage):
    """Test getting diff image for non-existent project."""
    response = client.get(f"/api/comparison/{uuid4()}/diff/Floor 1")

    assert response.status_code == 404


# ============================================================================
# Test GET /comparison/{project_id}/diff-images
# ============================================================================


def test_list_diff_images(temp_storage, sample_project_with_comparison):
    """Test listing all available diff images."""
    project_id = sample_project_with_comparison.project_id
    response = client.get(f"/api/comparison/{project_id}/diff-images")

    assert response.status_code == 200
    data = response.json()

    assert data["project_id"] == str(project_id)
    assert "diff_images" in data
    assert "Floor 1" in data["diff_images"]
    assert "Floor 2" in data["diff_images"]
    assert f"/api/comparison/{project_id}/diff/Floor 1" in data["diff_images"]["Floor 1"]


def test_list_diff_images_no_comparison(temp_storage, sample_project):
    """Test listing diff images when no comparison exists."""
    project_id = sample_project.project_id
    response = client.get(f"/api/comparison/{project_id}/diff-images")

    assert response.status_code == 200
    data = response.json()

    assert data["project_id"] == str(project_id)
    assert data["diff_images"] == {}


def test_list_diff_images_project_not_found(temp_storage):
    """Test listing diff images for non-existent project."""
    response = client.get(f"/api/comparison/{uuid4()}/diff-images")

    assert response.status_code == 404


# ============================================================================
# Test GET /comparison/{project_id}/report/{format}
# ============================================================================


def test_download_comparison_report_csv(temp_storage, sample_project_with_comparison):
    """Test downloading comparison report in CSV format."""
    project_id = sample_project_with_comparison.project_id
    response = client.get(f"/api/comparison/{project_id}/report/csv")

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "AP Name,Status,Floor" in response.text


def test_download_comparison_report_json(temp_storage, sample_project_with_comparison):
    """Test downloading comparison report in JSON format."""
    project_id = sample_project_with_comparison.project_id
    response = client.get(f"/api/comparison/{project_id}/report/json")

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    data = response.json()
    assert "total_changes" in data


def test_download_comparison_report_html(temp_storage, sample_project_with_comparison):
    """Test downloading comparison report in HTML format."""
    project_id = sample_project_with_comparison.project_id
    response = client.get(f"/api/comparison/{project_id}/report/html")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Comparison Report" in response.text


def test_download_comparison_report_no_comparison(temp_storage, sample_project):
    """Test downloading report when no comparison exists."""
    project_id = sample_project.project_id
    response = client.get(f"/api/comparison/{project_id}/report/csv")

    assert response.status_code == 404
    assert "No comparison data available" in response.json()["detail"]


def test_download_comparison_report_format_not_found(temp_storage, sample_project_with_comparison):
    """Test downloading report in format that doesn't exist."""
    project_id = sample_project_with_comparison.project_id

    # Remove the CSV file to simulate missing format
    project_dir = temp_storage.get_project_dir(project_id)
    comparison_dir = project_dir / "comparison"
    (comparison_dir / "test_comparison.csv").unlink()

    response = client.get(f"/api/comparison/{project_id}/report/csv")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_download_comparison_report_project_not_found(temp_storage):
    """Test downloading report for non-existent project."""
    response = client.get(f"/api/comparison/{uuid4()}/report/csv")

    assert response.status_code == 404


# ============================================================================
# Test DELETE /comparison/{project_id}
# ============================================================================


def test_delete_comparison(temp_storage, sample_project_with_comparison):
    """Test deleting comparison data."""
    project_id = sample_project_with_comparison.project_id

    # Verify comparison exists
    response = client.get(f"/api/comparison/{project_id}/summary")
    assert response.json()["has_comparison"] is True

    # Delete comparison
    response = client.delete(f"/api/comparison/{project_id}")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify comparison no longer exists
    response = client.get(f"/api/comparison/{project_id}/summary")
    assert response.json()["has_comparison"] is False


def test_delete_comparison_no_data(temp_storage, sample_project):
    """Test deleting comparison when none exists."""
    project_id = sample_project.project_id
    response = client.delete(f"/api/comparison/{project_id}")

    assert response.status_code == 200
    assert "No comparison data to delete" in response.json()["message"]


def test_delete_comparison_project_not_found(temp_storage):
    """Test deleting comparison for non-existent project."""
    response = client.delete(f"/api/comparison/{uuid4()}")

    assert response.status_code == 404


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================


def test_comparison_data_with_renamed_ap(temp_storage, sample_project):
    """Test comparison data with renamed AP."""
    project_id = sample_project.project_id
    project_dir = temp_storage.get_project_dir(project_id)

    # Create comparison with renamed AP
    comparison_dir = project_dir / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)

    comparison_data = {
        "project_a_name": "Old",
        "project_b_name": "New",
        "project_a_filename": "old.esx",
        "project_b_filename": "new.esx",
        "comparison_timestamp": datetime.now(UTC).isoformat(),
        "total_changes": 1,
        "has_changes": True,
        "inventory": {
            "old_total_aps": 1,
            "new_total_aps": 1,
            "aps_added": 0,
            "aps_removed": 0,
            "aps_modified": 0,
            "aps_moved": 0,
            "aps_renamed": 1,
            "aps_unchanged": 0,
        },
        "ap_changes": [
            {
                "status": "renamed",
                "ap_name": "AP-NEW-NAME",
                "floor_name": "Floor 1",
                "old_name": "AP-OLD-NAME",
                "new_name": "AP-NEW-NAME",
                "distance_moved": None,
                "old_coords": None,
                "new_coords": None,
                "changes": [],
            }
        ],
        "changes_by_floor": {},
        "floors": ["Floor 1"],
        "diff_images": {},
    }

    comparison_file = comparison_dir / "comparison_data.json"
    with open(comparison_file, "w", encoding="utf-8") as f:
        json.dump(comparison_data, f)

    # Verify renamed AP data
    response = client.get(f"/api/comparison/{project_id}")
    assert response.status_code == 200
    data = response.json()

    renamed_ap = data["ap_changes"][0]
    assert renamed_ap["status"] == "renamed"
    assert renamed_ap["old_name"] == "AP-OLD-NAME"
    assert renamed_ap["new_name"] == "AP-NEW-NAME"


def test_comparison_data_with_detailed_changes(temp_storage, sample_project):
    """Test comparison data with detailed field changes."""
    project_id = sample_project.project_id
    project_dir = temp_storage.get_project_dir(project_id)

    # Create comparison with detailed changes
    comparison_dir = project_dir / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)

    comparison_data = {
        "project_a_name": "Old",
        "project_b_name": "New",
        "project_a_filename": "old.esx",
        "project_b_filename": "new.esx",
        "comparison_timestamp": datetime.now(UTC).isoformat(),
        "total_changes": 1,
        "has_changes": True,
        "inventory": {
            "old_total_aps": 1,
            "new_total_aps": 1,
            "aps_added": 0,
            "aps_removed": 0,
            "aps_modified": 1,
            "aps_moved": 0,
            "aps_renamed": 0,
            "aps_unchanged": 0,
        },
        "ap_changes": [
            {
                "status": "modified",
                "ap_name": "AP-1",
                "floor_name": "Floor 1",
                "old_name": None,
                "new_name": None,
                "distance_moved": None,
                "old_coords": None,
                "new_coords": None,
                "changes": [
                    {
                        "field_name": "channel",
                        "category": "radio",
                        "old_value": "36",
                        "new_value": "44",
                    },
                    {
                        "field_name": "tx_power",
                        "category": "radio",
                        "old_value": "17",
                        "new_value": "20",
                    },
                    {
                        "field_name": "mounting_height",
                        "category": "placement",
                        "old_value": "3.0",
                        "new_value": "2.5",
                    },
                ],
            }
        ],
        "changes_by_floor": {},
        "floors": ["Floor 1"],
        "diff_images": {},
    }

    comparison_file = comparison_dir / "comparison_data.json"
    with open(comparison_file, "w", encoding="utf-8") as f:
        json.dump(comparison_data, f)

    # Verify detailed changes
    response = client.get(f"/api/comparison/{project_id}")
    assert response.status_code == 200
    data = response.json()

    changes = data["ap_changes"][0]["changes"]
    assert len(changes) == 3
    assert any(c["field_name"] == "channel" and c["old_value"] == "36" for c in changes)
    assert any(c["field_name"] == "tx_power" for c in changes)
    assert any(c["field_name"] == "mounting_height" for c in changes)


def test_comparison_empty_changes(temp_storage, sample_project):
    """Test comparison with no changes (identical projects)."""
    project_id = sample_project.project_id
    project_dir = temp_storage.get_project_dir(project_id)

    comparison_dir = project_dir / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)

    comparison_data = {
        "project_a_name": "Version 1",
        "project_b_name": "Version 2",
        "project_a_filename": "v1.esx",
        "project_b_filename": "v2.esx",
        "comparison_timestamp": datetime.now(UTC).isoformat(),
        "total_changes": 0,
        "has_changes": False,
        "inventory": {
            "old_total_aps": 10,
            "new_total_aps": 10,
            "aps_added": 0,
            "aps_removed": 0,
            "aps_modified": 0,
            "aps_moved": 0,
            "aps_renamed": 0,
            "aps_unchanged": 10,
        },
        "ap_changes": [],
        "changes_by_floor": {},
        "floors": [],
        "diff_images": {},
    }

    comparison_file = comparison_dir / "comparison_data.json"
    with open(comparison_file, "w", encoding="utf-8") as f:
        json.dump(comparison_data, f)

    # Verify empty comparison
    response = client.get(f"/api/comparison/{project_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["total_changes"] == 0
    assert data["has_changes"] is False
    assert len(data["ap_changes"]) == 0
    assert data["inventory"]["aps_unchanged"] == 10


def test_url_encoded_floor_name(temp_storage, sample_project_with_comparison):
    """Test getting diff image with URL-encoded floor name."""
    project_id = sample_project_with_comparison.project_id

    # Floor 1 contains a space, test URL encoding
    response = client.get(f"/api/comparison/{project_id}/diff/Floor%201")
    assert response.status_code == 200
