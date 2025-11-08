"""Storage Service - high-level storage operations with backend abstraction."""

import json
from pathlib import Path
from typing import Optional
from uuid import UUID

from app.config import get_settings
from app.models import ProjectMetadata
from app.services.storage.base import StorageBackend
from app.services.storage.factory import StorageFactory


class StorageService:
    """High-level storage operations with pluggable backend.

    This service provides a high-level API for storage operations
    while delegating actual file operations to a storage backend
    (local filesystem, S3, etc.).
    """

    def __init__(self):
        """Initialize storage service with configured backend."""
        settings = get_settings()
        self.backend: StorageBackend = StorageFactory.create_backend(settings)
        self.projects_dir = settings.projects_dir  # Keep for backward compatibility

    def get_project_dir(self, project_id: UUID) -> Path | str:
        """Get project directory path.

        Args:
            project_id: Project UUID

        Returns:
            Path to project directory (Path for local, str for S3)
        """
        return self.backend.get_project_dir(project_id)

    async def save_uploaded_file(self, project_id: UUID, filename: str, file_content: bytes) -> str:
        """Save uploaded .esx file.

        Args:
            project_id: Project UUID
            filename: File name (not used currently, always saves as original.esx)
            file_content: File content bytes

        Returns:
            Storage path to saved file
        """
        # Save original.esx file using backend
        storage_path = self.backend.save_file(project_id, "original.esx", file_content)
        return storage_path

    def save_metadata(self, project_id: UUID, metadata: ProjectMetadata) -> None:
        """Save metadata.json.

        Args:
            project_id: Project UUID
            metadata: Project metadata
        """
        # Serialize metadata to JSON bytes
        metadata_json = json.dumps(metadata.model_dump(mode="json"), indent=2, ensure_ascii=False)
        metadata_bytes = metadata_json.encode("utf-8")

        # Save using backend
        self.backend.save_file(project_id, "metadata.json", metadata_bytes)

    def load_metadata(self, project_id: UUID) -> Optional[ProjectMetadata]:
        """Load metadata.json.

        Args:
            project_id: Project UUID

        Returns:
            Project metadata or None if file doesn't exist
        """
        # Check if file exists
        if not self.backend.exists(project_id, "metadata.json"):
            return None

        try:
            # Load from backend
            metadata_bytes = self.backend.get_file(project_id, "metadata.json")
            data = json.loads(metadata_bytes.decode("utf-8"))
            return ProjectMetadata(**data)
        except FileNotFoundError:
            return None

    def get_reports_dir(self, project_id: UUID) -> Path | str:
        """Get reports directory path.

        Args:
            project_id: Project UUID

        Returns:
            Path to reports directory (Path for local, str for S3 prefix)
        """
        project_dir = self.get_project_dir(project_id)
        if isinstance(project_dir, Path):
            return project_dir / "reports"
        else:
            # S3 prefix
            return f"{project_dir}/reports"

    def get_visualizations_dir(self, project_id: UUID) -> Path | str:
        """Get visualizations directory path.

        Args:
            project_id: Project UUID

        Returns:
            Path to visualizations directory (Path for local, str for S3 prefix)

        Note:
            Visualizations are created by EkahauBOM CLI in output_dir/visualizations/
            Since we pass reports_dir as output_dir, they end up in reports/visualizations/
        """
        reports_dir = self.get_reports_dir(project_id)
        if isinstance(reports_dir, Path):
            return reports_dir / "visualizations"
        else:
            # S3 prefix
            return f"{reports_dir}/visualizations"

    def list_report_files(self, project_id: UUID) -> list[dict]:
        """List report files.

        Args:
            project_id: Project UUID

        Returns:
            List of dicts with file info (filename, size)
        """
        # List files in reports/ directory (non-recursive)
        files = self.backend.list_files(project_id, prefix="reports/", recursive=False)

        result = []
        for file_path in files:
            # Extract filename from path (e.g., "reports/file.csv" -> "file.csv")
            filename = file_path.split("/")[-1]

            # Get file size (need to read file for now, can optimize later)
            try:
                content = self.backend.get_file(project_id, file_path)
                size = len(content)
                result.append({"filename": filename, "size": size})
            except Exception:
                # Skip files that can't be read
                continue

        return result

    def list_visualization_files(self, project_id: UUID) -> list[dict]:
        """List visualization files (PNG only).

        Args:
            project_id: Project UUID

        Returns:
            List of dicts with file info (filename, size)
        """
        # List files in reports/visualizations/ directory (non-recursive)
        files = self.backend.list_files(
            project_id, prefix="reports/visualizations/", recursive=False
        )

        result = []
        for file_path in files:
            # Only include PNG files
            if not file_path.endswith(".png"):
                continue

            # Extract filename from path
            filename = file_path.split("/")[-1]

            # Get file size
            try:
                content = self.backend.get_file(project_id, file_path)
                size = len(content)
                result.append({"filename": filename, "size": size})
            except Exception:
                # Skip files that can't be read
                continue

        return result

    def load_project_data(self, project_id: UUID) -> Optional[dict]:
        """Load {project_name}_data.json from reports directory.

        Args:
            project_id: Project UUID

        Returns:
            Project data dict or None if file doesn't exist
        """
        # Get metadata to find project name
        metadata = self.load_metadata(project_id)
        if not metadata or not metadata.project_name:
            return None

        # Construct relative path to data.json
        data_file_path = f"reports/{metadata.project_name}_data.json"

        # Check if file exists
        if not self.backend.exists(project_id, data_file_path):
            return None

        try:
            # Load from backend
            data_bytes = self.backend.get_file(project_id, data_file_path)
            return json.loads(data_bytes.decode("utf-8"))
        except FileNotFoundError:
            return None

    def delete_project(self, project_id: UUID) -> None:
        """Delete project completely.

        Args:
            project_id: Project UUID
        """
        self.backend.delete_project(project_id)


# Singleton instance
storage_service = StorageService()
