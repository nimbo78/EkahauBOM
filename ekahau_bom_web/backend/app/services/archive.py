"""Archive Service - project compression and decompression."""

import logging
import shutil
import tarfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional
from uuid import UUID

from app.config import settings
from app.models import ProcessingStatus, ProjectMetadata
from app.services.cache import cache_service
from app.services.index import index_service
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

# Archive criteria
ARCHIVE_AFTER_DAYS = 60  # Archive projects not accessed for 60 days


class ArchiveService:
    """Service for archiving and unarchiving projects."""

    def __init__(self):
        """Initialize the archive service."""
        self.projects_dir = settings.projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def get_archive_path(self, project_id: UUID) -> Path:
        """
        Get path to project archive file.

        Args:
            project_id: Project UUID

        Returns:
            Path to .tar.gz archive
        """
        return self.projects_dir / f"{project_id}.tar.gz"

    def is_archived(self, project_id: UUID) -> bool:
        """
        Check if project is currently archived.

        Args:
            project_id: Project UUID

        Returns:
            True if project is archived (tar.gz exists, directory doesn't)
        """
        archive_path = self.get_archive_path(project_id)
        project_dir = storage_service.get_project_dir(project_id)

        return archive_path.exists() and not project_dir.exists()

    def should_archive(self, metadata: ProjectMetadata) -> bool:
        """
        Check if project should be archived based on criteria.

        A project should be archived if:
        - Processing is completed
        - Not already archived
        - Last accessed more than ARCHIVE_AFTER_DAYS ago (or never accessed)

        Args:
            metadata: Project metadata

        Returns:
            True if project should be archived
        """
        # Must be completed
        if metadata.processing_status != ProcessingStatus.COMPLETED:
            return False

        # Already archived
        if metadata.archived:
            return False

        # Check last access time
        if metadata.last_accessed is None:
            # Never accessed - use upload date + 60 days
            cutoff_date = metadata.upload_date + timedelta(days=ARCHIVE_AFTER_DAYS)
            return datetime.now(UTC) > cutoff_date

        # Check last accessed
        cutoff_date = metadata.last_accessed + timedelta(days=ARCHIVE_AFTER_DAYS)
        return datetime.now(UTC) > cutoff_date

    def archive_project(self, project_id: UUID) -> bool:
        """
        Archive a project by compressing it to tar.gz.

        Args:
            project_id: Project UUID

        Returns:
            True if archiving succeeded, False otherwise
        """
        try:
            project_dir = storage_service.get_project_dir(project_id)
            archive_path = self.get_archive_path(project_id)

            # Check if project directory exists
            if not project_dir.exists():
                logger.warning(f"Project directory not found: {project_dir}")
                return False

            # Check if already archived
            if archive_path.exists():
                logger.warning(f"Archive already exists: {archive_path}")
                return False

            logger.info(f"Archiving project {project_id} to {archive_path}")

            # Create tar.gz archive
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(project_dir, arcname=str(project_id))

            # Verify archive was created
            if not archive_path.exists():
                logger.error(f"Failed to create archive: {archive_path}")
                return False

            # Load metadata and update archived flag
            metadata = storage_service.load_metadata(project_id)
            if metadata:
                metadata.archived = True
                # Save metadata before deleting directory
                storage_service.save_metadata(project_id, metadata)
                # Update index
                index_service.add(metadata)

            # Remove original directory
            shutil.rmtree(project_dir)

            logger.info(
                f"Project {project_id} archived successfully. "
                f"Original size: {self._get_dir_size(project_dir)} bytes, "
                f"Archive size: {archive_path.stat().st_size} bytes"
            )

            # Invalidate cache
            cache_service.invalidate_project(str(project_id))

            return True

        except Exception as e:
            logger.error(f"Error archiving project {project_id}: {e}", exc_info=True)
            # Clean up partial archive if it exists
            if archive_path.exists():
                archive_path.unlink()
            return False

    def unarchive_project(self, project_id: UUID) -> bool:
        """
        Unarchive a project by extracting from tar.gz.

        Args:
            project_id: Project UUID

        Returns:
            True if unarchiving succeeded, False otherwise
        """
        try:
            archive_path = self.get_archive_path(project_id)
            project_dir = storage_service.get_project_dir(project_id)

            # Check if archive exists
            if not archive_path.exists():
                logger.warning(f"Archive not found: {archive_path}")
                return False

            # Check if directory already exists
            if project_dir.exists():
                logger.warning(f"Project directory already exists: {project_dir}")
                return False

            logger.info(f"Unarchiving project {project_id} from {archive_path}")

            # Extract tar.gz archive
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(path=self.projects_dir)

            # Verify directory was created
            if not project_dir.exists():
                logger.error(f"Failed to extract archive: {archive_path}")
                return False

            # Load metadata and update archived flag
            metadata = storage_service.load_metadata(project_id)
            if metadata:
                metadata.archived = False
                metadata.last_accessed = datetime.now(UTC)
                storage_service.save_metadata(project_id, metadata)
                # Update index
                index_service.add(metadata)

            # Remove archive file
            archive_path.unlink()

            logger.info(f"Project {project_id} unarchived successfully")

            # Invalidate cache
            cache_service.invalidate_project(str(project_id))

            return True

        except Exception as e:
            logger.error(f"Error unarchiving project {project_id}: {e}", exc_info=True)
            # Clean up partial extraction if it exists
            if project_dir.exists():
                shutil.rmtree(project_dir)
            return False

    def ensure_unarchived(self, project_id: UUID) -> bool:
        """
        Ensure project is unarchived before access.

        If project is archived, automatically unarchive it.
        Also updates last_accessed timestamp.

        Args:
            project_id: Project UUID

        Returns:
            True if project is available (was already unarchived or successfully unarchived),
            False if unarchiving failed
        """
        # Check if project is archived
        if not self.is_archived(project_id):
            # Not archived, just update last_accessed
            metadata = storage_service.load_metadata(project_id)
            if metadata:
                metadata.last_accessed = datetime.now(UTC)
                storage_service.save_metadata(project_id, metadata)
                index_service.add(metadata)
            return True

        # Project is archived, need to unarchive
        logger.info(f"Project {project_id} is archived, unarchiving...")
        return self.unarchive_project(project_id)

    def get_archive_stats(self, project_id: UUID) -> Optional[dict]:
        """
        Get archive statistics for a project.

        Args:
            project_id: Project UUID

        Returns:
            Dictionary with archive statistics or None if not archived
        """
        archive_path = self.get_archive_path(project_id)
        if not archive_path.exists():
            return None

        return {
            "archived": True,
            "archive_size": archive_path.stat().st_size,
            "archive_path": str(archive_path),
        }

    @staticmethod
    def _get_dir_size(directory: Path) -> int:
        """
        Calculate total size of directory.

        Args:
            directory: Path to directory

        Returns:
            Total size in bytes
        """
        total_size = 0
        for item in directory.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size
        return total_size


# Singleton instance
archive_service = ArchiveService()
