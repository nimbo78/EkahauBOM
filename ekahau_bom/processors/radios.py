#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Processor for radios data."""

from __future__ import annotations


import logging
from typing import Any

from ..models import Radio

logger = logging.getLogger(__name__)


class RadioProcessor:
    """Process radios data from Ekahau project."""

    # Frequency band mapping based on channel numbers
    BAND_24GHZ_CHANNELS = range(1, 15)  # 2.4 GHz: channels 1-14
    BAND_5GHZ_CHANNELS = range(32, 177)  # 5 GHz: channels 32-177
    BAND_6GHZ_CHANNELS = range(1, 234)  # 6 GHz: channels 1-233 (will need additional logic)

    def process(self, simulated_radios_data: dict[str, Any]) -> list[Radio]:
        """Process raw simulated radios data into Radio objects.

        Args:
            simulated_radios_data: Raw simulated radios data from parser

        Returns:
            List of Radio objects
        """
        radios = []
        radio_list = simulated_radios_data.get("simulatedRadios", [])

        logger.info(f"Processing {len(radio_list)} radios")

        for radio_data in radio_list:
            try:
                radio = self._process_single_radio(radio_data)
                radios.append(radio)
            except Exception as e:
                logger.warning(f"Error processing radio {radio_data.get('id', 'Unknown')}: {e}")
                continue

        logger.info(f"Successfully processed {len(radios)} radios")
        return radios

    def _process_single_radio(self, radio_data: dict[str, Any]) -> Radio:
        """Process a single radio configuration.

        Args:
            radio_data: Raw radio data from Ekahau

        Returns:
            Radio object
        """
        radio_id = radio_data.get("id", "")
        access_point_id = radio_data.get("accessPointId", "")

        # Extract channel - handle both int and list[int] formats
        channel_raw = radio_data.get("channel")
        channel = self._extract_value(channel_raw)

        frequency_band = self._determine_frequency_band(radio_data, channel)

        # Extract channel width (in MHz) - handle both int and list[int] formats
        channel_width_raw = radio_data.get("channelWidth")
        channel_width = self._extract_value(channel_width_raw)

        # Extract transmit power (in dBm)
        tx_power = radio_data.get("transmitPower")

        # Extract antenna type
        antenna_type_id = radio_data.get("antennaTypeId")

        # Determine Wi-Fi standard
        standard = self._determine_wifi_standard(radio_data, channel_width)

        # Extract antenna mounting and orientation data
        antenna_mounting = radio_data.get("antennaMounting")
        antenna_direction = radio_data.get("antennaDirection")
        antenna_tilt = radio_data.get("antennaTilt")
        antenna_height = radio_data.get("antennaHeight")

        return Radio(
            id=radio_id,
            access_point_id=access_point_id,
            frequency_band=frequency_band,
            channel=channel,
            channel_width=channel_width,
            tx_power=tx_power,
            antenna_type_id=antenna_type_id,
            standard=standard,
            antenna_mounting=antenna_mounting,
            antenna_direction=antenna_direction,
            antenna_tilt=antenna_tilt,
            antenna_height=antenna_height,
        )

    def _extract_value(self, value: Any) -> int | float | None:
        """Extract numeric value from various formats.

        Args:
            value: Can be int, float, list[int], list[float], or None

        Returns:
            First element if list, value itself if int/float, None otherwise
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, list) and len(value) > 0:
            return value[0]
        return None

    def _determine_frequency_band(
        self, radio_data: dict[str, Any], channel: int | None
    ) -> str | None:
        """Determine frequency band from radio data.

        Args:
            radio_data: Raw radio data
            channel: Channel number

        Returns:
            Frequency band string (2.4GHz, 5GHz, 6GHz) or None
        """
        # Check if band is explicitly specified
        if "band" in radio_data:
            band = radio_data["band"]
            if band == "TWO_DOT_FOUR_GHZ":
                return "2.4GHz"
            elif band == "FIVE_GHZ":
                return "5GHz"
            elif band == "SIX_GHZ":
                return "6GHz"

        # Try to determine from channel number
        if channel:
            if channel in self.BAND_24GHZ_CHANNELS:
                return "2.4GHz"
            elif channel >= 32:  # 5 GHz and 6 GHz overlap, need more logic
                # For now, assume 5 GHz if channel >= 32
                # 6 GHz detection would need additional fields from Ekahau
                return "5GHz"

        return None

    def _determine_wifi_standard(
        self, radio_data: dict[str, Any], channel_width: int | float | None = None
    ) -> str | None:
        """Determine Wi-Fi standard from radio data.

        Args:
            radio_data: Raw radio data
            channel_width: Channel width in MHz (optional)

        Returns:
            Wi-Fi standard string (802.11a/b/g/n/ac/ax/be) or None
        """
        # Check if standard is explicitly specified
        if "standard" in radio_data:
            return radio_data["standard"]

        # Check technology field (e.g., "N", "AC", "AX")
        technology = radio_data.get("technology")
        if technology:
            tech_mapping = {
                "A": "802.11a",
                "B": "802.11b",
                "G": "802.11g",
                "N": "802.11n",
                "AC": "802.11ac",
                "AX": "802.11ax",
                "BE": "802.11be",
            }
            if technology in tech_mapping:
                return tech_mapping[technology]

        # Try to infer from channel width
        if channel_width:
            if channel_width >= 160:
                return "802.11ax"  # Wi-Fi 6/6E supports 160 MHz
            elif channel_width >= 80:
                return "802.11ac"  # Wi-Fi 5 supports 80 MHz

        # Try to infer from band
        frequency_band = radio_data.get("band")
        if frequency_band == "FIVE_GHZ":
            return "802.11ac"  # Default for 5 GHz
        elif frequency_band == "TWO_DOT_FOUR_GHZ":
            return "802.11n"  # Default for 2.4 GHz

        return None
