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

    group_by: Optional[str] = (
        "model"  # 'model', 'floor', 'color', 'vendor', 'tag', or None
    )
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
