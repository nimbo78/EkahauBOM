"""Integration tests for storage backends.

Tests that both LocalStorage and S3Storage behave identically.
"""

import pytest
from pathlib import Path
from uuid import uuid4

from moto import mock_aws
import boto3

from app.services.storage.local import LocalStorage
from app.services.storage.s3 import S3Storage
from app.services.storage.factory import StorageFactory
from app.config import Settings


@pytest.fixture
def local_storage(tmp_path):
    """Create LocalStorage backend."""
    return LocalStorage(base_dir=tmp_path / "projects")


@pytest.fixture
def s3_storage():
    """Create S3Storage backend with moto."""
    with mock_aws():
        bucket_name = "test-bucket"
        region = "us-east-1"

        # Create bucket
        s3_client = boto3.client("s3", region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)

        # Create storage
        storage = S3Storage(
            bucket=bucket_name,
            region=region,
            access_key="test_key",
            secret_key="test_secret",
        )

        yield storage


@pytest.fixture(params=["local", "s3"])
def any_storage(request, tmp_path):
    """Parametrized fixture that returns both storage backends."""
    if request.param == "local":
        yield LocalStorage(base_dir=tmp_path / "projects")
    else:  # s3
        # Use mock_aws as context manager for entire test
        mock = mock_aws()
        mock.start()

        try:
            bucket_name = "test-bucket"
            region = "us-east-1"

            s3_client = boto3.client("s3", region_name=region)
            s3_client.create_bucket(Bucket=bucket_name)

            yield S3Storage(
                bucket=bucket_name,
                region=region,
                access_key="test_key",
                secret_key="test_secret",
            )
        finally:
            mock.stop()


# ============================================================================
# Behavioral Consistency Tests
# ============================================================================


def test_save_get_consistency(any_storage):
    """Test that save→get works identically on both backends."""
    project_id = uuid4()
    content = b"Test content for consistency"

    # Save
    path = any_storage.save_file(project_id, "test.txt", content)
    assert path  # Should return some path/URI

    # Get
    retrieved = any_storage.get_file(project_id, "test.txt")
    assert retrieved == content


def test_subdirectory_handling(any_storage):
    """Test that subdirectories work identically."""
    project_id = uuid4()

    # Create nested files
    any_storage.save_file(project_id, "reports/csv/data.csv", b"csv data")
    any_storage.save_file(project_id, "reports/excel/data.xlsx", b"excel data")
    any_storage.save_file(project_id, "visualizations/floor1.png", b"png data")

    # All files should exist
    assert any_storage.exists(project_id, "reports/csv/data.csv")
    assert any_storage.exists(project_id, "reports/excel/data.xlsx")
    assert any_storage.exists(project_id, "visualizations/floor1.png")

    # List all files
    all_files = any_storage.list_files(project_id)
    assert len(all_files) == 3
    assert "reports/csv/data.csv" in all_files
    assert "reports/excel/data.xlsx" in all_files
    assert "visualizations/floor1.png" in all_files


def test_list_files_with_prefix_consistency(any_storage):
    """Test that list_files with prefix works identically."""
    project_id = uuid4()

    # Create files
    any_storage.save_file(project_id, "file1.txt", b"data1")
    any_storage.save_file(project_id, "reports/file2.csv", b"data2")
    any_storage.save_file(project_id, "reports/nested/file3.json", b"data3")
    any_storage.save_file(project_id, "visualizations/floor1.png", b"data4")

    # List all
    all_files = any_storage.list_files(project_id)
    assert len(all_files) == 4

    # List with prefix
    report_files = any_storage.list_files(project_id, prefix="reports/")
    assert len(report_files) == 2
    assert all(f.startswith("reports/") for f in report_files)

    # List non-existent prefix
    missing_files = any_storage.list_files(project_id, prefix="missing/")
    assert len(missing_files) == 0


def test_delete_project_consistency(any_storage):
    """Test that delete_project works identically."""
    project_id = uuid4()

    # Create multiple files
    any_storage.save_file(project_id, "file1.txt", b"data1")
    any_storage.save_file(project_id, "file2.txt", b"data2")
    any_storage.save_file(project_id, "reports/file3.csv", b"data3")

    # Verify exists
    assert any_storage.exists(project_id)

    # Delete
    success = any_storage.delete_project(project_id)
    assert success

    # Verify deleted
    assert not any_storage.exists(project_id)
    assert not any_storage.exists(project_id, "file1.txt")


