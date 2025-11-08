"""
Background task to archive old batches.

This task should be run periodically (e.g., weekly) to archive batches
that haven't been accessed for 90+ days.

Usage:
    python -m app.tasks.archive_old_batches

Schedule with Windows Task Scheduler:
    - Action: python.exe
    - Arguments: -m app.tasks.archive_old_batches
    - Start in: C:\path\to\ekahau_bom_web\backend
    - Trigger: Weekly (Sunday 02:00)

Schedule with Linux cron:
    0 2 * * 0 cd /path/to/backend && python -m app.tasks.archive_old_batches
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.batch_service import batch_service
from app.services.storage_service import StorageService
from app.services.batch_archive_service import get_batch_archive_service

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main function to archive old batches."""
    logger.info("=" * 80)
    logger.info("Starting archive old batches task")
    logger.info("=" * 80)

    try:
        # Initialize services
        storage_service = StorageService()
        archive_service = get_batch_archive_service(batch_service, storage_service)

        # Get archive statistics before
        stats_before = archive_service.get_archive_statistics()
        logger.info(f"Statistics before archiving:")
        logger.info(f"  Total batches: {stats_before['total_batches']}")
        logger.info(f"  Archived batches: {stats_before['archived_batches']}")
        logger.info(f"  Active batches: {stats_before['active_batches']}")

        # Archive old batches (90+ days inactive)
        logger.info("Archiving batches not accessed for 90+ days...")
        result = archive_service.auto_archive_old_batches(days_threshold=90, dry_run=False)

        logger.info(f"Archive operation completed:")
        logger.info(f"  Total candidates: {result['total_candidates']}")
        logger.info(f"  Archived: {result['archived_count']}")
        logger.info(f"  Failed: {result['failed_count']}")

        # Get archive statistics after
        stats_after = archive_service.get_archive_statistics()
        logger.info(f"Statistics after archiving:")
        logger.info(f"  Total batches: {stats_after['total_batches']}")
        logger.info(f"  Archived batches: {stats_after['archived_batches']}")
        logger.info(f"  Active batches: {stats_after['active_batches']}")
        logger.info(f"  Space saved: {stats_after['space_saved'] / 1024 / 1024:.2f} MB")
        logger.info(f"  Compression ratio: {stats_after['compression_ratio']:.1f}%")

        logger.info("=" * 80)
        logger.info("Archive old batches task completed successfully")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Error in archive old batches task: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
