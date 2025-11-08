"""
Load testing for Web UI backend.

Tests cover:
- Large batch uploads (50+ projects)
- Concurrent batch uploads
- Large file handling
- Memory profiling
"""

import pytest
import io
import time
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient

from app.main import app
from app.services.storage_service import StorageService

# Try to import psutil for memory profiling (optional)
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

client = TestClient(app)

# Test credentials
ADMIN_TOKEN = None


@pytest.fixture(scope="module", autouse=True)
def setup_admin_auth():
    """Get admin token for authenticated requests."""
    global ADMIN_TOKEN
    response = client.post("/api/auth/login", json={"username": "admin", "password": "EkahauAdmin"})
    assert response.status_code == 200
    ADMIN_TOKEN = response.json()["access_token"]


@pytest.fixture
def auth_headers():
    """Provide authentication headers."""
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


@pytest.fixture
def storage_service():
    """Provide storage service instance."""
    return StorageService()


def create_dummy_esx_file(filename: str, size_kb: int = 10) -> io.BytesIO:
    """Create a dummy .esx file in memory.

    Args:
        filename: Name for the file
        size_kb: Approximate size in KB

    Returns:
        BytesIO object with dummy content
    """
    # Create content approximately size_kb in size
    content = b"DUMMY ESX FILE CONTENT " * (size_kb * 40)
    file_obj = io.BytesIO(content)
    file_obj.name = filename
    return file_obj


# ============================================================================
# Large Batch Tests
# ============================================================================


@pytest.mark.slow
class TestLargeBatchUpload:
    """Test batch uploads with many files."""

    def test_upload_50_small_files(self, auth_headers, storage_service):
        """Test uploading 50 small files in a single batch."""
        num_files = 50
        files = []

        # Create 50 dummy files
        for i in range(num_files):
            file_obj = create_dummy_esx_file(f"project_{i}.esx", size_kb=10)
            files.append(("files", (f"project_{i}.esx", file_obj, "application/octet-stream")))

        # Upload batch
        data = {
            "batch_name": f"Load Test - {num_files} Files",
            "parallel_workers": "4",
            "auto_process": "false",
        }

        start_time = time.time()
        response = client.post("/api/batches/upload", files=files, data=data, headers=auth_headers)
        upload_time = time.time() - start_time

        # Verify upload succeeded
        assert response.status_code == 200
        result = response.json()
        assert result["files_count"] == num_files
        assert len(result["files_uploaded"]) == num_files

        # Performance check - should complete in reasonable time
        # Expect ~0.05s per file on average (2.5s total for 50 files)
        assert (
            upload_time < num_files * 0.1
        ), f"Upload too slow: {upload_time:.2f}s for {num_files} files"

        print(
            f"\n50 files upload: {upload_time:.2f}s ({upload_time/num_files*1000:.0f}ms per file)"
        )

        # Cleanup
        batch_id = result["batch_id"]
        client.delete(f"/api/batches/{batch_id}", headers=auth_headers)

    def test_upload_100_files_memory_check(self, auth_headers, storage_service):
        """Test memory usage with 100 files."""
        if not PSUTIL_AVAILABLE:
            pytest.skip("psutil not available for memory profiling")

        num_files = 100

        # Get initial memory
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # Create files
        files = []
        for i in range(num_files):
            file_obj = create_dummy_esx_file(f"large_batch_{i}.esx", size_kb=5)
            files.append(("files", (f"large_batch_{i}.esx", file_obj, "application/octet-stream")))

        # Upload
        data = {
            "batch_name": f"Memory Test - {num_files} Files",
            "parallel_workers": "4",
            "auto_process": "false",
        }

        response = client.post("/api/batches/upload", files=files, data=data, headers=auth_headers)

        # Check memory after
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_increase = mem_after - mem_before

        assert response.status_code == 200
        result = response.json()
        assert result["files_count"] == num_files

        # Memory increase should be reasonable (< 200MB for 100 small files)
        assert mem_increase < 200, f"Excessive memory usage: {mem_increase:.1f}MB"

        print(f"\n100 files memory: {mem_increase:.1f}MB increase")

        # Cleanup
        batch_id = result["batch_id"]
        client.delete(f"/api/batches/{batch_id}", headers=auth_headers)


# ============================================================================
# Concurrent Upload Tests
# ============================================================================


