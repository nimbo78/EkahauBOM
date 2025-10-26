#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for NetworkSettingsProcessor."""

import pytest
from ekahau_bom.processors.network_settings import NetworkSettingsProcessor
from ekahau_bom.models import NetworkCapacitySettings, DataRate


@pytest.fixture
def sample_settings_data():
    """Create sample network capacity settings data."""
    return {
        "networkCapacitySettings": [
            {
                "frequencyBand": "TWO",
                "numberOfSsids": 3,
                "rtsCtsEnabled": True,
                "maxAssociatedClientsAmount": 150,
                "abgRates": [
                    {"rate": "1.0", "state": "MANDATORY"},
                    {"rate": "2.0", "state": "MANDATORY"},
                    {"rate": "5.5", "state": "SUPPORTED"},
                    {"rate": "11.0", "state": "DISABLED"}
                ]
            },
            {
                "frequencyBand": "FIVE",
                "numberOfSsids": 4,
                "rtsCtsEnabled": False,
                "maxAssociatedClientsAmount": 200,
                "abgRates": [
                    {"rate": "6.0", "state": "MANDATORY"},
                    {"rate": "9.0", "state": "SUPPORTED"},
                    {"rate": "12.0", "state": "SUPPORTED"},
                    {"rate": "18.0", "state": "DISABLED"}
                ]
            }
        ]
    }


