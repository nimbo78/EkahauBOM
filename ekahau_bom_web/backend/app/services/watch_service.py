"""
Watch Service - Monitor directories for new .esx files and auto-process them.

This service provides functionality to:
- Monitor specified directories for new .esx files
- Auto-create batches when new files are detected
- Process batches with configured settings
- Track watch status and statistics
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, List, Set
from datetime import datetime
import time
from threading import Thread, Lock

from ..models import ProcessingRequest, BatchStatus
from .batch_service import BatchService
from .storage_service import StorageService

logger = logging.getLogger(__name__)


class WatchConfig:
    """Configuration for directory watch mode."""

    def __init__(
        self,
        watch_directory: str,
        interval_seconds: int = 60,
        file_pattern: str = "*.esx",
        auto_process: bool = True,
        batch_name_prefix: str = "Watch",
        processing_options: Optional[ProcessingRequest] = None,
        parallel_workers: int = 1,
    ):
        self.watch_directory = Path(watch_directory)
        self.interval_seconds = interval_seconds
        self.file_pattern = file_pattern
        self.auto_process = auto_process
        self.batch_name_prefix = batch_name_prefix
        self.processing_options = processing_options or ProcessingRequest()
        self.parallel_workers = parallel_workers

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "watch_directory": str(self.watch_directory),
            "interval_seconds": self.interval_seconds,
            "file_pattern": self.file_pattern,
            "auto_process": self.auto_process,
            "batch_name_prefix": self.batch_name_prefix,
            "processing_options": (
                self.processing_options.model_dump() if self.processing_options else None
            ),
            "parallel_workers": self.parallel_workers,
        }


class WatchStatistics:
    """Statistics for watch mode."""

    def __init__(self):
        self.started_at: Optional[datetime] = None
        self.last_check_at: Optional[datetime] = None
        self.total_checks: int = 0
        self.total_files_found: int = 0
        self.total_batches_created: int = 0
        self.processed_files: Set[str] = set()

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_check_at": self.last_check_at.isoformat() if self.last_check_at else None,
            "total_checks": self.total_checks,
            "total_files_found": self.total_files_found,
            "total_batches_created": self.total_batches_created,
            "processed_files_count": len(self.processed_files),
        }


class WatchService:
    """
    Service for monitoring directories and auto-processing new .esx files.

    This service runs in a background thread and periodically checks for new files.
    When new files are detected, it creates a batch and optionally starts processing.
    """

    def __init__(self, batch_service: BatchService, storage_service: StorageService):
        self.batch_service = batch_service
        self.storage_service = storage_service
        self.config: Optional[WatchConfig] = None
        self.statistics = WatchStatistics()
        self.is_running = False
        self.watch_thread: Optional[Thread] = None
        self._lock = Lock()

    def start_watch(self, config: WatchConfig) -> bool:
        """
        Start watching directory for new files.

        Args:
            config: Watch configuration

        Returns:
            True if watch started successfully, False otherwise
        """
        with self._lock:
            if self.is_running:
                logger.warning("[WatchService] Watch mode already running")
                return False

            # Validate directory exists
            if not config.watch_directory.exists():
                logger.error(f"[WatchService] Directory does not exist: {config.watch_directory}")
                return False

            if not config.watch_directory.is_dir():
                logger.error(f"[WatchService] Path is not a directory: {config.watch_directory}")
                return False

            self.config = config
            self.statistics = WatchStatistics()
            self.statistics.started_at = datetime.now()
            self.is_running = True

            # Start watch thread
            self.watch_thread = Thread(target=self._watch_loop, daemon=True)
            self.watch_thread.start()

            logger.info(f"[WatchService] Started watching: {config.watch_directory}")
            return True

    def stop_watch(self) -> bool:
        """
        Stop watching directory.

        Returns:
            True if watch stopped successfully, False otherwise
        """
        with self._lock:
            if not self.is_running:
                logger.warning("[WatchService] Watch mode not running")
                return False

            self.is_running = False
            logger.info("[WatchService] Stopped watching")
            return True

    def get_status(self) -> Dict:
        """
        Get current watch status and statistics.

        Returns:
            Dictionary with status information
        """
        with self._lock:
            return {
                "is_running": self.is_running,
                "config": self.config.to_dict() if self.config else None,
                "statistics": self.statistics.to_dict(),
            }

    def _watch_loop(self):
        """Main watch loop (runs in background thread)."""
        logger.info("[WatchService] Watch loop started")

        while self.is_running:
            try:
                self._check_for_new_files()
                time.sleep(self.config.interval_seconds)
            except Exception as e:
                logger.error(f"[WatchService] Error in watch loop: {e}", exc_info=True)
                # Continue watching despite errors
                time.sleep(self.config.interval_seconds)

        logger.info("[WatchService] Watch loop stopped")

    def _check_for_new_files(self):
        """Check directory for new .esx files and process them."""
        if not self.config:
            return

        with self._lock:
            self.statistics.last_check_at = datetime.now()
            self.statistics.total_checks += 1

        # Find all matching files
        matching_files: List[Path] = list(
            self.config.watch_directory.glob(self.config.file_pattern)
        )
        logger.debug(f"[WatchService] Found {len(matching_files)} matching files")

        # Filter out already processed files
        new_files = [
            f for f in matching_files if str(f.absolute()) not in self.statistics.processed_files
        ]

        if not new_files:
            logger.debug("[WatchService] No new files found")
            return

        logger.info(f"[WatchService] Found {len(new_files)} new files")

        with self._lock:
            self.statistics.total_files_found += len(new_files)

        # Create batch for new files
        try:
            batch_name = (
                f"{self.config.batch_name_prefix} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            logger.info(f"[WatchService] Creating batch: {batch_name}")

            # Create batch metadata
            batch_metadata = self.batch_service.create_batch(
                batch_name=batch_name,
                processing_options=self.config.processing_options,
                parallel_workers=self.config.parallel_workers,
            )

            # Copy files to batch and add to index
            files_added = 0
            for file_path in new_files:
                try:
                    # Read file from filesystem
                    with open(file_path, "rb") as f:
                        file_content = f.read()

                    # Save to storage and create project metadata
                    project_metadata = self.storage_service.save_uploaded_file(
                        filename=file_path.name,
                        file_content=file_content,
                        project_name=file_path.stem,  # Use filename without extension
                        short_link_days=(
                            self.config.processing_options.short_link_days
                            if self.config.processing_options.create_short_link
                            else None
                        ),
                    )

                    # Add project to batch
                    self.batch_service.add_project_to_batch(
                        batch_metadata.batch_id, project_metadata.project_id
                    )

                    files_added += 1

                    # Mark file as processed
                    with self._lock:
                        self.statistics.processed_files.add(str(file_path.absolute()))

                    logger.info(f"[WatchService] Added file to batch: {file_path.name}")

                except Exception as e:
                    logger.error(
                        f"[WatchService] Error adding file {file_path}: {e}", exc_info=True
                    )
                    continue

            if files_added > 0:
                with self._lock:
                    self.statistics.total_batches_created += 1

                logger.info(
                    f"[WatchService] Created batch {batch_metadata.batch_id} with {files_added} files"
                )

                # Start processing if auto_process is enabled
                if self.config.auto_process:
                    logger.info(
                        f"[WatchService] Starting batch processing: {batch_metadata.batch_id}"
                    )
                    # Run processing in background (don't block watch loop)
                    Thread(
                        target=self.batch_service.process_batch,
                        args=(batch_metadata.batch_id,),
                        daemon=True,
                    ).start()
            else:
                logger.warning(f"[WatchService] No files added to batch {batch_metadata.batch_id}")

        except Exception as e:
            logger.error(f"[WatchService] Error creating batch: {e}", exc_info=True)


# Global watch service instance (singleton)
_watch_service_instance: Optional[WatchService] = None


def get_watch_service(batch_service: BatchService, storage_service: StorageService) -> WatchService:
    """Get or create the global watch service instance."""
    global _watch_service_instance
    if _watch_service_instance is None:
        _watch_service_instance = WatchService(batch_service, storage_service)
    return _watch_service_instance
