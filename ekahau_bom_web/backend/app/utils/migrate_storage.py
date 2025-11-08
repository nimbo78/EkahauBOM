"""Storage migration tool for moving projects between local and S3 storage.

Usage:
    python -m app.utils.migrate_storage --help
    python -m app.utils.migrate_storage local-to-s3 [--all | --project-id UUID]
    python -m app.utils.migrate_storage s3-to-local [--all | --project-id UUID]

Examples:
    # Migrate all projects from local to S3
    python -m app.utils.migrate_storage local-to-s3 --all

    # Migrate specific project from S3 to local
    python -m app.utils.migrate_storage s3-to-local --project-id 550e8400-e29b-41d4-a716-446655440000

    # Dry run (don't actually migrate, just show what would be done)
    python -m app.utils.migrate_storage local-to-s3 --all --dry-run
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional
from uuid import UUID

from app.config import Settings
from app.services.storage.base import StorageBackend, StorageError
from app.services.storage.factory import StorageFactory
from app.services.storage.local import LocalStorage
from app.services.storage.s3 import S3Storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class StorageMigrator:
    """Tool for migrating projects between storage backends."""

    def __init__(self, source: StorageBackend, target: StorageBackend):
        """Initialize migrator.

        Args:
            source: Source storage backend
            target: Target storage backend
        """
        self.source = source
        self.target = target
        self.migrated_count = 0
        self.failed_count = 0

    def migrate_project(self, project_id: UUID, dry_run: bool = False) -> bool:
        """Migrate a single project from source to target.

        Args:
            project_id: Project UUID to migrate
            dry_run: If True, don't actually migrate, just log what would be done

        Returns:
            True if migration succeeded, False otherwise
        """
        try:
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrating project {project_id}...")

            # Check if project exists in source
            if not self.source.exists(project_id):
                logger.warning(f"Project {project_id} not found in source storage")
                return False

            # Check if project already exists in target
            if self.target.exists(project_id):
                logger.warning(f"Project {project_id} already exists in target storage. Skipping.")
                return False

            # List all files in source project
            files = self.source.list_files(project_id, recursive=True)
            logger.info(f"Found {len(files)} files to migrate")

            if dry_run:
                logger.info(f"[DRY RUN] Would migrate {len(files)} files:")
                for file_path in files[:10]:  # Show first 10 files
                    logger.info(f"  - {file_path}")
                if len(files) > 10:
                    logger.info(f"  ... and {len(files) - 10} more files")
                return True

            # Migrate each file
            migrated = 0
            for file_path in files:
                try:
                    # Read from source
                    content = self.source.get_file(project_id, file_path)

                    # Write to target
                    self.target.save_file(project_id, file_path, content)

                    migrated += 1

                    # Progress logging every 10 files
                    if migrated % 10 == 0:
                        logger.info(f"Migrated {migrated}/{len(files)} files...")

                except Exception as e:
                    logger.error(f"Failed to migrate file {file_path}: {e}")
                    # Continue with other files

            logger.info(
                f"✅ Successfully migrated project {project_id} ({migrated}/{len(files)} files)"
            )

            # Calculate sizes
            source_size = self.source.get_project_size(project_id)
            target_size = self.target.get_project_size(project_id)
            logger.info(f"Source size: {source_size:,} bytes, Target size: {target_size:,} bytes")

            self.migrated_count += 1
            return True

        except Exception as e:
            logger.error(f"❌ Failed to migrate project {project_id}: {e}", exc_info=True)
            self.failed_count += 1
            return False

    def migrate_all_projects(self, dry_run: bool = False) -> tuple[int, int]:
        """Migrate all projects from source to target.

        Args:
            dry_run: If True, don't actually migrate, just log what would be done

        Returns:
            Tuple of (successful_count, failed_count)
        """
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting migration of all projects...")

        # Get list of all projects from source
        # For local storage: list directories in projects_dir
        # For S3: list prefixes under "projects/"
        project_ids = self._list_all_projects(self.source)

        logger.info(f"Found {len(project_ids)} projects in source storage")

        if dry_run:
            logger.info(f"[DRY RUN] Would migrate {len(project_ids)} projects:")
            for project_id in project_ids[:5]:
                logger.info(f"  - {project_id}")
            if len(project_ids) > 5:
                logger.info(f"  ... and {len(project_ids) - 5} more projects")

        # Migrate each project
        for i, project_id in enumerate(project_ids, 1):
            logger.info(f"\n--- Project {i}/{len(project_ids)} ---")
            self.migrate_project(project_id, dry_run=dry_run)

        logger.info("\n" + "=" * 60)
        logger.info("Migration Summary:")
        logger.info(f"  Total projects: {len(project_ids)}")
        logger.info(f"  ✅ Migrated: {self.migrated_count}")
        logger.info(f"  ❌ Failed: {self.failed_count}")
        logger.info("=" * 60)

        return self.migrated_count, self.failed_count

    def _list_all_projects(self, backend: StorageBackend) -> list[UUID]:
        """List all project IDs in a storage backend.

        Args:
            backend: Storage backend to list projects from

        Returns:
            List of project UUIDs
        """
        if isinstance(backend, LocalStorage):
            # List directories in projects_dir
            projects_dir = backend.base_dir
            project_ids = []

            for item in projects_dir.iterdir():
                if item.is_dir():
                    try:
                        project_id = UUID(item.name)
                        project_ids.append(project_id)
                    except ValueError:
                        # Not a valid UUID directory
                        continue

            return project_ids

        elif isinstance(backend, S3Storage):
            # List prefixes under "projects/"
            import boto3

            try:
                # Use paginator to handle large number of projects
                paginator = backend.s3.get_paginator("list_objects_v2")
                pages = paginator.paginate(
                    Bucket=backend.bucket,
                    Prefix="projects/",
                    Delimiter="/",  # Only get first-level "directories"
                )

                project_ids = []
                for page in pages:
                    if "CommonPrefixes" in page:
                        for prefix_obj in page["CommonPrefixes"]:
                            prefix = prefix_obj["Prefix"]
                            # Extract UUID from "projects/UUID/"
                            project_dir = prefix.rstrip("/").split("/")[-1]
                            try:
                                project_id = UUID(project_dir)
                                project_ids.append(project_id)
                            except ValueError:
                                continue

                return project_ids

            except Exception as e:
                logger.error(f"Failed to list projects from S3: {e}")
                return []

        else:
            logger.error(f"Unsupported backend type: {type(backend)}")
            return []


def create_backend_from_settings(backend_type: str, settings: Settings) -> Optional[StorageBackend]:
    """Create storage backend from settings.

    Args:
        backend_type: "local" or "s3"
        settings: Application settings

    Returns:
        Storage backend instance or None if configuration invalid
    """
    try:
        if backend_type == "local":
            return LocalStorage(base_dir=settings.projects_dir)

        elif backend_type == "s3":
            if not settings.s3_bucket_name:
                logger.error("S3_BUCKET_NAME is required for S3 backend")
                return None

            return S3Storage(
                bucket=settings.s3_bucket_name,
                region=settings.s3_region,
                access_key=settings.s3_access_key,
                secret_key=settings.s3_secret_key,
                endpoint_url=settings.s3_endpoint_url,
                use_ssl=settings.s3_use_ssl,
                verify=settings.s3_verify,
                ca_bundle=settings.s3_ca_bundle,
            )

        else:
            logger.error(f"Unknown backend type: {backend_type}")
            return None

    except Exception as e:
        logger.error(f"Failed to create {backend_type} backend: {e}")
        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate projects between local and S3 storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "direction",
        choices=["local-to-s3", "s3-to-local"],
        help="Migration direction",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="Migrate all projects",
    )
    group.add_argument(
        "--project-id",
        type=str,
        help="Migrate specific project by UUID",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (don't actually migrate, just show what would be done)",
    )

    args = parser.parse_args()

    # Load settings
    from app.config import settings

    # Create source and target backends
    if args.direction == "local-to-s3":
        logger.info("Migration direction: Local → S3")
        source = create_backend_from_settings("local", settings)
        target = create_backend_from_settings("s3", settings)
    else:  # s3-to-local
        logger.info("Migration direction: S3 → Local")
        source = create_backend_from_settings("s3", settings)
        target = create_backend_from_settings("local", settings)

    if not source or not target:
        logger.error("Failed to create storage backends. Check your configuration.")
        sys.exit(1)

    # Create migrator
    migrator = StorageMigrator(source=source, target=target)

    # Run migration
    if args.all:
        migrated, failed = migrator.migrate_all_projects(dry_run=args.dry_run)
        sys.exit(0 if failed == 0 else 1)
    else:
        # Migrate specific project
        try:
            project_id = UUID(args.project_id)
            success = migrator.migrate_project(project_id, dry_run=args.dry_run)
            sys.exit(0 if success else 1)
        except ValueError:
            logger.error(f"Invalid project UUID: {args.project_id}")
            sys.exit(1)


if __name__ == "__main__":
    main()
