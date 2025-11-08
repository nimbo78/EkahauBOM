"""Upload API endpoints."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from app.auth import verify_admin
from app.models import (
    ProcessingRequest,
    ProcessingStatus,
    ProjectMetadata,
    UploadResponse,
)
from app.services.cache import cache_service
from app.services.index import index_service
from app.services.processor import ProcessorService
from app.services.storage_service import StorageService
from app.utils.short_links import calculate_expiry_date, generate_short_link

router = APIRouter(prefix="/upload", tags=["upload"])

# Initialize services
storage_service = StorageService()
processor_service = ProcessorService(storage_service)


def extract_project_name(file_content: bytes) -> str | None:
    """Extract project name from .esx file (ZIP archive).

    Args:
        file_content: Binary content of .esx file

    Returns:
        Project name or None if not found
    """
    try:
        with zipfile.ZipFile(BytesIO(file_content), "r") as zf:
            if "project.json" in zf.namelist():
                project_data = json.loads(zf.read("project.json"))
                project_info = project_data.get("project", {})
                # Try 'title' first (user-friendly name), then fall back to 'name'
                return project_info.get("title") or project_info.get("name")
    except Exception:
        # If extraction fails, return None (will use filename instead)
        pass
    return None


@router.post("", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...), _admin: str = Depends(verify_admin)
) -> UploadResponse:
    """Upload .esx file.

    Requires admin authentication.

    Args:
        file: Uploaded .esx file

    Returns:
        UploadResponse with project_id and short_link
    """
    # Validate file extension
    if not file.filename or not file.filename.endswith(".esx"):
        raise HTTPException(status_code=400, detail="Only .esx files are allowed")

    # Generate project ID
    project_id = uuid4()

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Validate file size (max 500 MB)
    if file_size > 500 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 500 MB allowed)")

    # Extract project name from .esx file
    project_name = extract_project_name(file_content)

    # Check if project with same name already exists
    if project_name:
        # Search by project name
        existing_projects = index_service.search(project_name)
        # Find exact match (case-insensitive)
        existing = next(
            (
                p
                for p in existing_projects
                if p.project_name and p.project_name.lower() == project_name.lower()
            ),
            None,
        )

        if existing:
            # Project with same name exists - return info without creating new
            from app.models import ProjectListItem

            return UploadResponse(
                project_id=existing.project_id,
                message=f"Project '{project_name}' already exists",
                short_link=existing.short_link,
                exists=True,
                existing_project=ProjectListItem(
                    project_id=existing.project_id,
                    project_name=existing.project_name or existing.filename,
                    filename=existing.filename,
                    upload_date=existing.upload_date,
                    aps_count=existing.aps_count,
                    processing_status=existing.processing_status,
                    short_link=existing.short_link,
                ),
            )

    # No existing project - create new one
    # Save file to storage
    file_path = await storage_service.save_uploaded_file(project_id, file.filename, file_content)

    # Generate short link
    short_link = generate_short_link()
    short_link_expires = calculate_expiry_date(days=30)

    # Create metadata
    metadata = ProjectMetadata(
        project_id=project_id,
        filename=file.filename,
        file_size=file_size,
        original_file=str(file_path.relative_to(storage_service.projects_dir.parent)),
        short_link=short_link,
        short_link_expires=short_link_expires,
        project_name=project_name,  # Use extracted project name
    )

    # Save metadata
    storage_service.save_metadata(project_id, metadata)

    # Add to index
    index_service.add(metadata)
    index_service.save_to_disk()

    # Invalidate projects list cache (new project added)
    cache_service.invalidate_projects_list()

    return UploadResponse(
        project_id=project_id,
        message=f"File '{file.filename}' uploaded successfully",
        short_link=short_link,
        exists=False,
    )


@router.put("/{project_id}/update", response_model=UploadResponse)
async def update_project(
    project_id: str, file: UploadFile = File(...), _admin: str = Depends(verify_admin)
) -> UploadResponse:
    """Update existing project with new .esx file.

    Replaces the original file and resets processing status.
    Requires admin authentication.

    Args:
        project_id: Project UUID to update
        file: New .esx file

    Returns:
        UploadResponse with updated project info

    Raises:
        HTTPException: If project not found or file invalid
    """
    # Validate project ID
    try:
        from uuid import UUID

        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    # Validate file extension
    if not file.filename or not file.filename.endswith(".esx"):
        raise HTTPException(status_code=400, detail="Only .esx files are allowed")

    # Check if project exists
    metadata = storage_service.load_metadata(project_uuid)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Read new file content
    file_content = await file.read()
    file_size = len(file_content)

    # Validate file size
    if file_size > 500 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 500 MB allowed)")

    # Extract project name from new file
    project_name = extract_project_name(file_content)

    # Save new file (overwrites old one)
    file_path = await storage_service.save_uploaded_file(project_uuid, file.filename, file_content)

    # Update metadata
    from datetime import UTC, datetime

    metadata.filename = file.filename
    metadata.file_size = file_size
    metadata.upload_date = datetime.now(UTC)
    metadata.project_name = project_name
    metadata.processing_status = ProcessingStatus.PENDING
    metadata.processing_started = None
    metadata.processing_completed = None
    metadata.processing_error = None
    metadata.aps_count = None
    metadata.buildings_count = None
    metadata.floors_count = None
    metadata.processing_flags = {}

    # Save updated metadata
    storage_service.save_metadata(project_uuid, metadata)

    # Update index
    index_service.add(metadata)  # add() also updates existing entries
    index_service.save_to_disk()

    # Invalidate cache (project updated)
    cache_service.invalidate_project(project_uuid)

    return UploadResponse(
        project_id=project_uuid,
        message=f"Project updated with '{file.filename}'",
        short_link=metadata.short_link,
        exists=False,
    )


@router.post("/{project_id}/process")
async def process_project(
    project_id: str,
    request: ProcessingRequest,
    background_tasks: BackgroundTasks,
    _admin: str = Depends(verify_admin),
) -> dict:
    """Start processing uploaded .esx file.

    Requires admin authentication.

    Args:
        project_id: Project UUID
        request: Processing configuration
        background_tasks: FastAPI background tasks

    Returns:
        Status message
    """
    # Validate project exists
    try:
        from uuid import UUID

        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    metadata = storage_service.load_metadata(project_uuid)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if already processing
    if metadata.processing_status.value == "processing":
        raise HTTPException(status_code=409, detail="Project is already being processed")

    # Start processing in background
    background_tasks.add_task(
        processor_service.process_project,
        project_uuid,
        request.group_by,
        request.output_formats,
        request.visualize_floor_plans,
        request.show_azimuth_arrows,
        request.ap_opacity,
        request.include_text_notes,
        request.include_picture_notes,
        request.include_cable_notes,
    )

    return {
        "message": "Processing started",
        "project_id": str(project_uuid),
        "processing_flags": {
            "group_by": request.group_by,
            "output_formats": request.output_formats,
            "visualize_floor_plans": request.visualize_floor_plans,
            "show_azimuth_arrows": request.show_azimuth_arrows,
            "ap_opacity": request.ap_opacity,
            "include_text_notes": request.include_text_notes,
            "include_picture_notes": request.include_picture_notes,
            "include_cable_notes": request.include_cable_notes,
        },
    }
