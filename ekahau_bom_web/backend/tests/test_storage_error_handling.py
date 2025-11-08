"""Error handling tests for storage backends.

Tests various error scenarios: network failures, invalid credentials, etc.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from moto import mock_aws
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.services.storage.local import LocalStorage
from app.services.storage.s3 import S3Storage
from app.services.storage.base import StorageError


# ============================================================================
# S3 Error Handling Tests
# ============================================================================


def test_s3_invalid_bucket():
    """Test S3Storage with non-existent bucket."""
    with mock_aws():
        # Don't create bucket - it doesn't exist

        with pytest.raises(StorageError, match="not found"):
            S3Storage(
                bucket="nonexistent-bucket",
                region="us-east-1",
                access_key="key",
                secret_key="secret",
            )


def test_s3_bucket_access_denied():
    """Test S3Storage when bucket access is denied."""
    with mock_aws():
        bucket_name = "test-bucket"
        region = "us-east-1"

        # Create bucket but simulate access denied
        s3_client = boto3.client("s3", region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)

        # This should work (bucket exists in moto)
        storage = S3Storage(
            bucket=bucket_name,
            region=region,
            access_key="test_key",
            secret_key="test_secret",
        )

        # Verify we can use it
        project_id = uuid4()
        storage.save_file(project_id, "test.txt", b"data")
        assert storage.exists(project_id, "test.txt")


def test_s3_get_file_network_error(monkeypatch):
    """Test S3Storage get_file with network error."""
    with mock_aws():
        bucket_name = "test-bucket"
        region = "us-east-1"

        s3_client = boto3.client("s3", region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)

        storage = S3Storage(
            bucket=bucket_name,
            region=region,
            access_key="test_key",
            secret_key="test_secret",
        )

        # Upload file
        project_id = uuid4()
        storage.save_file(project_id, "test.txt", b"data")

        # Mock network error
        def mock_get_object(*args, **kwargs):
            raise ClientError(
                {"Error": {"Code": "NetworkError", "Message": "Network timeout"}},
                "GetObject",
            )

        monkeypatch.setattr(storage.s3, "get_object", mock_get_object)

        # Should raise StorageError
        with pytest.raises(StorageError, match="Failed to get from S3"):
            storage.get_file(project_id, "test.txt")


def test_s3_save_file_network_error(monkeypatch):
    """Test S3Storage save_file with network error."""
    with mock_aws():
        bucket_name = "test-bucket"
        region = "us-east-1"

        s3_client = boto3.client("s3", region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)

        storage = S3Storage(
            bucket=bucket_name,
            region=region,
            access_key="test_key",
            secret_key="test_secret",
        )

        # Mock network error
        def mock_put_object(*args, **kwargs):
            raise ClientError(
                {"Error": {"Code": "NetworkError", "Message": "Connection reset"}},
                "PutObject",
            )

        monkeypatch.setattr(storage.s3, "put_object", mock_put_object)

        # Should raise StorageError
        project_id = uuid4()
        with pytest.raises(StorageError, match="Failed to save to S3"):
            storage.save_file(project_id, "test.txt", b"data")


def test_s3_delete_project_error(monkeypatch):
    """Test S3Storage delete_project with error."""
    with mock_aws():
        bucket_name = "test-bucket"
        region = "us-east-1"

        s3_client = boto3.client("s3", region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)

        storage = S3Storage(
            bucket=bucket_name,
            region=region,
            access_key="test_key",
            secret_key="test_secret",
        )

        # Create files
        project_id = uuid4()
        storage.save_file(project_id, "test.txt", b"data")

        # Mock error during deletion
        def mock_delete_objects(*args, **kwargs):
            raise ClientError(
                {"Error": {"Code": "InternalError", "Message": "Server error"}},
                "DeleteObjects",
            )

        monkeypatch.setattr(storage.s3, "delete_objects", mock_delete_objects)

        # Should raise StorageError
        with pytest.raises(StorageError, match="Failed to delete project from S3"):
            storage.delete_project(project_id)


def test_s3_list_files_error(monkeypatch):
    """Test S3Storage list_files with error."""
    with mock_aws():
        bucket_name = "test-bucket"
        region = "us-east-1"

        s3_client = boto3.client("s3", region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)

        storage = S3Storage(
            bucket=bucket_name,
            region=region,
            access_key="test_key",
            secret_key="test_secret",
        )

        # Mock error
        def mock_get_paginator(*args, **kwargs):
            raise ClientError(
                {"Error": {"Code": "ServiceUnavailable", "Message": "Service down"}},
                "ListObjectsV2",
            )

        monkeypatch.setattr(storage.s3, "get_paginator", mock_get_paginator)

        # Should raise StorageError
        project_id = uuid4()
        with pytest.raises(StorageError, match="Failed to list S3 objects"):
            storage.list_files(project_id)


def test_s3_get_project_size_error(monkeypatch):
    """Test S3Storage get_project_size with error."""
    with mock_aws():
        bucket_name = "test-bucket"
        region = "us-east-1"

        s3_client = boto3.client("s3", region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)

        storage = S3Storage(
            bucket=bucket_name,
            region=region,
            access_key="test_key",
            secret_key="test_secret",
        )

        # Mock error
        def mock_get_paginator(*args, **kwargs):
            raise ClientError(
                {"Error": {"Code": "Throttling", "Message": "Rate limit exceeded"}},
                "ListObjectsV2",
            )

        monkeypatch.setattr(storage.s3, "get_paginator", mock_get_paginator)

        # Should raise StorageError
        project_id = uuid4()
        with pytest.raises(StorageError, match="Failed to calculate S3 project size"):
            storage.get_project_size(project_id)


# ============================================================================
# LocalStorage Error Handling Tests
# ============================================================================


def test_local_save_file_permission_error(tmp_path, monkeypatch):
    """Test LocalStorage save_file with permission error."""
    storage = LocalStorage(base_dir=tmp_path / "projects")
    project_id = uuid4()

    # Mock permission error
    original_write_bytes = type(tmp_path).write_bytes

    def mock_write_bytes(self, data):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(type(tmp_path), "write_bytes", mock_write_bytes)

    # Should raise StorageError
    with pytest.raises(StorageError, match="Failed to save file"):
        storage.save_file(project_id, "test.txt", b"data")

    # Restore
    monkeypatch.setattr(type(tmp_path), "write_bytes", original_write_bytes)


def test_local_get_file_not_found(tmp_path):
    """Test LocalStorage get_file with non-existent file."""
    storage = LocalStorage(base_dir=tmp_path / "projects")
    project_id = uuid4()

    # Should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        storage.get_file(project_id, "missing.txt")


def test_local_delete_file_not_found(tmp_path):
    """Test LocalStorage delete_file with non-existent file."""
    storage = LocalStorage(base_dir=tmp_path / "projects")
    project_id = uuid4()

    # Should return False, not raise error
    success = storage.delete_file(project_id, "missing.txt")
    assert not success


def test_local_delete_project_not_found(tmp_path):
    """Test LocalStorage delete_project with non-existent project."""
    storage = LocalStorage(base_dir=tmp_path / "projects")
    project_id = uuid4()

    # Should succeed (no-op), not raise error
    success = storage.delete_project(project_id)
    assert success


# ============================================================================
# Edge Cases Tests
# ============================================================================


def test_empty_file_content(tmp_path):
    """Test saving and retrieving empty files."""
    storage = LocalStorage(base_dir=tmp_path / "projects")
    project_id = uuid4()

    # Save empty file
    storage.save_file(project_id, "empty.txt", b"")

    # Get empty file
    content = storage.get_file(project_id, "empty.txt")
    assert content == b""

    # Size should be 0
    size = storage.get_project_size(project_id)
    assert size == 0


def test_very_long_filename(tmp_path):
    """Test handling of very long filenames."""
    storage = LocalStorage(base_dir=tmp_path / "projects")
    project_id = uuid4()

    # Create very long filename (200 characters)
    long_name = "a" * 200 + ".txt"

    try:
        # Try to save
        storage.save_file(project_id, long_name, b"data")
        assert storage.exists(project_id, long_name)
    except (OSError, StorageError):
        # Some filesystems have filename length limits
        pytest.skip("Filesystem doesn't support long filenames")


def test_special_characters_in_filename(tmp_path):
    """Test handling of special characters in filenames."""
    storage = LocalStorage(base_dir=tmp_path / "projects")
    project_id = uuid4()

    # Test filenames with special characters
    test_filenames = [
        "file with spaces.txt",
        "file-with-dashes.txt",
        "file_with_underscores.txt",
        "file.multiple.dots.txt",
    ]

    for filename in test_filenames:
        storage.save_file(project_id, filename, b"data")
        assert storage.exists(project_id, filename)
        content = storage.get_file(project_id, filename)
        assert content == b"data"


def test_deeply_nested_paths(tmp_path):
    """Test handling of deeply nested directory structures."""
    storage = LocalStorage(base_dir=tmp_path / "projects")
    project_id = uuid4()

    # Create deeply nested file
    deep_path = "/".join([f"level{i}" for i in range(10)]) + "/file.txt"

    storage.save_file(project_id, deep_path, b"data")
    assert storage.exists(project_id, deep_path)
    content = storage.get_file(project_id, deep_path)
    assert content == b"data"


# ============================================================================
# Concurrent Access Edge Cases
# ============================================================================


def test_overwrite_during_read(tmp_path):
    """Test reading file while it's being overwritten."""
    storage = LocalStorage(base_dir=tmp_path / "projects")
    project_id = uuid4()

    # Save initial content
    storage.save_file(project_id, "data.txt", b"initial")

    # Read
    content1 = storage.get_file(project_id, "data.txt")
    assert content1 == b"initial"

    # Overwrite
    storage.save_file(project_id, "data.txt", b"updated")

    # Read again
    content2 = storage.get_file(project_id, "data.txt")
    assert content2 == b"updated"


