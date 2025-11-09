"""Pydantic models for Ekahau BOM Web API."""

from datetime import UTC, datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """Processing status enum."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectMetadata(BaseModel):
    """Project metadata for storage in metadata.json."""

    project_id: UUID = Field(default_factory=uuid4)
    filename: str
    upload_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    file_size: int  # bytes
    processing_status: ProcessingStatus = ProcessingStatus.PENDING

    # Metadata from .esx
    project_name: Optional[str] = None
    buildings_count: Optional[int] = None
    floors_count: Optional[int] = None
    aps_count: Optional[int] = None

    # Project details from .esx
    customer: Optional[str] = None
    location: Optional[str] = None
    responsible_person: Optional[str] = None

    # Summary from JSON report (after processing)
    total_antennas: Optional[int] = None
    unique_vendors: Optional[int] = None
    unique_colors: Optional[int] = None
    vendors: Optional[list[str]] = None
    floors: Optional[list[str]] = None

    # Processing
    processing_flags: dict = {}
    processing_started: Optional[datetime] = None
    processing_completed: Optional[datetime] = None
    processing_error: Optional[str] = None

    # File paths (relative)
    original_file: str  # projects/{project_id}/original.esx
    reports_dir: Optional[str] = None
    visualizations_dir: Optional[str] = None

    # Short link
    short_link: Optional[str] = None
    short_link_expires: Optional[datetime] = None

    # Archive
    archived: bool = False
    last_accessed: Optional[datetime] = None


class ProjectListItem(BaseModel):
    """Project list item for UI."""

    project_id: UUID
    project_name: str
    filename: str
    upload_date: datetime
    aps_count: Optional[int]
    processing_status: ProcessingStatus
    short_link: Optional[str]


class UploadResponse(BaseModel):
    """Response for file upload."""

    project_id: UUID
    message: str
    short_link: Optional[str]
    exists: bool = False  # True if project with same name already exists
    existing_project: Optional["ProjectListItem"] = None  # Details of existing project


class ProcessingRequest(BaseModel):
    """Request for project processing."""

    group_by: Optional[str] = "model"  # 'model', 'floor', 'color', 'vendor', 'tag', or None
    output_formats: list[str] = [
        "csv",
        "excel",
        "html",
    ]  # ['csv', 'excel', 'html', 'json', 'pdf']
    visualize_floor_plans: bool = True
    show_azimuth_arrows: bool = False
    ap_opacity: float = 0.6  # 0.0-1.0, default 0.6
    include_text_notes: bool = False
    include_picture_notes: bool = False
    include_cable_notes: bool = False
    create_short_link: bool = False  # Whether to create short link
    short_link_days: int = 30  # Short link expiration in days (1-365)


# ============================================================================
# Batch Processing Models
# ============================================================================


class BatchStatus(str, Enum):
    """Batch processing status enum."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some projects succeeded, some failed


class BatchProjectStatus(BaseModel):
    """Status of individual project within batch."""

    project_id: UUID
    filename: str
    status: ProcessingStatus
    processing_time: Optional[float] = None  # seconds
    error_message: Optional[str] = None
    access_points_count: Optional[int] = None
    antennas_count: Optional[int] = None


class BatchStatistics(BaseModel):
    """Aggregated statistics for batch processing."""

    total_projects: int = 0
    successful_projects: int = 0
    failed_projects: int = 0
    total_processing_time: float = 0.0  # seconds

    # Equipment totals
    total_access_points: int = 0
    total_antennas: int = 0

    # Aggregated BOM (vendor+model -> quantity)
    ap_by_vendor_model: dict[str, int] = {}  # "Vendor|Model" -> quantity
    antenna_by_model: dict[str, int] = {}  # "Model" -> quantity


class BatchMetadata(BaseModel):
    """Batch metadata for storage in batch_metadata.json."""

    batch_id: UUID = Field(default_factory=uuid4)
    batch_name: Optional[str] = None  # User-provided or auto-generated
    created_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str = "admin"  # User who created the batch

    # Tags for categorization and organization
    tags: list[str] = Field(default_factory=list)

    # Batch status
    status: BatchStatus = BatchStatus.PENDING
    processing_started: Optional[datetime] = None
    processing_completed: Optional[datetime] = None

    # Projects in batch
    project_ids: list[UUID] = []
    project_statuses: list[BatchProjectStatus] = []

    # Processing options (inherited by all projects)
    processing_options: ProcessingRequest = Field(default_factory=lambda: ProcessingRequest())

    # Parallel processing
    parallel_workers: int = 1

    # Statistics
    statistics: BatchStatistics = Field(default_factory=BatchStatistics)

    # File paths (relative)
    batch_dir: str  # batches/{batch_id}/
    aggregated_reports_dir: Optional[str] = None  # batches/{batch_id}/aggregated/

    # Archive
    archived: bool = False
    last_accessed: Optional[datetime] = None


class BatchListItem(BaseModel):
    """Batch list item for UI."""

    batch_id: UUID
    batch_name: Optional[str]
    created_date: datetime
    status: BatchStatus
    total_projects: int
    successful_projects: int
    failed_projects: int
    tags: list[str] = Field(default_factory=list)


class BatchUploadRequest(BaseModel):
    """Request for batch upload."""

    batch_name: Optional[str] = None
    processing_options: Optional[ProcessingRequest] = None
    parallel_workers: int = 1


class BatchUploadResponse(BaseModel):
    """Response for batch upload."""

    batch_id: UUID
    message: str
    files_count: int
    files_uploaded: list[str]
    files_failed: list[str]


class ScannedFile(BaseModel):
    """Information about a scanned .esx file."""

    filename: str
    filepath: str  # Absolute path
    filesize: int  # bytes
    modified_date: datetime


class DirectoryScanResponse(BaseModel):
    """Response for directory scan."""

    directory: str
    total_files: int
    files: list[ScannedFile]
    subdirectories_scanned: int = 0


class ImportFromPathsRequest(BaseModel):
    """Request for importing files from server paths."""

    file_paths: list[str]
    batch_name: str | None = None
    parallel_workers: int = Field(default=1, ge=1, le=8)
    processing_options: dict | None = None  # ProcessingRequest as dict
    auto_process: bool = False


# ============================================================================
# Batch Template Models
# ============================================================================


class BatchTemplate(BaseModel):
    """Template for batch processing configuration."""

    template_id: UUID = Field(default_factory=uuid4)
    name: str  # Template name (e.g., "CSV Only", "Full Reports")
    description: Optional[str] = None  # Template description
    created_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str = "admin"  # User who created the template
    last_used: Optional[datetime] = None  # Last time template was applied
    usage_count: int = 0  # Number of times template has been used
    is_system: bool = False  # True for predefined templates, False for user-created

    # Processing configuration
    processing_options: ProcessingRequest = Field(default_factory=lambda: ProcessingRequest())
    parallel_workers: int = Field(default=1, ge=1, le=8)  # Default parallel workers


class TemplateListItem(BaseModel):
    """Template list item for UI."""

    template_id: UUID
    name: str
    description: Optional[str]
    created_date: datetime
    last_used: Optional[datetime]
    usage_count: int
    is_system: bool


class TemplateCreateRequest(BaseModel):
    """Request for creating a new template."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    processing_options: ProcessingRequest = Field(default_factory=lambda: ProcessingRequest())
    parallel_workers: int = Field(default=1, ge=1, le=8)


class TemplateUpdateRequest(BaseModel):
    """Request for updating an existing template."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    processing_options: Optional[ProcessingRequest] = None
    parallel_workers: Optional[int] = Field(None, ge=1, le=8)