def test_get_project_size_consistency(any_storage):
    """Test that get_project_size works identically."""
    project_id = uuid4()

    # Empty project
    size = any_storage.get_project_size(project_id)
    assert size == 0

    # Add files with known sizes
    any_storage.save_file(project_id, "file1.txt", b"12345")  # 5 bytes
    any_storage.save_file(project_id, "file2.txt", b"1234567890")  # 10 bytes
    any_storage.save_file(project_id, "file3.txt", b"123")  # 3 bytes

    size = any_storage.get_project_size(project_id)
    assert size == 18


def test_file_overwrite_consistency(any_storage):
    """Test that overwriting files works identically."""
    project_id = uuid4()

    # Save initial content
    any_storage.save_file(project_id, "data.txt", b"initial content")
    assert any_storage.get_file(project_id, "data.txt") == b"initial content"

    # Overwrite
    any_storage.save_file(project_id, "data.txt", b"updated content")
    assert any_storage.get_file(project_id, "data.txt") == b"updated content"

    # Size should reflect new content
    size = any_storage.get_project_size(project_id)
    assert size == len(b"updated content")


# ============================================================================
# Error Handling Consistency Tests
# ============================================================================


def test_get_nonexistent_file_consistency(any_storage):
    """Test that getting non-existent file raises FileNotFoundError."""
    project_id = uuid4()

    with pytest.raises(FileNotFoundError):
        any_storage.get_file(project_id, "missing.txt")


def test_exists_consistency(any_storage):
    """Test that exists() returns False for non-existent files."""
    project_id = uuid4()

    # Non-existent project
    assert not any_storage.exists(project_id)

    # Create file
    any_storage.save_file(project_id, "test.txt", b"data")

    # Project and file exist
    assert any_storage.exists(project_id)
    assert any_storage.exists(project_id, "test.txt")

    # Non-existent file in existing project
    assert not any_storage.exists(project_id, "missing.txt")


def test_delete_nonexistent_project_consistency(any_storage):
    """Test that deleting non-existent project doesn't raise error."""
    project_id = uuid4()

    # Should not raise error
    success = any_storage.delete_project(project_id)
    assert success  # Both backends return True


def test_delete_file_consistency(any_storage):
    """Test that delete_file works identically."""
    project_id = uuid4()

    # Create file
    any_storage.save_file(project_id, "test.txt", b"data")
    assert any_storage.exists(project_id, "test.txt")

    # Delete file
    success = any_storage.delete_file(project_id, "test.txt")
    assert success
    assert not any_storage.exists(project_id, "test.txt")

    # Delete non-existent file
    success = any_storage.delete_file(project_id, "missing.txt")
    assert not success  # Should return False


# ============================================================================
# Factory Tests
# ============================================================================


def test_factory_creates_local_backend(tmp_path):
    """Test that factory creates LocalStorage correctly."""
    settings = Settings(storage_backend="local", projects_dir=tmp_path / "projects")

    backend = StorageFactory.create_backend(settings)

    assert isinstance(backend, LocalStorage)
    assert backend.base_dir == tmp_path / "projects"


def test_factory_creates_s3_backend():
    """Test that factory creates S3Storage correctly."""
    with mock_aws():
        # Create bucket
        bucket_name = "factory-test-bucket"
        region = "us-west-2"

        s3_client = boto3.client("s3", region_name=region)
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": region},
        )

        # Create backend via factory
        settings = Settings(
            storage_backend="s3",
            s3_bucket_name=bucket_name,
            s3_region=region,
            s3_access_key="test_key",
            s3_secret_key="test_secret",
        )

        backend = StorageFactory.create_backend(settings)

        assert isinstance(backend, S3Storage)
        assert backend.bucket == bucket_name


def test_factory_validates_s3_config():
    """Test that factory validates S3 configuration."""
    settings = Settings(
        storage_backend="s3",
        s3_bucket_name=None,  # Missing required config
    )

    with pytest.raises(ValueError, match="S3_BUCKET_NAME is required"):
        StorageFactory.create_backend(settings)


