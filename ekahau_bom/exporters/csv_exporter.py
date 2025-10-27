#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""CSV exporter for project data."""

from __future__ import annotations


import csv
import logging
from collections import Counter
from pathlib import Path

from .base import BaseExporter
from ..models import ProjectData, AccessPoint, Antenna
from ..analytics import CoverageAnalytics, MountingAnalytics, RadioAnalytics

logger = logging.getLogger(__name__)


class CSVExporter(BaseExporter):
    """Export project data to CSV files.

    Creates two CSV files:
    - {project_name}_access_points.csv: Access points with vendor, model, floor, color, tags, quantity
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

        # Export access points BOM (aggregated)
        ap_file = self._export_access_points(
            project_data.access_points, project_data.project_name, project_data.metadata
        )
        files.append(ap_file)

        # Export detailed access points (individual with mounting data)
        detailed_ap_file = self._export_detailed_access_points(
            project_data.access_points, project_data.radios, project_data.project_name
        )
        files.append(detailed_ap_file)

        # Export antennas
        antenna_file = self._export_antennas(project_data.antennas, project_data.project_name)
        files.append(antenna_file)

        # Export analytics if data available
        analytics_file = self._export_analytics(
            project_data.access_points, project_data.radios, project_data.project_name
        )
        if analytics_file:
            files.append(analytics_file)

        self.log_export_success(files)
        return files

    def _export_access_points(
        self, access_points: list[AccessPoint], project_name: str, metadata=None
    ) -> Path:
        """Export access points to CSV file.

        Args:
            access_points: List of access points to export
            project_name: Name of the project
            metadata: Optional project metadata

        Returns:
            Path to created CSV file
        """
        output_file = self._get_output_filename(project_name, "access_points.csv")

        # Count occurrences of each unique AP configuration
        # Create tuples for counting: (vendor, model, floor, color, tags)
        # Tags are converted to frozenset for hashability
        ap_tuples = [
            (
                ap.vendor,
                ap.model,
                ap.floor_name,
                ap.color,
                frozenset(str(tag) for tag in ap.tags),
            )
            for ap in access_points
        ]
        ap_counts = Counter(ap_tuples)

        logger.info(f"Exporting {len(access_points)} access points ({len(ap_counts)} unique)")

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            # Write metadata as comments if available
            if metadata:
                f.write("# Ekahau BOM - Access Points Bill of Materials\n")
                if metadata.name:
                    f.write(f"# Project Name: {metadata.name}\n")
                if metadata.customer:
                    f.write(f"# Customer: {metadata.customer}\n")
                if metadata.location:
                    f.write(f"# Location: {metadata.location}\n")
                if metadata.responsible_person:
                    f.write(f"# Responsible Person: {metadata.responsible_person}\n")
                f.write("#\n")

            writer = csv.writer(f, dialect="excel", quoting=csv.QUOTE_ALL)

            # Write header
            writer.writerow(["Vendor", "Model", "Floor", "Color", "Tags", "Quantity"])

            # Write data rows
            for (vendor, model, floor, color, tags), count in ap_counts.items():
                # Format tags as "Key1:Value1; Key2:Value2"
                tags_str = "; ".join(sorted(tags)) if tags else ""
                writer.writerow([vendor, model, floor, color or "", tags_str, count])

        logger.debug(f"Access points exported to {output_file}")
        return output_file

    def _export_detailed_access_points(
        self, access_points: list[AccessPoint], radios: list, project_name: str
    ) -> Path:
        """Export detailed access points with installation parameters.

        Each row represents a single access point with all its properties including
        mounting height, azimuth, tilt, and location coordinates.

        Args:
            access_points: List of access points to export
            radios: List of radios (to get antenna_height)
            project_name: Name of the project

        Returns:
            Path to created CSV file
        """
        output_file = self._get_output_filename(project_name, "access_points_detailed.csv")

        logger.info(f"Exporting {len(access_points)} access points with detailed parameters")

        # Create AP ID -> Radio mapping for quick lookup of antenna height
        ap_radio_map = {}
        for radio in radios:
            if radio.access_point_id not in ap_radio_map:
                ap_radio_map[radio.access_point_id] = []
            ap_radio_map[radio.access_point_id].append(radio)

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, dialect="excel", quoting=csv.QUOTE_ALL)

            # Write header with all fields
            writer.writerow(
                [
                    "AP Name",
                    "Vendor",
                    "Model",
                    "Floor",
                    "Location X (m)",
                    "Location Y (m)",
                    "Mounting Height (m)",
                    "Azimuth (°)",
                    "Tilt (°)",
                    "Color",
                    "Tags",
                    "Enabled",
                ]
            )

            # Write data rows - one row per AP
            for ap in access_points:
                # Format tags as "Key1:Value1; Key2:Value2"
                tags_str = (
                    "; ".join(str(tag) for tag in sorted(ap.tags, key=lambda t: t.key))
                    if ap.tags
                    else ""
                )

                # Format numeric values with appropriate precision
                location_x = f"{ap.location_x:.2f}" if ap.location_x is not None else ""
                location_y = f"{ap.location_y:.2f}" if ap.location_y is not None else ""

                # Get mounting height from first radio's antenna_height (if available)
                mounting_height_value = ap.mounting_height
                if mounting_height_value is None and ap.id in ap_radio_map:
                    first_radio = ap_radio_map[ap.id][0]
                    mounting_height_value = first_radio.antenna_height

                mounting_height = (
                    f"{mounting_height_value:.2f}" if mounting_height_value is not None else ""
                )
                azimuth = f"{ap.azimuth:.1f}" if ap.azimuth is not None else ""
                tilt = f"{ap.tilt:.1f}" if ap.tilt is not None else ""

                writer.writerow(
                    [
                        ap.name or "",
                        ap.vendor,
                        ap.model,
                        ap.floor_name,
                        location_x,
                        location_y,
                        mounting_height,
                        azimuth,
                        tilt,
                        ap.color or "",
                        tags_str,
                        "Yes" if ap.enabled else "No",
                    ]
                )

        logger.debug(f"Detailed access points exported to {output_file}")
        return output_file

    def _export_antennas(self, antennas: list[Antenna], project_name: str) -> Path:
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

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, dialect="excel", quoting=csv.QUOTE_ALL)

            # Write header
            writer.writerow(["Antenna Model", "Quantity"])

            # Write data rows
            for antenna_name, count in antenna_counts.items():
                writer.writerow([antenna_name, count])

        logger.debug(f"Antennas exported to {output_file}")
        return output_file

    def _export_analytics(
        self, access_points: list[AccessPoint], radios: list, project_name: str
    ) -> Path | None:
        """Export analytics metrics to CSV file.

        Args:
            access_points: List of access points
            radios: List of radios
            project_name: Name of the project

        Returns:
            Path to created CSV file, or None if no analytics data available
        """
        # Check if there's any analytics data to export
        has_height_data = any(ap.mounting_height is not None for ap in access_points)
        has_radio_data = len(radios) > 0

        if not has_height_data and not has_radio_data:
            logger.debug("No analytics data to export")
            return None

        output_file = self._get_output_filename(project_name, "analytics.csv")

        # Calculate metrics
        mounting_metrics = MountingAnalytics.calculate_mounting_metrics(access_points)
        height_distribution = MountingAnalytics.group_by_height_range(access_points)

        logger.info(f"Exporting analytics metrics")

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, dialect="excel", quoting=csv.QUOTE_ALL)

            # Mounting Metrics Section
            writer.writerow(["=== MOUNTING METRICS ==="])
            writer.writerow([])

            writer.writerow(["Metric", "Value", "Unit"])

            if mounting_metrics.avg_height is not None:
                writer.writerow(
                    [
                        "Average Mounting Height",
                        f"{mounting_metrics.avg_height:.2f}",
                        "meters",
                    ]
                )
                writer.writerow(["Minimum Height", f"{mounting_metrics.min_height:.2f}", "meters"])
                writer.writerow(["Maximum Height", f"{mounting_metrics.max_height:.2f}", "meters"])
                writer.writerow(
                    ["Height Variance", f"{mounting_metrics.height_variance:.4f}", "m²"]
                )

            writer.writerow(["APs with Height Data", mounting_metrics.aps_with_height, "count"])

            if mounting_metrics.avg_azimuth is not None:
                writer.writerow(
                    [
                        "Average Azimuth",
                        f"{mounting_metrics.avg_azimuth:.1f}",
                        "degrees",
                    ]
                )

            if mounting_metrics.avg_tilt is not None:
                writer.writerow(["Average Tilt", f"{mounting_metrics.avg_tilt:.1f}", "degrees"])

            # Height Distribution Section
            writer.writerow([])
            writer.writerow(["=== HEIGHT DISTRIBUTION ==="])
            writer.writerow([])
            writer.writerow(["Height Range", "AP Count"])

            for range_name in [
                "< 2.5m",
                "2.5-3.5m",
                "3.5-4.5m",
                "4.5-6.0m",
                "> 6.0m",
                "Unknown",
            ]:
                count = height_distribution.get(range_name, 0)
                if count > 0:
                    writer.writerow([range_name, count])

            # Installation Summary
            writer.writerow([])
            writer.writerow(["=== INSTALLATION SUMMARY ==="])
            writer.writerow([])

            aps_requiring_adjustment = sum(
                1
                for ap in access_points
                if ap.mounting_height and (ap.mounting_height < 2.5 or ap.mounting_height > 6.0)
            )

            writer.writerow(["Total APs", len(access_points)])
            writer.writerow(
                [
                    "APs with Tilt Data",
                    sum(1 for ap in access_points if ap.tilt is not None),
                ]
            )
            writer.writerow(
                [
                    "APs with Azimuth Data",
                    sum(1 for ap in access_points if ap.azimuth is not None),
                ]
            )
            writer.writerow(["APs Requiring Height Adjustment", aps_requiring_adjustment])

            # Radio Analytics Section
            if radios:
                radio_metrics = RadioAnalytics.calculate_radio_metrics(radios)

                writer.writerow([])
                writer.writerow(["=== RADIO CONFIGURATION ANALYTICS ==="])
                writer.writerow([])

                writer.writerow(["Metric", "Value", "Unit"])
                writer.writerow(["Total Radios", radio_metrics.total_radios, "count"])

                # Frequency Bands
                writer.writerow([])
                writer.writerow(["=== FREQUENCY BANDS ==="])
                writer.writerow([])
                writer.writerow(["Band", "Count", "Percentage"])
                for band, count in sorted(radio_metrics.band_distribution.items()):
                    percentage = (
                        (count / radio_metrics.total_radios * 100)
                        if radio_metrics.total_radios > 0
                        else 0
                    )
                    writer.writerow([band, count, f"{percentage:.1f}%"])

                # Wi-Fi Standards
                if radio_metrics.standard_distribution:
                    writer.writerow([])
                    writer.writerow(["=== WI-FI STANDARDS ==="])
                    writer.writerow([])
                    writer.writerow(["Standard", "Count", "Percentage"])
                    for standard, count in sorted(radio_metrics.standard_distribution.items()):
                        percentage = (
                            (count / radio_metrics.total_radios * 100)
                            if radio_metrics.total_radios > 0
                            else 0
                        )
                        writer.writerow([standard, count, f"{percentage:.1f}%"])

                # Channel Widths
                if radio_metrics.channel_width_distribution:
                    writer.writerow([])
                    writer.writerow(["=== CHANNEL WIDTHS ==="])
                    writer.writerow([])
                    writer.writerow(["Width", "Count"])
                    for width, count in sorted(radio_metrics.channel_width_distribution.items()):
                        writer.writerow([f"{width} MHz", count])

                # TX Power
                if radio_metrics.avg_tx_power:
                    writer.writerow([])
                    writer.writerow(["=== TRANSMIT POWER ==="])
                    writer.writerow([])
                    writer.writerow(["Metric", "Value", "Unit"])
                    writer.writerow(
                        ["Average TX Power", f"{radio_metrics.avg_tx_power:.1f}", "dBm"]
                    )
                    writer.writerow(
                        ["Minimum TX Power", f"{radio_metrics.min_tx_power:.1f}", "dBm"]
                    )
                    writer.writerow(
                        ["Maximum TX Power", f"{radio_metrics.max_tx_power:.1f}", "dBm"]
                    )

                # TX Power Distribution
                power_dist = RadioAnalytics.get_tx_power_distribution(radios)
                writer.writerow([])
                writer.writerow(["=== TX POWER DISTRIBUTION ==="])
                writer.writerow([])
                writer.writerow(["Power Range", "Count"])
                for range_label, count in power_dist.items():
                    if count > 0:
                        writer.writerow([range_label, count])

        logger.debug(f"Analytics exported to {output_file}")
        return output_file
