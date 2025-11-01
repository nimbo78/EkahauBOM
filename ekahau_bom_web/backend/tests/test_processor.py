"""Tests for Processor Service."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models import ProcessingStatus, ProjectMetadata
from app.services.processor import ProcessorService
from app.services.storage import StorageService


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage service."""
    storage = StorageService()
    storage.projects_dir = tmp_path / "projects"
    storage.projects_dir.mkdir(parents=True, exist_ok=True)
    return storage


@pytest.fixture
def sample_metadata(temp_storage):
    """Create sample project metadata."""
    project_id = uuid4()
    metadata = ProjectMetadata(
        project_id=project_id,
        filename="test.esx",
        file_size=1024,
        processing_status=ProcessingStatus.PENDING,
        original_file=f"projects/{project_id}/original.esx",
    )

    # Create project directory and original file
    project_dir = temp_storage.get_project_dir(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "original.esx").write_text("test")

    # Save metadata
    temp_storage.save_metadata(project_id, metadata)

    return metadata


@pytest.fixture
def processor(temp_storage):
    """Create processor service."""
    return ProcessorService(temp_storage)


@pytest.mark.asyncio
async def test_build_command(processor, sample_metadata, temp_storage):
    """Test building EkahauBOM CLI command."""
    project_dir = temp_storage.get_project_dir(sample_metadata.project_id)
    original_file = project_dir / "original.esx"
    reports_dir = temp_storage.get_reports_dir(sample_metadata.project_id)

    cmd = processor._build_command(
        original_file=original_file,
        output_dir=reports_dir,
        group_aps=True,
        output_formats=["csv", "xlsx", "html"],
        visualize_floor_plans=True,
    )

    assert "python" in cmd
    assert "-m" in cmd
    assert "ekahau_bom" in cmd
    assert str(original_file) in cmd
    assert "--output-dir" in cmd
    assert str(reports_dir) in cmd
    assert "--group-aps" in cmd
    assert "--csv" in cmd
    assert "--excel" in cmd
    assert "--html" in cmd
    assert "--visualize-floor-plans" in cmd


@pytest.mark.asyncio
async def test_build_command_minimal(processor, sample_metadata, temp_storage):
    """Test building minimal CLI command."""
    project_dir = temp_storage.get_project_dir(sample_metadata.project_id)
    original_file = project_dir / "original.esx"
    reports_dir = temp_storage.get_reports_dir(sample_metadata.project_id)

    cmd = processor._build_command(
        original_file=original_file,
        output_dir=reports_dir,
        group_aps=False,
        output_formats=["csv"],
        visualize_floor_plans=False,
    )

    assert "--group-aps" not in cmd
    assert "--excel" not in cmd
    assert "--html" not in cmd
    assert "--visualize-floor-plans" not in cmd
    assert "--csv" in cmd


@pytest.mark.asyncio
async def test_process_project_success(
    processor, sample_metadata, temp_storage, tmp_path
):
    """Test successful project processing."""
    project_id = sample_metadata.project_id

    # Mock subprocess
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"Success", b""))

    # Mock index_service
    with patch(
        "app.services.processor.asyncio.create_subprocess_exec",
        return_value=mock_process,
    ):
        with patch("app.services.processor.index_service") as mock_index:
            mock_index.add = MagicMock()
            mock_index.save_to_disk = MagicMock()

            # Create a dummy CSV file for metadata extraction
            reports_dir = temp_storage.get_reports_dir(project_id)
            reports_dir.mkdir(parents=True, exist_ok=True)
            csv_file = reports_dir / "test_access_points.csv"
            csv_file.write_text("header\nrow1\nrow2\nrow3\n")

            # Process
            await processor.process_project(
                project_id=project_id,
                group_aps=True,
                output_formats=["csv", "xlsx"],
                visualize_floor_plans=True,
            )

    # Verify metadata updated
    metadata = temp_storage.load_metadata(project_id)
    assert metadata.processing_status == ProcessingStatus.COMPLETED
    assert metadata.processing_completed is not None
    assert metadata.processing_error is None
    assert metadata.reports_dir is not None
    assert metadata.visualizations_dir is not None
    assert metadata.processing_flags["group_aps"] is True
    assert "csv" in metadata.processing_flags["output_formats"]


