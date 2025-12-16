"""Tests for BatchService."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.models import (
    BatchMetadata,
    BatchProjectStatus,
    BatchStatistics,
    BatchStatus,
    ProcessingRequest,
    ProcessingStatus,
    ProjectMetadata,
)
from app.services.batch_service import BatchService
from app.services.storage_service import StorageService


@pytest.fixture
def temp_batch_service(tmp_path):
    """Create temporary batch service with temp storage."""
    from app.services.storage.local import LocalStorage

    storage = StorageService()
    temp_backend = LocalStorage(base_dir=tmp_path / "projects")
    storage.backend = temp_backend
    storage.projects_dir = tmp_path / "projects"  # Critical: list_batches uses this

    batch_service = BatchService(storage_service=storage)
    yield batch_service


@pytest.fixture
def sample_processing_request():
    """Create sample processing request."""
    return ProcessingRequest(
        group_by="model",
        output_formats=["csv", "excel"],
        visualize_floor_plans=True,
        show_azimuth_arrows=False,
        ap_opacity=0.6,
    )


@pytest.fixture
def sample_project_metadata(temp_batch_service):
    """Create sample project metadata."""
    project_id = uuid4()
    metadata = ProjectMetadata(
        project_id=project_id,
        filename="test.esx",
        file_size=1024,
        processing_status=ProcessingStatus.PENDING,
        original_file=f"projects/{project_id}/original.esx",
        project_name="Test Project",
        aps_count=10,
        total_antennas=20,
    )

    # Save metadata to storage
    temp_batch_service.storage.save_metadata(project_id, metadata)
    return metadata


class TestBatchServiceCreation:
    """Tests for batch creation."""

    def test_create_batch_minimal(self, temp_batch_service):
        """Test creating batch with minimal parameters."""
        batch = temp_batch_service.create_batch()

        assert isinstance(batch.batch_id, UUID)
        assert batch.batch_name.startswith("Batch ")
        assert batch.status == BatchStatus.PENDING
        assert len(batch.project_ids) == 0
        assert batch.parallel_workers == 1

    def test_create_batch_with_name(self, temp_batch_service):
        """Test creating batch with custom name."""
        batch = temp_batch_service.create_batch(batch_name="My Custom Batch")

        assert batch.batch_name == "My Custom Batch"

    def test_create_batch_with_processing_options(
        self, temp_batch_service, sample_processing_request
    ):
        """Test creating batch with processing options."""
        batch = temp_batch_service.create_batch(processing_options=sample_processing_request)

        assert batch.processing_options.group_by == "model"
        assert batch.processing_options.output_formats == ["csv", "excel"]
        assert batch.processing_options.visualize_floor_plans is True

    def test_create_batch_with_parallel_workers(self, temp_batch_service):
        """Test creating batch with parallel workers."""
        batch = temp_batch_service.create_batch(parallel_workers=4)

        assert batch.parallel_workers == 4

    def test_create_batch_saves_metadata(self, temp_batch_service):
        """Test that batch metadata is saved to disk."""
        batch = temp_batch_service.create_batch()

        metadata_path = temp_batch_service._get_batch_metadata_path(batch.batch_id)
        assert metadata_path.exists()

        # Verify metadata content
        with open(metadata_path, "r") as f:
            data = json.load(f)
            assert data["batch_id"] == str(batch.batch_id)
            assert data["status"] == "pending"


class TestBatchServiceMetadata:
    """Tests for batch metadata operations."""

    def test_load_batch_metadata_success(self, temp_batch_service):
        """Test loading batch metadata."""
        batch = temp_batch_service.create_batch(batch_name="Test Batch")

        loaded = temp_batch_service.load_batch_metadata(batch.batch_id)

        assert loaded is not None
        assert loaded.batch_id == batch.batch_id
        assert loaded.batch_name == "Test Batch"

    def test_load_batch_metadata_not_found(self, temp_batch_service):
        """Test loading non-existent batch."""
        fake_id = uuid4()
        loaded = temp_batch_service.load_batch_metadata(fake_id)

        assert loaded is None

    def test_save_batch_metadata_updates_file(self, temp_batch_service):
        """Test that saving metadata updates the file."""
        batch = temp_batch_service.create_batch()

        # Modify batch
        batch.batch_name = "Updated Name"
        batch.status = BatchStatus.PROCESSING

        # Save
        temp_batch_service._save_batch_metadata(batch)

        # Reload and verify
        loaded = temp_batch_service.load_batch_metadata(batch.batch_id)
        assert loaded.batch_name == "Updated Name"
        assert loaded.status == BatchStatus.PROCESSING


class TestBatchServiceProjects:
    """Tests for adding projects to batches."""

    def test_add_project_to_batch(self, temp_batch_service, sample_project_metadata):
        """Test adding project to batch."""
        batch = temp_batch_service.create_batch()

        temp_batch_service.add_project_to_batch(
            batch.batch_id, sample_project_metadata.project_id, "test.esx"
        )

        # Reload batch and verify
        updated = temp_batch_service.load_batch_metadata(batch.batch_id)
        assert len(updated.project_ids) == 1
        assert updated.project_ids[0] == sample_project_metadata.project_id
        assert len(updated.project_statuses) == 1
        assert updated.project_statuses[0].filename == "test.esx"
        assert updated.project_statuses[0].status == ProcessingStatus.PENDING

    def test_add_multiple_projects_to_batch(self, temp_batch_service):
        """Test adding multiple projects to batch."""
        batch = temp_batch_service.create_batch()

        project_id_1 = uuid4()
        project_id_2 = uuid4()

        temp_batch_service.add_project_to_batch(batch.batch_id, project_id_1, "test1.esx")
        temp_batch_service.add_project_to_batch(batch.batch_id, project_id_2, "test2.esx")

        # Reload and verify
        updated = temp_batch_service.load_batch_metadata(batch.batch_id)
        assert len(updated.project_ids) == 2
        assert len(updated.project_statuses) == 2

    def test_add_duplicate_project_ignored(self, temp_batch_service):
        """Test that adding same project twice doesn't duplicate."""
        batch = temp_batch_service.create_batch()
        project_id = uuid4()

        temp_batch_service.add_project_to_batch(batch.batch_id, project_id, "test.esx")
        temp_batch_service.add_project_to_batch(batch.batch_id, project_id, "test.esx")

        # Reload and verify
        updated = temp_batch_service.load_batch_metadata(batch.batch_id)
        assert len(updated.project_ids) == 1

    def test_add_project_to_nonexistent_batch_raises(self, temp_batch_service):
        """Test adding project to non-existent batch raises error."""
        fake_batch_id = uuid4()
        project_id = uuid4()

        with pytest.raises(ValueError, match="Batch .* not found"):
            temp_batch_service.add_project_to_batch(fake_batch_id, project_id, "test.esx")


