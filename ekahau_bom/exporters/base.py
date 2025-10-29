#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Base class for exporters."""

from __future__ import annotations


import logging
import re
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from pathlib import Path

from ..models import AccessPoint, Antenna, ProjectData, Radio

logger = logging.getLogger(__name__)


class BaseExporter(ABC):
    """Abstract base class for all exporters.

    Exporters are responsible for converting ProjectData into various
    output formats (CSV, Excel, HTML, JSON, etc.).
    """

    def __init__(self, output_dir: Path):
        """Initialize exporter with output directory.

        Args:
            output_dir: Directory where export files will be saved
        """
        self.output_dir = Path(output_dir)

    @abstractmethod
    def export(self, project_data: ProjectData) -> list[Path]:
        """Export project data to one or more files.

        Args:
            project_data: Processed project data to export

        Returns:
            List of paths to created files

        Raises:
            IOError: If export fails
        """
        pass

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Human-readable name of the export format."""
        pass

    def _sanitize_filename(self, filename: str) -> str:
        r"""Sanitize filename by removing invalid characters.

        Removes or replaces characters that are not allowed in filenames
        on Windows: < > : " / \ | ? *

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for all operating systems
        """
        # Replace invalid characters with underscore
        # Windows reserved: < > : " / \ | ? *
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)

        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip(". ")

        # Ensure filename is not empty
        if not sanitized:
            sanitized = "unnamed"

        return sanitized

    def _get_output_filename(self, project_name: str, suffix: str) -> Path:
        """Generate output filename.

        Args:
            project_name: Name of the project (base name)
            suffix: Type/category suffix (e.g., 'access_points', 'antennas')

        Returns:
            Full path to output file
        """
        # Sanitize project name to remove invalid filename characters
        safe_project_name = self._sanitize_filename(project_name)
        filename = f"{safe_project_name}_{suffix}"
        return self.output_dir / filename

    def log_export_success(self, files: list[Path]) -> None:
        """Log successful export.

        Args:
            files: List of exported files
        """
        logger.info(
            f"{self.format_name} export completed: {len(files)} file(s) created"
        )
        for file in files:
            logger.info(f"  - {file}")

    def _filter_and_group_antennas(self, antennas: list[Antenna]) -> Counter:
        """Filter and group antennas for BOM export.

        Only processes external antennas (those that need to be purchased separately).
        Integrated antennas are filtered out as they're built into the AP.

        For dual-band external antennas (same model on multiple frequency bands),
        aggregates them by AP + model number and counts physical antenna units
        based on max spatial streams.

        Args:
            antennas: List of all antennas

        Returns:
            Counter with antenna display names and quantities
        """
        # Filter to only external antennas (exclude integrated antennas)
        external_antennas = [ant for ant in antennas if ant.is_external]

        # Group dual-band antennas by (AP ID, antenna_model)
        # This aggregates 2.4GHz + 5GHz radios into physical antenna count
        antenna_groups = defaultdict(list)
        for ant in external_antennas:
            # Group by AP ID + antenna model (extracted from AP model)
            if ant.access_point_id and ant.antenna_model:
                key = (ant.access_point_id, ant.antenna_model)
                antenna_groups[key].append(ant)

        # Calculate physical antenna counts
        antenna_counts = Counter()

        for (ap_id, antenna_model), group_antennas in antenna_groups.items():
            # Get max spatial streams across all radios (determines physical antenna count)
            max_spatial_streams = max(
                ant.spatial_streams or 0 for ant in group_antennas
            )
            # Note: antenna_model is already the cleaned antenna name
            # extracted from AP model (part after " + ")

            # Create aggregated name for dual-band antennas
            if len(group_antennas) > 1:
                # Multiple radios (2.4GHz + 5GHz) = Dual-Band
                antenna_display_name = f"{antenna_model} Dual-Band"
            else:
                # Single radio = keep antenna model as-is
                antenna_display_name = antenna_model

            # Add quantity based on max spatial streams
            antenna_counts[antenna_display_name] += max_spatial_streams

        logger.debug(
            f"Filtered antennas: {len(external_antennas)} external, "
            f"{len(antenna_counts)} unique after dual-band aggregation, "
            f"filtered out {len(antennas) - len(external_antennas)} integrated"
        )

        return antenna_counts

    def _get_mounting_height(
        self, ap: AccessPoint, radios: list[Radio]
    ) -> float | None:
        """Get mounting height for an AP with fallback to radio antenna height.

        Attempts to get mounting height from AccessPoint.mounting_height first.
        If not available (None), falls back to antenna_height from the first
        radio associated with this AP.

        Args:
            ap: AccessPoint to get mounting height for
            radios: List of all radios to search for AP's radio

        Returns:
            Mounting height in meters, or None if not available from either source
        """
        # Try AP's mounting_height first
        if ap.mounting_height is not None:
            return ap.mounting_height

        # Fallback to radio's antenna_height
        for radio in radios:
            if radio.access_point_id == ap.id and radio.antenna_height is not None:
                return radio.antenna_height

        return None
