"""Cleanup job for expired short links.

This script removes short links that have expired.
Can be run as a scheduled task (cron job or Windows Task Scheduler).

Usage:
    python -m app.tasks.cleanup_expired_links
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.services.cache import cache_service
from app.services.index import index_service
from app.services.storage_service import StorageService
from app.utils.short_links import is_link_expired

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize services
storage_service = StorageService()


def cleanup_expired_links() -> dict:
    """Remove expired short links from all projects.

    Returns:
        Dictionary with cleanup statistics
    """
    logger.info("Starting cleanup of expired short links")

    total_projects = 0
    expired_links_removed = 0
    errors = 0

    # Get all projects from index
    all_projects = index_service.list_all()
    total_projects = len(all_projects)

    logger.info(f"Checking {total_projects} projects for expired links")

    for project_item in all_projects:
        try:
            # Load full metadata
            metadata = storage_service.load_metadata(project_item.project_id)
            if not metadata:
                continue

            # Check if project has a short link
            if not metadata.short_link:
                continue

            # Check if short link has expired
            if is_link_expired(metadata.short_link_expires):
                logger.info(
                    f"Removing expired short link for project {project_item.project_id} "
                    f"(link: {metadata.short_link}, expired: {metadata.short_link_expires})"
                )

                # Remove short link
                metadata.short_link = None
                metadata.short_link_expires = None

                # Save metadata
                storage_service.save_metadata(project_item.project_id, metadata)
                index_service.add(metadata)

                # Invalidate cache
                cache_service.invalidate_project(project_item.project_id)

                expired_links_removed += 1

        except Exception as e:
            logger.error(
                f"Error processing project {project_item.project_id}: {e}",
                exc_info=True,
            )
            errors += 1

    # Save index to disk
    index_service.save_to_disk()

    # Invalidate projects list cache (short links changed)
    cache_service.invalidate_projects_list()

    stats = {
        "timestamp": datetime.now(UTC).isoformat(),
        "total_projects_checked": total_projects,
        "expired_links_removed": expired_links_removed,
        "errors": errors,
    }

    logger.info(
        f"Cleanup complete: {expired_links_removed} expired links removed "
        f"from {total_projects} projects (errors: {errors})"
    )

    return stats


if __name__ == "__main__":
    # Run cleanup
    result = cleanup_expired_links()

    # Print summary
    print("\n=== Cleanup Summary ===")
    print(f"Timestamp: {result['timestamp']}")
    print(f"Projects checked: {result['total_projects_checked']}")
    print(f"Expired links removed: {result['expired_links_removed']}")
    print(f"Errors: {result['errors']}")
    print("=" * 23)
