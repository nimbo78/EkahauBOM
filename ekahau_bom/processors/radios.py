#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Processor for radios data."""

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

        # Extract channel and frequency band
        channel = radio_data.get("channel")
        frequency_band = self._determine_frequency_band(radio_data, channel)

        # Extract channel width (in MHz)
        channel_width = radio_data.get("channelWidth")

        # Extract transmit power (in dBm)
        tx_power = radio_data.get("transmitPower")

        # Extract antenna type
        antenna_type_id = radio_data.get("antennaTypeId")

        # Determine Wi-Fi standard
        standard = self._determine_wifi_standard(radio_data)

        return Radio(
            id=radio_id,
            access_point_id=access_point_id,
            frequency_band=frequency_band,
            channel=channel,
            channel_width=channel_width,
            tx_power=tx_power,
            antenna_type_id=antenna_type_id,
            standard=standard
        )

    def _determine_frequency_band(self, radio_data: dict[str, Any], channel: int | None) -> str | None:
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

    def _determine_wifi_standard(self, radio_data: dict[str, Any]) -> str | None:
        """Determine Wi-Fi standard from radio data.

        Args:
            radio_data: Raw radio data

        Returns:
            Wi-Fi standard string (802.11a/b/g/n/ac/ax/be) or None
        """
        # Check if standard is explicitly specified
        if "standard" in radio_data:
            return radio_data["standard"]

        # Try to infer from other fields if available
        # This is a simplification - actual detection would need more data
        frequency_band = radio_data.get("band")
        channel_width = radio_data.get("channelWidth")

        # Basic inference (simplified)
        if channel_width and channel_width >= 160:
            return "802.11ax"  # Wi-Fi 6/6E supports 160 MHz
        elif channel_width and channel_width >= 80:
            return "802.11ac"  # Wi-Fi 5 supports 80 MHz
        elif frequency_band == "FIVE_GHZ":
            return "802.11ac"  # Default for 5 GHz
        elif frequency_band == "TWO_DOT_FOUR_GHZ":
            return "802.11n"  # Default for 2.4 GHz

        return None