class TestBatchServiceListing:
    """Tests for listing batches."""

    def test_list_batches_empty(self, temp_batch_service):
        """Test listing batches when none exist."""
        batches = temp_batch_service.list_batches()
        assert len(batches) == 0

    def test_list_batches_single(self, temp_batch_service):
        """Test listing single batch."""
        batch = temp_batch_service.create_batch(batch_name="Test Batch")

        batches = temp_batch_service.list_batches()
        assert len(batches) == 1
        assert batches[0].batch_id == batch.batch_id

    def test_list_batches_multiple(self, temp_batch_service):
        """Test listing multiple batches."""
        batch1 = temp_batch_service.create_batch(batch_name="Batch 1")
        batch2 = temp_batch_service.create_batch(batch_name="Batch 2")

        batches = temp_batch_service.list_batches()
        assert len(batches) == 2

        # Should be sorted by created_date (newest first)
        assert batches[0].batch_id == batch2.batch_id
        assert batches[1].batch_id == batch1.batch_id

    def test_list_batches_with_status_filter(self, temp_batch_service):
        """Test listing batches with status filter."""
        batch1 = temp_batch_service.create_batch()
        batch2 = temp_batch_service.create_batch()

        # Update batch2 status
        batch2_meta = temp_batch_service.load_batch_metadata(batch2.batch_id)
        batch2_meta.status = BatchStatus.COMPLETED
        temp_batch_service._save_batch_metadata(batch2_meta)

        # Filter by pending
        pending_batches = temp_batch_service.list_batches(status=BatchStatus.PENDING)
        assert len(pending_batches) == 1
        assert pending_batches[0].batch_id == batch1.batch_id

        # Filter by completed
        completed_batches = temp_batch_service.list_batches(status=BatchStatus.COMPLETED)
        assert len(completed_batches) == 1
        assert completed_batches[0].batch_id == batch2.batch_id

    def test_list_batches_with_limit(self, temp_batch_service):
        """Test listing batches with limit."""
        temp_batch_service.create_batch(batch_name="Batch 1")
        temp_batch_service.create_batch(batch_name="Batch 2")
        temp_batch_service.create_batch(batch_name="Batch 3")

        batches = temp_batch_service.list_batches(limit=2)
        assert len(batches) == 2


