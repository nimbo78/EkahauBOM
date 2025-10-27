#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Filtering utilities for access points."""

import logging
from typing import Optional

from .models import AccessPoint

logger = logging.getLogger(__name__)


class APFilter:
    """Filter access points by various criteria.

    Supports filtering by floors, colors, vendors, and tags with AND logic.
    """

    @staticmethod
    def by_floors(access_points: list[AccessPoint], floors: list[str]) -> list[AccessPoint]:
        """Filter access points by floor names.

        Args:
            access_points: List of access points to filter
            floors: List of floor names to include

        Returns:
            Filtered list of access points
        """
        if not floors:
            return access_points

        filtered = [ap for ap in access_points if ap.floor_name in floors]
        logger.info(
            f"Floor filter: {len(access_points)} → {len(filtered)} APs (floors: {', '.join(floors)})"
        )
        return filtered

    @staticmethod
    def by_colors(access_points: list[AccessPoint], colors: list[str]) -> list[AccessPoint]:
        """Filter access points by colors.

        Args:
            access_points: List of access points to filter
            colors: List of color names to include

        Returns:
            Filtered list of access points
        """
        if not colors:
            return access_points

        filtered = [ap for ap in access_points if ap.color in colors]
        logger.info(
            f"Color filter: {len(access_points)} → {len(filtered)} APs (colors: {', '.join(colors)})"
        )
        return filtered

    @staticmethod
    def by_vendors(access_points: list[AccessPoint], vendors: list[str]) -> list[AccessPoint]:
        """Filter access points by vendors.

        Args:
            access_points: List of access points to filter
            vendors: List of vendor names to include

        Returns:
            Filtered list of access points
        """
        if not vendors:
            return access_points

        filtered = [ap for ap in access_points if ap.vendor in vendors]
        logger.info(
            f"Vendor filter: {len(access_points)} → {len(filtered)} APs (vendors: {', '.join(vendors)})"
        )
        return filtered

    @staticmethod
    def by_models(access_points: list[AccessPoint], models: list[str]) -> list[AccessPoint]:
        """Filter access points by model names.

        Args:
            access_points: List of access points to filter
            models: List of model names to include

        Returns:
            Filtered list of access points
        """
        if not models:
            return access_points

        filtered = [ap for ap in access_points if ap.model in models]
        logger.info(
            f"Model filter: {len(access_points)} → {len(filtered)} APs (models: {', '.join(models)})"
        )
        return filtered

    @staticmethod
    def by_tag(
        access_points: list[AccessPoint], tag_key: str, tag_values: list[str]
    ) -> list[AccessPoint]:
        """Filter access points by specific tag key-value pairs.

        Args:
            access_points: List of access points to filter
            tag_key: Name of the tag key (e.g., "Location")
            tag_values: List of acceptable tag values (e.g., ["Building A", "Building B"])

        Returns:
            Filtered list of access points
        """
        if not tag_values:
            return access_points

        filtered = []
        for ap in access_points:
            for tag in ap.tags:
                if tag.key == tag_key and tag.value in tag_values:
                    filtered.append(ap)
                    break

        logger.info(
            f"Tag filter ({tag_key}): {len(access_points)} → {len(filtered)} APs (values: {', '.join(tag_values)})"
        )
        return filtered

    @staticmethod
    def by_tags(
        access_points: list[AccessPoint], tag_filters: dict[str, list[str]]
    ) -> list[AccessPoint]:
        """Filter access points by multiple tag key-value pairs.

        Args:
            access_points: List of access points to filter
            tag_filters: Dictionary mapping tag keys to lists of acceptable values
                        Example: {"Location": ["Building A"], "Zone": ["Office"]}

        Returns:
            Filtered list of access points matching ALL tag filters (AND logic)
        """
        if not tag_filters:
            return access_points

        filtered = access_points
        for tag_key, tag_values in tag_filters.items():
            filtered = APFilter.by_tag(filtered, tag_key, tag_values)

        return filtered

    @staticmethod
    def exclude_floors(access_points: list[AccessPoint], floors: list[str]) -> list[AccessPoint]:
        """Exclude access points on specific floors.

        Args:
            access_points: List of access points to filter
            floors: List of floor names to exclude

        Returns:
            Filtered list of access points
        """
        if not floors:
            return access_points

        filtered = [ap for ap in access_points if ap.floor_name not in floors]
        logger.info(
            f"Exclude floors: {len(access_points)} → {len(filtered)} APs (excluded: {', '.join(floors)})"
        )
        return filtered

    @staticmethod
    def exclude_colors(access_points: list[AccessPoint], colors: list[str]) -> list[AccessPoint]:
        """Exclude access points with specific colors.

        Args:
            access_points: List of access points to filter
            colors: List of color names to exclude

        Returns:
            Filtered list of access points
        """
        if not colors:
            return access_points

        filtered = [ap for ap in access_points if ap.color not in colors]
        logger.info(
            f"Exclude colors: {len(access_points)} → {len(filtered)} APs (excluded: {', '.join(colors)})"
        )
        return filtered

    @staticmethod
    def exclude_vendors(access_points: list[AccessPoint], vendors: list[str]) -> list[AccessPoint]:
        """Exclude access points from specific vendors.

        Args:
            access_points: List of access points to filter
            vendors: List of vendor names to exclude

        Returns:
            Filtered list of access points
        """
        if not vendors:
            return access_points

        filtered = [ap for ap in access_points if ap.vendor not in vendors]
        logger.info(
            f"Exclude vendors: {len(access_points)} → {len(filtered)} APs (excluded: {', '.join(vendors)})"
        )
        return filtered

    @staticmethod
    def apply_filters(
        access_points: list[AccessPoint],
        include_floors: Optional[list[str]] = None,
        include_colors: Optional[list[str]] = None,
        include_vendors: Optional[list[str]] = None,
        include_models: Optional[list[str]] = None,
        include_tags: Optional[dict[str, list[str]]] = None,
        exclude_floors: Optional[list[str]] = None,
        exclude_colors: Optional[list[str]] = None,
        exclude_vendors: Optional[list[str]] = None,
    ) -> list[AccessPoint]:
        """Apply multiple filters to access points with AND logic.

        Filters are applied in this order:
        1. Include filters (floors, colors, vendors, models, tags)
        2. Exclude filters (floors, colors, vendors)

        Args:
            access_points: List of access points to filter
            include_floors: Floors to include
            include_colors: Colors to include
            include_vendors: Vendors to include
            include_models: Models to include
            include_tags: Tags to include (dict of key -> values)
            exclude_floors: Floors to exclude
            exclude_colors: Colors to exclude
            exclude_vendors: Vendors to exclude

        Returns:
            Filtered list of access points
        """
        original_count = len(access_points)
        result = access_points

        # Apply include filters
        if include_floors:
            result = APFilter.by_floors(result, include_floors)

        if include_colors:
            result = APFilter.by_colors(result, include_colors)

        if include_vendors:
            result = APFilter.by_vendors(result, include_vendors)

        if include_models:
            result = APFilter.by_models(result, include_models)

        if include_tags:
            result = APFilter.by_tags(result, include_tags)

        # Apply exclude filters
        if exclude_floors:
            result = APFilter.exclude_floors(result, exclude_floors)

        if exclude_colors:
            result = APFilter.exclude_colors(result, exclude_colors)

        if exclude_vendors:
            result = APFilter.exclude_vendors(result, exclude_vendors)

        final_count = len(result)
        if original_count != final_count:
            logger.info(
                f"Total filtering: {original_count} → {final_count} APs ({final_count/original_count*100:.1f}% remaining)"
            )

        return result