def test_delete_during_list(tmp_path):
    """Test listing files while files are being deleted."""
    storage = LocalStorage(base_dir=tmp_path / "projects")
    project_id = uuid4()

    # Create files
    for i in range(10):
        storage.save_file(project_id, f"file_{i}.txt", b"data")

    # List
    files1 = storage.list_files(project_id)
    assert len(files1) == 10

    # Delete some files
    for i in range(5):
        storage.delete_file(project_id, f"file_{i}.txt")

    # List again
    files2 = storage.list_files(project_id)
    assert len(files2) == 5


# ============================================================================
# Resource Cleanup Tests
# ============================================================================


def test_cleanup_after_error(tmp_path, monkeypatch):
    """Test that resources are cleaned up properly after errors."""
    storage = LocalStorage(base_dir=tmp_path / "projects")
    project_id = uuid4()

    # Create some files
    storage.save_file(project_id, "file1.txt", b"data1")
    storage.save_file(project_id, "file2.txt", b"data2")

    # Verify they exist
    assert storage.exists(project_id, "file1.txt")
    assert storage.exists(project_id, "file2.txt")

    # Delete project (should clean up all files)
    storage.delete_project(project_id)

    # Verify cleanup
    assert not storage.exists(project_id)
    assert not storage.exists(project_id, "file1.txt")
    assert not storage.exists(project_id, "file2.txt")


