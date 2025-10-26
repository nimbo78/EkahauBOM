#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Process network capacity settings from Ekahau project data."""

import logging
from typing import Any

from ..models import NetworkCapacitySettings, DataRate

logger = logging.getLogger(__name__)


class NetworkSettingsProcessor:
    """Process network capacity settings from Ekahau project."""

    @staticmethod
    def process_network_settings(settings_data: dict[str, Any]) -> list[NetworkCapacitySettings]:
        """Process network capacity settings.

        Args:
            settings_data: Raw network capacity settings data from JSON

        Returns:
            List of NetworkCapacitySettings objects
        """
        if not settings_data or "networkCapacitySettings" not in settings_data:
            logger.info("No network capacity settings found in project")
            return []

        settings_list = settings_data.get("networkCapacitySettings", [])
        processed_settings = []

        for setting_data in settings_list:
            try:
                setting = NetworkSettingsProcessor._process_single_setting(setting_data)
                processed_settings.append(setting)
            except Exception as e:
                logger.warning(f"Failed to process network setting: {e}")
                continue

        logger.info(f"Processed {len(processed_settings)}/{len(settings_list)} network capacity settings")
        return processed_settings

    @staticmethod
    def _process_single_setting(setting_data: dict[str, Any]) -> NetworkCapacitySettings:
        """Process a single network capacity setting.

        Args:
            setting_data: Raw setting data

        Returns:
            NetworkCapacitySettings object
        """
        # Map Ekahau band names to readable format
        band_map = {
            "TWO": "2.4GHz",
            "FIVE": "5GHz",
            "SIX": "6GHz"
        }

        frequency_band = band_map.get(
            setting_data.get("frequencyBand", ""),
            setting_data.get("frequencyBand", "Unknown")
        )

        # Process data rates
        data_rates = []
        for rate_data in setting_data.get("abgRates", []):
            data_rates.append(DataRate(
                rate=rate_data.get("rate", ""),
                state=rate_data.get("state", "")
            ))

        return NetworkCapacitySettings(
            frequency_band=frequency_band,
            number_of_ssids=setting_data.get("numberOfSsids", 1),
            rts_cts_enabled=setting_data.get("rtsCtsEnabled", False),
            max_associated_clients=setting_data.get("maxAssociatedClientsAmount", 200),
            data_rates=data_rates
        )

    @staticmethod
    def get_ssid_summary(settings: list[NetworkCapacitySettings]) -> dict[str, Any]:
        """Get summary of SSID configuration.

        Args:
            settings: List of network capacity settings

        Returns:
            Dictionary with SSID summary
        """
        if not settings:
            return {}

        total_ssids_24 = 0
        total_ssids_5 = 0
        max_clients_24 = 0
        max_clients_5 = 0

        for setting in settings:
            if "2.4" in setting.frequency_band:
                total_ssids_24 = setting.number_of_ssids
                max_clients_24 = setting.max_associated_clients
            elif "5" in setting.frequency_band:
                total_ssids_5 = setting.number_of_ssids
                max_clients_5 = setting.max_associated_clients

        return {
            "ssids_2_4ghz": total_ssids_24,
            "ssids_5ghz": total_ssids_5,
            "max_clients_2_4ghz": max_clients_24,
            "max_clients_5ghz": max_clients_5
        }

    @staticmethod
    def get_data_rate_summary(settings: list[NetworkCapacitySettings]) -> dict[str, Any]:
        """Get summary of data rate configuration.

        Args:
            settings: List of network capacity settings

        Returns:
            Dictionary with data rate summary per band
        """
        summary = {}

        for setting in settings:
            band = setting.frequency_band
            mandatory_rates = [r.rate for r in setting.data_rates if r.state == "MANDATORY"]
            disabled_rates = [r.rate for r in setting.data_rates if r.state == "DISABLED"]

            summary[band] = {
                "mandatory_rates": mandatory_rates,
                "disabled_rates": disabled_rates,
                "total_rates": len(setting.data_rates)
            }

        return summary
