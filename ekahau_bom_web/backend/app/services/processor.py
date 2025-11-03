"""Processor Service - Integration with EkahauBOM CLI."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from app.models import ProcessingStatus, ProjectMetadata
from app.services.index import index_service
from app.services.storage import StorageService

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
    ) -> None:
        """Process .esx file using EkahauBOM CLI.

        Args:
            project_id: Project UUID
            group_by: Group APs by dimension ('model', 'floor', 'color', 'vendor', 'tag', or None)
            output_formats: List of output formats (csv, excel, html, json, pdf)
            visualize_floor_plans: Generate floor plan visualizations
            show_azimuth_arrows: Show azimuth direction arrows on AP markers
            ap_opacity: Opacity for AP markers (0.0-1.0, default 0.6)
        """
        if output_formats is None:
            output_formats = ["csv", "excel", "html"]

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
                await self._extract_project_metadata(
                    project_id, original_file, metadata
                )

                # Extract summary from JSON report if available
                await self._extract_report_summary(project_id, reports_dir, metadata)

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

    def _build_command(
        self,
        original_file: Path,
        output_dir: Path,
        group_by: str | None,
        output_formats: list[str],
        visualize_floor_plans: bool,
        show_azimuth_arrows: bool,
        ap_opacity: float,
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
                    metadata.project_name = project_info.get(
                        "title"
                    ) or project_info.get("name")

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
