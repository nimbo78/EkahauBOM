"""Performance benchmarks for storage backends.

Run with: pytest tests/test_storage_performance.py -v -s

The -s flag shows print output with timing information.
"""

import time
import pytest
from uuid import uuid4

from moto import mock_aws
import boto3

from app.services.storage.local import LocalStorage
from app.services.storage.s3 import S3Storage


@pytest.fixture
def local_storage(tmp_path):
    """Create LocalStorage backend."""
    return LocalStorage(base_dir=tmp_path / "projects")


@pytest.fixture
def s3_storage():
    """Create S3Storage backend with moto."""
    with mock_aws():
        bucket_name = "perf-test-bucket"
        region = "us-east-1"

        s3_client = boto3.client("s3", region_name=region)
        s3_client.create_bucket(Bucket=bucket_name)

        storage = S3Storage(
            bucket=bucket_name,
            region=region,
            access_key="test_key",
            secret_key="test_secret",
        )

        yield storage


# ============================================================================
# Upload Performance Tests
# ============================================================================


@pytest.mark.parametrize(
    "size_mb,description",
    [
        (1, "1MB file"),
        (10, "10MB file"),
        (50, "50MB file"),
    ],
)
def test_upload_performance_local(local_storage, size_mb, description):
    """Benchmark file upload speed for LocalStorage."""
    project_id = uuid4()

    # Generate file
    content = b"x" * (size_mb * 1024 * 1024)

    # Upload
    start = time.time()
    local_storage.save_file(project_id, f"test_{size_mb}mb.bin", content)
    duration = time.time() - start

    speed = size_mb / duration if duration > 0 else 0
    print(f"\n[Local] Upload {description}: {duration:.3f}s ({speed:.2f} MB/s)")

    # Cleanup
    local_storage.delete_project(project_id)


@pytest.mark.parametrize(
    "size_mb,description",
    [
        (1, "1MB file"),
        (10, "10MB file"),
        (50, "50MB file"),
    ],
)
def test_upload_performance_s3(s3_storage, size_mb, description):
    """Benchmark file upload speed for S3Storage."""
    project_id = uuid4()

    # Generate file
    content = b"x" * (size_mb * 1024 * 1024)

    # Upload
    start = time.time()
    s3_storage.save_file(project_id, f"test_{size_mb}mb.bin", content)
    duration = time.time() - start

    speed = size_mb / duration if duration > 0 else 0
    print(f"\n[S3] Upload {description}: {duration:.3f}s ({speed:.2f} MB/s)")

    # Cleanup
    s3_storage.delete_project(project_id)


# ============================================================================
# Download Performance Tests
# ============================================================================


@pytest.mark.parametrize("size_mb", [1, 10, 50])
def test_download_performance_local(local_storage, size_mb):
    """Benchmark file download speed for LocalStorage."""
    project_id = uuid4()

    # Upload file
    content = b"x" * (size_mb * 1024 * 1024)
    local_storage.save_file(project_id, f"test_{size_mb}mb.bin", content)

    # Download
    start = time.time()
    retrieved = local_storage.get_file(project_id, f"test_{size_mb}mb.bin")
    duration = time.time() - start

    speed = size_mb / duration if duration > 0 else 0
    print(f"\n[Local] Download {size_mb}MB: {duration:.3f}s ({speed:.2f} MB/s)")

    assert len(retrieved) == size_mb * 1024 * 1024

    # Cleanup
    local_storage.delete_project(project_id)


@pytest.mark.parametrize("size_mb", [1, 10, 50])
def test_download_performance_s3(s3_storage, size_mb):
    """Benchmark file download speed for S3Storage."""
    project_id = uuid4()

    # Upload file
    content = b"x" * (size_mb * 1024 * 1024)
    s3_storage.save_file(project_id, f"test_{size_mb}mb.bin", content)

    # Download
    start = time.time()
    retrieved = s3_storage.get_file(project_id, f"test_{size_mb}mb.bin")
    duration = time.time() - start

    speed = size_mb / duration if duration > 0 else 0
    print(f"\n[S3] Download {size_mb}MB: {duration:.3f}s ({speed:.2f} MB/s)")

    assert len(retrieved) == size_mb * 1024 * 1024

    # Cleanup
    s3_storage.delete_project(project_id)


# ============================================================================
# List Operations Performance Tests
# ============================================================================


