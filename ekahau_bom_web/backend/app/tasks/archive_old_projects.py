"""Archive old projects job.

This script compresses old projects (not accessed for 60+ days) to save disk space.
Can be run as a scheduled task (cron job or Windows Task Scheduler).

Usage:
    python -m app.tasks.archive_old_projects
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.services.archive import archive_service
from app.services.cache import cache_service
from app.services.index import index_service
from app.services.storage_service import StorageService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize services
storage_service = StorageService()


def archive_old_projects() -> dict:
    """Archive old projects to save disk space.

    Projects are archived if:
    - Processing status is COMPLETED
    - Last accessed > 60 days ago (or never accessed)
    - Not already archived

    Returns:
        Dictionary with archiving statistics
    """
    logger.info("Starting archiving of old projects")

    total_projects = 0
    projects_archived = 0
    errors = 0
    total_space_saved = 0

    # Get all projects from index
    all_projects = index_service.list_all()
    total_projects = len(all_projects)

    logger.info(f"Checking {total_projects} projects for archiving")

    for project_item in all_projects:
        try:
            # Load full metadata
            metadata = storage_service.load_metadata(project_item.project_id)
            if not metadata:
                continue

            # Check if project should be archived
            if not archive_service.should_archive(metadata):
                continue

            logger.info(
                f"Archiving project {project_item.project_id} "
                f"(name: {metadata.project_name}, "
                f"last_accessed: {metadata.last_accessed}, "
                f"upload_date: {metadata.upload_date})"
            )

            # Get project size before archiving
            project_dir = storage_service.get_project_dir(project_item.project_id)
            original_size = archive_service._get_dir_size(project_dir)

            # Archive project
            if archive_service.archive_project(project_item.project_id):
                # Get archive size
                archive_path = archive_service.get_archive_path(project_item.project_id)
                archive_size = archive_path.stat().st_size if archive_path.exists() else 0

                space_saved = original_size - archive_size
                total_space_saved += space_saved

                logger.info(
                    f"Project {project_item.project_id} archived successfully. "
                    f"Original: {original_size / 1024 / 1024:.2f} MB, "
                    f"Archive: {archive_size / 1024 / 1024:.2f} MB, "
                    f"Saved: {space_saved / 1024 / 1024:.2f} MB "
                    f"({(space_saved / original_size * 100):.1f}%)"
                )

                projects_archived += 1

                # Update index
                metadata = storage_service.load_metadata(project_item.project_id)
                if metadata:
                    index_service.add(metadata)
            else:
                logger.error(f"Failed to archive project {project_item.project_id}")
                errors += 1

        except Exception as e:
            logger.error(
                f"Error processing project {project_item.project_id}: {e}",
                exc_info=True,
            )
            errors += 1

    # Save index to disk
    index_service.save_to_disk()

    # Invalidate projects list cache (archived status changed)
    cache_service.invalidate_projects_list()

    stats = {
        "timestamp": datetime.now(UTC).isoformat(),
        "total_projects_checked": total_projects,
        "projects_archived": projects_archived,
        "total_space_saved_bytes": total_space_saved,
        "total_space_saved_mb": total_space_saved / 1024 / 1024,
        "errors": errors,
    }

    logger.info(
        f"Archiving complete: {projects_archived} projects archived "
        f"from {total_projects} projects "
        f"(saved: {total_space_saved / 1024 / 1024:.2f} MB, errors: {errors})"
    )

    return stats


if __name__ == "__main__":
    # Run archiving
    result = archive_old_projects()

    # Print summary
    print("\n=== Archiving Summary ===")
    print(f"Timestamp: {result['timestamp']}")
    print(f"Projects checked: {result['total_projects_checked']}")
    print(f"Projects archived: {result['projects_archived']}")
    print(f"Space saved: {result['total_space_saved_mb']:.2f} MB")
    print(f"Errors: {result['errors']}")
    print("=" * 25)
