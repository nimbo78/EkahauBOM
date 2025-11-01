"""Projects API endpoints."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.models import ProcessingStatus, ProjectListItem, ProjectMetadata
from app.services.index import index_service
from app.services.storage import StorageService
from app.utils.short_links import is_link_expired

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
        List of projects
    """
    if search:
        # Search by query
        projects = index_service.search(search)
        if limit:
            projects = projects[:limit]
    else:
        # List all with optional filters
        projects = index_service.list_all(status=status, limit=limit)

    return projects


@router.get("/{project_id}", response_model=ProjectMetadata)
async def get_project(project_id: UUID) -> ProjectMetadata:
    """Get project details by ID.

    Args:
        project_id: Project UUID

    Returns:
        Project metadata
    """
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

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

    return metadata


@router.delete("/{project_id}")
async def delete_project(project_id: UUID) -> dict:
    """Delete project.

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

    return {"message": "Project deleted successfully", "project_id": str(project_id)}


@router.get("/stats/summary")
async def get_stats_summary() -> dict:
    """Get statistics summary.

    Returns:
        Summary statistics about projects
    """
    return {
        "total": index_service.count(),
        "pending": index_service.count(status=ProcessingStatus.PENDING),
        "processing": index_service.count(status=ProcessingStatus.PROCESSING),
        "completed": index_service.count(status=ProcessingStatus.COMPLETED),
        "failed": index_service.count(status=ProcessingStatus.FAILED),
    }
