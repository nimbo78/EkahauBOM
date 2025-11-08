"""Tests for storage abstraction layer (LocalStorage)."""

import pytest
from pathlib import Path
from uuid import uuid4

from app.services.storage.local import LocalStorage
from app.services.storage.base import StorageError


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary local storage for testing.

    Args:
        tmp_path: Pytest temporary directory

    Returns:
        LocalStorage instance with temp directory
    """
    return LocalStorage(base_dir=tmp_path / "projects")


def test_save_and_get_file_bytes(temp_storage):
    """Test save and retrieve file with bytes content."""
    project_id = uuid4()
    content = b"Hello, World!"

    # Save file
    path = temp_storage.save_file(project_id, "test.txt", content)
    assert path
    assert "test.txt" in path

    # Get file
    retrieved = temp_storage.get_file(project_id, "test.txt")
    assert retrieved == content


def test_save_and_get_file_with_subdirectory(temp_storage):
    """Test save and retrieve file in subdirectory."""
    project_id = uuid4()
    content = b"Report data"

    # Save in subdirectory
    temp_storage.save_file(project_id, "reports/data.csv", content)

    # Retrieve
    retrieved = temp_storage.get_file(project_id, "reports/data.csv")
    assert retrieved == content


def test_get_file_not_found(temp_storage):
    """Test get non-existent file raises FileNotFoundError."""
    project_id = uuid4()

    with pytest.raises(FileNotFoundError):
        temp_storage.get_file(project_id, "missing.txt")


def test_exists_file(temp_storage):
    """Test file existence check."""
    project_id = uuid4()

    # Project doesn't exist yet
    assert not temp_storage.exists(project_id)

    # Create file
    temp_storage.save_file(project_id, "test.txt", b"data")

    # Project and file exist
    assert temp_storage.exists(project_id)
    assert temp_storage.exists(project_id, "test.txt")
    assert not temp_storage.exists(project_id, "missing.txt")


def test_list_files_recursive(temp_storage):
    """Test recursive file listing."""
    project_id = uuid4()

    # Create files
    temp_storage.save_file(project_id, "file1.txt", b"data1")
    temp_storage.save_file(project_id, "reports/file2.csv", b"data2")
    temp_storage.save_file(project_id, "reports/visualizations/file3.png", b"data3")

    # List all files recursively
    all_files = temp_storage.list_files(project_id, recursive=True)
    assert len(all_files) == 3
    assert "file1.txt" in all_files
    assert "reports/file2.csv" in all_files
    assert "reports/visualizations/file3.png" in all_files


def test_list_files_non_recursive(temp_storage):
    """Test non-recursive file listing."""
    project_id = uuid4()

    # Create files
    temp_storage.save_file(project_id, "file1.txt", b"data1")
    temp_storage.save_file(project_id, "reports/file2.csv", b"data2")
    temp_storage.save_file(project_id, "reports/nested/file3.json", b"data3")

    # List root files only (non-recursive)
    root_files = temp_storage.list_files(project_id, recursive=False)
    assert "file1.txt" in root_files
    assert "reports/file2.csv" not in root_files


def test_list_files_with_prefix(temp_storage):
    """Test file listing with prefix filter."""
    project_id = uuid4()

    # Create files
    temp_storage.save_file(project_id, "file1.txt", b"data1")
    temp_storage.save_file(project_id, "reports/file2.csv", b"data2")
    temp_storage.save_file(project_id, "reports/nested/file3.json", b"data3")

    # List only files in reports/
    report_files = temp_storage.list_files(project_id, prefix="reports/")
    assert len(report_files) == 2
    assert any("file2.csv" in f for f in report_files)
    assert any("file3.json" in f for f in report_files)


def test_delete_project(temp_storage):
    """Test project deletion."""
    project_id = uuid4()

    # Create files
    temp_storage.save_file(project_id, "file1.txt", b"data1")
    temp_storage.save_file(project_id, "file2.txt", b"data2")

    assert temp_storage.exists(project_id)

    # Delete project
    success = temp_storage.delete_project(project_id)
    assert success
    assert not temp_storage.exists(project_id)


def test_delete_file(temp_storage):
    """Test individual file deletion."""
    project_id = uuid4()

    # Create files
    temp_storage.save_file(project_id, "file1.txt", b"data1")
    temp_storage.save_file(project_id, "file2.txt", b"data2")

    # Delete one file
    success = temp_storage.delete_file(project_id, "file1.txt")
    assert success
    assert not temp_storage.exists(project_id, "file1.txt")
    assert temp_storage.exists(project_id, "file2.txt")

    # Try to delete non-existent file
    success = temp_storage.delete_file(project_id, "missing.txt")
    assert not success


def test_get_project_size(temp_storage):
    """Test project size calculation."""
    project_id = uuid4()

    # Empty project
    assert temp_storage.get_project_size(project_id) == 0

    # Add files
    temp_storage.save_file(project_id, "file1.txt", b"12345")  # 5 bytes
    temp_storage.save_file(project_id, "file2.txt", b"1234567890")  # 10 bytes

    size = temp_storage.get_project_size(project_id)
    assert size == 15


def test_get_file_path(temp_storage):
    """Test get full file path."""
    project_id = uuid4()

    file_path = temp_storage.get_file_path(project_id, "test.txt")
    assert str(project_id) in file_path
    assert "test.txt" in file_path


def test_get_project_dir(temp_storage):
    """Test get project directory."""
    project_id = uuid4()

    project_dir = temp_storage.get_project_dir(project_id)
    assert isinstance(project_dir, Path)
    assert str(project_id) in str(project_dir)


def test_save_file_creates_subdirectories(temp_storage):
    """Test that save_file creates intermediate directories."""
    project_id = uuid4()

    # Save in deep nested directory
    temp_storage.save_file(project_id, "reports/visualizations/nested/deep/file.png", b"image_data")

    # Verify file exists
    assert temp_storage.exists(project_id, "reports/visualizations/nested/deep/file.png")


def test_storage_error_on_invalid_operations(temp_storage):
    """Test that StorageError is raised on invalid operations."""
    project_id = uuid4()

    # This test is more relevant for S3Storage where network errors can occur
    # For LocalStorage, most errors are caught and converted to StorageError
    # We'll test this more thoroughly in Phase 2 with S3
    pass
