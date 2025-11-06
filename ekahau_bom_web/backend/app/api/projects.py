"""Projects API endpoints."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import verify_admin
from app.models import ProcessingStatus, ProjectListItem, ProjectMetadata
from app.services.archive import archive_service
from app.services.cache import cache_service
from app.services.index import index_service
from app.services.storage import StorageService
from app.utils.short_links import (
    calculate_expiry_date,
    generate_short_link,
    is_link_expired,
)

router = APIRouter(prefix="/projects", tags=["projects"])

# Initialize services
storage_service = StorageService()


@router.get("", response_model=list[ProjectListItem])
async def list_projects(
    status: Optional[ProcessingStatus] = Query(None, description="Filter by status"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    search: Optional[str] = Query(None, description="Search by name or filename"),
) -> list[ProjectListItem]:
    """List all projects.

    Args:
        status: Optional status filter (pending, processing, completed, failed)
        limit: Optional limit on number of results
        search: Optional search query for project name or filename

    Returns:
        List of projects (cached for 5 min if no filters)
    """
    # Only cache if no filters/search/limit (most common case)
    use_cache = not search and not status and not limit

    if use_cache:
        # Try to get from cache
        cached = cache_service.get_projects()
        if cached is not None:
            return cached

    # Fetch from index service
    if search:
        # Search by query
        projects = index_service.search(search)
        if limit:
            projects = projects[:limit]
    else:
        # List all with optional filters
        projects = index_service.list_all(status=status, limit=limit)

    # Cache only if no filters
    if use_cache:
        cache_service.set_projects(projects)

    return projects


@router.get("/{project_id}", response_model=ProjectMetadata)
async def get_project(project_id: UUID) -> ProjectMetadata:
    """Get project details by ID.

    Args:
        project_id: Project UUID

    Returns:
        Project metadata (cached for 10 min)
    """
    # Ensure project is unarchived before access
    if not archive_service.ensure_unarchived(project_id):
        raise HTTPException(status_code=503, detail="Failed to unarchive project")

    # Try to get from cache
    cached = cache_service.get_project_details(project_id)
    if cached is not None:
        return ProjectMetadata(**cached)

    # Fetch from storage
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Cache the result
    cache_service.set_project_details(project_id, metadata.model_dump())

    return metadata


@router.get("/short/{short_link}", response_model=ProjectMetadata)
async def get_project_by_short_link(short_link: str) -> ProjectMetadata:
    """Get project by short link.

    Args:
        short_link: Short link code

    Returns:
        Project metadata
    """
    metadata = index_service.get_by_short_link(short_link)
    if not metadata:
        raise HTTPException(status_code=404, detail="Short link not found")

    # Check if link is expired
    if is_link_expired(metadata.short_link_expires):
        raise HTTPException(status_code=410, detail="Short link has expired")

    # Ensure project is unarchived before access
    if not archive_service.ensure_unarchived(metadata.project_id):
        raise HTTPException(status_code=503, detail="Failed to unarchive project")

    return metadata


@router.delete("/{project_id}")
async def delete_project(project_id: UUID, _admin: str = Depends(verify_admin)) -> dict:
    """Delete project.

    Requires admin authentication.

    Args:
        project_id: Project UUID

    Returns:
        Success message
    """
    # Check if project exists
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Remove from index
    index_service.remove(project_id)
    index_service.save_to_disk()

    # Delete files
    storage_service.delete_project(project_id)

    # Invalidate cache
    cache_service.invalidate_project(project_id)

    return {"message": "Project deleted successfully", "project_id": str(project_id)}


@router.get("/stats/summary")
async def get_stats_summary() -> dict:
    """Get statistics summary.

    Returns:
        Summary statistics about projects (cached for 5 min)
    """
    # Try to get from cache
    cached = cache_service.get_stats()
    if cached is not None:
        return cached

    # Calculate stats
    stats = {
        "total": index_service.count(),
        "pending": index_service.count(status=ProcessingStatus.PENDING),
        "processing": index_service.count(status=ProcessingStatus.PROCESSING),
        "completed": index_service.count(status=ProcessingStatus.COMPLETED),
        "failed": index_service.count(status=ProcessingStatus.FAILED),
    }

    # Cache the result
    cache_service.set_stats(stats)

    return stats


# ===== Short Link Management (Admin Only) =====


@router.post("/{project_id}/short-link/renew")
async def renew_short_link(
    project_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to extend"),
    _admin: str = Depends(verify_admin),
) -> dict:
    """Renew/extend expiry date for project short link (admin only).

    Args:
        project_id: Project UUID
        days: Number of days to extend (1-365, default 30)

    Returns:
        Updated short link info with new expiry date

    Raises:
        HTTPException: If project not found or no short link exists
    """
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    if not metadata.short_link:
        raise HTTPException(status_code=404, detail="No short link exists for this project")

    # Extend expiry date from now
    metadata.short_link_expires = calculate_expiry_date(days)

    # Save metadata
    storage_service.save_metadata(project_id, metadata)
    index_service.add(metadata)
    index_service.save_to_disk()

    # Invalidate cache
    cache_service.invalidate_project(project_id)

    return {
        "message": f"Short link renewed for {days} days",
        "short_link": metadata.short_link,
        "expires_at": metadata.short_link_expires.isoformat(),
    }


@router.post("/{project_id}/short-link/create")
async def create_short_link(
    project_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days until expiry"),
    _admin: str = Depends(verify_admin),
) -> dict:
    """Create new short link for project (admin only).

    If short link already exists, regenerates it with new expiry.

    Args:
        project_id: Project UUID
        days: Number of days until expiry (1-365, default 30)

    Returns:
        New short link info

    Raises:
        HTTPException: If project not found
    """
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Generate new short link
    metadata.short_link = generate_short_link()
    metadata.short_link_expires = calculate_expiry_date(days)

    # Save metadata
    storage_service.save_metadata(project_id, metadata)
    index_service.add(metadata)
    index_service.save_to_disk()

    # Invalidate cache
    cache_service.invalidate_project(project_id)

    return {
        "message": "Short link created successfully",
        "short_link": metadata.short_link,
        "expires_at": metadata.short_link_expires.isoformat(),
    }


@router.delete("/{project_id}/short-link")
async def delete_short_link(project_id: UUID, _admin: str = Depends(verify_admin)) -> dict:
    """Delete short link for project (admin only).

    Args:
        project_id: Project UUID

    Returns:
        Success message

    Raises:
        HTTPException: If project not found or no short link exists
    """
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    if not metadata.short_link:
        raise HTTPException(status_code=404, detail="No short link exists for this project")

    # Clear short link
    metadata.short_link = None
    metadata.short_link_expires = None

    # Save metadata
    storage_service.save_metadata(project_id, metadata)
    index_service.add(metadata)
    index_service.save_to_disk()

    # Invalidate cache
    cache_service.invalidate_project(project_id)

    return {"message": "Short link deleted successfully"}