@pytest.mark.parametrize("num_files", [10, 100, 1000])
def test_list_performance_local(local_storage, num_files):
    """Benchmark list operations with many files for LocalStorage."""
    project_id = uuid4()

    # Create files
    for i in range(num_files):
        local_storage.save_file(project_id, f"file_{i:04d}.txt", b"data")

    # List all files
    start = time.time()
    files = local_storage.list_files(project_id)
    duration = time.time() - start

    print(f"\n[Local] List {num_files} files: {duration:.3f}s")
    assert len(files) == num_files

    # Cleanup
    local_storage.delete_project(project_id)


@pytest.mark.parametrize("num_files", [10, 100, 1000])
def test_list_performance_s3(s3_storage, num_files):
    """Benchmark list operations with many files for S3Storage."""
    project_id = uuid4()

    # Create files
    for i in range(num_files):
        s3_storage.save_file(project_id, f"file_{i:04d}.txt", b"data")

    # List all files
    start = time.time()
    files = s3_storage.list_files(project_id)
    duration = time.time() - start

    print(f"\n[S3] List {num_files} files: {duration:.3f}s")
    assert len(files) == num_files

    # Cleanup
    s3_storage.delete_project(project_id)


# ============================================================================
# Delete Operations Performance Tests
# ============================================================================


@pytest.mark.parametrize("num_files", [10, 100, 500])
def test_delete_performance_local(local_storage, num_files):
    """Benchmark delete operations with many files for LocalStorage."""
    project_id = uuid4()

    # Create files
    for i in range(num_files):
        local_storage.save_file(project_id, f"file_{i:04d}.txt", b"data")

    # Delete project
    start = time.time()
    success = local_storage.delete_project(project_id)
    duration = time.time() - start

    print(f"\n[Local] Delete {num_files} files: {duration:.3f}s")
    assert success
    assert not local_storage.exists(project_id)


@pytest.mark.parametrize("num_files", [10, 100, 500])
def test_delete_performance_s3(s3_storage, num_files):
    """Benchmark delete operations with many files for S3Storage."""
    project_id = uuid4()

    # Create files
    for i in range(num_files):
        s3_storage.save_file(project_id, f"file_{i:04d}.txt", b"data")

    # Delete project
    start = time.time()
    success = s3_storage.delete_project(project_id)
    duration = time.time() - start

    print(f"\n[S3] Delete {num_files} files: {duration:.3f}s")
    assert success
    assert not s3_storage.exists(project_id)


# ============================================================================
# Mixed Operations Performance Tests
# ============================================================================


def test_mixed_operations_local(local_storage):
    """Benchmark realistic mixed operations for LocalStorage."""
    project_id = uuid4()

    start_total = time.time()

    # 1. Upload multiple files
    start = time.time()
    local_storage.save_file(project_id, "original.esx", b"x" * (5 * 1024 * 1024))
    local_storage.save_file(project_id, "metadata.json", b'{"name": "test"}')
    local_storage.save_file(project_id, "reports/report.csv", b"data" * 1000)
    local_storage.save_file(project_id, "reports/report.xlsx", b"data" * 5000)
    local_storage.save_file(project_id, "visualizations/floor1.png", b"x" * 100000)
    upload_duration = time.time() - start

    # 2. List files
    start = time.time()
    files = local_storage.list_files(project_id)
    list_duration = time.time() - start

    # 3. Read files
    start = time.time()
    local_storage.get_file(project_id, "original.esx")
    local_storage.get_file(project_id, "reports/report.csv")
    read_duration = time.time() - start

    # 4. Get project size
    start = time.time()
    size = local_storage.get_project_size(project_id)
    size_duration = time.time() - start

    # 5. Delete project
    start = time.time()
    local_storage.delete_project(project_id)
    delete_duration = time.time() - start

    total_duration = time.time() - start_total

    print(f"\n[Local] Mixed operations:")
    print(f"  Upload (5 files, ~5MB): {upload_duration:.3f}s")
    print(f"  List: {list_duration:.3f}s")
    print(f"  Read (2 files): {read_duration:.3f}s")
    print(f"  Size: {size_duration:.3f}s")
    print(f"  Delete: {delete_duration:.3f}s")
    print(f"  Total: {total_duration:.3f}s")

    assert len(files) == 5
    assert size > 5 * 1024 * 1024


