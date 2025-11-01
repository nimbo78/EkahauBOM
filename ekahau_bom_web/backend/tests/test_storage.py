"""Tests for Storage Service."""

import asyncio
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from app.models import ProjectMetadata, ProcessingStatus
from app.services.storage import StorageService


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage service."""
    storage = StorageService()
    storage.projects_dir = tmp_path / "projects"
    storage.projects_dir.mkdir(parents=True, exist_ok=True)
    yield storage
    # Cleanup
    if storage.projects_dir.exists():
        shutil.rmtree(storage.projects_dir)


@pytest.fixture
def sample_metadata():
    """Create sample project metadata."""
    return ProjectMetadata(
        project_id=uuid4(),
        filename="test.esx",
        file_size=1024,
        processing_status=ProcessingStatus.PENDING,
        original_file="projects/test/original.esx",
    )


def test_save_and_load_metadata(temp_storage, sample_metadata):
    """Test saving and loading metadata."""
    # Save metadata
    temp_storage.save_metadata(sample_metadata.project_id, sample_metadata)

    # Load metadata
    loaded = temp_storage.load_metadata(sample_metadata.project_id)

    assert loaded is not None
    assert loaded.project_id == sample_metadata.project_id
    assert loaded.filename == sample_metadata.filename
    assert loaded.file_size == sample_metadata.file_size
    assert loaded.processing_status == sample_metadata.processing_status


def test_load_nonexistent_metadata(temp_storage):
    """Test loading metadata for non-existent project."""
    result = temp_storage.load_metadata(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_save_uploaded_file(temp_storage, sample_metadata):
    """Test saving uploaded file."""
    file_content = b"Test file content"

    # Save file
    file_path = await temp_storage.save_uploaded_file(
        sample_metadata.project_id, "test.esx", file_content
    )

    # Check file exists
    assert file_path.exists()
    assert file_path.name == "original.esx"

    # Check content
    with open(file_path, "rb") as f:
        assert f.read() == file_content


def test_get_project_dir(temp_storage, sample_metadata):
    """Test getting project directory."""
    project_dir = temp_storage.get_project_dir(sample_metadata.project_id)

    assert project_dir == temp_storage.projects_dir / str(sample_metadata.project_id)


def test_list_report_files_empty(temp_storage, sample_metadata):
    """Test listing report files when directory doesn't exist."""
    files = temp_storage.list_report_files(sample_metadata.project_id)
    assert files == []


def test_list_report_files(temp_storage, sample_metadata):
    """Test listing report files."""
    # Create reports directory with some files
    reports_dir = temp_storage.get_reports_dir(sample_metadata.project_id)
    reports_dir.mkdir(parents=True)

    # Create test files
    (reports_dir / "report1.csv").write_text("test")
    (reports_dir / "report2.xlsx").write_text("test")

    files = temp_storage.list_report_files(sample_metadata.project_id)

    assert len(files) == 2
    assert "report1.csv" in files
    assert "report2.xlsx" in files


def test_list_visualization_files(temp_storage, sample_metadata):
    """Test listing visualization files."""
    # Create visualizations directory with some files
    viz_dir = temp_storage.get_visualizations_dir(sample_metadata.project_id)
    viz_dir.mkdir(parents=True)

    # Create test files
    (viz_dir / "floor1.png").write_text("test")
    (viz_dir / "floor2.png").write_text("test")
    (viz_dir / "readme.txt").write_text("test")  # Should be ignored

    files = temp_storage.list_visualization_files(sample_metadata.project_id)

    assert len(files) == 2
    assert "floor1.png" in files
    assert "floor2.png" in files
    assert "readme.txt" not in files  # Only .png files


def test_delete_project(temp_storage, sample_metadata):
    """Test deleting project."""
    # Create project directory with some files
    project_dir = temp_storage.get_project_dir(sample_metadata.project_id)
    project_dir.mkdir(parents=True)
    (project_dir / "test.txt").write_text("test")

    # Verify it exists
    assert project_dir.exists()

    # Delete project
    temp_storage.delete_project(sample_metadata.project_id)

    # Verify it's deleted
    assert not project_dir.exists()
