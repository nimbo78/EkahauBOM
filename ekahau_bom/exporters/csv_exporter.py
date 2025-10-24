#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""CSV exporter for project data."""

import csv
import logging
from collections import Counter
from pathlib import Path

from .base import BaseExporter
from ..models import ProjectData, AccessPoint, Antenna

logger = logging.getLogger(__name__)


class CSVExporter(BaseExporter):
    """Export project data to CSV files.

    Creates two CSV files:
    - {project_name}_access_points.csv: Access points with vendor, model, floor, color, quantity
    - {project_name}_antennas.csv: Antennas with model and quantity
    """

    @property
    def format_name(self) -> str:
        """Human-readable name of the export format."""
        return "CSV"

    def export(self, project_data: ProjectData) -> list[Path]:
        """Export project data to CSV files.

        Args:
            project_data: Processed project data to export

        Returns:
            List of paths to created CSV files

        Raises:
            IOError: If file writing fails
        """
        files = []

        # Export access points
        ap_file = self._export_access_points(
            project_data.access_points,
            project_data.project_name
        )
        files.append(ap_file)

        # Export antennas
        antenna_file = self._export_antennas(
            project_data.antennas,
            project_data.project_name
        )
        files.append(antenna_file)

        self.log_export_success(files)
        return files

    def _export_access_points(
        self,
        access_points: list[AccessPoint],
        project_name: str
    ) -> Path:
        """Export access points to CSV file.

        Args:
            access_points: List of access points to export
            project_name: Name of the project

        Returns:
            Path to created CSV file
        """
        output_file = self._get_output_filename(project_name, "access_points.csv")

        # Count occurrences of each unique AP configuration
        # Create tuples for counting: (vendor, model, floor, color)
        ap_tuples = [
            (ap.vendor, ap.model, ap.floor_name, ap.color)
            for ap in access_points
        ]
        ap_counts = Counter(ap_tuples)

        logger.info(f"Exporting {len(access_points)} access points ({len(ap_counts)} unique)")

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, dialect='excel', quoting=csv.QUOTE_ALL)

            # Write header
            writer.writerow(["Vendor", "Model", "Floor", "Color", "Quantity"])

            # Write data rows
            for (vendor, model, floor, color), count in ap_counts.items():
                writer.writerow([vendor, model, floor, color or "", count])

        logger.debug(f"Access points exported to {output_file}")
        return output_file

    def _export_antennas(
        self,
        antennas: list[Antenna],
        project_name: str
    ) -> Path:
        """Export antennas to CSV file.

        Args:
            antennas: List of antennas to export
            project_name: Name of the project

        Returns:
            Path to created CSV file
        """
        output_file = self._get_output_filename(project_name, "antennas.csv")

        # Count occurrences of each antenna type
        antenna_names = [antenna.name for antenna in antennas]
        antenna_counts = Counter(antenna_names)

        logger.info(f"Exporting {len(antennas)} antennas ({len(antenna_counts)} unique)")

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, dialect='excel', quoting=csv.QUOTE_ALL)

            # Write header
            writer.writerow(["Antenna Model", "Quantity"])

            # Write data rows
            for antenna_name, count in antenna_counts.items():
                writer.writerow([antenna_name, count])

        logger.debug(f"Antennas exported to {output_file}")
        return output_file
