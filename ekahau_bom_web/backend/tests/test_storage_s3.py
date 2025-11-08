"""Tests for S3 storage backend using moto (mock AWS)."""

import pytest
from uuid import uuid4

from moto import mock_aws
import boto3

from app.services.storage.s3 import S3Storage
from app.services.storage.base import StorageError


@pytest.fixture
def s3_storage():
    """Create mock S3 storage for testing.

    Uses moto to mock AWS S3 services without actual network calls.
    """
    with mock_aws():
        # Create mock S3 bucket
        bucket_name = "test-bucket"
        region = "us-east-1"

        # Create bucket using boto3 (mocked)
        s3_client = boto3.client("s3", region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)

        # Create S3Storage instance
        storage = S3Storage(
            bucket=bucket_name,
            region=region,
            access_key="test_key",
            secret_key="test_secret",
        )

        yield storage


def test_save_and_get_file_bytes_s3(s3_storage):
    """Test save and retrieve file from S3 with bytes content."""
    project_id = uuid4()
    content = b"Hello, S3!"

    # Save
    path = s3_storage.save_file(project_id, "test.txt", content)
    assert path.startswith("s3://")
    assert "test.txt" in path

    # Get
    retrieved = s3_storage.get_file(project_id, "test.txt")
    assert retrieved == content


def test_save_and_get_file_with_subdirectory_s3(s3_storage):
    """Test save and retrieve file in subdirectory."""
    project_id = uuid4()
    content = b"Report data"

    # Save in subdirectory
    s3_storage.save_file(project_id, "reports/data.csv", content)

    # Retrieve
    retrieved = s3_storage.get_file(project_id, "reports/data.csv")
    assert retrieved == content


def test_get_file_not_found_s3(s3_storage):
    """Test get non-existent file from S3 raises FileNotFoundError."""
    project_id = uuid4()

    with pytest.raises(FileNotFoundError):
        s3_storage.get_file(project_id, "missing.txt")


def test_exists_file_s3(s3_storage):
    """Test file existence check in S3."""
    project_id = uuid4()

    # Project doesn't exist
    assert not s3_storage.exists(project_id)

    # Create file
    s3_storage.save_file(project_id, "test.txt", b"data")

    # Project and file exist
    assert s3_storage.exists(project_id)
    assert s3_storage.exists(project_id, "test.txt")
    assert not s3_storage.exists(project_id, "missing.txt")


def test_list_files_recursive_s3(s3_storage):
    """Test recursive file listing in S3."""
    project_id = uuid4()

    # Create files
    s3_storage.save_file(project_id, "file1.txt", b"data1")
    s3_storage.save_file(project_id, "reports/file2.csv", b"data2")
    s3_storage.save_file(project_id, "reports/visualizations/file3.png", b"data3")

    # List all files recursively
    all_files = s3_storage.list_files(project_id, recursive=True)
    assert len(all_files) == 3
    assert "file1.txt" in all_files
    assert "reports/file2.csv" in all_files
    assert "reports/visualizations/file3.png" in all_files


def test_list_files_non_recursive_s3(s3_storage):
    """Test non-recursive file listing in S3."""
    project_id = uuid4()

    # Create files
    s3_storage.save_file(project_id, "file1.txt", b"data1")
    s3_storage.save_file(project_id, "reports/file2.csv", b"data2")
    s3_storage.save_file(project_id, "reports/nested/file3.json", b"data3")

    # List root files only (non-recursive)
    root_files = s3_storage.list_files(project_id, recursive=False)
    assert "file1.txt" in root_files
    # Nested files should not be included
    assert not any("/" in f for f in root_files if f != "file1.txt")


def test_list_files_with_prefix_s3(s3_storage):
    """Test file listing with prefix filter in S3."""
    project_id = uuid4()

    # Create files
    s3_storage.save_file(project_id, "file1.txt", b"data1")
    s3_storage.save_file(project_id, "reports/file2.csv", b"data2")
    s3_storage.save_file(project_id, "reports/nested/file3.json", b"data3")

    # List only files in reports/
    report_files = s3_storage.list_files(project_id, prefix="reports/")
    assert len(report_files) == 2
    assert any("file2.csv" in f for f in report_files)
    assert any("file3.json" in f for f in report_files)