class TestNetworkSettingsProcessor:
    """Test NetworkSettingsProcessor class."""

    def test_process_network_settings_success(self, sample_settings_data):
        """Test successful processing of network settings."""
        settings = NetworkSettingsProcessor.process_network_settings(sample_settings_data)

        assert len(settings) == 2
        assert all(isinstance(s, NetworkCapacitySettings) for s in settings)

        # Check 2.4GHz settings
        setting_24 = settings[0]
        assert setting_24.frequency_band == "2.4GHz"
        assert setting_24.number_of_ssids == 3
        assert setting_24.rts_cts_enabled is True
        assert setting_24.max_associated_clients == 150
        assert len(setting_24.data_rates) == 4

        # Check 5GHz settings
        setting_5 = settings[1]
        assert setting_5.frequency_band == "5GHz"
        assert setting_5.number_of_ssids == 4
        assert setting_5.rts_cts_enabled is False
        assert setting_5.max_associated_clients == 200
        assert len(setting_5.data_rates) == 4

    def test_process_network_settings_empty_data(self):
        """Test processing with empty data."""
        settings = NetworkSettingsProcessor.process_network_settings({})
        assert settings == []

        settings = NetworkSettingsProcessor.process_network_settings(None)
        assert settings == []

    def test_process_network_settings_no_settings_key(self):
        """Test processing when networkCapacitySettings key is missing."""
        data = {"otherKey": "value"}
        settings = NetworkSettingsProcessor.process_network_settings(data)
        assert settings == []

    def test_process_network_settings_empty_list(self):
        """Test processing with empty settings list."""
        data = {"networkCapacitySettings": []}
        settings = NetworkSettingsProcessor.process_network_settings(data)
        assert settings == []

    def test_process_single_setting_6ghz(self):
        """Test processing 6GHz band."""
        setting_data = {
            "frequencyBand": "SIX",
            "numberOfSsids": 2,
            "rtsCtsEnabled": False,
            "maxAssociatedClientsAmount": 100,
            "abgRates": []
        }

        setting = NetworkSettingsProcessor._process_single_setting(setting_data)

        assert setting.frequency_band == "6GHz"
        assert setting.number_of_ssids == 2
        assert setting.rts_cts_enabled is False
        assert setting.max_associated_clients == 100
        assert len(setting.data_rates) == 0

    def test_process_single_setting_unknown_band(self):
        """Test processing unknown frequency band."""
        setting_data = {
            "frequencyBand": "UNKNOWN_BAND",
            "numberOfSsids": 1,
            "rtsCtsEnabled": False,
            "maxAssociatedClientsAmount": 200,
            "abgRates": []
        }

        setting = NetworkSettingsProcessor._process_single_setting(setting_data)

        assert setting.frequency_band == "UNKNOWN_BAND"

    def test_process_single_setting_missing_fields(self):
        """Test processing with missing fields (defaults)."""
        setting_data = {
            "frequencyBand": "TWO",
            # Missing all other fields
        }

        setting = NetworkSettingsProcessor._process_single_setting(setting_data)

        assert setting.frequency_band == "2.4GHz"
        assert setting.number_of_ssids == 1  # Default
        assert setting.rts_cts_enabled is False  # Default
        assert setting.max_associated_clients == 200  # Default
        assert len(setting.data_rates) == 0  # No rates

    def test_process_single_setting_with_rates(self):
        """Test processing data rates."""
        setting_data = {
            "frequencyBand": "FIVE",
            "abgRates": [
                {"rate": "6.0", "state": "MANDATORY"},
                {"rate": "12.0", "state": "SUPPORTED"},
                {"rate": "24.0", "state": "DISABLED"}
            ]
        }

        setting = NetworkSettingsProcessor._process_single_setting(setting_data)

        assert len(setting.data_rates) == 3
        assert all(isinstance(r, DataRate) for r in setting.data_rates)
        assert setting.data_rates[0].rate == "6.0"
        assert setting.data_rates[0].state == "MANDATORY"
        assert setting.data_rates[2].state == "DISABLED"

    def test_get_ssid_summary(self, sample_settings_data):
        """Test SSID summary generation."""
        settings = NetworkSettingsProcessor.process_network_settings(sample_settings_data)
        summary = NetworkSettingsProcessor.get_ssid_summary(settings)

        assert summary["ssids_2_4ghz"] == 3
        assert summary["ssids_5ghz"] == 4
        assert summary["max_clients_2_4ghz"] == 150
        assert summary["max_clients_5ghz"] == 200

    def test_get_ssid_summary_empty_settings(self):
        """Test SSID summary with empty settings."""
        summary = NetworkSettingsProcessor.get_ssid_summary([])
        assert summary == {}

    def test_get_ssid_summary_only_24ghz(self):
        """Test SSID summary with only 2.4GHz settings."""
        settings = [
            NetworkCapacitySettings(
                frequency_band="2.4GHz",
                number_of_ssids=2,
                rts_cts_enabled=True,
                max_associated_clients=100,
                data_rates=[]
            )
        ]

        summary = NetworkSettingsProcessor.get_ssid_summary(settings)

        assert summary["ssids_2_4ghz"] == 2
        assert summary["ssids_5ghz"] == 0
        assert summary["max_clients_2_4ghz"] == 100
        assert summary["max_clients_5ghz"] == 0

    def test_get_data_rate_summary(self, sample_settings_data):
        """Test data rate summary generation."""
        settings = NetworkSettingsProcessor.process_network_settings(sample_settings_data)
        summary = NetworkSettingsProcessor.get_data_rate_summary(settings)

        assert "2.4GHz" in summary
        assert "5GHz" in summary

        # Check 2.4GHz rates
        rates_24 = summary["2.4GHz"]
        assert rates_24["total_rates"] == 4
        assert "1.0" in rates_24["mandatory_rates"]
        assert "2.0" in rates_24["mandatory_rates"]
        assert "11.0" in rates_24["disabled_rates"]

        # Check 5GHz rates
        rates_5 = summary["5GHz"]
        assert rates_5["total_rates"] == 4
        assert "6.0" in rates_5["mandatory_rates"]
        assert "18.0" in rates_5["disabled_rates"]

    def test_get_data_rate_summary_empty_settings(self):
        """Test data rate summary with empty settings."""
        summary = NetworkSettingsProcessor.get_data_rate_summary([])
        assert summary == {}

    def test_get_data_rate_summary_no_rates(self):
        """Test data rate summary with no data rates."""
        settings = [
            NetworkCapacitySettings(
                frequency_band="2.4GHz",
                number_of_ssids=1,
                rts_cts_enabled=False,
                max_associated_clients=200,
                data_rates=[]
            )
        ]

        summary = NetworkSettingsProcessor.get_data_rate_summary(settings)

        assert "2.4GHz" in summary
        assert summary["2.4GHz"]["total_rates"] == 0
        assert summary["2.4GHz"]["mandatory_rates"] == []
        assert summary["2.4GHz"]["disabled_rates"] == []

    def test_process_network_settings_with_error(self):
        """Test processing with malformed data (should skip bad entries)."""
        data = {
            "networkCapacitySettings": [
                {
                    "frequencyBand": "TWO",
                    "numberOfSsids": 1,
                    "abgRates": []
                },
                # This entry will cause an error
                None,
                {
                    "frequencyBand": "FIVE",
                    "numberOfSsids": 2,
                    "abgRates": []
                }
            ]
        }

        settings = NetworkSettingsProcessor.process_network_settings(data)

        # Should successfully process 2 out of 3 (skipping the None entry)
        assert len(settings) == 2
        assert settings[0].frequency_band == "2.4GHz"
        assert settings[1].frequency_band == "5GHz"
