"""
Batch Archive Service - Archive and restore old batches.

This service provides functionality to:
- Archive batches not accessed for 90+ days
- Compress batch data with tar.gz
- Automatic cleanup of archived batch files
- Restore archived batches on demand
"""

import logging
import tarfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from uuid import UUID

from ..models import BatchMetadata
from .batch_service import BatchService
from .storage_service import StorageService

logger = logging.getLogger(__name__)


class BatchArchiveService:
    """
    Service for archiving and restoring old batches.

    This service manages batch lifecycle:
    - Identifies batches not accessed for specified period
    - Archives batch data with tar.gz compression
    - Tracks archive status in metadata
    - Restores batches from archive on demand
    """

    def __init__(self, batch_service: BatchService, storage_service: StorageService):
        self.batch_service = batch_service
        self.storage_service = storage_service
        self.archive_threshold_days = 90  # Archive batches not accessed for 90+ days

    def find_old_batches(self, days_threshold: Optional[int] = None) -> List[BatchMetadata]:
        """
        Find batches that haven't been accessed for specified number of days.

        Args:
            days_threshold: Number of days of inactivity (default: 90)

        Returns:
            List of BatchMetadata for old batches
        """
        if days_threshold is None:
            days_threshold = self.archive_threshold_days

        logger.info(
            f"[BatchArchiveService] Finding batches not accessed for {days_threshold}+ days"
        )

        threshold_date = datetime.now() - timedelta(days=days_threshold)
        all_batches = self.batch_service.list_batches()

        old_batches = []
        for batch in all_batches:
            # Check if batch has archived flag (skip already archived)
            if hasattr(batch, "archived") and batch.archived:
                continue

            # Get last access date (use created_date if last_accessed not available)
            last_accessed = getattr(batch, "last_accessed", None)
            if last_accessed:
                access_date = datetime.fromisoformat(last_accessed)
            else:
                access_date = datetime.fromisoformat(batch.created_date)

            # Check if batch is old enough to archive
            if access_date < threshold_date:
                old_batches.append(batch)

        logger.info(f"[BatchArchiveService] Found {len(old_batches)} old batches")
        return old_batches

    def archive_batch(self, batch_id: UUID) -> bool:
        """
        Archive a batch to tar.gz format.

        Args:
            batch_id: Batch ID to archive

        Returns:
            True if archived successfully, False otherwise
        """
        logger.info(f"[BatchArchiveService] Archiving batch: {batch_id}")

        try:
            # Load batch metadata
            metadata = self.batch_service.load_batch_metadata(batch_id)

            # Get batch directory
            batch_dir = self.storage_service.projects_dir.parent / "batches" / str(batch_id)
            if not batch_dir.exists():
                logger.error(f"[BatchArchiveService] Batch directory not found: {batch_dir}")
                return False

            # Create archive directory if not exists
            archive_dir = self.storage_service.projects_dir.parent / "archives"
            archive_dir.mkdir(exist_ok=True)

            # Create tar.gz archive
            archive_path = archive_dir / f"batch_{batch_id}.tar.gz"
            logger.info(f"[BatchArchiveService] Creating archive: {archive_path}")

            with tarfile.open(archive_path, "w:gz") as tar:
                # Add batch directory to archive
                tar.add(batch_dir, arcname=f"batch_{batch_id}")

                # Add all project directories for this batch
                for project_id in metadata.project_ids:
                    project_dir = self.storage_service.projects_dir / str(project_id)
                    if project_dir.exists():
                        tar.add(project_dir, arcname=f"projects/{project_id}")

            # Get archive size
            archive_size = archive_path.stat().st_size
            original_size = sum(f.stat().st_size for f in batch_dir.rglob("*") if f.is_file())

            # Calculate compression ratio
            compression_ratio = (1 - archive_size / original_size) * 100 if original_size > 0 else 0

            logger.info(
                f"[BatchArchiveService] Archive created successfully. "
                f"Original: {original_size / 1024 / 1024:.2f}MB, "
                f"Archived: {archive_size / 1024 / 1024:.2f}MB, "
                f"Compression: {compression_ratio:.1f}%"
            )

            # Update metadata to mark as archived
            metadata.archived = True
            metadata.archived_at = datetime.now().isoformat()
            metadata.archive_path = str(archive_path)
            metadata.archive_size = archive_size
            metadata.original_size = original_size

            # Save updated metadata
            metadata_path = batch_dir / "metadata.json"
            import json

            with open(metadata_path, "w") as f:
                json.dump(metadata.model_dump(), f, indent=2, default=str)

            # Delete original batch files (but keep metadata for restore)
            for project_id in metadata.project_ids:
                project_dir = self.storage_service.projects_dir / str(project_id)
                if project_dir.exists():
                    shutil.rmtree(project_dir)
                    logger.info(f"[BatchArchiveService] Deleted project directory: {project_id}")

            logger.info(f"[BatchArchiveService] Batch {batch_id} archived successfully")
            return True

        except Exception as e:
            logger.error(
                f"[BatchArchiveService] Error archiving batch {batch_id}: {e}", exc_info=True
            )
            return False

    def restore_batch(self, batch_id: UUID) -> bool:
        """
        Restore a batch from archive.

        Args:
            batch_id: Batch ID to restore

        Returns:
            True if restored successfully, False otherwise
        """
        logger.info(f"[BatchArchiveService] Restoring batch: {batch_id}")

        try:
            # Load batch metadata
            metadata = self.batch_service.load_batch_metadata(batch_id)

            # Check if batch is archived
            if not getattr(metadata, "archived", False):
                logger.warning(f"[BatchArchiveService] Batch {batch_id} is not archived")
                return False

            # Get archive path
            archive_path = Path(getattr(metadata, "archive_path", ""))
            if not archive_path.exists():
                logger.error(f"[BatchArchiveService] Archive not found: {archive_path}")
                return False

            logger.info(f"[BatchArchiveService] Extracting archive: {archive_path}")

            # Extract archive
            with tarfile.open(archive_path, "r:gz") as tar:
                # Extract to temporary directory first
                temp_extract_dir = self.storage_service.projects_dir.parent / "temp_restore"
                temp_extract_dir.mkdir(exist_ok=True)

                tar.extractall(temp_extract_dir)

                # Move batch directory back
                batch_dir = self.storage_service.projects_dir.parent / "batches" / str(batch_id)
                extracted_batch_dir = temp_extract_dir / f"batch_{batch_id}"
                if extracted_batch_dir.exists():
                    if batch_dir.exists():
                        shutil.rmtree(batch_dir)
                    shutil.move(str(extracted_batch_dir), str(batch_dir))

                # Move project directories back
                projects_extract_dir = temp_extract_dir / "projects"
                if projects_extract_dir.exists():
                    for project_dir in projects_extract_dir.iterdir():
                        project_id = project_dir.name
                        target_dir = self.storage_service.projects_dir / project_id
                        if target_dir.exists():
                            shutil.rmtree(target_dir)
                        shutil.move(str(project_dir), str(target_dir))

                # Clean up temp directory
                shutil.rmtree(temp_extract_dir)

            # Update metadata to mark as not archived
            metadata.archived = False
            metadata.restored_at = datetime.now().isoformat()

            # Save updated metadata
            metadata_path = batch_dir / "metadata.json"
            import json

            with open(metadata_path, "w") as f:
                json.dump(metadata.model_dump(), f, indent=2, default=str)

            logger.info(f"[BatchArchiveService] Batch {batch_id} restored successfully")
            return True

        except Exception as e:
            logger.error(
                f"[BatchArchiveService] Error restoring batch {batch_id}: {e}", exc_info=True
            )
            return False

    def get_archive_statistics(self) -> Dict:
        """
        Get archive statistics.

        Returns:
            Dictionary with archive statistics
        """
        all_batches = self.batch_service.list_batches()

        archived_count = 0
        total_archive_size = 0
        total_original_size = 0

        for batch in all_batches:
            if getattr(batch, "archived", False):
                archived_count += 1
                total_archive_size += getattr(batch, "archive_size", 0)
                total_original_size += getattr(batch, "original_size", 0)

        space_saved = total_original_size - total_archive_size
        compression_ratio = (
            (space_saved / total_original_size * 100) if total_original_size > 0 else 0
        )

        return {
            "total_batches": len(all_batches),
            "archived_batches": archived_count,
            "active_batches": len(all_batches) - archived_count,
            "total_archive_size": total_archive_size,
            "total_original_size": total_original_size,
            "space_saved": space_saved,
            "compression_ratio": round(compression_ratio, 1),
        }

    def auto_archive_old_batches(
        self, days_threshold: Optional[int] = None, dry_run: bool = False
    ) -> Dict:
        """
        Automatically archive old batches.

        Args:
            days_threshold: Number of days of inactivity (default: 90)
            dry_run: If True, only report what would be archived without actually archiving

        Returns:
            Dictionary with results
        """
        logger.info(f"[BatchArchiveService] Starting auto-archive (dry_run={dry_run})")

        old_batches = self.find_old_batches(days_threshold)

        if dry_run:
            logger.info(f"[BatchArchiveService] DRY RUN: Would archive {len(old_batches)} batches")
            return {
                "dry_run": True,
                "batches_to_archive": len(old_batches),
                "batch_ids": [str(b.batch_id) for b in old_batches],
            }

        # Archive old batches
        archived_count = 0
        failed_count = 0

        for batch in old_batches:
            success = self.archive_batch(batch.batch_id)
            if success:
                archived_count += 1
            else:
                failed_count += 1

        logger.info(
            f"[BatchArchiveService] Auto-archive completed. "
            f"Archived: {archived_count}, Failed: {failed_count}"
        )

        return {
            "dry_run": False,
            "total_candidates": len(old_batches),
            "archived_count": archived_count,
            "failed_count": failed_count,
        }


# Global instance (singleton)
_batch_archive_service_instance: Optional[BatchArchiveService] = None


def get_batch_archive_service(
    batch_service: BatchService, storage_service: StorageService
) -> BatchArchiveService:
    """Get or create the global batch archive service instance."""
    global _batch_archive_service_instance
    if _batch_archive_service_instance is None:
        _batch_archive_service_instance = BatchArchiveService(batch_service, storage_service)
    return _batch_archive_service_instance
