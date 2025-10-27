#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Processor for access points data."""

from __future__ import annotations


import logging
from typing import Any, Optional

from ..models import AccessPoint, Floor
from ..utils import get_color_name
from .tags import TagProcessor

logger = logging.getLogger(__name__)


class AccessPointProcessor:
    """Process access points data from Ekahau project."""

    def __init__(
        self, color_database: dict[str, str], tag_processor: Optional[TagProcessor] = None
    ):
        """Initialize processor with color database and optional tag processor.

        Args:
            color_database: Dictionary mapping hex color codes to names
            tag_processor: Optional TagProcessor for handling tags. If None, tags won't be processed.
        """
        self.color_database = color_database
        self.tag_processor = tag_processor

    def process(
        self,
        access_points_data: dict[str, Any],
        floors: dict[str, Floor],
        simulated_radios_data: dict[str, Any] = None,
    ) -> list[AccessPoint]:
        """Process raw access points data into AccessPoint objects.

        Args:
            access_points_data: Raw access points data from parser
            floors: Dictionary mapping floor IDs to Floor objects
            simulated_radios_data: Optional simulated radios data for antenna parameters

        Returns:
            List of AccessPoint objects
        """
        access_points = []
        ap_list = access_points_data.get("accessPoints", [])

        # Build radio lookup by access point ID for O(1) access
        radios_by_ap = {}
        if simulated_radios_data:
            for radio in simulated_radios_data.get("simulatedRadios", []):
                ap_id = radio.get("accessPointId")
                if ap_id:
                    if ap_id not in radios_by_ap:
                        radios_by_ap[ap_id] = []
                    radios_by_ap[ap_id].append(radio)

        logger.info(f"Processing {len(ap_list)} access points")

        for ap_data in ap_list:
            # Only process APs that belong to this project (not neighbor/survey APs)
            if not ap_data.get("mine", False):
                logger.debug(f"Skipping non-mine AP: {ap_data.get('name', 'Unknown')}")
                continue

            try:
                # Get radios for this AP
                ap_id = ap_data.get("id")
                ap_radios = radios_by_ap.get(ap_id, [])

                ap = self._process_single_ap(ap_data, floors, ap_radios)
                access_points.append(ap)
            except Exception as e:
                logger.warning(f"Error processing AP {ap_data.get('name', 'Unknown')}: {e}")
                continue

        logger.info(f"Successfully processed {len(access_points)} access points")
        return access_points

    def _process_single_ap(
        self, ap_data: dict[str, Any], floors: dict[str, Floor], radios: list[dict[str, Any]] = None
    ) -> AccessPoint:
        """Process a single access point.

        Args:
            ap_data: Raw access point data
            floors: Dictionary mapping floor IDs to Floor objects
            radios: List of simulated radios for this AP (optional)

        Returns:
            AccessPoint object
        """
        if radios is None:
            radios = []
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

        # Process tags
        tags = []
        if self.tag_processor and "tags" in ap_data:
            ap_tags = ap_data.get("tags", [])
            if ap_tags:
                tags = self.tag_processor.process_ap_tags(ap_tags)
                logger.debug(f"Processed {len(tags)} tags for AP {ap_data.get('name', 'Unknown')}")

        # Extract mounting and location parameters
        location = ap_data.get("location", {})
        mounting_height = location.get("z")  # Height above floor in meters

        # Extract x, y coordinates from location.coord
        coord = location.get("coord", {})
        location_x = coord.get("x")
        location_y = coord.get("y")

        # Extract antenna parameters from simulated radios
        # Use first radio's parameters if available (typically all radios of an AP have same mounting)
        azimuth = None
        tilt = None
        antenna_height = None

        if radios:
            # Get first radio's antenna configuration
            first_radio = radios[0]
            azimuth = first_radio.get("antennaDirection")  # Azimuth in degrees
            tilt = first_radio.get("antennaTilt")  # Tilt in degrees
            antenna_height = first_radio.get("antennaHeight")  # Height in meters

            logger.debug(
                f"AP {ap_data.get('name', 'Unknown')}: tilt={tilt}°, azimuth={azimuth}°, antenna_height={antenna_height}m"
            )

        # Fallback: Check if antenna properties are in the AP data (old format)
        elif "antennas" in ap_data and ap_data["antennas"]:
            first_antenna = ap_data["antennas"][0]
            azimuth = first_antenna.get("azimuth")
            tilt = first_antenna.get("tilt")
            antenna_height = first_antenna.get("antennaHeight")

        return AccessPoint(
            id=ap_data.get("id"),
            vendor=vendor,
            model=model,
            color=color,
            floor_name=floor_name,
            tags=tags,
            mine=ap_data.get("mine", True),
            floor_id=floor_id,
            name=ap_data.get("name"),
            location_x=location_x,
            location_y=location_y,
            mounting_height=mounting_height,
            azimuth=azimuth,
            tilt=tilt,
            antenna_height=antenna_height,
        )
