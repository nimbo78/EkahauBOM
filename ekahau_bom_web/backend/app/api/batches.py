"""Batch processing API endpoints."""

from __future__ import annotations


import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID
from collections import defaultdict

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.auth import verify_admin
from app.models import (
    BatchListItem,
    BatchMetadata,
    BatchStatus,
    BatchUploadRequest,
    BatchUploadResponse,
    DirectoryScanResponse,
    ProcessingRequest,
    ScannedFile,
)
from app.services.batch_service import batch_service
from app.services.storage_service import StorageService
from app.services.index import index_service
from app.services.watch_service import get_watch_service, WatchConfig
from app.services.report_schedule_service import get_report_schedule_service, TimeRange
from app.services.batch_archive_service import get_batch_archive_service
from app.websocket import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batches", tags=["batches"])

# Initialize services
storage_service = StorageService()
watch_service = get_watch_service(batch_service, storage_service)
report_schedule_service = get_report_schedule_service(batch_service, storage_service)
batch_archive_service = get_batch_archive_service(batch_service, storage_service)


@router.post("/upload", response_model=BatchUploadResponse, dependencies=[Depends(verify_admin)])
async def upload_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(..., description="Multiple .esx files"),
    batch_name: Optional[str] = Form(None, description="Optional batch name"),
    parallel_workers: int = Form(1, description="Number of parallel workers"),
    processing_options: Optional[str] = Form(None, description="Processing options as JSON"),
    auto_process: bool = Form(False, description="Automatically start processing after upload"),
    file_actions: Optional[str] = Form(None, description="Per-file actions as JSON"),
) -> BatchUploadResponse:
    """Upload multiple .esx files for batch processing.

    Args:
        background_tasks: FastAPI background tasks
        files: List of uploaded .esx files
        batch_name: Optional batch name
        parallel_workers: Number of parallel workers (1-8)
        processing_options: Optional processing options as JSON string
        auto_process: Whether to automatically start processing after upload

    Returns:
        Batch upload response with batch ID and upload status
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Validate parallel_workers
    if parallel_workers < 1 or parallel_workers > 8:
        raise HTTPException(status_code=400, detail="parallel_workers must be between 1 and 8")

    # Parse processing options if provided
    proc_options = None
    if processing_options:
        import json

        try:
            proc_options = ProcessingRequest(**json.loads(processing_options))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid processing_options: {e}")

    # Create batch
    batch_metadata = batch_service.create_batch(
        batch_name=batch_name,
        processing_options=proc_options,
        parallel_workers=parallel_workers,
    )

    # Parse file actions if provided
    actions_map = {}
    if file_actions:
        import json

        try:
            actions_list = json.loads(file_actions)
            actions_map = {action["filename"]: action for action in actions_list}
        except Exception as e:
            logger.warning(f"Failed to parse file_actions: {e}")

    files_uploaded = []
    files_failed = []

    # Upload each file and add to batch
    for file in files:
        if not file.filename or not file.filename.endswith(".esx"):
            files_failed.append(file.filename or "unknown")
            continue

        # Check file action
        action_config = actions_map.get(file.filename, {"action": "new"})
        action = action_config.get("action", "new")

        # Skip if action is 'skip'
        if action == "skip":
            logger.info(f"Skipping {file.filename} as per user request")
            continue

        try:
            file_content = await file.read()

            if action == "update" and "existingProjectId" in action_config:
                # Update existing project
                from uuid import UUID

                existing_project_id = UUID(action_config["existingProjectId"])

                # Check if project exists
                metadata = storage_service.load_metadata(existing_project_id)
                if not metadata:
                    logger.error(f"Project {existing_project_id} not found for update")
                    files_failed.append(file.filename)
                    continue

                # Save new file (overwrites old one)
                file_path = await storage_service.save_uploaded_file(
                    existing_project_id, file.filename, file_content
                )

                # Update metadata
                from datetime import UTC, datetime
                from app.models import ProcessingStatus

                metadata.filename = file.filename
                metadata.file_size = len(file_content)
                metadata.upload_date = datetime.now(UTC)
                metadata.processing_status = ProcessingStatus.PENDING
                metadata.processing_started = None
                metadata.processing_completed = None
                metadata.processing_error = None

                # Save updated metadata
                storage_service.save_metadata(existing_project_id, metadata)

                # Add to batch
                batch_service.add_project_to_batch(
                    batch_id=batch_metadata.batch_id,
                    project_id=existing_project_id,
                    filename=file.filename,
                )

                # Update index
                index_service.add(metadata)

                files_uploaded.append(file.filename)
                logger.info(f"Updated project {existing_project_id} with {file.filename}")

            else:
                # Create new project
                from uuid import uuid4

                project_id = uuid4()

                # Save file using storage service
                file_path = await storage_service.save_uploaded_file(
                    project_id, file.filename, file_content
                )

                # Extract project name from .esx file
                from app.api.upload import extract_project_name

                project_name = extract_project_name(file_content)

                # Generate short link if requested in processing options
                short_link = None
                short_link_expires = None
                if proc_options and getattr(proc_options, "create_short_link", False):
                    from app.utils.short_links import calculate_expiry_date, generate_short_link

                    short_link = generate_short_link()
                    days = getattr(proc_options, "short_link_days", 30)
                    short_link_expires = calculate_expiry_date(days=days)

                # Create metadata
                from app.models import ProjectMetadata, ProcessingStatus

                metadata = ProjectMetadata(
                    project_id=project_id,
                    filename=file.filename,
                    file_size=len(file_content),
                    original_file=file_path,  # Already a string path
                    processing_status=ProcessingStatus.PENDING,
                    project_name=project_name,
                    short_link=short_link,
                    short_link_expires=short_link_expires,
                )

                # Save metadata
                storage_service.save_metadata(project_id, metadata)

                # Add project to batch
                batch_service.add_project_to_batch(
                    batch_id=batch_metadata.batch_id,
                    project_id=project_id,
                    filename=file.filename,
                )

                # Add to index
                index_service.add(metadata)

                files_uploaded.append(file.filename)
                logger.info(f"Uploaded {file.filename} to batch {batch_metadata.batch_id}")

        except Exception as e:
            logger.error(f"Failed to upload {file.filename}: {e}")
            files_failed.append(file.filename)

    # Save index to disk
    if files_uploaded:
        index_service.save_to_disk()

    # Broadcast batch created notification
    await connection_manager.send_batch_created(batch_metadata.batch_id)

    # Schedule batch processing in background if auto_process is True
    if files_uploaded and auto_process and proc_options:
        background_tasks.add_task(
            batch_service.process_batch,
            batch_metadata.batch_id,
        )

    return BatchUploadResponse(
        batch_id=batch_metadata.batch_id,
        message=f"Uploaded {len(files_uploaded)} files, {len(files_failed)} failed",
        files_count=len(files),
        files_uploaded=files_uploaded,
        files_failed=files_failed,
    )


@router.get("", response_model=list[BatchListItem])
async def list_batches(
    status: Optional[BatchStatus] = Query(None, description="Filter by status"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    search: Optional[str] = Query(None, description="Search in batch names and project names"),
    created_after: Optional[str] = Query(
        None, description="Filter batches created after date (ISO format)"
    ),
    created_before: Optional[str] = Query(
        None, description="Filter batches created before date (ISO format)"
    ),
    min_projects: Optional[int] = Query(None, description="Minimum number of projects", ge=0),
    max_projects: Optional[int] = Query(None, description="Maximum number of projects", ge=0),
    sort_by: str = Query(
        "date",
        description="Sort field: date, name, project_count, success_rate",
        pattern="^(date|name|project_count|success_rate)$",
    ),
    sort_order: str = Query("desc", description="Sort order: asc or desc", pattern="^(asc|desc)$"),
    limit: Optional[int] = Query(None, description="Limit number of results", ge=1),
) -> list[BatchListItem]:
    """List all batches with advanced filtering and sorting.

    Args:
        status: Optional status filter
        tags: Optional tags filter (comma-separated, e.g., "customer-x,production")
        search: Optional text search (searches batch name and project names)
        created_after: Optional filter for batches created after this date (ISO 8601)
        created_before: Optional filter for batches created before this date (ISO 8601)
        min_projects: Optional minimum number of projects
        max_projects: Optional maximum number of projects
        sort_by: Sort field (date, name, project_count, success_rate)
        sort_order: Sort order (asc or desc)
        limit: Optional limit on number of results

    Returns:
        List of batches matching the filters
    """
    # Parse tags if provided
    tags_list = None
    if tags:
        tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

    # Parse dates if provided
    created_after_dt = None
    created_before_dt = None

    if created_after:
        try:
            created_after_dt = datetime.fromisoformat(created_after.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid created_after date format: {created_after}. Use ISO 8601 format.",
            )

    if created_before:
        try:
            created_before_dt = datetime.fromisoformat(created_before.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid created_before date format: {created_before}. Use ISO 8601 format.",
            )

    batches = batch_service.list_batches(
        status=status,
        tags=tags_list,
        search_query=search,
        created_after=created_after_dt,
        created_before=created_before_dt,
        min_projects=min_projects,
        max_projects=max_projects,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
    )

    return [
        BatchListItem(
            batch_id=batch.batch_id,
            batch_name=batch.batch_name,
            created_date=batch.created_date,
            status=batch.status,
            total_projects=batch.statistics.total_projects,
            successful_projects=batch.statistics.successful_projects,
            failed_projects=batch.statistics.failed_projects,
            tags=batch.tags,
        )
        for batch in batches
    ]


@router.get("/{batch_id}/download", dependencies=[Depends(verify_admin)])
async def download_batch(
    batch_id: UUID,
) -> FileResponse:
    """Download all batch projects as a ZIP archive.

    Args:
        batch_id: Batch UUID

    Returns:
        ZIP file with all batch projects

    Raises:
        HTTPException: If batch not found or archive creation fails
    """
    # Create archive for download
    logger.info(f"Creating archive for batch {batch_id}")

    try:
        # Create ZIP archive
        zip_path = batch_service.create_batch_archive(batch_id)

        # Get batch metadata for filename
        metadata = batch_service.load_batch_metadata(batch_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Batch not found")

        # Sanitize batch name for filename
        safe_batch_name = metadata.batch_name.replace("/", "_").replace("\\", "_").replace(" ", "_")
        filename = f"batch_{safe_batch_name}_{batch_id}.zip"

        # Return file with cleanup
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=filename,
            background=BackgroundTask(lambda: cleanup_temp_file(zip_path)),
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    except Exception as e:
        logger.error(f"Failed to create batch archive: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create batch archive: {str(e)}")


@router.get("/{batch_id}", response_model=BatchMetadata)
async def get_batch(batch_id: UUID) -> BatchMetadata:
    """Get batch details by ID.

    Args:
        batch_id: Batch UUID

    Returns:
        Batch metadata with full details
    """
    metadata = batch_service.load_batch_metadata(batch_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Batch not found")

    return metadata


@router.patch("/{batch_id}/tags", dependencies=[Depends(verify_admin)])
async def update_batch_tags(
    batch_id: UUID,
    tags_to_add: list[str] = Query([], description="Tags to add"),
    tags_to_remove: list[str] = Query([], description="Tags to remove"),
) -> dict:
    """Add or remove tags from a batch.

    Args:
        batch_id: Batch UUID
        tags_to_add: List of tags to add to the batch
        tags_to_remove: List of tags to remove from the batch

    Returns:
        Updated tags list
    """
    metadata = batch_service.load_batch_metadata(batch_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Update tags using batch service method
    updated_tags = batch_service.update_batch_tags(
        batch_id=batch_id,
        tags_to_add=tags_to_add,
        tags_to_remove=tags_to_remove,
    )

    return {
        "batch_id": str(batch_id),
        "tags": updated_tags,
        "message": f"Tags updated successfully. Added: {tags_to_add}, Removed: {tags_to_remove}",
    }


@router.post(
    "/{batch_id}/process", response_model=BatchMetadata, dependencies=[Depends(verify_admin)]
)
async def process_batch(
    batch_id: UUID,
    background_tasks: BackgroundTasks,
) -> BatchMetadata:
    """Start processing a batch.

    Args:
        batch_id: Batch UUID
        background_tasks: FastAPI background tasks

    Returns:
        Updated batch metadata
    """
    metadata = batch_service.load_batch_metadata(batch_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Batch not found")

    if metadata.status == BatchStatus.PROCESSING:
        raise HTTPException(status_code=409, detail="Batch is already being processed")

    if metadata.status in [BatchStatus.COMPLETED, BatchStatus.PARTIAL]:
        raise HTTPException(
            status_code=409,
            detail="Batch already processed. Create a new batch to reprocess.",
        )

    # Schedule processing in background
    background_tasks.add_task(batch_service.process_batch, batch_id)

    return metadata


@router.get("/{batch_id}/status", response_model=dict)
async def get_batch_status(batch_id: UUID) -> dict:
    """Get batch processing status.

    Args:
        batch_id: Batch UUID

    Returns:
        Batch status summary
    """
    metadata = batch_service.load_batch_metadata(batch_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Batch not found")

    return {
        "batch_id": str(metadata.batch_id),
        "status": metadata.status,
        "total_projects": len(metadata.project_ids),
        "completed_projects": sum(
            1 for ps in metadata.project_statuses if ps.status == "completed"
        ),
        "failed_projects": sum(1 for ps in metadata.project_statuses if ps.status == "failed"),
        "statistics": metadata.statistics.model_dump(),
    }


@router.delete("/{batch_id}", dependencies=[Depends(verify_admin)])
async def delete_batch(batch_id: UUID) -> dict:
    """Delete a batch and all its data.

    Args:
        batch_id: Batch UUID

    Returns:
        Success message
    """
    success = batch_service.delete_batch(batch_id)
    if not success:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Broadcast batch deleted notification
    await connection_manager.send_batch_deleted(batch_id)

    return {"message": f"Batch {batch_id} deleted successfully"}


@router.post(
    "/scan-directory", response_model=DirectoryScanResponse, dependencies=[Depends(verify_admin)]
)
async def scan_directory(
    directory_path: str = Form(..., description="Absolute path to directory"),
    recursive: bool = Form(False, description="Scan subdirectories recursively"),
) -> DirectoryScanResponse:
    """Scan a directory for .esx files.

    Args:
        directory_path: Absolute path to directory to scan
        recursive: Whether to scan subdirectories

    Returns:
        DirectoryScanResponse with list of found .esx files
    """
    from pathlib import Path
    from datetime import datetime

    try:
        directory = Path(directory_path)

        # Validate directory exists
        if not directory.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {directory_path}")

        if not directory.is_dir():
            raise HTTPException(
                status_code=400, detail=f"Path is not a directory: {directory_path}"
            )

        # Scan for .esx files
        scanned_files: list[ScannedFile] = []
        subdirs_scanned = 0

        if recursive:
            # Recursive scan
            for esx_file in directory.rglob("*.esx"):
                if esx_file.is_file():
                    stat = esx_file.stat()
                    scanned_files.append(
                        ScannedFile(
                            filename=esx_file.name,
                            filepath=str(esx_file.absolute()),
                            filesize=stat.st_size,
                            modified_date=datetime.fromtimestamp(stat.st_mtime),
                        )
                    )

            # Count subdirectories
            subdirs_scanned = sum(1 for _ in directory.rglob("*") if _.is_dir())
        else:
            # Non-recursive scan (current directory only)
            for esx_file in directory.glob("*.esx"):
                if esx_file.is_file():
                    stat = esx_file.stat()
                    scanned_files.append(
                        ScannedFile(
                            filename=esx_file.name,
                            filepath=str(esx_file.absolute()),
                            filesize=stat.st_size,
                            modified_date=datetime.fromtimestamp(stat.st_mtime),
                        )
                    )

        # Sort by filename
        scanned_files.sort(key=lambda x: x.filename.lower())

        logger.info(
            f"Scanned directory {directory_path} (recursive={recursive}): "
            f"found {len(scanned_files)} .esx files"
        )

        return DirectoryScanResponse(
            directory=directory_path,
            total_files=len(scanned_files),
            files=scanned_files,
            subdirectories_scanned=subdirs_scanned,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning directory {directory_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error scanning directory: {str(e)}")


@router.post(
    "/import-from-paths", response_model=BatchUploadResponse, dependencies=[Depends(verify_admin)]
)
async def import_from_paths(
    background_tasks: BackgroundTasks,
    request: dict,
) -> BatchUploadResponse:
    """Import .esx files from server filesystem paths into a batch.

    Args:
        background_tasks: FastAPI background tasks
        request: Import request containing file paths and processing options

    Returns:
        Batch upload response with batch ID and import status
    """
    import json
    import shutil
    from pathlib import Path
    from uuid import uuid4
    from datetime import UTC, datetime
    from app.models import ImportFromPathsRequest, ProjectMetadata, ProcessingStatus

    # Parse and validate request
    try:
        import_request = ImportFromPathsRequest(**request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    if not import_request.file_paths:
        raise HTTPException(status_code=400, detail="No file paths provided")

    # Validate parallel_workers
    if import_request.parallel_workers < 1 or import_request.parallel_workers > 8:
        raise HTTPException(status_code=400, detail="parallel_workers must be between 1 and 8")

    # Parse processing options if provided
    proc_options = None
    if import_request.processing_options:
        try:
            proc_options = ProcessingRequest(**import_request.processing_options)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid processing_options: {e}")

    # Create batch
    batch_metadata = batch_service.create_batch(
        batch_name=import_request.batch_name,
        processing_options=proc_options,
        parallel_workers=import_request.parallel_workers,
    )

    files_uploaded = []
    files_failed = []

    # Import each file from server path
    for file_path_str in import_request.file_paths:
        file_path = Path(file_path_str)

        # Validate file exists and is .esx
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            files_failed.append(str(file_path))
            continue

        if not file_path.is_file():
            logger.error(f"Not a file: {file_path}")
            files_failed.append(str(file_path))
            continue

        if not file_path.suffix.lower() == ".esx":
            logger.error(f"Not an .esx file: {file_path}")
            files_failed.append(str(file_path))
            continue

        try:
            # Read file content
            file_content = file_path.read_bytes()
            filename = file_path.name

            # Create new project
            project_id = uuid4()

            # Save file using storage service
            saved_path = await storage_service.save_uploaded_file(
                project_id, filename, file_content
            )

            # Extract project name from .esx file
            from app.api.upload import extract_project_name

            project_name = extract_project_name(file_content)

            # Generate short link if requested in processing options
            short_link = None
            short_link_expires = None
            if proc_options and getattr(proc_options, "create_short_link", False):
                from app.utils.short_links import calculate_expiry_date, generate_short_link

                short_link = generate_short_link()
                days = getattr(proc_options, "short_link_days", 30)
                short_link_expires = calculate_expiry_date(days=days)

            # Create metadata
            metadata = ProjectMetadata(
                project_id=project_id,
                filename=filename,
                file_size=len(file_content),
                original_file=saved_path,  # Already a string path
                processing_status=ProcessingStatus.PENDING,
                project_name=project_name,
                short_link=short_link,
                short_link_expires=short_link_expires,
            )

            # Save metadata
            storage_service.save_metadata(project_id, metadata)

            # Add project to batch
            batch_service.add_project_to_batch(
                batch_id=batch_metadata.batch_id,
                project_id=project_id,
                filename=filename,
            )

            # Add to index
            index_service.add(metadata)

            files_uploaded.append(filename)
            logger.info(f"Imported {filename} from {file_path} to batch {batch_metadata.batch_id}")

        except Exception as e:
            logger.error(f"Failed to import {file_path}: {e}")
            files_failed.append(str(file_path))

    # Save index to disk
    if files_uploaded:
        index_service.save_to_disk()

    # Schedule batch processing in background if auto_process is True
    if files_uploaded and import_request.auto_process and proc_options:
        background_tasks.add_task(
            batch_service.process_batch,
            batch_metadata.batch_id,
        )

    return BatchUploadResponse(
        batch_id=batch_metadata.batch_id,
        message=f"Imported {len(files_uploaded)} files, {len(files_failed)} failed",
        files_count=len(import_request.file_paths),
        files_uploaded=files_uploaded,
        files_failed=files_failed,
    )


def cleanup_temp_file(file_path: Path) -> None:
    """Clean up temporary file and its parent directory.

    Args:
        file_path: Path to temporary file
    """
    try:
        import shutil

        if file_path.exists():
            parent_dir = file_path.parent
            file_path.unlink()
            if parent_dir.exists() and parent_dir.name.startswith("tmp"):
                shutil.rmtree(parent_dir)
            logger.info(f"Cleaned up temporary archive: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")


# ============================================================================
# Watch Mode Endpoints
# ============================================================================


@router.post("/watch/start", dependencies=[Depends(verify_admin)])
async def start_watch_mode(
    watch_directory: str = Form(..., description="Directory to watch for new .esx files"),
    interval_seconds: int = Form(60, description="Check interval in seconds"),
    file_pattern: str = Form("*.esx", description="File pattern to match"),
    auto_process: bool = Form(True, description="Auto-process new files"),
    batch_name_prefix: str = Form("Watch", description="Prefix for auto-created batch names"),
    parallel_workers: int = Form(1, description="Number of parallel workers"),
    processing_options: Optional[str] = Form(None, description="Processing options as JSON"),
) -> dict:
    """
    Start watch mode to monitor a directory for new .esx files.

    When new files are detected, they are automatically added to a batch
    and optionally processed with the specified settings.

    Args:
        watch_directory: Path to directory to watch
        interval_seconds: How often to check for new files (seconds)
        file_pattern: Glob pattern to match files (default: *.esx)
        auto_process: Whether to auto-process new batches
        batch_name_prefix: Prefix for auto-created batch names
        parallel_workers: Number of parallel workers for processing
        processing_options: JSON string with processing configuration

    Returns:
        Status message and watch configuration
    """
    logger.info(f"[API] Starting watch mode for directory: {watch_directory}")

    # Parse processing options
    proc_options = None
    if processing_options:
        import json

        try:
            proc_options = ProcessingRequest(**json.loads(processing_options))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid processing_options: {e}")

    # Create watch configuration
    config = WatchConfig(
        watch_directory=watch_directory,
        interval_seconds=interval_seconds,
        file_pattern=file_pattern,
        auto_process=auto_process,
        batch_name_prefix=batch_name_prefix,
        processing_options=proc_options,
        parallel_workers=parallel_workers,
    )

    # Start watching
    success = watch_service.start_watch(config)

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to start watch mode (already running or invalid directory)",
        )

    return {
        "status": "started",
        "message": f"Watch mode started for {watch_directory}",
        "config": config.to_dict(),
    }


@router.post("/watch/stop", dependencies=[Depends(verify_admin)])
async def stop_watch_mode() -> dict:
    """
    Stop watch mode.

    Returns:
        Status message
    """
    logger.info("[API] Stopping watch mode")

    success = watch_service.stop_watch()

    if not success:
        raise HTTPException(status_code=400, detail="Watch mode is not running")

    return {
        "status": "stopped",
        "message": "Watch mode stopped",
    }


@router.get("/watch/status")
async def get_watch_status() -> dict:
    """
    Get current watch mode status and statistics.

    Returns:
        Watch status, configuration, and statistics
    """
    return watch_service.get_status()


# ============================================================================
# Scheduled Reports Endpoints
# ============================================================================


@router.get("/reports/aggregated", dependencies=[Depends(verify_admin)])
async def get_aggregated_report(
    time_range: str = Query(
        "last_month", description="Time range: last_week, last_month, last_quarter, last_year"
    ),
    format: str = Query("json", description="Output format: json, csv, text"),
) -> dict:
    """
    Generate aggregated report across all batches for specified time range.

    This endpoint generates comprehensive management reports with:
    - Total batches, projects, and equipment counts
    - Vendor/model distribution analysis
    - Time-based trends (batches and APs over time)
    - Success/failure statistics

    Args:
        time_range: Time range for filtering (last_week, last_month, last_quarter, last_year)
        format: Output format (json, csv, text)

    Returns:
        Aggregated report data in specified format
    """
    logger.info(f"[API] Generating aggregated report for time_range={time_range}, format={format}")

    # Generate report
    report_data = report_schedule_service.generate_aggregated_report(time_range=time_range)

    # Return based on format
    if format == "csv":
        csv_content = report_schedule_service.export_to_csv(report_data)
        return {
            "format": "csv",
            "content": csv_content,
        }
    elif format == "text":
        text_content = report_schedule_service.export_to_text(report_data)
        return {
            "format": "text",
            "content": text_content,
        }
    else:  # json (default)
        return {
            "format": "json",
            "data": report_data.to_dict(),
        }


@router.get("/reports/vendor-analysis", dependencies=[Depends(verify_admin)])
async def get_vendor_analysis(
    time_range: str = Query(
        "last_month", description="Time range: last_week, last_month, last_quarter, last_year"
    ),
) -> dict:
    """
    Get vendor/model distribution analysis.

    Returns detailed breakdown of equipment by vendor and model
    across all batches in the specified time range.

    Args:
        time_range: Time range for filtering

    Returns:
        Vendor/model distribution data
    """
    logger.info(f"[API] Getting vendor analysis for time_range={time_range}")

    report_data = report_schedule_service.generate_aggregated_report(time_range=time_range)

    # Calculate vendor totals (sum all models for each vendor)
    vendor_totals = defaultdict(int)
    for vendor_model, quantity in report_data.ap_by_vendor_model.items():
        vendor = vendor_model.split("|")[0] if "|" in vendor_model else "Unknown"
        vendor_totals[vendor] += quantity

    # Sort by quantity
    top_vendors = sorted(vendor_totals.items(), key=lambda x: x[1], reverse=True)
    top_models = sorted(report_data.ap_by_vendor_model.items(), key=lambda x: x[1], reverse=True)[
        :20
    ]

    return {
        "time_range": time_range,
        "total_access_points": report_data.total_access_points,
        "top_vendors": [
            {
                "vendor": vendor,
                "quantity": quantity,
                "percentage": (
                    round(quantity / report_data.total_access_points * 100, 2)
                    if report_data.total_access_points > 0
                    else 0
                ),
            }
            for vendor, quantity in top_vendors
        ],
        "top_models": [
            {
                "vendor_model": vendor_model,
                "quantity": quantity,
                "percentage": (
                    round(quantity / report_data.total_access_points * 100, 2)
                    if report_data.total_access_points > 0
                    else 0
                ),
            }
            for vendor_model, quantity in top_models
        ],
    }


# ============================================================================
# Batch Archive Endpoints
# ============================================================================


@router.get("/archives/statistics", dependencies=[Depends(verify_admin)])
async def get_archive_statistics() -> dict:
    """
    Get batch archive statistics.

    Returns statistics about archived batches including:
    - Total number of batches
    - Number of archived batches
    - Archive size and compression ratio
    - Space saved by archiving

    Returns:
        Archive statistics
    """
    logger.info("[API] Getting archive statistics")
    return batch_archive_service.get_archive_statistics()


@router.get("/archives/candidates", dependencies=[Depends(verify_admin)])
async def get_archive_candidates(
    days_threshold: int = Query(90, description="Days of inactivity threshold"),
) -> dict:
    """
    Get list of batches eligible for archiving.

    Args:
        days_threshold: Number of days of inactivity (default: 90)

    Returns:
        List of batches eligible for archiving
    """
    logger.info(f"[API] Getting archive candidates (threshold={days_threshold} days)")

    old_batches = batch_archive_service.find_old_batches(days_threshold)

    return {
        "days_threshold": days_threshold,
        "candidates_count": len(old_batches),
        "candidates": [
            {
                "batch_id": str(batch.batch_id),
                "batch_name": batch.batch_name,
                "created_date": batch.created_date,
                "total_projects": batch.statistics.total_projects if batch.statistics else 0,
            }
            for batch in old_batches
        ],
    }


@router.post("/archives/{batch_id}", dependencies=[Depends(verify_admin)])
async def archive_batch(batch_id: UUID) -> dict:
    """
    Archive a specific batch.

    Compresses batch data to tar.gz format and removes original files
    to save disk space.

    Args:
        batch_id: Batch ID to archive

    Returns:
        Success message
    """
    logger.info(f"[API] Archiving batch: {batch_id}")

    success = batch_archive_service.archive_batch(batch_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to archive batch")

    return {
        "batch_id": str(batch_id),
        "status": "archived",
        "message": "Batch archived successfully",
    }


@router.post("/archives/{batch_id}/restore", dependencies=[Depends(verify_admin)])
async def restore_batch(batch_id: UUID) -> dict:
    """
    Restore a batch from archive.

    Extracts archived batch data and makes it available again.

    Args:
        batch_id: Batch ID to restore

    Returns:
        Success message
    """
    logger.info(f"[API] Restoring batch: {batch_id}")

    success = batch_archive_service.restore_batch(batch_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to restore batch")

    return {
        "batch_id": str(batch_id),
        "status": "restored",
        "message": "Batch restored successfully",
    }


@router.post("/archives/auto-archive", dependencies=[Depends(verify_admin)])
async def auto_archive_batches(
    days_threshold: int = Query(90, description="Days of inactivity threshold"),
    dry_run: bool = Query(False, description="Only report what would be archived"),
) -> dict:
    """
    Automatically archive old batches.

    Args:
        days_threshold: Number of days of inactivity (default: 90)
        dry_run: If True, only report what would be archived

    Returns:
        Archive operation results
    """
    logger.info(f"[API] Auto-archiving batches (threshold={days_threshold}, dry_run={dry_run})")

    result = batch_archive_service.auto_archive_old_batches(days_threshold, dry_run)

    return result
