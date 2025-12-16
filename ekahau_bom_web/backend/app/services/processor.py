"""Processor Service - Integration with EkahauBOM CLI."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from app.models import ProcessingStatus, ProjectMetadata
from app.services.cache import cache_service
from app.services.index import index_service
from app.services.storage_service import StorageService
from app.utils.thumbnails import generate_all_thumbnails
from app.websocket import connection_manager

logger = logging.getLogger(__name__)


class ProcessorService:
    """Service for processing .esx files using EkahauBOM CLI."""

    def __init__(self, storage: StorageService):
        self.storage = storage

    async def process_project(
        self,
        project_id: UUID,
        group_by: str | None = "model",
        output_formats: list[str] = None,
        visualize_floor_plans: bool = True,
        show_azimuth_arrows: bool = False,
        ap_opacity: float = 0.6,
        include_text_notes: bool = False,
        include_picture_notes: bool = False,
        include_cable_notes: bool = False,
    ) -> None:
        """Process .esx file using EkahauBOM CLI.

        Args:
            project_id: Project UUID
            group_by: Group APs by dimension ('model', 'floor', 'color', 'vendor', 'tag', or None)
            output_formats: List of output formats (csv, excel, html, json, pdf)
            visualize_floor_plans: Generate floor plan visualizations
            show_azimuth_arrows: Show azimuth direction arrows on AP markers
            ap_opacity: Opacity for AP markers (0.0-1.0, default 0.6)
            include_text_notes: Include text notes on floor plan visualizations
            include_picture_notes: Include picture note markers on floor plan visualizations
            include_cable_notes: Include cable routing paths on floor plan visualizations
        """
        if output_formats is None:
            output_formats = ["csv", "excel", "html", "json"]  # Added json for BOM aggregation

        # Load metadata
        metadata = self.storage.load_metadata(project_id)
        if not metadata:
            raise ValueError(f"Project {project_id} not found")

        # Update status to processing
        metadata.processing_status = ProcessingStatus.PROCESSING
        metadata.processing_started = datetime.now(UTC)
        metadata.processing_error = None
        self.storage.save_metadata(project_id, metadata)
        index_service.add(metadata)
        index_service.save_to_disk()

        try:
            # Get file paths
            project_dir = self.storage.get_project_dir(project_id)
            original_file = project_dir / "original.esx"
            reports_dir = self.storage.get_reports_dir(project_id)
            visualizations_dir = self.storage.get_visualizations_dir(project_id)

            # Create output directories
            reports_dir.mkdir(parents=True, exist_ok=True)
            visualizations_dir.mkdir(parents=True, exist_ok=True)

            # Create temporary file with original filename for correct report naming
            # EkahauBOM CLI uses input filename for output, so "original.esx" -> "original_original.xlsx"
            # To fix, temporarily copy to correct filename
            import shutil

            temp_file = project_dir / metadata.filename
            shutil.copy2(original_file, temp_file)

            try:
                # Build command with temp file
                cmd = self._build_command(
                    original_file=temp_file,
                    output_dir=reports_dir,
                    group_by=group_by,
                    output_formats=output_formats,
                    visualize_floor_plans=visualize_floor_plans,
                    show_azimuth_arrows=show_azimuth_arrows,
                    ap_opacity=ap_opacity,
                    include_text_notes=include_text_notes,
                    include_picture_notes=include_picture_notes,
                    include_cable_notes=include_cable_notes,
                    project_name=metadata.project_name,
                )

                logger.info(f"Processing project {project_id}: {' '.join(cmd)}")

                # Run EkahauBOM CLI (using sync subprocess wrapped in asyncio.to_thread for Windows compatibility)
                def run_subprocess():
                    return subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False,
                    )

                result = await asyncio.to_thread(run_subprocess)

                if result.returncode != 0:
                    error_msg = (
                        result.stderr.decode("utf-8", errors="replace")
                        if result.stderr
                        else "Unknown error"
                    )
                    logger.error(f"Processing failed for {project_id}: {error_msg}")
                    raise RuntimeError(f"EkahauBOM processing failed: {error_msg}")

                # Log stdout for debugging
                if result.stdout:
                    logger.info(
                        f"EkahauBOM output: {result.stdout.decode('utf-8', errors='replace')}"
                    )

                # Extract metadata from project if possible
                await self._extract_project_metadata(project_id, original_file, metadata)

                # Extract summary from JSON report if available
                await self._extract_report_summary(project_id, reports_dir, metadata)

                # Generate thumbnails for floor plan visualizations
                if visualize_floor_plans:
                    await self._generate_thumbnails(project_id, visualizations_dir)

                # Run comparison if previous.esx exists
                previous_file = project_dir / "previous.esx"
                if previous_file.exists():
                    await self._run_comparison(project_id, previous_file, original_file)

                # Update metadata
                metadata.processing_status = ProcessingStatus.COMPLETED
                metadata.processing_completed = datetime.now(UTC)
                metadata.reports_dir = str(reports_dir.relative_to(project_dir.parent))
                if visualize_floor_plans:
                    metadata.visualizations_dir = str(
                        visualizations_dir.relative_to(project_dir.parent)
                    )

                # Store processing flags
                metadata.processing_flags = {
                    "group_by": group_by,
                    "output_formats": output_formats,
                    "visualize_floor_plans": visualize_floor_plans,
                    "show_azimuth_arrows": show_azimuth_arrows,
                    "ap_opacity": ap_opacity,
                    "include_text_notes": include_text_notes,
                    "include_picture_notes": include_picture_notes,
                    "include_cable_notes": include_cable_notes,
                }

                logger.info(f"Processing completed for {project_id}")

            finally:
                # Clean up temporary file
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Removed temporary file: {temp_file}")

        except Exception as e:
            logger.exception(f"Error processing {project_id}")
            metadata.processing_status = ProcessingStatus.FAILED
            metadata.processing_error = str(e)

        finally:
            # Save final metadata
            self.storage.save_metadata(project_id, metadata)
            index_service.add(metadata)
            index_service.save_to_disk()

            # Invalidate cache (project processed/updated)
            cache_service.invalidate_project(project_id)

    def _build_command(
        self,
        original_file: Path,
        output_dir: Path,
        group_by: str | None,
        output_formats: list[str],
        visualize_floor_plans: bool,
        show_azimuth_arrows: bool,
        ap_opacity: float,
        include_text_notes: bool,
        include_picture_notes: bool,
        include_cable_notes: bool,
        project_name: str | None = None,
    ) -> list[str]:
        """Build EkahauBOM CLI command."""
        cmd = [sys.executable, "-m", "ekahau_bom", str(original_file)]

        # Output directory
        cmd.extend(["--output-dir", str(output_dir)])

        # Project name (use extracted title from .esx instead of filename)
        if project_name:
            cmd.extend(["--project-name", project_name])

        # Group APs by specified dimension
        if group_by:
            cmd.extend(["--group-by", group_by])

        # Output formats (combine into comma-separated string)
        if output_formats:
            format_str = ",".join(output_formats)
            cmd.extend(["--format", format_str])

        # Floor plan visualizations
        if visualize_floor_plans:
            cmd.append("--visualize-floor-plans")

            # Azimuth arrows (only if visualizations enabled)
            if show_azimuth_arrows:
                cmd.append("--show-azimuth-arrows")

            # AP opacity (only if visualizations enabled)
            if ap_opacity != 0.6:  # Only add if not default
                cmd.extend(["--ap-opacity", str(ap_opacity)])

            # Notes on floor plans (only if visualizations enabled)
            if include_text_notes:
                cmd.append("--include-text-notes")

            if include_picture_notes:
                cmd.append("--include-picture-notes")

            if include_cable_notes:
                cmd.append("--include-cable-notes")

        return cmd

    async def _extract_project_metadata(
        self, project_id: UUID, esx_file: Path, metadata: ProjectMetadata
    ) -> None:
        """Extract project metadata from .esx file (counts of buildings, floors, APs).

        Parses the .esx ZIP archive to extract project information.
        """
        try:
            import json
            import zipfile

            with zipfile.ZipFile(esx_file, "r") as zf:
                # Extract project name and metadata
                if "project.json" in zf.namelist():
                    project_data = json.loads(zf.read("project.json"))
                    # Project data is nested under "project" key
                    project_info = project_data.get("project", {})
                    # Try 'title' first (user-friendly name), then fall back to 'name'
                    metadata.project_name = project_info.get("title") or project_info.get("name")

                    # Extract project details
                    metadata.customer = project_info.get("customer")
                    metadata.location = project_info.get("location")
                    metadata.responsible_person = project_info.get("responsiblePerson")

                # Count access points
                if "accessPoints.json" in zf.namelist():
                    aps_data = json.loads(zf.read("accessPoints.json"))
                    metadata.aps_count = len(aps_data.get("accessPoints", []))

                # Count floors
                if "floorPlans.json" in zf.namelist():
                    floors_data = json.loads(zf.read("floorPlans.json"))
                    metadata.floors_count = len(floors_data.get("floorPlans", []))

                # Count buildings (if available)
                if "buildings.json" in zf.namelist():
                    buildings_data = json.loads(zf.read("buildings.json"))
                    metadata.buildings_count = len(buildings_data.get("buildings", []))

        except Exception as e:
            logger.warning(f"Could not extract metadata for {project_id}: {e}")

    async def _extract_report_summary(
        self, project_id: UUID, reports_dir: Path, metadata: ProjectMetadata
    ) -> None:
        """Extract summary data from JSON report.

        Reads the generated JSON report to extract:
        - total_antennas
        - unique_vendors
        - unique_colors
        - vendors list
        - floors list
        """
        try:
            import json

            # Find JSON report file (should be {project_name}_data.json)
            json_files = list(reports_dir.glob("*_data.json"))
            if not json_files:
                logger.debug(f"No JSON report found for {project_id}")
                return

            json_file = json_files[0]
            with open(json_file, "r", encoding="utf-8") as f:
                report_data = json.load(f)

            # Extract summary data
            summary = report_data.get("summary", {})
            metadata.total_antennas = summary.get("total_antennas")
            metadata.unique_vendors = summary.get("unique_vendors")
            metadata.unique_colors = summary.get("unique_colors")

            # Extract vendors from bill_of_materials
            bom = report_data.get("access_points", {}).get("bill_of_materials", [])
            vendors = sorted(set(item["vendor"] for item in bom if "vendor" in item))
            metadata.vendors = vendors if vendors else None

            # Extract floor names
            floors_data = report_data.get("floors", [])
            floors = [floor["name"] for floor in floors_data if "name" in floor]
            metadata.floors = floors if floors else None

            logger.debug(f"Extracted summary for {project_id}: {summary}")

        except Exception as e:
            logger.warning(f"Could not extract report summary for {project_id}: {e}")

    async def _generate_thumbnails(self, project_id: UUID, visualizations_dir: Path) -> None:
        """Generate thumbnails for all floor plan PNG visualizations.

        Creates small (200x150) and medium (800x600) thumbnails for each PNG file
        in the visualizations directory.

        Args:
            project_id: Project UUID
            visualizations_dir: Directory containing PNG visualizations
        """
        try:
            # Find all PNG files
            png_files = list(visualizations_dir.glob("*.png"))
            if not png_files:
                logger.debug(f"No PNG visualizations found for {project_id}")
                return

            # Create thumbs directory
            thumbs_dir = visualizations_dir / "thumbs"
            thumbs_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Generating thumbnails for {len(png_files)} visualizations...")

            # Generate thumbnails for each PNG file
            thumbnail_count = 0
            for png_file in png_files:
                try:
                    # Run thumbnail generation in thread pool to avoid blocking
                    def generate_thumbs():
                        return generate_all_thumbnails(png_file, thumbs_dir)

                    thumbs = await asyncio.to_thread(generate_thumbs)
                    thumbnail_count += len(thumbs)
                    logger.debug(f"Generated thumbnails for {png_file.name}: {list(thumbs.keys())}")

                except Exception as e:
                    logger.error(f"Failed to generate thumbnails for {png_file.name}: {e}")
                    # Continue with other files even if one fails

            logger.info(f"Generated {thumbnail_count} thumbnails for project {project_id}")

        except Exception as e:
            logger.error(f"Error generating thumbnails for {project_id}: {e}")
            # Don't fail the entire processing if thumbnail generation fails

    async def cancel_processing(self, project_id: UUID) -> None:
        """Cancel ongoing processing (if possible).

        Note: This is a simplified version. Full implementation would track
        running processes and send termination signals.
        """
        metadata = self.storage.load_metadata(project_id)
        if metadata and metadata.processing_status == ProcessingStatus.PROCESSING:
            metadata.processing_status = ProcessingStatus.FAILED
            metadata.processing_error = "Processing cancelled by user"
            self.storage.save_metadata(project_id, metadata)
            index_service.add(metadata)
            index_service.save_to_disk()

    async def _run_comparison(self, project_id: UUID, old_file: Path, new_file: Path) -> None:
        """Run comparison between two .esx files and save results.

        Args:
            project_id: Project UUID
            old_file: Path to previous .esx file
            new_file: Path to current .esx file
        """
        try:
            logger.info(f"Running comparison for project {project_id}")

            # Import comparison engine
            from ekahau_bom.comparison.engine import ComparisonEngine
            from ekahau_bom.comparison.visual_diff import VisualDiffGenerator

            # Run comparison in thread pool
            def run_comparison():
                engine = ComparisonEngine()
                return engine.compare_files(old_file, new_file)

            result = await asyncio.to_thread(run_comparison)

            # Create comparison directory
            project_dir = self.storage.get_project_dir(project_id)
            comparison_dir = project_dir / "comparison"
            comparison_dir.mkdir(parents=True, exist_ok=True)

            # Convert result to JSON-serializable format
            comparison_data = {
                "project_a_name": result.project_a_name,
                "project_b_name": result.project_b_name,
                "project_a_filename": result.project_a_filename,
                "project_b_filename": result.project_b_filename,
                "comparison_timestamp": result.comparison_timestamp.isoformat(),
                "total_changes": result.total_changes,
                "has_changes": result.total_changes > 0,
                "inventory": {
                    "old_total_aps": result.inventory_change.old_total_aps,
                    "new_total_aps": result.inventory_change.new_total_aps,
                    "aps_added": result.inventory_change.aps_added,
                    "aps_removed": result.inventory_change.aps_removed,
                    "aps_modified": result.inventory_change.aps_modified,
                    "aps_moved": result.inventory_change.aps_moved,
                    "aps_renamed": result.inventory_change.aps_renamed,
                    "aps_unchanged": result.inventory_change.aps_unchanged,
                },
                "metadata_change": None,
                "ap_changes": [],
                "changes_by_floor": {},
                "floors": result.floors,
                "diff_images": {},
            }

            # Convert metadata change if present
            if result.metadata_change:
                comparison_data["metadata_change"] = {
                    "old_name": result.metadata_change.old_name,
                    "new_name": result.metadata_change.new_name,
                    "old_customer": result.metadata_change.old_customer,
                    "new_customer": result.metadata_change.new_customer,
                    "old_location": result.metadata_change.old_location,
                    "new_location": result.metadata_change.new_location,
                    "changes": [
                        {
                            "field_name": c.field_name,
                            "category": c.category,
                            "old_value": c.old_value,
                            "new_value": c.new_value,
                        }
                        for c in result.metadata_change.changed_fields
                    ],
                }

            # Convert AP changes
            for ap_change in result.ap_changes:
                change_dict = {
                    "status": ap_change.status.value,
                    "ap_name": ap_change.ap_name,
                    "floor_name": ap_change.floor_name,
                    "old_name": ap_change.old_name,
                    "new_name": ap_change.new_name,
                    "distance_moved": ap_change.distance_moved,
                    "old_coords": ap_change.old_coords,
                    "new_coords": ap_change.new_coords,
                    "changes": [
                        {
                            "field_name": c.field_name,
                            "category": c.category,
                            "old_value": str(c.old_value) if c.old_value is not None else None,
                            "new_value": str(c.new_value) if c.new_value is not None else None,
                        }
                        for c in (ap_change.changes or [])
                    ],
                }
                comparison_data["ap_changes"].append(change_dict)

            # Group changes by floor
            for floor, changes in result.changes_by_floor.items():
                comparison_data["changes_by_floor"][floor] = [
                    {
                        "status": c.status.value,
                        "ap_name": c.ap_name,
                        "floor_name": c.floor_name,
                        "old_name": c.old_name,
                        "new_name": c.new_name,
                        "distance_moved": c.distance_moved,
                        "old_coords": c.old_coords,
                        "new_coords": c.new_coords,
                        "changes": [
                            {
                                "field_name": fc.field_name,
                                "category": fc.category,
                                "old_value": (
                                    str(fc.old_value) if fc.old_value is not None else None
                                ),
                                "new_value": (
                                    str(fc.new_value) if fc.new_value is not None else None
                                ),
                            }
                            for fc in (c.changes or [])
                        ],
                    }
                    for c in changes
                ]

            # Generate visual diff images
            visualizations_dir = comparison_dir / "visualizations"
            visualizations_dir.mkdir(parents=True, exist_ok=True)

            def generate_visual_diffs():
                diff_images = {}
                try:
                    with VisualDiffGenerator(old_file, new_file) as diff_generator:
                        generated = diff_generator.generate_all_diffs(result, visualizations_dir)
                        # Convert Path to string for JSON serialization
                        diff_images = {floor: path.name for floor, path in generated.items()}
                except Exception as e:
                    logger.warning(f"Failed to generate visual diffs: {e}")
                return diff_images

            diff_images = await asyncio.to_thread(generate_visual_diffs)
            comparison_data["diff_images"] = diff_images

            # Save comparison data
            comparison_file = comparison_dir / "comparison_data.json"
            with open(comparison_file, "w", encoding="utf-8") as f:
                json.dump(comparison_data, f, indent=2, ensure_ascii=False)

            # Generate comparison reports (CSV, HTML, JSON)
            def generate_reports():
                from ekahau_bom.comparison.exporters import export_comparison

                # Build diff_images dict with full paths for embedding in HTML
                diff_images_paths = {}
                if diff_images:
                    for floor_name, filename in diff_images.items():
                        img_path = visualizations_dir / filename
                        if img_path.exists():
                            diff_images_paths[floor_name] = img_path

                return export_comparison(
                    comparison=result,
                    output_dir=comparison_dir,
                    formats=["csv", "html", "json"],
                    project_name=result.project_b_name or "comparison",
                    diff_images=diff_images_paths if diff_images_paths else None,
                )

            try:
                report_paths = await asyncio.to_thread(generate_reports)
                logger.info(f"Generated comparison reports: {list(report_paths.keys())}")
            except Exception as report_err:
                logger.warning(f"Failed to generate comparison reports: {report_err}")

            logger.info(
                f"Comparison completed for {project_id}: "
                f"{result.total_changes} changes detected"
            )

        except Exception as e:
            logger.error(f"Error running comparison for {project_id}: {e}")
            # Don't fail processing if comparison fails