def test_delete_project_s3(s3_storage):
    """Test project deletion from S3."""
    project_id = uuid4()

    # Create files
    s3_storage.save_file(project_id, "file1.txt", b"data1")
    s3_storage.save_file(project_id, "file2.txt", b"data2")

    assert s3_storage.exists(project_id)

    # Delete
    success = s3_storage.delete_project(project_id)
    assert success
    assert not s3_storage.exists(project_id)


def test_delete_file_s3(s3_storage):
    """Test individual file deletion from S3."""
    project_id = uuid4()

    # Create files
    s3_storage.save_file(project_id, "file1.txt", b"data1")
    s3_storage.save_file(project_id, "file2.txt", b"data2")

    # Delete one file
    success = s3_storage.delete_file(project_id, "file1.txt")
    assert success
    assert not s3_storage.exists(project_id, "file1.txt")
    assert s3_storage.exists(project_id, "file2.txt")

    # Try to delete non-existent file
    success = s3_storage.delete_file(project_id, "missing.txt")
    assert not success


def test_get_project_size_s3(s3_storage):
    """Test project size calculation in S3."""
    project_id = uuid4()

    # Empty project
    assert s3_storage.get_project_size(project_id) == 0

    # Add files
    s3_storage.save_file(project_id, "file1.txt", b"12345")  # 5 bytes
    s3_storage.save_file(project_id, "file2.txt", b"1234567890")  # 10 bytes

    size = s3_storage.get_project_size(project_id)
    assert size == 15


def test_get_file_path_s3(s3_storage):
    """Test get S3 URI for file."""
    project_id = uuid4()

    file_path = s3_storage.get_file_path(project_id, "test.txt")
    assert file_path.startswith("s3://")
    assert str(project_id) in file_path
    assert "test.txt" in file_path


def test_get_project_dir_s3(s3_storage):
    """Test get S3 prefix for project."""
    project_id = uuid4()

    project_dir = s3_storage.get_project_dir(project_id)
    assert isinstance(project_dir, str)
    assert str(project_id) in project_dir


def test_save_file_creates_nested_structure_s3(s3_storage):
    """Test that save_file creates nested S3 key structure."""
    project_id = uuid4()

    # Save in deep nested directory
    s3_storage.save_file(project_id, "reports/visualizations/nested/deep/file.png", b"image_data")

    # Verify file exists
    assert s3_storage.exists(project_id, "reports/visualizations/nested/deep/file.png")


def test_large_batch_delete_s3(s3_storage):
    """Test deletion of >1000 files (S3 batch limit)."""
    project_id = uuid4()

    # Create 1500 files (exceeds S3 batch delete limit of 1000)
    for i in range(1500):
        s3_storage.save_file(project_id, f"file_{i}.txt", b"data")

    # Verify files exist
    assert s3_storage.exists(project_id)

    # Delete all files
    success = s3_storage.delete_project(project_id)
    assert success

    # Verify all deleted
    assert not s3_storage.exists(project_id)


def test_invalid_bucket_s3():
    """Test handling of invalid bucket."""
    with mock_aws():
        # Don't create bucket
        with pytest.raises(StorageError, match="not found"):
            S3Storage(
                bucket="nonexistent-bucket",
                region="us-east-1",
                access_key="key",
                secret_key="secret",
            )


def test_s3_storage_with_custom_endpoint():
    """Test S3Storage with custom endpoint parameters.

    Note: moto doesn't support custom endpoints well, so we just test
    that parameters are accepted without errors.
    """
    with mock_aws():
        bucket_name = "test-bucket"
        region = "us-east-1"

        # Create bucket
        s3_client = boto3.client("s3", region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)

        # Create storage with custom endpoint parameters (but use mocked default)
        storage = S3Storage(
            bucket=bucket_name,
            region=region,
            access_key="test_key",
            secret_key="test_secret",
            endpoint_url=None,  # Use default (mocked)
            use_ssl=True,
            verify=False,  # Test that verify parameter works
        )

        # Basic test
        project_id = uuid4()
        storage.save_file(project_id, "test.txt", b"data")
        assert storage.exists(project_id, "test.txt")
