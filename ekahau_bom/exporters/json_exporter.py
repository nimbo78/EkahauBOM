#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""JSON exporter for machine-readable output and integrations."""

import json
import logging
from collections import Counter
from pathlib import Path

from .base import BaseExporter
from ..models import ProjectData, AccessPoint, Antenna, Tag, Floor
from ..analytics import GroupingAnalytics, CoverageAnalytics, MountingAnalytics, RadioAnalytics

logger = logging.getLogger(__name__)


class JSONExporter(BaseExporter):
    """Export project data to structured JSON format.

    Creates JSON output suitable for:
    - API integrations
    - Data processing pipelines
    - Import into other systems
    - Programmatic analysis

    Includes both raw data and analytics/grouping information.
    """

    def __init__(self, output_dir: Path, indent: int = 2):
        """Initialize JSON exporter.

        Args:
            output_dir: Directory where export files will be saved
            indent: Number of spaces for JSON indentation (None for compact)
        """
        super().__init__(output_dir)
        self.indent = indent

    @property
    def format_name(self) -> str:
        """Human-readable name of the export format."""
        return "JSON"

    def export(self, project_data: ProjectData) -> list[Path]:
        """Export project data to JSON file.

        Args:
            project_data: Processed project data to export

        Returns:
            List containing path to the created JSON file
        """
        output_file = self._get_output_filename(
            project_data.project_name,
            "data.json"
        )

        # Generate JSON structure
        json_data = self._generate_json_structure(project_data)

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=self.indent, ensure_ascii=False)

        files = [output_file]
        self.log_export_success(files)
        return files

    def _generate_json_structure(self, project_data: ProjectData) -> dict:
        """Generate complete JSON structure.

        Args:
            project_data: Project data to export

        Returns:
            Dictionary suitable for JSON serialization
        """
        # Count access points for BOM
        ap_counts = Counter()
        for ap in project_data.access_points:
            tags_tuple = tuple(sorted((tag.key, tag.value) for tag in ap.tags))
            key = (ap.vendor, ap.model, ap.floor_name, ap.color or "", tags_tuple)
            ap_counts[key] += 1

        # Count antennas
        antenna_counts = Counter(antenna.name for antenna in project_data.antennas)

        # Generate analytics
        analytics = GroupingAnalytics()
        by_vendor = analytics.group_by_dimension(project_data.access_points, "vendor")
        by_floor = analytics.group_by_dimension(project_data.access_points, "floor")
        by_color = analytics.group_by_dimension(project_data.access_points, "color")
        by_model = analytics.group_by_dimension(project_data.access_points, "model")

        # Calculate mounting metrics
        mounting_metrics = MountingAnalytics.calculate_mounting_metrics(project_data.access_points)
        height_distribution = MountingAnalytics.group_by_height_range(project_data.access_points)

        # Calculate radio metrics
        radio_metrics = None
        if project_data.radios:
            radio_metrics = RadioAnalytics.calculate_radio_metrics(project_data.radios)

        # Build metadata section
        metadata_section = {
            "file_name": project_data.project_name,
            "export_format": "json",
            "version": "2.3.0"
        }

        # Add project metadata if available
        if project_data.metadata:
            project_info = {}
            if project_data.metadata.name:
                project_info["project_name"] = project_data.metadata.name
            if project_data.metadata.customer:
                project_info["customer"] = project_data.metadata.customer
            if project_data.metadata.location:
                project_info["location"] = project_data.metadata.location
            if project_data.metadata.responsible_person:
                project_info["responsible_person"] = project_data.metadata.responsible_person
            if project_data.metadata.schema_version:
                project_info["schema_version"] = project_data.metadata.schema_version
            if project_data.metadata.note_ids:
                project_info["note_ids"] = project_data.metadata.note_ids
            if project_data.metadata.project_ancestors:
                project_info["project_ancestors"] = project_data.metadata.project_ancestors

            if project_info:
                metadata_section["project_info"] = project_info

        # Build JSON structure
        json_structure = {
            "metadata": metadata_section,
            "summary": {
                "total_access_points": len(project_data.access_points),
                "total_antennas": len(project_data.antennas),
                "unique_vendors": len(set(ap.vendor for ap in project_data.access_points)),
                "unique_floors": len(set(ap.floor_name for ap in project_data.access_points)),
                "unique_colors": len(set(ap.color for ap in project_data.access_points if ap.color)),
                "unique_models": len(set(ap.model for ap in project_data.access_points))
            },
            "floors": [
                {
                    "id": floor.id,
                    "name": floor.name
                }
                for floor in project_data.floors.values()
            ],
            "access_points": {
                "bill_of_materials": [
                    {
                        "vendor": vendor,
                        "model": model,
                        "floor": floor,
                        "color": color if color else None,
                        "tags": [
                            {"key": key, "value": value}
                            for key, value in sorted(tags_tuple)
                        ] if tags_tuple else [],
                        "quantity": count
                    }
                    for (vendor, model, floor, color, tags_tuple), count in sorted(
                        ap_counts.items(),
                        key=lambda x: (x[0][0], x[0][1], x[0][2])  # Sort by vendor, model, floor
                    )
                ],
                "details": [
                    {
                        "name": ap.name,
                        "vendor": ap.vendor,
                        "model": ap.model,
                        "floor": ap.floor_name,
                        "floor_id": ap.floor_id,
                        "location": {
                            "x": ap.location_x,
                            "y": ap.location_y
                        } if ap.location_x is not None and ap.location_y is not None else None,
                        "installation": {
                            "mounting_height": ap.mounting_height,
                            "azimuth": ap.azimuth,
                            "tilt": ap.tilt,
                            "antenna_height": ap.antenna_height
                        },
                        "color": ap.color,
                        "mine": ap.mine,
                        "enabled": ap.enabled,
                        "tags": [
                            {
                                "key": tag.key,
                                "value": tag.value,
                                "tag_key_id": tag.tag_key_id
                            }
                            for tag in ap.tags
                        ]
                    }
                    for ap in project_data.access_points
                ]
            },
            "antennas": {
                "bill_of_materials": [
                    {
                        "name": name,
                        "quantity": count
                    }
                    for name, count in sorted(antenna_counts.items())
                ],
                "details": [
                    {
                        "name": antenna.name,
                        "antenna_type_id": antenna.antenna_type_id
                    }
                    for antenna in project_data.antennas
                ]
            },
            "analytics": {
                "by_vendor": self._format_grouping(by_vendor),
                "by_floor": self._format_grouping(by_floor),
                "by_color": self._format_grouping(by_color),
                "by_model": self._format_grouping(by_model),
                "mounting": {
                    "avg_height_m": mounting_metrics.avg_height,
                    "min_height_m": mounting_metrics.min_height,
                    "max_height_m": mounting_metrics.max_height,
                    "height_variance": mounting_metrics.height_variance,
                    "aps_with_height_data": mounting_metrics.aps_with_height,
                    "avg_azimuth_deg": mounting_metrics.avg_azimuth,
                    "avg_tilt_deg": mounting_metrics.avg_tilt,
                    "height_distribution": [
                        {"range": range_name, "count": count}
                        for range_name, count in sorted(height_distribution.items())
                    ]
                },
                "radio": {
                    "total_radios": radio_metrics.total_radios if radio_metrics else 0,
                    "frequency_bands": radio_metrics.band_distribution if radio_metrics else {},
                    "channel_distribution": {str(k): v for k, v in radio_metrics.channel_distribution.items()} if radio_metrics else {},
                    "channel_widths": {str(k): v for k, v in radio_metrics.channel_width_distribution.items()} if radio_metrics else {},
                    "wifi_standards": radio_metrics.standard_distribution if radio_metrics else {},
                    "tx_power": {
                        "avg_dbm": radio_metrics.avg_tx_power,
                        "min_dbm": radio_metrics.min_tx_power,
                        "max_dbm": radio_metrics.max_tx_power
                    } if radio_metrics and radio_metrics.avg_tx_power else None
                }
            }
        }

        return json_structure

    def _format_grouping(self, grouped_data: dict) -> dict:
        """Format grouped data for JSON output.

        Args:
            grouped_data: Dictionary of {label: count}

        Returns:
            Dictionary with counts and percentages
        """
        total = sum(grouped_data.values())

        return {
            "total": total,
            "groups": [
                {
                    "name": str(label),
                    "count": count,
                    "percentage": round((count / total * 100) if total > 0 else 0, 2)
                }
                for label, count in sorted(
                    grouped_data.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            ]
        }


class CompactJSONExporter(JSONExporter):
    """JSON exporter with compact (minified) output.

    Useful for:
    - Minimizing file size
    - Network transfers
    - Embedded systems
    """

    def __init__(self, output_dir: Path):
        """Initialize compact JSON exporter.

        Args:
            output_dir: Directory where export files will be saved
        """
        super().__init__(output_dir, indent=None)

    @property
    def format_name(self) -> str:
        """Human-readable name of the export format."""
        return "JSON (Compact)"