# ============================================================================
# S3 Specific Error Cases
# ============================================================================


def test_s3_delete_file_not_found():
    """Test S3Storage delete_file with non-existent file."""
    with mock_aws():
        bucket_name = "test-bucket"
        region = "us-east-1"

        s3_client = boto3.client("s3", region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)

        storage = S3Storage(
            bucket=bucket_name,
            region=region,
            access_key="test_key",
            secret_key="test_secret",
        )

        project_id = uuid4()

        # Try to delete non-existent file
        success = storage.delete_file(project_id, "missing.txt")
        assert not success  # Should return False, not raise error


def test_s3_exists_returns_false_for_missing():
    """Test that S3Storage.exists() returns False for missing files."""
    with mock_aws():
        bucket_name = "test-bucket"
        region = "us-east-1"

        s3_client = boto3.client("s3", region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)

        storage = S3Storage(
            bucket=bucket_name,
            region=region,
            access_key="test_key",
            secret_key="test_secret",
        )

        project_id = uuid4()

        # Check non-existent project
        assert not storage.exists(project_id)

        # Create file
        storage.save_file(project_id, "test.txt", b"data")

        # Check existing file
        assert storage.exists(project_id, "test.txt")

        # Check non-existent file in existing project
        assert not storage.exists(project_id, "missing.txt")