def test_mixed_operations_s3(s3_storage):
    """Benchmark realistic mixed operations for S3Storage."""
    project_id = uuid4()

    start_total = time.time()

    # 1. Upload multiple files
    start = time.time()
    s3_storage.save_file(project_id, "original.esx", b"x" * (5 * 1024 * 1024))
    s3_storage.save_file(project_id, "metadata.json", b'{"name": "test"}')
    s3_storage.save_file(project_id, "reports/report.csv", b"data" * 1000)
    s3_storage.save_file(project_id, "reports/report.xlsx", b"data" * 5000)
    s3_storage.save_file(project_id, "visualizations/floor1.png", b"x" * 100000)
    upload_duration = time.time() - start

    # 2. List files
    start = time.time()
    files = s3_storage.list_files(project_id)
    list_duration = time.time() - start

    # 3. Read files
    start = time.time()
    s3_storage.get_file(project_id, "original.esx")
    s3_storage.get_file(project_id, "reports/report.csv")
    read_duration = time.time() - start

    # 4. Get project size
    start = time.time()
    size = s3_storage.get_project_size(project_id)
    size_duration = time.time() - start

    # 5. Delete project
    start = time.time()
    s3_storage.delete_project(project_id)
    delete_duration = time.time() - start

    total_duration = time.time() - start_total

    print(f"\n[S3] Mixed operations:")
    print(f"  Upload (5 files, ~5MB): {upload_duration:.3f}s")
    print(f"  List: {list_duration:.3f}s")
    print(f"  Read (2 files): {read_duration:.3f}s")
    print(f"  Size: {size_duration:.3f}s")
    print(f"  Delete: {delete_duration:.3f}s")
    print(f"  Total: {total_duration:.3f}s")

    assert len(files) == 5
    assert size > 5 * 1024 * 1024


# ============================================================================
# Batch Operations Performance Tests
# ============================================================================


def test_batch_upload_local(local_storage):
    """Benchmark batch upload of many small files for LocalStorage."""
    project_id = uuid4()
    num_files = 100

    start = time.time()
    for i in range(num_files):
        local_storage.save_file(project_id, f"batch/file_{i:03d}.txt", f"content{i}".encode())
    duration = time.time() - start

    files_per_sec = num_files / duration if duration > 0 else 0
    print(
        f"\n[Local] Batch upload {num_files} files: {duration:.3f}s ({files_per_sec:.1f} files/s)"
    )

    # Cleanup
    local_storage.delete_project(project_id)


def test_batch_upload_s3(s3_storage):
    """Benchmark batch upload of many small files for S3Storage."""
    project_id = uuid4()
    num_files = 100

    start = time.time()
    for i in range(num_files):
        s3_storage.save_file(project_id, f"batch/file_{i:03d}.txt", f"content{i}".encode())
    duration = time.time() - start

    files_per_sec = num_files / duration if duration > 0 else 0
    print(f"\n[S3] Batch upload {num_files} files: {duration:.3f}s ({files_per_sec:.1f} files/s)")

    # Cleanup
    s3_storage.delete_project(project_id)


# ============================================================================
# Exists Check Performance Tests
# ============================================================================


def test_exists_check_performance_local(local_storage):
    """Benchmark exists checks for LocalStorage."""
    project_id = uuid4()

    # Create 50 files
    for i in range(50):
        local_storage.save_file(project_id, f"file_{i:02d}.txt", b"data")

    # Check existence of all files
    start = time.time()
    for i in range(50):
        exists = local_storage.exists(project_id, f"file_{i:02d}.txt")
        assert exists
    duration = time.time() - start

    checks_per_sec = 50 / duration if duration > 0 else 0
    print(f"\n[Local] 50 exists checks: {duration:.3f}s ({checks_per_sec:.1f} checks/s)")

    # Cleanup
    local_storage.delete_project(project_id)


def test_exists_check_performance_s3(s3_storage):
    """Benchmark exists checks for S3Storage."""
    project_id = uuid4()

    # Create 50 files
    for i in range(50):
        s3_storage.save_file(project_id, f"file_{i:02d}.txt", b"data")

    # Check existence of all files
    start = time.time()
    for i in range(50):
        exists = s3_storage.exists(project_id, f"file_{i:02d}.txt")
        assert exists
    duration = time.time() - start

    checks_per_sec = 50 / duration if duration > 0 else 0
    print(f"\n[S3] 50 exists checks: {duration:.3f}s ({checks_per_sec:.1f} checks/s)")

    # Cleanup
    s3_storage.delete_project(project_id)