@pytest.mark.slow
class TestConcurrentUploads:
    """Test concurrent batch uploads."""

    def upload_single_batch(self, batch_num: int, num_files: int = 5) -> dict:
        """Upload a single batch (for concurrent testing).

        Args:
            batch_num: Batch number for naming
            num_files: Number of files in batch

        Returns:
            Response JSON
        """
        # Get auth token
        auth_response = client.post(
            "/api/auth/login", json={"username": "admin", "password": "EkahauAdmin"}
        )
        token = auth_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create files
        files = []
        for i in range(num_files):
            file_obj = create_dummy_esx_file(f"batch{batch_num}_file{i}.esx", size_kb=5)
            files.append(
                ("files", (f"batch{batch_num}_file{i}.esx", file_obj, "application/octet-stream"))
            )

        # Upload
        data = {
            "batch_name": f"Concurrent Batch {batch_num}",
            "parallel_workers": "2",
            "auto_process": "false",
        }

        response = client.post("/api/batches/upload", files=files, data=data, headers=headers)

        return {
            "batch_num": batch_num,
            "status_code": response.status_code,
            "result": response.json() if response.status_code == 200 else None,
        }

    def test_concurrent_batch_uploads(self, auth_headers):
        """Test multiple concurrent batch uploads."""
        num_concurrent = 5
        files_per_batch = 5

        start_time = time.time()

        # Upload batches concurrently
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [
                executor.submit(self.upload_single_batch, i, files_per_batch)
                for i in range(num_concurrent)
            ]

            results = [future.result() for future in as_completed(futures)]

        elapsed = time.time() - start_time

        # Verify all succeeded
        for result in results:
            assert result["status_code"] == 200
            assert result["result"]["files_count"] == files_per_batch

        print(
            f"\n{num_concurrent} concurrent batches ({files_per_batch} files each): {elapsed:.2f}s"
        )

        # Cleanup
        for result in results:
            if result["result"]:
                batch_id = result["result"]["batch_id"]
                client.delete(f"/api/batches/{batch_id}", headers=auth_headers)


# ============================================================================
# Large File Tests
# ============================================================================


@pytest.mark.slow
class TestLargeFiles:
    """Test handling of large files."""

    def test_upload_large_files(self, auth_headers):
        """Test uploading files larger than typical size."""
        # Create 3 larger files (1MB each)
        files = []
        for i in range(3):
            file_obj = create_dummy_esx_file(f"large_file_{i}.esx", size_kb=1024)
            files.append(("files", (f"large_file_{i}.esx", file_obj, "application/octet-stream")))

        data = {"batch_name": "Large Files Test", "parallel_workers": "2", "auto_process": "false"}

        start_time = time.time()
        response = client.post("/api/batches/upload", files=files, data=data, headers=auth_headers)
        upload_time = time.time() - start_time

        assert response.status_code == 200
        result = response.json()
        assert result["files_count"] == 3

        # Should handle 3MB in reasonable time (< 5s)
        assert upload_time < 5.0, f"Large file upload too slow: {upload_time:.2f}s"

        print(f"\n3x1MB files: {upload_time:.2f}s")

        # Cleanup
        batch_id = result["batch_id"]
        client.delete(f"/api/batches/{batch_id}", headers=auth_headers)

    def test_mixed_file_sizes(self, auth_headers):
        """Test uploading mixed small and large files."""
        files = []

        # 2 large files (500KB each)
        for i in range(2):
            file_obj = create_dummy_esx_file(f"large_{i}.esx", size_kb=500)
            files.append(("files", (f"large_{i}.esx", file_obj, "application/octet-stream")))

        # 10 small files (10KB each)
        for i in range(10):
            file_obj = create_dummy_esx_file(f"small_{i}.esx", size_kb=10)
            files.append(("files", (f"small_{i}.esx", file_obj, "application/octet-stream")))

        data = {"batch_name": "Mixed Sizes Test", "parallel_workers": "3", "auto_process": "false"}

        response = client.post("/api/batches/upload", files=files, data=data, headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["files_count"] == 12

        # Cleanup
        batch_id = result["batch_id"]
        client.delete(f"/api/batches/{batch_id}", headers=auth_headers)


# ============================================================================
# API Performance Tests
# ============================================================================


class TestAPIPerformance:
    """Test API endpoint performance."""

    def test_list_batches_performance(self, auth_headers):
        """Test batch list performance with many batches."""
        # Get current batch count
        response = client.get("/api/batches", headers=auth_headers)
        assert response.status_code == 200

        start_time = time.time()
        response = client.get("/api/batches", headers=auth_headers)
        query_time = time.time() - start_time

        assert response.status_code == 200
        batches = response.json()

        # Should respond quickly even with many batches (< 1s)
        assert query_time < 1.0, f"List batches too slow: {query_time:.3f}s"

        print(f"\nList {len(batches)} batches: {query_time*1000:.0f}ms")

    def test_batch_detail_performance(self, auth_headers):
        """Test batch detail retrieval performance."""
        # Get first batch
        response = client.get("/api/batches", headers=auth_headers)
        batches = response.json()

        if len(batches) == 0:
            pytest.skip("No batches available for testing")

        batch_id = batches[0]["batch_id"]

        # Measure detail retrieval time
        start_time = time.time()
        response = client.get(f"/api/batches/{batch_id}", headers=auth_headers)
        query_time = time.time() - start_time

        assert response.status_code == 200

        # Should respond quickly (< 500ms)
        assert query_time < 0.5, f"Batch detail too slow: {query_time*1000:.0f}ms"

        print(f"\nBatch detail: {query_time*1000:.0f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