@pytest.mark.asyncio
async def test_process_project_failure(processor, sample_metadata, temp_storage):
    """Test project processing failure."""
    project_id = sample_metadata.project_id

    # Mock subprocess with error
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate = AsyncMock(return_value=(b"", b"Error occurred"))

    with patch(
        "app.services.processor.asyncio.create_subprocess_exec",
        return_value=mock_process,
    ):
        with patch("app.services.processor.index_service") as mock_index:
            mock_index.add = MagicMock()
            mock_index.save_to_disk = MagicMock()

            # Process (should not raise, but update metadata)
            await processor.process_project(project_id=project_id)

    # Verify metadata shows failure
    metadata = temp_storage.load_metadata(project_id)
    assert metadata.processing_status == ProcessingStatus.FAILED
    assert metadata.processing_error is not None
    assert "Error occurred" in metadata.processing_error


@pytest.mark.asyncio
async def test_process_project_not_found(processor):
    """Test processing non-existent project."""
    with pytest.raises(ValueError, match="Project .* not found"):
        await processor.process_project(project_id=uuid4())


@pytest.mark.asyncio
async def test_extract_project_metadata(processor, sample_metadata, temp_storage):
    """Test extracting metadata from processed files."""
    project_id = sample_metadata.project_id
    project_dir = temp_storage.get_project_dir(project_id)
    original_file = project_dir / "original.esx"

    # Create test files
    reports_dir = temp_storage.get_reports_dir(project_id)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Create CSV with 5 APs (header + 5 rows)
    csv_file = reports_dir / "test_access_points.csv"
    csv_file.write_text("header\nap1\nap2\nap3\nap4\nap5\n")

    # Create visualizations
    viz_dir = temp_storage.get_visualizations_dir(project_id)
    viz_dir.mkdir(parents=True, exist_ok=True)
    (viz_dir / "floor1.png").write_text("test")
    (viz_dir / "floor2.png").write_text("test")

    # Extract metadata
    await processor._extract_project_metadata(
        project_id, original_file, sample_metadata
    )

    # Verify counts
    assert sample_metadata.aps_count == 5
    assert sample_metadata.floors_count == 2


@pytest.mark.asyncio
async def test_extract_project_metadata_no_files(
    processor, sample_metadata, temp_storage
):
    """Test extracting metadata when no files exist."""
    project_id = sample_metadata.project_id
    project_dir = temp_storage.get_project_dir(project_id)
    original_file = project_dir / "original.esx"

    # Should not raise exception
    await processor._extract_project_metadata(
        project_id, original_file, sample_metadata
    )

    # Counts should remain None
    assert sample_metadata.aps_count is None
    assert sample_metadata.floors_count is None


@pytest.mark.asyncio
async def test_cancel_processing(processor, sample_metadata, temp_storage):
    """Test cancelling processing."""
    project_id = sample_metadata.project_id

    # Set status to processing
    sample_metadata.processing_status = ProcessingStatus.PROCESSING
    temp_storage.save_metadata(project_id, sample_metadata)

    with patch("app.services.processor.index_service") as mock_index:
        mock_index.add = MagicMock()
        mock_index.save_to_disk = MagicMock()

        # Cancel
        await processor.cancel_processing(project_id)

    # Verify status changed to failed
    metadata = temp_storage.load_metadata(project_id)
    assert metadata.processing_status == ProcessingStatus.FAILED
    assert "cancelled" in metadata.processing_error.lower()


@pytest.mark.asyncio
async def test_processing_updates_status_to_processing(
    processor, sample_metadata, temp_storage
):
    """Test that processing updates status and index multiple times."""
    project_id = sample_metadata.project_id

    # Mock subprocess
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"", b""))

    with patch(
        "app.services.processor.asyncio.create_subprocess_exec",
        return_value=mock_process,
    ):
        with patch("app.services.processor.index_service") as mock_index:
            mock_index.add = MagicMock()
            mock_index.save_to_disk = MagicMock()

            # Process
            await processor.process_project(project_id=project_id)

            # Verify index was updated at least twice (start and end)
            assert mock_index.add.call_count >= 2
            assert mock_index.save_to_disk.call_count >= 2

    # Verify final status is COMPLETED
    metadata = temp_storage.load_metadata(project_id)
    assert metadata.processing_status == ProcessingStatus.COMPLETED
