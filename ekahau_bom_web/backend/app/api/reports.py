"""Reports API endpoints."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.storage import StorageService

router = APIRouter(prefix="/reports", tags=["reports"])

# Initialize services
storage_service = StorageService()


@router.get("/{project_id}/list")
async def list_reports(project_id: UUID) -> dict:
    """List all reports and visualizations for a project.

    Args:
        project_id: Project UUID

    Returns:
        Dictionary with lists of reports and visualizations
    """
    # Check if project exists
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get report files
    reports = storage_service.list_report_files(project_id)

    # Get visualization files
    visualizations = storage_service.list_visualization_files(project_id)

    return {
        "project_id": str(project_id),
        "reports": reports,
        "visualizations": visualizations,
    }


@router.get("/{project_id}/download/{filename}")
async def download_report(project_id: UUID, filename: str) -> FileResponse:
    """Download a report file.

    Args:
        project_id: Project UUID
        filename: Report filename

    Returns:
        File download response
    """
    # Check if project exists
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get reports directory
    reports_dir = storage_service.get_reports_dir(project_id)

    # Sanitize filename to prevent directory traversal
    safe_filename = Path(filename).name
    file_path = reports_dir / safe_filename

    # Check if file exists
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Report file not found")

    # Determine media type based on extension
    media_types = {
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".html": "text/html",
        ".pdf": "application/pdf",
    }
    media_type = media_types.get(file_path.suffix.lower(), "application/octet-stream")

    # For HTML files, explicitly set inline disposition to display in browser
    # For other files, use attachment (default)
    if file_path.suffix.lower() == ".html":
        return FileResponse(
            path=file_path,
            media_type=media_type,
            headers={"Content-Disposition": "inline"},
        )
    else:
        return FileResponse(
            path=file_path, filename=safe_filename, media_type=media_type
        )


@router.get("/{project_id}/visualization/{filename}")
async def get_visualization(project_id: UUID, filename: str) -> FileResponse:
    """Get a floor plan visualization image.

    Args:
        project_id: Project UUID
        filename: Visualization filename (PNG)

    Returns:
        Image file response
    """
    # Check if project exists
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get visualizations directory
    viz_dir = storage_service.get_visualizations_dir(project_id)

    # Sanitize filename to prevent directory traversal
    safe_filename = Path(filename).name
    file_path = viz_dir / safe_filename

    # Check if file exists and is PNG
    if not file_path.exists() or not file_path.is_file() or file_path.suffix != ".png":
        raise HTTPException(status_code=404, detail="Visualization not found")

    return FileResponse(path=file_path, filename=safe_filename, media_type="image/png")


@router.get("/{project_id}/original")
async def download_original(project_id: UUID) -> FileResponse:
    """Download original .esx file.

    Args:
        project_id: Project UUID

    Returns:
        File download response
    """
    # Check if project exists
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get original file path
    project_dir = storage_service.get_project_dir(project_id)
    original_file = project_dir / "original.esx"

    # Check if file exists
    if not original_file.exists():
        raise HTTPException(status_code=404, detail="Original file not found")

    return FileResponse(
        path=original_file,
        filename=metadata.filename,
        media_type="application/zip",  # .esx is a ZIP archive
    )
