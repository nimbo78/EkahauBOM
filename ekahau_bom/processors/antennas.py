#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Processor for antennas data."""

from __future__ import annotations


import logging
from typing import Any

from ..models import Antenna

logger = logging.getLogger(__name__)


class AntennaProcessor:
    """Process antennas data from Ekahau project."""

    @staticmethod
    def _extract_antenna_model(ap_model: str) -> str | None:
        """Extract antenna model from AP model string.

        AP models with external antennas follow pattern: "AP Model + Antenna Model"
        Example: "Huawei AirEngine 6760-X1E + Huawei 27013718" → "Huawei 27013718"

        Args:
            ap_model: Full AP model string

        Returns:
            Antenna model (part after " + ") or None if no " + " found
        """
        if " + " in ap_model:
            parts = ap_model.split(" + ", 1)
            if len(parts) > 1:
                return parts[1].strip()
        return None

    def process(
        self,
        simulated_radios_data: dict[str, Any],
        antenna_types_data: dict[str, Any],
        access_points_data: dict[str, Any] = None,
    ) -> list[Antenna]:
        """Process raw antenna data into Antenna objects.

        Args:
            simulated_radios_data: Raw simulated radios data from parser
            antenna_types_data: Raw antenna types data from parser
            access_points_data: Optional raw access points data for detecting external antennas

        Returns:
            List of Antenna objects with is_external flag set based on AP model detection
        """
        # Create antenna type lookup dictionary for O(1) access
        antenna_types_map = {
            ant["id"]: {
                "name": ant["name"],
                "apCoupling": ant.get("apCoupling", "INTERNAL_ANTENNA"),
            }
            for ant in antenna_types_data.get("antennaTypes", [])
        }

        logger.info(f"Found {len(antenna_types_map)} antenna types")

        # Build AP ID → AP model mapping for external antenna detection
        ap_models = {}
        if access_points_data:
            for ap in access_points_data.get("accessPoints", []):
                ap_id = ap.get("id")
                model = ap.get("model", "")
                if ap_id:
                    ap_models[ap_id] = model

        antennas = []
        radios = simulated_radios_data.get("simulatedRadios", [])

        logger.info(f"Processing {len(radios)} simulated radios")

        for radio in radios:
            antenna_type_id = radio.get("antennaTypeId")
            ap_id = radio.get("accessPointId")

            if not antenna_type_id:
                logger.debug("Radio without antenna type ID, skipping")
                continue

            antenna_info = antenna_types_map.get(antenna_type_id)

            if not antenna_info:
                logger.warning(
                    f"Antenna type ID {antenna_type_id} not found in antenna types"
                )
                continue

            antenna_name = antenna_info["name"]

            # Get AP model for external antenna detection and model extraction
            ap_model = ap_models.get(ap_id, "")

            # Extract antenna model from AP model (part after " + ")
            # This gives us the clean antenna name for dual-band aggregation
            # Example: "Huawei AirEngine 6760-X1E + Huawei 27013718" → "Huawei 27013718"
            antenna_model = self._extract_antenna_model(ap_model)

            # Get spatial streams from radio
            # Ekahau stores this in "spatialStreamCount" field
            spatial_streams = radio.get("spatialStreamCount", 1)

            # Detect external antennas
            # PRIMARY METHOD: Check if AP model contains " + " (space-plus-space)
            is_external = False

            if " + " in ap_model:
                is_external = True
                logger.debug(
                    f"External antenna detected via AP model: {ap_model} → {antenna_name} "
                    f"(spatial streams: {spatial_streams})"
                )
            else:
                # ALTERNATIVE: Validate with apCoupling field
                ap_coupling = antenna_info.get("apCoupling", "INTERNAL_ANTENNA")
                is_external_by_coupling = "EXTERNAL" in ap_coupling.upper()

                # Log warning if methods disagree (shouldn't happen in normal cases)
                if is_external != is_external_by_coupling:
                    logger.debug(
                        f"External antenna detection mismatch for {antenna_name}: "
                        f"model={is_external}, apCoupling={is_external_by_coupling}"
                    )

            antenna = Antenna(
                name=antenna_name,
                antenna_type_id=antenna_type_id,
                access_point_id=ap_id,
                is_external=is_external,
                spatial_streams=spatial_streams,
                antenna_model=antenna_model,
            )
            antennas.append(antenna)

        external_count = sum(1 for ant in antennas if ant.is_external)
        logger.info(
            f"Successfully processed {len(antennas)} antennas "
            f"({external_count} external, {len(antennas) - external_count} integrated)"
        )
        return antennas
