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
from app.services.storage_service import StorageService


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage service."""
    from app.services.storage.local import LocalStorage

    storage = StorageService()
    temp_backend = LocalStorage(base_dir=tmp_path / "projects")
    storage.backend = temp_backend
    storage.projects_dir = tmp_path / "projects"  # Keep for backward compatibility
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
        group_by="model",
        output_formats=["csv", "excel", "html"],
        visualize_floor_plans=True,
        show_azimuth_arrows=False,
        ap_opacity=0.6,
        include_text_notes=True,
        include_picture_notes=True,
        include_cable_notes=True,
    )

    assert "python" in str(cmd) or "-m" in cmd
    assert "-m" in cmd
    assert "ekahau_bom" in cmd
    assert str(original_file) in cmd
    assert "--output-dir" in cmd
    assert str(reports_dir) in cmd
    assert "--group-by" in cmd
    assert "model" in cmd
    assert "--format" in cmd
    assert "csv,excel,html" in cmd
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
        group_by=None,
        output_formats=["csv"],
        visualize_floor_plans=False,
        show_azimuth_arrows=False,
        ap_opacity=0.6,
        include_text_notes=False,
        include_picture_notes=False,
        include_cable_notes=False,
    )

    assert "--group-by" not in cmd
    assert "excel" not in ",".join(cmd).lower()
    assert "html" not in ",".join(cmd).lower()
    assert "--visualize-floor-plans" not in cmd
    assert "--format" in cmd
    assert "csv" in cmd


@pytest.mark.asyncio
async def test_process_project_success(processor, sample_metadata, temp_storage, tmp_path):
    """Test successful project processing."""
    project_id = sample_metadata.project_id

    # Mock subprocess.run result
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b"Success"
    mock_result.stderr = b""

    # Mock subprocess.run
    with patch("app.services.processor.subprocess.run", return_value=mock_result):
        with patch("app.services.processor.index_service") as mock_index:
            mock_index.add = MagicMock()
            mock_index.save_to_disk = MagicMock()

            # Create project with valid .esx structure for metadata extraction
            import zipfile
            import json

            project_dir = temp_storage.get_project_dir(project_id)
            original_file = project_dir / "original.esx"

            # Create a valid .esx file for metadata extraction
            with zipfile.ZipFile(original_file, "w") as zf:
                zf.writestr("project.json", json.dumps({"project": {"name": "Test Project"}}))
                zf.writestr(
                    "accessPoints.json",
                    json.dumps({"accessPoints": [{}, {}, {}]}),  # 3 APs
                )
                zf.writestr("floorPlans.json", json.dumps({"floorPlans": [{}]}))  # 1 floor

            # Process
            await processor.process_project(
                project_id=project_id,
                group_by="model",
                output_formats=["csv", "excel"],
                visualize_floor_plans=True,
            )

    # Verify metadata updated
    metadata = temp_storage.load_metadata(project_id)
    assert metadata.processing_status == ProcessingStatus.COMPLETED
    assert metadata.processing_completed is not None
    assert metadata.processing_error is None
    assert metadata.reports_dir is not None
    assert metadata.visualizations_dir is not None
    assert metadata.processing_flags["group_by"] == "model"
    assert "csv" in metadata.processing_flags["output_formats"]


@pytest.mark.asyncio
async def test_process_project_failure(processor, sample_metadata, temp_storage):
    """Test project processing failure."""
    project_id = sample_metadata.project_id

    # Mock subprocess.run result with error
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = b""
    mock_result.stderr = b"Error occurred"

    with patch("app.services.processor.subprocess.run", return_value=mock_result):
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
    import zipfile
    import json

    project_id = sample_metadata.project_id
    project_dir = temp_storage.get_project_dir(project_id)
    original_file = project_dir / "original.esx"

    # Create a valid .esx file (ZIP) with project metadata
    with zipfile.ZipFile(original_file, "w") as zf:
        # Project info
        # Note: 'title' has priority over 'name' in metadata extraction
        zf.writestr(
            "project.json",
            json.dumps({"project": {"name": "Test Project", "title": "Test Title"}}),
        )
        # 5 access points
        zf.writestr("accessPoints.json", json.dumps({"accessPoints": [{}, {}, {}, {}, {}]}))
        # 2 floors
        zf.writestr("floorPlans.json", json.dumps({"floorPlans": [{}, {}]}))

    # Extract metadata
    await processor._extract_project_metadata(project_id, original_file, sample_metadata)

    # Verify counts
    assert sample_metadata.aps_count == 5
    assert sample_metadata.floors_count == 2
    # Title has priority over name in metadata extraction
    assert sample_metadata.project_name == "Test Title"


@pytest.mark.asyncio
async def test_extract_project_metadata_no_files(processor, sample_metadata, temp_storage):
    """Test extracting metadata when no files exist."""
    project_id = sample_metadata.project_id
    project_dir = temp_storage.get_project_dir(project_id)
    original_file = project_dir / "original.esx"

    # Should not raise exception
    await processor._extract_project_metadata(project_id, original_file, sample_metadata)

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
async def test_processing_updates_status_to_processing(processor, sample_metadata, temp_storage):
    """Test that processing updates status and index multiple times."""
    import zipfile
    import json

    project_id = sample_metadata.project_id

    # Create a valid .esx file for metadata extraction
    project_dir = temp_storage.get_project_dir(project_id)
    original_file = project_dir / "original.esx"

    with zipfile.ZipFile(original_file, "w") as zf:
        zf.writestr("project.json", json.dumps({"project": {"name": "Test"}}))
        zf.writestr("accessPoints.json", json.dumps({"accessPoints": [{}]}))

    # Mock subprocess.run result
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b""
    mock_result.stderr = b""

    with patch("app.services.processor.subprocess.run", return_value=mock_result):
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