class TestBatchServiceStatistics:
    """Tests for statistics calculation."""

    def test_calculate_statistics_empty(self, temp_batch_service):
        """Test calculating statistics for empty batch."""
        batch = temp_batch_service.create_batch()

        stats = temp_batch_service._calculate_statistics(batch)

        assert stats.total_projects == 0
        assert stats.successful_projects == 0
        assert stats.failed_projects == 0
        assert stats.total_processing_time == 0.0
        assert stats.total_access_points == 0
        assert stats.total_antennas == 0

    def test_calculate_statistics_with_projects(self, temp_batch_service):
        """Test calculating statistics with projects."""
        batch = temp_batch_service.create_batch()

        # Add project statuses manually
        batch.project_statuses = [
            BatchProjectStatus(
                project_id=uuid4(),
                filename="project1.esx",
                status=ProcessingStatus.COMPLETED,
                processing_time=10.5,
                access_points_count=5,
                antennas_count=10,
            ),
            BatchProjectStatus(
                project_id=uuid4(),
                filename="project2.esx",
                status=ProcessingStatus.COMPLETED,
                processing_time=15.3,
                access_points_count=8,
                antennas_count=16,
            ),
            BatchProjectStatus(
                project_id=uuid4(),
                filename="project3.esx",
                status=ProcessingStatus.FAILED,
                error_message="Test error",
            ),
        ]

        stats = temp_batch_service._calculate_statistics(batch)

        assert stats.total_projects == 3
        assert stats.successful_projects == 2
        assert stats.failed_projects == 1
        assert stats.total_processing_time == 25.8
        assert stats.total_access_points == 13
        assert stats.total_antennas == 26


class TestBatchServiceDeletion:
    """Tests for batch deletion."""

    def test_delete_batch_success(self, temp_batch_service):
        """Test deleting batch."""
        batch = temp_batch_service.create_batch()

        # Verify batch exists
        assert temp_batch_service.load_batch_metadata(batch.batch_id) is not None

        # Delete
        result = temp_batch_service.delete_batch(batch.batch_id)
        assert result is True

        # Verify batch is gone
        assert temp_batch_service.load_batch_metadata(batch.batch_id) is None

    def test_delete_batch_not_found(self, temp_batch_service):
        """Test deleting non-existent batch."""
        fake_id = uuid4()
        result = temp_batch_service.delete_batch(fake_id)
        assert result is False


class TestBatchServiceUpdateStatus:
    """Tests for updating project status in batch."""

    def test_update_project_status(self, temp_batch_service, sample_project_metadata):
        """Test updating project status in batch."""
        batch = temp_batch_service.create_batch()
        temp_batch_service.add_project_to_batch(
            batch.batch_id, sample_project_metadata.project_id, "test.esx"
        )

        # Reload batch
        batch = temp_batch_service.load_batch_metadata(batch.batch_id)

        # Update status
        temp_batch_service._update_project_status(
            batch,
            sample_project_metadata.project_id,
            ProcessingStatus.COMPLETED,
            processing_time=12.5,
        )

        # Verify update
        assert batch.project_statuses[0].status == ProcessingStatus.COMPLETED
        assert batch.project_statuses[0].processing_time == 12.5

    def test_update_project_status_with_error(self, temp_batch_service):
        """Test updating project status with error message."""
        batch = temp_batch_service.create_batch()
        project_id = uuid4()
        temp_batch_service.add_project_to_batch(batch.batch_id, project_id, "test.esx")

        # Reload batch
        batch = temp_batch_service.load_batch_metadata(batch.batch_id)

        # Update with error
        temp_batch_service._update_project_status(
            batch, project_id, ProcessingStatus.FAILED, error_message="Test error"
        )

        # Verify update
        assert batch.project_statuses[0].status == ProcessingStatus.FAILED
        assert batch.project_statuses[0].error_message == "Test error"

    def test_update_project_status_loads_counts(self, temp_batch_service, sample_project_metadata):
        """Test that updating status loads AP and antenna counts."""
        batch = temp_batch_service.create_batch()
        temp_batch_service.add_project_to_batch(
            batch.batch_id, sample_project_metadata.project_id, "test.esx"
        )

        # Reload batch
        batch = temp_batch_service.load_batch_metadata(batch.batch_id)

        # Update status
        temp_batch_service._update_project_status(
            batch, sample_project_metadata.project_id, ProcessingStatus.COMPLETED
        )

        # Verify counts were loaded from project metadata
        assert batch.project_statuses[0].access_points_count == 10
        assert batch.project_statuses[0].antennas_count == 20
