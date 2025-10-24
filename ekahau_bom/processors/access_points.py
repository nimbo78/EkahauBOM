#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Processor for access points data."""

import logging
from typing import Any

from ..models import AccessPoint, Floor
from ..utils import get_color_name

logger = logging.getLogger(__name__)


class AccessPointProcessor:
    """Process access points data from Ekahau project."""

    def __init__(self, color_database: dict[str, str]):
        """Initialize processor with color database.

        Args:
            color_database: Dictionary mapping hex color codes to names
        """
        self.color_database = color_database

    def process(
        self,
        access_points_data: dict[str, Any],
        floors: dict[str, Floor]
    ) -> list[AccessPoint]:
        """Process raw access points data into AccessPoint objects.

        Args:
            access_points_data: Raw access points data from parser
            floors: Dictionary mapping floor IDs to Floor objects

        Returns:
            List of AccessPoint objects
        """
        access_points = []
        ap_list = access_points_data.get("accessPoints", [])

        logger.info(f"Processing {len(ap_list)} access points")

        for ap_data in ap_list:
            # Only process APs that belong to this project (not neighbor/survey APs)
            if not ap_data.get("mine", False):
                logger.debug(f"Skipping non-mine AP: {ap_data.get('name', 'Unknown')}")
                continue

            try:
                ap = self._process_single_ap(ap_data, floors)
                access_points.append(ap)
            except Exception as e:
                logger.warning(f"Error processing AP {ap_data.get('name', 'Unknown')}: {e}")
                continue

        logger.info(f"Successfully processed {len(access_points)} access points")
        return access_points

    def _process_single_ap(
        self,
        ap_data: dict[str, Any],
        floors: dict[str, Floor]
    ) -> AccessPoint:
        """Process a single access point.

        Args:
            ap_data: Raw access point data
            floors: Dictionary mapping floor IDs to Floor objects

        Returns:
            AccessPoint object
        """
        vendor = ap_data.get("vendor", "Unknown")
        model = ap_data.get("model", "Unknown")

        # Get floor information
        floor_id = ap_data.get("location", {}).get("floorPlanId")
        floor = floors.get(floor_id) if floor_id else None
        floor_name = floor.name if floor else "Unknown Floor"

        # Process color
        color = None
        if "color" in ap_data:
            hex_color = ap_data["color"]
            color = get_color_name(hex_color, self.color_database)
            if color == hex_color:
                logger.debug(f"Unknown color code: {hex_color}")

        return AccessPoint(
            vendor=vendor,
            model=model,
            color=color,
            floor_name=floor_name,
            mine=ap_data.get("mine", True),
            floor_id=floor_id
        )
