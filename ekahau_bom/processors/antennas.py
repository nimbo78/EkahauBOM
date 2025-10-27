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
        self, simulated_radios_data: dict[str, Any], antenna_types_data: dict[str, Any]
    ) -> list[Antenna]:
        """Process raw antenna data into Antenna objects.

        Args:
            simulated_radios_data: Raw simulated radios data from parser
            antenna_types_data: Raw antenna types data from parser

        Returns:
            List of Antenna objects
        """
        # Create antenna type lookup dictionary for O(1) access
        antenna_types_map = {
            ant["id"]: ant["name"] for ant in antenna_types_data.get("antennaTypes", [])
        }

        logger.info(f"Found {len(antenna_types_map)} antenna types")

        antennas = []
        radios = simulated_radios_data.get("simulatedRadios", [])

        logger.info(f"Processing {len(radios)} simulated radios")

        for radio in radios:
            antenna_type_id = radio.get("antennaTypeId")

            if not antenna_type_id:
                logger.debug("Radio without antenna type ID, skipping")
                continue

            antenna_name = antenna_types_map.get(antenna_type_id)

            if not antenna_name:
                logger.warning(f"Antenna type ID {antenna_type_id} not found in antenna types")
                continue

            antenna = Antenna(name=antenna_name, antenna_type_id=antenna_type_id)
            antennas.append(antenna)

        logger.info(f"Successfully processed {len(antennas)} antennas")
        return antennas
