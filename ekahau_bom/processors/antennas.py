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

            # Detect external antennas
            # PRIMARY METHOD: Check if AP model contains " + " (space-plus-space)
            is_external = False
            ap_model = ap_models.get(ap_id, "")

            if " + " in ap_model:
                is_external = True
                logger.debug(
                    f"External antenna detected via AP model: {ap_model} → {antenna_name}"
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
            )
            antennas.append(antenna)

        external_count = sum(1 for ant in antennas if ant.is_external)
        logger.info(
            f"Successfully processed {len(antennas)} antennas "
            f"({external_count} external, {len(antennas) - external_count} integrated)"
        )
        return antennas