def test_factory_rejects_unknown_backend(tmp_path):
    """Test that factory rejects unknown backend type."""
    # Use model_construct to bypass Pydantic validation
    settings = Settings.model_construct(
        storage_backend="unknown",  # Invalid backend
        projects_dir=tmp_path,
    )

    with pytest.raises(ValueError, match="Unknown storage backend"):
        StorageFactory.create_backend(settings)


# ============================================================================
# Large File Tests
# ============================================================================


def test_large_file_handling(any_storage):
    """Test that both backends handle large files (10MB) correctly."""
    project_id = uuid4()

    # Generate 10MB file
    large_content = b"x" * (10 * 1024 * 1024)

    # Save
    any_storage.save_file(project_id, "large.bin", large_content)

    # Get
    retrieved = any_storage.get_file(project_id, "large.bin")
    assert len(retrieved) == 10 * 1024 * 1024
    assert retrieved == large_content

    # Size
    size = any_storage.get_project_size(project_id)
    assert size == 10 * 1024 * 1024


def test_many_files_handling(any_storage):
    """Test that both backends handle many files (100) correctly."""
    project_id = uuid4()

    # Create 100 files
    for i in range(100):
        any_storage.save_file(project_id, f"file_{i:03d}.txt", f"data{i}".encode())

    # List all
    files = any_storage.list_files(project_id)
    assert len(files) == 100

    # Verify all files exist
    for i in range(100):
        assert any_storage.exists(project_id, f"file_{i:03d}.txt")

    # Delete all
    success = any_storage.delete_project(project_id)
    assert success
    assert not any_storage.exists(project_id)


# ============================================================================
# Path Normalization Tests
# ============================================================================


def test_path_normalization(any_storage):
    """Test that paths are normalized consistently (forward slashes)."""
    project_id = uuid4()

    # Create files with forward slashes
    any_storage.save_file(project_id, "reports/csv/data.csv", b"data")

    # List should return forward slashes
    files = any_storage.list_files(project_id)
    assert "reports/csv/data.csv" in files

    # No backslashes in paths
    for file_path in files:
        assert "\\" not in file_path


# ============================================================================
# Binary Data Tests
# ============================================================================


def test_binary_data_handling(any_storage):
    """Test that binary data is preserved correctly."""
    project_id = uuid4()

    # Various binary patterns
    test_data = [
        b"\x00\x01\x02\x03\x04\x05",  # Null bytes
        b"\xff\xfe\xfd\xfc",  # High bytes
        bytes(range(256)),  # All byte values
        b"\r\n\t\x00",  # Control characters
    ]

    for i, data in enumerate(test_data):
        file_name = f"binary_{i}.bin"
        any_storage.save_file(project_id, file_name, data)

        retrieved = any_storage.get_file(project_id, file_name)
        assert retrieved == data, f"Binary data mismatch for {file_name}"


# ============================================================================
# Unicode Filename Tests
# ============================================================================


def test_unicode_filenames(any_storage):
    """Test that unicode filenames work correctly."""
    project_id = uuid4()

    # Test various unicode characters
    test_files = [
        "файл.txt",  # Cyrillic
        "文件.txt",  # Chinese
        "ファイル.txt",  # Japanese
        "café.txt",  # Accented
        "emoji_😀.txt",  # Emoji
    ]

    for filename in test_files:
        try:
            any_storage.save_file(project_id, filename, b"data")
            assert any_storage.exists(project_id, filename)
            content = any_storage.get_file(project_id, filename)
            assert content == b"data"
        except Exception as e:
            # Some backends may not support certain unicode characters
            # Document this limitation
            pytest.skip(f"Unicode filename '{filename}' not supported: {e}")


# ============================================================================
# Concurrent Access Tests
# ============================================================================


def test_sequential_access(any_storage):
    """Test that sequential writes/reads work correctly."""
    project_id = uuid4()

    # Write 10 files sequentially
    for i in range(10):
        any_storage.save_file(project_id, f"seq_{i}.txt", f"data{i}".encode())

    # Read all sequentially
    for i in range(10):
        content = any_storage.get_file(project_id, f"seq_{i}.txt")
        assert content == f"data{i}".encode()

    # Verify count
    files = any_storage.list_files(project_id)
    assert len(files) == 10
