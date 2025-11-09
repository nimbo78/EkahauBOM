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


# ============================================================================
# Scheduled Processing Models
# ============================================================================


class TriggerType(str, Enum):
    """Schedule trigger type."""

    CRON = "cron"  # Time-based trigger with cron expression
    DIRECTORY = "directory"  # Watch directory for new files
    S3 = "s3"  # Watch S3 bucket for new objects


class ScheduleStatus(str, Enum):
    """Schedule execution status."""

    SUCCESS = "success"  # Batch processing completed successfully
    FAILED = "failed"  # Batch processing failed
    PARTIAL = "partial"  # Some projects succeeded, some failed
    RUNNING = "running"  # Currently executing


class TriggerConfig(BaseModel):
    """Trigger-specific configuration."""

    directory: Optional[str] = None  # Directory path for directory trigger
    s3_bucket: Optional[str] = None  # S3 bucket name for S3 trigger
    s3_prefix: Optional[str] = None  # S3 object prefix filter
    batch_template_id: Optional[UUID] = None  # Template to use for processing
    pattern: str = "*.esx"  # File pattern for filtering
    recursive: bool = True  # Search subdirectories


class NotificationConfig(BaseModel):
    """Notification configuration."""

    email: list[str] = Field(default_factory=list)  # Email addresses
    webhook_url: Optional[str] = None  # Webhook URL for HTTP POST
    slack_webhook: Optional[str] = None  # Slack webhook URL
    notify_on_success: bool = True  # Send notification on success
    notify_on_failure: bool = True  # Send notification on failure
    notify_on_partial: bool = True  # Send notification on partial success


class Schedule(BaseModel):
    """Scheduled batch processing job."""

    schedule_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    cron_expression: str  # Cron expression (e.g., "0 2 * * *")
    enabled: bool = True  # Schedule is active
    trigger_type: TriggerType = TriggerType.CRON
    trigger_config: TriggerConfig = Field(default_factory=TriggerConfig)
    notification_config: NotificationConfig = Field(default_factory=NotificationConfig)

    # Execution tracking
    next_run_time: Optional[datetime] = None  # Next scheduled execution
    last_run_time: Optional[datetime] = None  # Last execution time
    last_run_status: Optional[ScheduleStatus] = None  # Last execution status
    last_batch_id: Optional[UUID] = None  # Last created batch ID
    execution_count: int = 0  # Total number of executions

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str = "admin"  # User who created the schedule


class ScheduleRun(BaseModel):
    """Schedule execution history entry."""

    run_id: UUID = Field(default_factory=uuid4)
    schedule_id: UUID  # Parent schedule
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: ScheduleStatus  # Execution status
    batch_id: Optional[UUID] = None  # Created batch ID
    duration_seconds: float = 0.0  # Execution duration
    projects_processed: int = 0  # Number of projects processed
    projects_succeeded: int = 0  # Number of successful projects
    projects_failed: int = 0  # Number of failed projects
    error_message: Optional[str] = None  # Error message if failed
    files_found: int = 0  # Number of .esx files found
    files_processed: int = 0  # Number of .esx files processed


class ScheduleListItem(BaseModel):
    """Schedule list item for UI."""

    schedule_id: UUID
    name: str
    description: str
    cron_expression: str
    enabled: bool
    trigger_type: TriggerType
    next_run_time: Optional[datetime]
    last_run_time: Optional[datetime]
    last_run_status: Optional[ScheduleStatus]
    execution_count: int


class ScheduleCreateRequest(BaseModel):
    """Request for creating a new schedule."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    cron_expression: str = Field(..., min_length=5)  # Min: "* * * * *"
    enabled: bool = True
    trigger_type: TriggerType = TriggerType.CRON
    trigger_config: TriggerConfig = Field(default_factory=TriggerConfig)
    notification_config: NotificationConfig = Field(default_factory=NotificationConfig)


class ScheduleUpdateRequest(BaseModel):
    """Request for updating an existing schedule."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    cron_expression: Optional[str] = Field(None, min_length=5)
    enabled: Optional[bool] = None
    trigger_type: Optional[TriggerType] = None
    trigger_config: Optional[TriggerConfig] = None
    notification_config: Optional[NotificationConfig] = None
