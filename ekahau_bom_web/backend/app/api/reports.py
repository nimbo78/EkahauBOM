"""Reports API endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import FileResponse, Response

from app.services.archive import archive_service
from app.services.cache import cache_service
from app.services.storage_service import StorageService
from app.utils.etag import generate_etag, should_return_304
from app.utils.thumbnails import get_thumbnail_path, ThumbnailSize

router = APIRouter(prefix="/reports", tags=["reports"])

# Initialize services
storage_service = StorageService()


@router.get("/{project_id}/list")
async def list_reports(project_id: UUID) -> dict:
    """List all reports and visualizations for a project.

    Args:
        project_id: Project UUID

    Returns:
        Dictionary with lists of reports and visualizations (cached for 15 min)
    """
    # Ensure project is unarchived before access
    if not archive_service.ensure_unarchived(project_id):
        raise HTTPException(status_code=503, detail="Failed to unarchive project")

    # Try to get from cache
    cached = cache_service.get_reports(project_id)
    if cached is not None:
        return cached

    # Check if project exists
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get report files
    reports = storage_service.list_report_files(project_id)

    # Get visualization files
    visualizations = storage_service.list_visualization_files(project_id)

    result = {
        "project_id": str(project_id),
        "reports": reports,
        "visualizations": visualizations,
    }

    # Cache the result
    cache_service.set_reports(project_id, result)

    return result


@router.get("/{project_id}/download/{filename}", response_model=None)
async def download_report(
    project_id: UUID,
    filename: str,
    if_none_match: Optional[str] = Header(None),
) -> FileResponse | Response:
    """Download a report file with ETag support.

    Args:
        project_id: Project UUID
        filename: Report filename
        if_none_match: If-None-Match header for ETag validation

    Returns:
        File download response or 304 Not Modified
    """
    # Ensure project is unarchived before access
    if not archive_service.ensure_unarchived(project_id):
        raise HTTPException(status_code=503, detail="Failed to unarchive project")

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

    # Generate ETag for the file
    etag = generate_etag(file_path)

    # Check if client has fresh copy
    if should_return_304(etag, if_none_match):
        return Response(status_code=304, headers={"ETag": etag})

    # Determine media type based on extension
    media_types = {
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".html": "text/html",
        ".pdf": "application/pdf",
    }
    media_type = media_types.get(file_path.suffix.lower(), "application/octet-stream")

    # For HTML and PDF files, explicitly set inline disposition to display in browser
    # For other files, use attachment (default)
    if file_path.suffix.lower() in [".html", ".pdf"]:
        return FileResponse(
            path=file_path,
            media_type=media_type,
            headers={"Content-Disposition": "inline", "ETag": etag},
        )
    else:
        return FileResponse(
            path=file_path,
            filename=safe_filename,
            media_type=media_type,
            headers={"ETag": etag},
        )


@router.get("/{project_id}/visualization/{filename}", response_model=None)
async def get_visualization(
    project_id: UUID,
    filename: str,
    if_none_match: Optional[str] = Header(None),
) -> FileResponse | Response:
    """Get a floor plan visualization image with ETag support.

    Args:
        project_id: Project UUID
        filename: Visualization filename (PNG)
        if_none_match: If-None-Match header for ETag validation

    Returns:
        Image file response or 304 Not Modified
    """
    # Ensure project is unarchived before access
    if not archive_service.ensure_unarchived(project_id):
        raise HTTPException(status_code=503, detail="Failed to unarchive project")

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

    # Generate ETag for the file
    etag = generate_etag(file_path)

    # Check if client has fresh copy
    if should_return_304(etag, if_none_match):
        return Response(status_code=304, headers={"ETag": etag})

    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type="image/png",
        headers={"ETag": etag},
    )


@router.get("/{project_id}/visualization/{filename}/thumb", response_model=None)
async def get_visualization_thumbnail(
    project_id: UUID,
    filename: str,
    size: ThumbnailSize = Query(
        "small", description="Thumbnail size: small (200x150) or medium (800x600)"
    ),
    if_none_match: Optional[str] = Header(None),
) -> FileResponse | Response:
    """Get a thumbnail for a floor plan visualization with ETag support.

    If thumbnail doesn't exist, returns the original image as fallback.

    Args:
        project_id: Project UUID
        filename: Visualization filename (PNG)
        size: Thumbnail size ('small' or 'medium')
        if_none_match: If-None-Match header for ETag validation

    Returns:
        Thumbnail image or original image as fallback or 304 Not Modified

    Example:
        GET /api/reports/{id}/visualization/floor1.png/thumb?size=small
    """
    # Ensure project is unarchived before access
    if not archive_service.ensure_unarchived(project_id):
        raise HTTPException(status_code=503, detail="Failed to unarchive project")

    # Check if project exists
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get visualizations directory
    viz_dir = storage_service.get_visualizations_dir(project_id)

    # Sanitize filename to prevent directory traversal
    safe_filename = Path(filename).name
    original_path = viz_dir / safe_filename

    # Check if original file exists
    if not original_path.exists() or not original_path.is_file() or original_path.suffix != ".png":
        raise HTTPException(status_code=404, detail="Visualization not found")

    # Try to get thumbnail
    thumbs_dir = viz_dir / "thumbs"
    thumb_path = get_thumbnail_path(original_path, size, thumbs_dir)

    # Determine which file to serve (thumbnail or original)
    file_to_serve = thumb_path if thumb_path.exists() else original_path

    # Generate ETag for the file
    etag = generate_etag(file_to_serve)

    # Check if client has fresh copy
    if should_return_304(etag, if_none_match):
        return Response(status_code=304, headers={"ETag": etag})

    return FileResponse(path=file_to_serve, media_type="image/png", headers={"ETag": etag})


@router.get("/{project_id}/original", response_model=None)
async def download_original(
    project_id: UUID,
    if_none_match: Optional[str] = Header(None),
) -> FileResponse | Response:
    """Download original .esx file with ETag support.

    Args:
        project_id: Project UUID
        if_none_match: If-None-Match header for ETag validation

    Returns:
        File download response or 304 Not Modified
    """
    # Ensure project is unarchived before access
    if not archive_service.ensure_unarchived(project_id):
        raise HTTPException(status_code=503, detail="Failed to unarchive project")

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

    # Generate ETag for the file
    etag = generate_etag(original_file)

    # Check if client has fresh copy
    if should_return_304(etag, if_none_match):
        return Response(status_code=304, headers={"ETag": etag})

    return FileResponse(
        path=original_file,
        filename=metadata.filename,
        media_type="application/zip",  # .esx is a ZIP archive
        headers={"ETag": etag},
    )
