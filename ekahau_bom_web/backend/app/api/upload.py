"""Upload API endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.models import ProcessingRequest, ProjectMetadata, UploadResponse
from app.services.index import index_service
from app.services.processor import ProcessorService
from app.services.storage import StorageService
from app.utils.short_links import calculate_expiry_date, generate_short_link

router = APIRouter(prefix="/upload", tags=["upload"])

# Initialize services
storage_service = StorageService()
processor_service = ProcessorService(storage_service)


@router.post("", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    """Upload .esx file.

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
        raise HTTPException(
            status_code=413, detail="File too large (max 500 MB allowed)"
        )

    # Save file to storage
    file_path = await storage_service.save_uploaded_file(
        project_id, file.filename, file_content
    )

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
    )

    # Save metadata
    storage_service.save_metadata(project_id, metadata)

    # Add to index
    index_service.add(metadata)
    index_service.save_to_disk()

    return UploadResponse(
        project_id=project_id,
        message=f"File '{file.filename}' uploaded successfully",
        short_link=short_link,
    )


@router.post("/{project_id}/process")
async def process_project(
    project_id: str,
    request: ProcessingRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    """Start processing uploaded .esx file.

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
        raise HTTPException(
            status_code=409, detail="Project is already being processed"
        )

    # Start processing in background
    background_tasks.add_task(
        processor_service.process_project,
        project_uuid,
        request.group_by,
        request.output_formats,
        request.visualize_floor_plans,
        request.show_azimuth_arrows,
        request.ap_opacity,
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
        },
    }
