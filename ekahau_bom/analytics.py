#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Analytics and grouping utilities for access points."""

import logging
from collections import Counter, defaultdict
from typing import Any

from .models import AccessPoint

logger = logging.getLogger(__name__)


class GroupingAnalytics:
    """Analytics and grouping for project data.

    Provides methods for grouping access points by various dimensions
    and calculating statistics.
    """

    @staticmethod
    def group_by_floor(access_points: list[AccessPoint]) -> dict[str, int]:
        """Group access points by floor with counts.

        Args:
            access_points: List of access points to group

        Returns:
            Dictionary mapping floor name to count
        """
        counts = Counter(ap.floor_name for ap in access_points)
        logger.info(f"Grouped {len(access_points)} APs by floor: {len(counts)} unique floors")
        return dict(counts)

    @staticmethod
    def group_by_color(access_points: list[AccessPoint]) -> dict[str, int]:
        """Group access points by color with counts.

        Args:
            access_points: List of access points to group

        Returns:
            Dictionary mapping color name to count
        """
        counts = Counter(ap.color or "No Color" for ap in access_points)
        logger.info(f"Grouped {len(access_points)} APs by color: {len(counts)} unique colors")
        return dict(counts)

    @staticmethod
    def group_by_vendor(access_points: list[AccessPoint]) -> dict[str, int]:
        """Group access points by vendor with counts.

        Args:
            access_points: List of access points to group

        Returns:
            Dictionary mapping vendor name to count
        """
        counts = Counter(ap.vendor for ap in access_points)
        logger.info(f"Grouped {len(access_points)} APs by vendor: {len(counts)} unique vendors")
        return dict(counts)

    @staticmethod
    def group_by_model(access_points: list[AccessPoint]) -> dict[str, int]:
        """Group access points by model with counts.

        Args:
            access_points: List of access points to group

        Returns:
            Dictionary mapping model name to count
        """
        counts = Counter(ap.model for ap in access_points)
        logger.info(f"Grouped {len(access_points)} APs by model: {len(counts)} unique models")
        return dict(counts)

    @staticmethod
    def group_by_tag(
        access_points: list[AccessPoint],
        tag_key: str
    ) -> dict[str, int]:
        """Group access points by specific tag key.

        Args:
            access_points: List of access points to group
            tag_key: Name of the tag key to group by

        Returns:
            Dictionary mapping tag value to count
        """
        tag_values = []
        for ap in access_points:
            value_found = False
            for tag in ap.tags:
                if tag.key == tag_key:
                    tag_values.append(tag.value)
                    value_found = True
                    break
            if not value_found:
                tag_values.append(f"No {tag_key}")

        counts = Counter(tag_values)
        logger.info(f"Grouped {len(access_points)} APs by tag '{tag_key}': {len(counts)} unique values")
        return dict(counts)

    @staticmethod
    def group_by_vendor_and_model(access_points: list[AccessPoint]) -> dict[tuple[str, str], int]:
        """Group access points by vendor and model combination.

        Args:
            access_points: List of access points to group

        Returns:
            Dictionary mapping (vendor, model) tuple to count
        """
        counts = Counter((ap.vendor, ap.model) for ap in access_points)
        logger.info(f"Grouped {len(access_points)} APs by vendor+model: {len(counts)} unique combinations")
        return dict(counts)

    @staticmethod
    def multi_dimensional_grouping(
        access_points: list[AccessPoint],
        dimensions: list[str],
        tag_key: str | None = None
    ) -> dict[tuple, int]:
        """Multi-dimensional grouping of access points.

        Args:
            access_points: List of access points to group
            dimensions: List of dimensions to group by.
                       Valid values: "floor", "color", "vendor", "model", "tag"
            tag_key: Tag key name (required if "tag" in dimensions)

        Returns:
            Dictionary mapping tuple of values to count

        Example:
            >>> group_multi(aps, ["floor", "color"])
            {("Floor 1", "Yellow"): 10, ("Floor 1", "Red"): 5, ...}
        """
        groups = defaultdict(int)

        for ap in access_points:
            key = []
            for dim in dimensions:
                if dim == "floor":
                    key.append(ap.floor_name)
                elif dim == "color":
                    key.append(ap.color or "No Color")
                elif dim == "vendor":
                    key.append(ap.vendor)
                elif dim == "model":
                    key.append(ap.model)
                elif dim == "tag" and tag_key:
                    value = ap.get_tag_value(tag_key)
                    key.append(value or f"No {tag_key}")
                else:
                    logger.warning(f"Unknown dimension: {dim}")
                    key.append("Unknown")

            groups[tuple(key)] += 1

        logger.info(f"Multi-dimensional grouping ({'+'.join(dimensions)}): {len(groups)} unique combinations")
        return dict(groups)

    @staticmethod
    def calculate_percentages(counts: dict[Any, int]) -> dict[Any, tuple[int, float]]:
        """Calculate percentages for each group.

        Args:
            counts: Dictionary of counts

        Returns:
            Dictionary mapping key to (count, percentage) tuple
        """
        total = sum(counts.values())
        if total == 0:
            return {key: (0, 0.0) for key in counts.keys()}

        return {
            key: (count, (count / total * 100))
            for key, count in counts.items()
        }

    @staticmethod
    def get_summary_statistics(access_points: list[AccessPoint]) -> dict[str, Any]:
        """Get summary statistics for access points.

        Args:
            access_points: List of access points

        Returns:
            Dictionary with various statistics
        """
        if not access_points:
            return {
                "total": 0,
                "unique_vendors": 0,
                "unique_models": 0,
                "unique_floors": 0,
                "unique_colors": 0,
                "with_tags": 0
            }

        return {
            "total": len(access_points),
            "unique_vendors": len(set(ap.vendor for ap in access_points)),
            "unique_models": len(set(ap.model for ap in access_points)),
            "unique_floors": len(set(ap.floor_name for ap in access_points)),
            "unique_colors": len(set(ap.color for ap in access_points if ap.color)),
            "with_tags": sum(1 for ap in access_points if ap.tags)
        }

    @staticmethod
    def print_grouped_results(
        grouped_data: dict[Any, int],
        title: str = "Grouping Results",
        show_percentages: bool = True
    ) -> None:
        """Print grouped results to logger in a formatted way.

        Args:
            grouped_data: Dictionary of grouped counts
            title: Title for the output
            show_percentages: Whether to show percentages
        """
        logger.info("=" * 60)
        logger.info(title)
        logger.info("=" * 60)

        if not grouped_data:
            logger.info("No data to display")
            return

        # Calculate percentages if needed
        if show_percentages:
            percentages = GroupingAnalytics.calculate_percentages(grouped_data)
            # Sort by count (descending)
            sorted_data = sorted(percentages.items(), key=lambda x: x[1][0], reverse=True)

            for key, (count, pct) in sorted_data:
                logger.info(f"  {key}: {count} ({pct:.1f}%)")
        else:
            # Sort by count (descending)
            sorted_data = sorted(grouped_data.items(), key=lambda x: x[1], reverse=True)

            for key, count in sorted_data:
                logger.info(f"  {key}: {count}")

        logger.info("=" * 60)
