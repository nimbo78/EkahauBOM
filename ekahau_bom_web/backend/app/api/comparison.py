"""Comparison API endpoints for project version comparison."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from app.models import ComparisonData, ComparisonSummaryDTO
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/comparison", tags=["comparison"])

# Initialize services
storage_service = StorageService()


def _get_comparison_dir(project_id: UUID) -> Path:
    """Get comparison directory for a project."""
    project_dir = storage_service.get_project_dir(project_id)
    return project_dir / "comparison"


def _load_comparison_data(project_id: UUID) -> Optional[ComparisonData]:
    """Load comparison data from storage."""
    comparison_dir = _get_comparison_dir(project_id)
    comparison_file = comparison_dir / "comparison_data.json"

    if not comparison_file.exists():
        return None

    try:
        with open(comparison_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ComparisonData(**data)
    except Exception as e:
        logger.error(f"Error loading comparison data: {e}")
        return None


@router.get("/{project_id}")
async def get_comparison(project_id: UUID) -> ComparisonData:
    """Get comparison data for a project.

    Args:
        project_id: Project UUID

    Returns:
        ComparisonData with all comparison details

    Raises:
        HTTPException: If project or comparison not found
    """
    # Check if project exists
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load comparison data
    comparison = _load_comparison_data(project_id)
    if not comparison:
        raise HTTPException(
            status_code=404,
            detail="No comparison data available. Upload a new version to generate comparison.",
        )

    return comparison


@router.get("/{project_id}/summary")
async def get_comparison_summary(project_id: UUID) -> ComparisonSummaryDTO:
    """Get comparison summary for a project.

    Args:
        project_id: Project UUID

    Returns:
        ComparisonSummaryDTO with summary information

    Raises:
        HTTPException: If project not found
    """
    # Check if project exists
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load comparison data
    comparison = _load_comparison_data(project_id)
    if not comparison:
        return ComparisonSummaryDTO(has_comparison=False)

    return ComparisonSummaryDTO(
        has_comparison=True,
        comparison_timestamp=comparison.comparison_timestamp,
        total_changes=comparison.total_changes,
        aps_added=comparison.inventory.aps_added,
        aps_removed=comparison.inventory.aps_removed,
        aps_modified=comparison.inventory.aps_modified,
        aps_moved=comparison.inventory.aps_moved,
        aps_renamed=comparison.inventory.aps_renamed,
    )


@router.get("/{project_id}/diff/{floor_name}")
async def get_diff_image(
    project_id: UUID,
    floor_name: str,
) -> FileResponse:
    """Get visual diff image for a specific floor.

    Args:
        project_id: Project UUID
        floor_name: Floor name (URL-encoded)

    Returns:
        PNG image file

    Raises:
        HTTPException: If project, comparison, or floor diff not found
    """
    # Check if project exists
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load comparison to check for diff images
    comparison = _load_comparison_data(project_id)
    if not comparison:
        raise HTTPException(status_code=404, detail="No comparison data available")

    # Check if floor has a diff image
    if floor_name not in comparison.diff_images:
        raise HTTPException(status_code=404, detail=f"No diff image for floor: {floor_name}")

    # Get diff image path
    comparison_dir = _get_comparison_dir(project_id)
    diff_image_path = comparison_dir / "visualizations" / comparison.diff_images[floor_name]

    if not diff_image_path.exists():
        raise HTTPException(status_code=404, detail="Diff image file not found")

    return FileResponse(
        path=diff_image_path,
        media_type="image/png",
        filename=f"diff_{floor_name}.png",
    )


@router.get("/{project_id}/diff-images")
async def list_diff_images(project_id: UUID) -> dict:
    """List available diff images for a project.

    Args:
        project_id: Project UUID

    Returns:
        Dictionary with floor names and image URLs
    """
    # Check if project exists
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load comparison data
    comparison = _load_comparison_data(project_id)
    if not comparison:
        return {"project_id": str(project_id), "diff_images": {}}

    # Build URLs for diff images
    diff_images = {}
    for floor_name, filename in comparison.diff_images.items():
        diff_images[floor_name] = f"/api/comparison/{project_id}/diff/{floor_name}"

    return {"project_id": str(project_id), "diff_images": diff_images}


@router.get("/{project_id}/report/{format}")
async def download_comparison_report(
    project_id: UUID,
    format: Literal["csv", "json", "html"],
) -> FileResponse:
    """Download comparison report in specified format.

    Args:
        project_id: Project UUID
        format: Report format (csv, json, html)

    Returns:
        Report file download

    Raises:
        HTTPException: If project, comparison, or report not found
    """
    # Check if project exists
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load comparison data
    comparison = _load_comparison_data(project_id)
    if not comparison:
        raise HTTPException(status_code=404, detail="No comparison data available")

    # Find report file
    comparison_dir = _get_comparison_dir(project_id)

    # Look for report file with the format extension
    report_files = list(comparison_dir.glob(f"*_comparison.{format}"))
    if not report_files:
        raise HTTPException(
            status_code=404, detail=f"Comparison report in {format} format not found"
        )

    report_path = report_files[0]

    # Set media type based on format
    media_types = {
        "csv": "text/csv",
        "json": "application/json",
        "html": "text/html",
    }

    return FileResponse(
        path=report_path,
        media_type=media_types.get(format, "application/octet-stream"),
        filename=report_path.name,
    )


@router.delete("/{project_id}")
async def delete_comparison(project_id: UUID) -> dict:
    """Delete comparison data for a project.

    Args:
        project_id: Project UUID

    Returns:
        Success message

    Raises:
        HTTPException: If project not found
    """
    # Check if project exists
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get comparison directory
    comparison_dir = _get_comparison_dir(project_id)
    if not comparison_dir.exists():
        return {"message": "No comparison data to delete"}

    # Delete comparison data
    import shutil

    try:
        shutil.rmtree(comparison_dir)
        logger.info(f"Deleted comparison data for project {project_id}")
        return {"message": "Comparison data deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting comparison data: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete comparison data")
