"""Batch processing service."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from app.models import (
    BatchMetadata,
    BatchProjectStatus,
    BatchStatistics,
    BatchStatus,
    BatchUploadResponse,
    ProcessingRequest,
    ProcessingStatus,
    ProjectMetadata,
)
from app.services.processor import ProcessorService
from app.services.storage_service import StorageService
from app.websocket import connection_manager

logger = logging.getLogger(__name__)


class BatchService:
    """Service for managing batch processing of multiple projects."""

    def __init__(self, storage_service: Optional[StorageService] = None):
        """Initialize batch service.

        Args:
            storage_service: Optional storage service instance
        """
        self.storage = storage_service or StorageService()
        self.batches_dir = Path("batches")

    def _get_batch_dir(self, batch_id: UUID) -> Path:
        """Get batch directory path.

        Args:
            batch_id: Batch UUID

        Returns:
            Path to batch directory
        """
        return self.storage.projects_dir.parent / self.batches_dir / str(batch_id)

    def _get_batch_metadata_path(self, batch_id: UUID) -> Path:
        """Get path to batch metadata file.

        Args:
            batch_id: Batch UUID

        Returns:
            Path to batch metadata JSON file
        """
        return self._get_batch_dir(batch_id) / "batch_metadata.json"

    def create_batch(
        self,
        batch_name: Optional[str] = None,
        processing_options: Optional[ProcessingRequest] = None,
        parallel_workers: int = 1,
        template_id: Optional[str] = None,
    ) -> BatchMetadata:
        """Create a new batch.

        Args:
            batch_name: Optional batch name
            processing_options: Processing options to use for all projects
            parallel_workers: Number of parallel workers
            template_id: Optional template ID if using a template

        Returns:
            Created batch metadata
        """
        metadata = BatchMetadata(
            batch_name=batch_name or f"Batch {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}",
            processing_options=processing_options or ProcessingRequest(),
            parallel_workers=parallel_workers,
            template_id=template_id,
            batch_dir=str(self.batches_dir / "{batch_id}"),
        )

        # Create batch directory
        batch_dir = self._get_batch_dir(metadata.batch_id)
        batch_dir.mkdir(parents=True, exist_ok=True)

        # Update batch_dir with actual path
        metadata.batch_dir = str(self.batches_dir / str(metadata.batch_id))

        # Save metadata
        self._save_batch_metadata(metadata)

        logger.info(f"Created batch {metadata.batch_id}: {metadata.batch_name}")
        return metadata

    def _save_batch_metadata(self, metadata: BatchMetadata) -> None:
        """Save batch metadata to JSON file.

        Args:
            metadata: Batch metadata to save
        """
        metadata_path = self._get_batch_metadata_path(metadata.batch_id)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(mode="json"), f, indent=2, default=str)

    def load_batch_metadata(self, batch_id: UUID) -> Optional[BatchMetadata]:
        """Load batch metadata from storage.

        Args:
            batch_id: Batch UUID

        Returns:
            Batch metadata or None if not found
        """
        metadata_path = self._get_batch_metadata_path(batch_id)
        if not metadata_path.exists():
            return None

        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return BatchMetadata(**data)

    def list_batches(
        self,
        status: Optional[BatchStatus] = None,
        tags: Optional[list[str]] = None,
        search_query: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        min_projects: Optional[int] = None,
        max_projects: Optional[int] = None,
        sort_by: str = "date",
        sort_order: str = "desc",
        limit: Optional[int] = None,
    ) -> list[BatchMetadata]:
        """List all batches with advanced filtering and sorting.

        Args:
            status: Optional status filter
            tags: Optional tags filter (batch must have all specified tags)
            search_query: Optional text search (searches batch name and project names)
            created_after: Optional filter for batches created after this date
            created_before: Optional filter for batches created before this date
            min_projects: Optional minimum number of projects
            max_projects: Optional maximum number of projects
            sort_by: Sort field ("date", "name", "project_count", "success_rate")
            sort_order: Sort order ("asc" or "desc")
            limit: Optional limit

        Returns:
            List of batch metadata
        """
        batches_base = self.storage.projects_dir.parent / self.batches_dir
        if not batches_base.exists():
            return []

        batches = []
        for batch_dir in batches_base.iterdir():
            if not batch_dir.is_dir():
                continue

            try:
                batch_id = UUID(batch_dir.name)
                metadata = self.load_batch_metadata(batch_id)
                if metadata:
                    # Filter by status
                    if status is not None and metadata.status != status:
                        continue

                    # Filter by tags (batch must have ALL specified tags)
                    if tags:
                        batch_tags = set(metadata.tags)
                        required_tags = set(tags)
                        if not required_tags.issubset(batch_tags):
                            continue

                    # Filter by date range
                    if created_after and metadata.created_date < created_after:
                        continue
                    if created_before and metadata.created_date > created_before:
                        continue

                    # Filter by project count
                    project_count = len(metadata.project_ids)
                    if min_projects is not None and project_count < min_projects:
                        continue
                    if max_projects is not None and project_count > max_projects:
                        continue

                    # Filter by search query (batch name or project filenames)
                    if search_query:
                        query_lower = search_query.lower()
                        batch_name_match = (
                            metadata.batch_name and query_lower in metadata.batch_name.lower()
                        )
                        # Check if any project filename matches
                        project_match = any(
                            query_lower in ps.filename.lower() for ps in metadata.project_statuses
                        )
                        if not (batch_name_match or project_match):
                            continue

                    batches.append(metadata)
            except (ValueError, Exception) as e:
                logger.warning(f"Failed to load batch {batch_dir.name}: {e}")
                continue

        # Sort batches
        reverse = sort_order == "desc"

        if sort_by == "date":
            batches.sort(key=lambda b: b.created_date, reverse=reverse)
        elif sort_by == "name":
            batches.sort(
                key=lambda b: (b.batch_name or "").lower(),
                reverse=reverse,
            )
        elif sort_by == "project_count":
            batches.sort(key=lambda b: len(b.project_ids), reverse=reverse)
        elif sort_by == "success_rate":
            # Calculate success rate (avoid division by zero)
            def success_rate(b: BatchMetadata) -> float:
                total = b.statistics.total_projects
                return b.statistics.successful_projects / total if total > 0 else 0.0

            batches.sort(key=success_rate, reverse=reverse)
        else:
            # Default to date sorting
            batches.sort(key=lambda b: b.created_date, reverse=reverse)

        if limit:
            batches = batches[:limit]

        return batches

    def add_project_to_batch(self, batch_id: UUID, project_id: UUID, filename: str) -> None:
        """Add a project to batch.

        Args:
            batch_id: Batch UUID
            project_id: Project UUID
            filename: Original filename
        """
        metadata = self.load_batch_metadata(batch_id)
        if not metadata:
            raise ValueError(f"Batch {batch_id} not found")

        # Add project ID if not already present
        if project_id not in metadata.project_ids:
            metadata.project_ids.append(project_id)

            # Add project status
            metadata.project_statuses.append(
                BatchProjectStatus(
                    project_id=project_id,
                    filename=filename,
                    status=ProcessingStatus.PENDING,
                )
            )

            # Recalculate statistics to update total_projects count
            metadata.statistics = self._calculate_statistics(metadata)

            self._save_batch_metadata(metadata)
            logger.info(f"Added project {project_id} to batch {batch_id}")

    def update_batch_tags(
        self,
        batch_id: UUID,
        tags_to_add: list[str],
        tags_to_remove: list[str],
    ) -> list[str]:
        """Update batch tags by adding and/or removing tags.

        Args:
            batch_id: Batch UUID
            tags_to_add: List of tags to add
            tags_to_remove: List of tags to remove

        Returns:
            Updated list of tags

        Raises:
            ValueError: If batch not found
        """
        metadata = self.load_batch_metadata(batch_id)
        if not metadata:
            raise ValueError(f"Batch {batch_id} not found")

        # Convert to set for efficient operations
        current_tags = set(metadata.tags)

        # Add new tags
        for tag in tags_to_add:
            if tag and tag.strip():  # Only add non-empty tags
                current_tags.add(tag.strip())

        # Remove tags
        for tag in tags_to_remove:
            current_tags.discard(tag.strip())

        # Update metadata
        metadata.tags = sorted(list(current_tags))  # Keep tags sorted
        self._save_batch_metadata(metadata)

        logger.info(
            f"Updated tags for batch {batch_id}: "
            f"added={tags_to_add}, removed={tags_to_remove}, "
            f"current={metadata.tags}"
        )

        return metadata.tags

    async def process_batch(self, batch_id: UUID) -> BatchMetadata:
        """Process all projects in batch.

        Args:
            batch_id: Batch UUID

        Returns:
            Updated batch metadata with results
        """
        metadata = self.load_batch_metadata(batch_id)
        if not metadata:
            raise ValueError(f"Batch {batch_id} not found")

        # Update status
        metadata.status = BatchStatus.PROCESSING
        metadata.processing_started = datetime.now(UTC)
        self._save_batch_metadata(metadata)

        # Broadcast batch started
        await connection_manager.send_batch_update(
            batch_id=batch_id,
            status="processing",
            progress=0,
            message=f"Started processing {len(metadata.project_ids)} projects",
        )

        logger.info(
            f"Starting batch processing for {batch_id}: {len(metadata.project_ids)} projects"
        )

        # Process projects (sequential for now, parallel implementation later)
        for idx, project_id in enumerate(metadata.project_ids):
            logger.info(f"Processing project {idx + 1}/{len(metadata.project_ids)}: {project_id}")

            # Calculate progress (0-100%)
            progress = int((idx / len(metadata.project_ids)) * 100)

            # Broadcast project started
            await connection_manager.send_project_update(
                batch_id=batch_id,
                project_id=project_id,
                status="processing",
                message=f"Processing project {idx + 1} of {len(metadata.project_ids)}",
            )

            try:
                # Load project metadata
                project_metadata = self.storage.load_metadata(project_id)
                if not project_metadata:
                    raise ValueError(f"Project {project_id} not found")

                # Process project
                start_time = datetime.now(UTC)
                success = await self._process_single_project(
                    project_metadata, metadata.processing_options
                )
                end_time = datetime.now(UTC)
                processing_time = (end_time - start_time).total_seconds()

                # Update project status in batch
                self._update_project_status(
                    metadata,
                    project_id,
                    ProcessingStatus.COMPLETED if success else ProcessingStatus.FAILED,
                    processing_time,
                )

                # Broadcast project completed
                await connection_manager.send_project_update(
                    batch_id=batch_id,
                    project_id=project_id,
                    status="completed" if success else "failed",
                    message=f"Project {idx + 1} completed in {processing_time:.1f}s",
                )

                # Update batch progress
                progress_after = int(((idx + 1) / len(metadata.project_ids)) * 100)
                await connection_manager.send_batch_update(
                    batch_id=batch_id,
                    status="processing",
                    progress=progress_after,
                    message=f"Completed {idx + 1} of {len(metadata.project_ids)} projects",
                )

            except Exception as e:
                logger.error(f"Failed to process project {project_id}: {e}")
                self._update_project_status(
                    metadata,
                    project_id,
                    ProcessingStatus.FAILED,
                    error_message=str(e),
                )

                # Broadcast project failed
                await connection_manager.send_project_update(
                    batch_id=batch_id,
                    project_id=project_id,
                    status="failed",
                    message=f"Project {idx + 1} failed: {str(e)}",
                )

                # Update batch progress even on failure
                progress_after = int(((idx + 1) / len(metadata.project_ids)) * 100)
                await connection_manager.send_batch_update(
                    batch_id=batch_id,
                    status="processing",
                    progress=progress_after,
                    message=f"Completed {idx + 1} of {len(metadata.project_ids)} projects ({metadata.statistics.failed_projects + 1} failed)",
                )

        # Calculate final statistics
        metadata.statistics = self._calculate_statistics(metadata)

        # Determine final batch status
        if metadata.statistics.failed_projects == 0:
            metadata.status = BatchStatus.COMPLETED
        elif metadata.statistics.successful_projects == 0:
            metadata.status = BatchStatus.FAILED
        else:
            metadata.status = BatchStatus.PARTIAL

        metadata.processing_completed = datetime.now(UTC)
        self._save_batch_metadata(metadata)

        # Broadcast final batch status
        status_str = (
            metadata.status.value if hasattr(metadata.status, "value") else str(metadata.status)
        )
        await connection_manager.send_batch_update(
            batch_id=batch_id,
            status=status_str,
            progress=100,
            message=f"Batch processing complete: {metadata.statistics.successful_projects} succeeded, {metadata.statistics.failed_projects} failed",
        )

        logger.info(
            f"Batch {batch_id} processing completed: "
            f"{metadata.statistics.successful_projects} succeeded, "
            f"{metadata.statistics.failed_projects} failed"
        )

        return metadata

    async def _process_single_project(
        self, project_metadata: ProjectMetadata, options: ProcessingRequest
    ) -> bool:
        """Process a single project.

        Args:
            project_metadata: Project metadata
            options: Processing options

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create processor service instance
            processor = ProcessorService(storage=self.storage)

            # Call process_project with options
            await processor.process_project(
                project_id=project_metadata.project_id,
                group_by=options.group_by,
                output_formats=options.output_formats,
                visualize_floor_plans=options.visualize_floor_plans,
                show_azimuth_arrows=options.show_azimuth_arrows,
                ap_opacity=options.ap_opacity,
                include_text_notes=options.include_text_notes,
                include_picture_notes=options.include_picture_notes,
                include_cable_notes=options.include_cable_notes,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to process project {project_metadata.project_id}: {e}")
            return False

    def _update_project_status(
        self,
        metadata: BatchMetadata,
        project_id: UUID,
        status: ProcessingStatus,
        processing_time: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update project status in batch metadata.

        Args:
            metadata: Batch metadata
            project_id: Project UUID
            status: New status
            processing_time: Processing time in seconds
            error_message: Optional error message
        """
        for project_status in metadata.project_statuses:
            if project_status.project_id == project_id:
                project_status.status = status
                project_status.processing_time = processing_time
                project_status.error_message = error_message

                # Load project metadata to get counts
                try:
                    project_metadata = self.storage.load_metadata(project_id)
                    if project_metadata:
                        project_status.access_points_count = project_metadata.aps_count
                        project_status.antennas_count = project_metadata.total_antennas
                except Exception as e:
                    logger.warning(f"Failed to load project metadata for {project_id}: {e}")

                break

        self._save_batch_metadata(metadata)

    def _calculate_statistics(self, metadata: BatchMetadata) -> BatchStatistics:
        """Calculate aggregate statistics from all projects.

        Args:
            metadata: Batch metadata

        Returns:
            Calculated statistics
        """
        from collections import defaultdict

        stats = BatchStatistics()
        stats.total_projects = len(metadata.project_statuses)

        # Temporary dictionaries for aggregation
        ap_by_vendor_model = defaultdict(int)
        antenna_by_model = defaultdict(int)

        for project_status in metadata.project_statuses:
            if project_status.status == ProcessingStatus.COMPLETED:
                stats.successful_projects += 1

                if project_status.processing_time:
                    stats.total_processing_time += project_status.processing_time

                if project_status.access_points_count:
                    stats.total_access_points += project_status.access_points_count

                if project_status.antennas_count:
                    stats.total_antennas += project_status.antennas_count

                # Load project BOM data and aggregate by vendor/model
                try:
                    project_dir = self.storage.projects_dir / str(project_status.project_id)
                    reports_dir = project_dir / "reports"

                    if not reports_dir.exists():
                        continue

                    # Try JSON first (new projects with JSON format)
                    json_report_path = reports_dir / "bom_report.json"
                    if json_report_path.exists():
                        import json

                        with open(json_report_path, "r", encoding="utf-8") as f:
                            bom_data = json.load(f)

                        # Aggregate access points by vendor|model
                        for ap in bom_data.get("access_points", []):
                            vendor = ap.get("vendor", "Unknown")
                            model = ap.get("model", "Unknown")
                            quantity = ap.get("quantity", 1)
                            vendor_model = f"{vendor}|{model}"
                            ap_by_vendor_model[vendor_model] += quantity

                        # Aggregate antennas by model
                        for antenna in bom_data.get("antennas", []):
                            model = antenna.get("model", "Unknown")
                            quantity = antenna.get("quantity", 1)
                            antenna_by_model[model] += quantity

                    else:
                        # Fallback to CSV (old projects without JSON)
                        import csv

                        # Find access points CSV file (format: projectname_access_points.csv)
                        csv_files = list(reports_dir.glob("*_access_points.csv"))

                        if csv_files:
                            csv_path = csv_files[0]  # Use first match

                            with open(csv_path, "r", encoding="utf-8") as f:
                                # Skip comment lines starting with #
                                lines = [line for line in f if not line.startswith("#")]
                                reader = csv.DictReader(lines)

                                for row in reader:
                                    vendor = row.get("Vendor", "Unknown").strip('"')
                                    model = row.get("Model", "Unknown").strip('"')
                                    quantity = int(row.get("Quantity", "1").strip('"'))
                                    vendor_model = f"{vendor}|{model}"
                                    ap_by_vendor_model[vendor_model] += quantity

                        # Find antennas CSV file (format: projectname_antennas.csv)
                        antenna_csv_files = list(reports_dir.glob("*_antennas.csv"))

                        if antenna_csv_files:
                            antenna_csv_path = antenna_csv_files[0]

                            with open(antenna_csv_path, "r", encoding="utf-8") as f:
                                # Skip comment lines
                                lines = [line for line in f if not line.startswith("#")]
                                reader = csv.DictReader(lines)

                                for row in reader:
                                    model = row.get("Model", "Unknown").strip('"')
                                    quantity = int(row.get("Quantity", "1").strip('"'))
                                    antenna_by_model[model] += quantity

                except Exception as e:
                    logger.warning(
                        f"Failed to load BOM data for project {project_status.project_id}: {e}"
                    )

            elif project_status.status == ProcessingStatus.FAILED:
                stats.failed_projects += 1

        # Convert defaultdict to regular dict for Pydantic model
        stats.ap_by_vendor_model = dict(ap_by_vendor_model)
        stats.antenna_by_model = dict(antenna_by_model)

        return stats

    def create_batch_archive(self, batch_id: UUID) -> Path:
        """Create a ZIP archive with all batch projects and their files.

        Args:
            batch_id: Batch UUID

        Returns:
            Path to created ZIP file

        Raises:
            FileNotFoundError: If batch not found
        """
        import shutil
        import tempfile
        import zipfile

        # Load batch metadata
        metadata = self.load_batch_metadata(batch_id)
        if not metadata:
            raise FileNotFoundError(f"Batch {batch_id} not found")

        # Create temporary directory for ZIP
        temp_dir = Path(tempfile.mkdtemp())
        zip_filename = f"batch_{metadata.batch_name}_{batch_id}.zip"
        zip_path = temp_dir / zip_filename

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Add batch summary
                summary_content = self._generate_batch_summary(metadata)
                zipf.writestr("batch_summary.txt", summary_content)

                # Add each project's files
                for project_id in metadata.project_ids:
                    # project_id is already a UUID object
                    project_metadata = self.storage.load_metadata(project_id)

                    if not project_metadata:
                        logger.warning(f"Project {project_id} metadata not found, skipping")
                        continue

                    # Create project folder name (sanitize for filesystem)
                    project_name = (
                        (project_metadata.project_name or f"project_{project_id}")
                        .replace("/", "_")
                        .replace("\\", "_")
                    )
                    project_folder = f"{project_name}/"

                    # Add original .esx file
                    original_file = self.storage.projects_dir / str(project_id) / "original.esx"
                    if original_file.exists():
                        zipf.write(original_file, f"{project_folder}{project_metadata.filename}")

                    # Add reports directory
                    reports_dir = self.storage.projects_dir / str(project_id) / "reports"
                    if reports_dir.exists():
                        for report_file in reports_dir.rglob("*"):
                            if report_file.is_file():
                                rel_path = report_file.relative_to(
                                    self.storage.projects_dir / str(project_id)
                                )
                                zipf.write(report_file, f"{project_folder}{rel_path}")

                    # Add visualizations directory
                    viz_dir = (
                        self.storage.projects_dir / str(project_id) / "reports" / "visualizations"
                    )
                    if viz_dir.exists():
                        for viz_file in viz_dir.rglob("*"):
                            if viz_file.is_file():
                                rel_path = viz_file.relative_to(
                                    self.storage.projects_dir / str(project_id)
                                )
                                zipf.write(viz_file, f"{project_folder}{rel_path}")

            logger.info(f"Created batch archive: {zip_path} ({zip_path.stat().st_size} bytes)")
            return zip_path

        except Exception as e:
            # Cleanup on error
            if zip_path.exists():
                zip_path.unlink()
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            logger.error(f"Failed to create batch archive for {batch_id}: {e}")
            raise

    def _generate_batch_summary(self, metadata: BatchMetadata) -> str:
        """Generate batch summary text.

        Args:
            metadata: Batch metadata

        Returns:
            Summary text
        """
        lines = [
            "=" * 80,
            f"BATCH SUMMARY: {metadata.batch_name}",
            "=" * 80,
            "",
            f"Batch ID: {metadata.batch_id}",
            f"Created: {metadata.created_date}",
            f"Created By: {metadata.created_by}",
            f"Status: {metadata.status}",
            "",
            "STATISTICS:",
            f"  Total Projects: {metadata.statistics.total_projects}",
            f"  Successful: {metadata.statistics.successful_projects}",
            f"  Failed: {metadata.statistics.failed_projects}",
            f"  Total Access Points: {metadata.statistics.total_access_points}",
            f"  Total Antennas: {metadata.statistics.total_antennas}",
            f"  Total Processing Time: {metadata.statistics.total_processing_time:.2f}s",
            "",
            "PROCESSING OPTIONS:",
            f"  Group By: {metadata.processing_options.group_by}",
            f"  Output Formats: {', '.join(metadata.processing_options.output_formats)}",
            f"  Visualize Floor Plans: {metadata.processing_options.visualize_floor_plans}",
            f"  Show Azimuth Arrows: {metadata.processing_options.show_azimuth_arrows}",
            f"  AP Opacity: {metadata.processing_options.ap_opacity * 100:.0f}%",
            "",
            "PROJECTS:",
        ]

        # Add project details
        for i, project_status in enumerate(metadata.project_statuses, 1):
            lines.append(f"\n{i}. {project_status.filename}")
            lines.append(f"   Project ID: {project_status.project_id}")
            lines.append(f"   Status: {project_status.status}")
            if project_status.processing_time:
                lines.append(f"   Processing Time: {project_status.processing_time:.2f}s")
            if project_status.access_points_count:
                lines.append(f"   Access Points: {project_status.access_points_count}")
            if project_status.antennas_count:
                lines.append(f"   Antennas: {project_status.antennas_count}")
            if project_status.error_message:
                lines.append(f"   Error: {project_status.error_message}")

        lines.append("")
        lines.append("=" * 80)
        lines.append("Generated by Ekahau BOM Web")
        lines.append("=" * 80)

        return "\n".join(lines)

    def delete_batch(self, batch_id: UUID) -> bool:
        """Delete a batch and all its data.

        Args:
            batch_id: Batch UUID

        Returns:
            True if deleted, False if not found
        """
        batch_dir = self._get_batch_dir(batch_id)
        if not batch_dir.exists():
            return False

        try:
            import shutil

            shutil.rmtree(batch_dir)
            logger.info(f"Deleted batch {batch_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete batch {batch_id}: {e}")
            raise


# Singleton instance
batch_service = BatchService()
