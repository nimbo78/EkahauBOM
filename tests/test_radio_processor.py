#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for RadioProcessor."""

import pytest
from ekahau_bom.processors.radios import RadioProcessor
from ekahau_bom.models import Radio


class TestRadioProcessor:
    """Test cases for RadioProcessor."""

    @pytest.fixture
    def processor(self):
        """Create a RadioProcessor instance."""
        return RadioProcessor()

    def test_extract_value_from_int(self, processor):
        """Test extracting value from integer."""
        assert processor._extract_value(42) == 42

    def test_extract_value_from_float(self, processor):
        """Test extracting value from float."""
        assert processor._extract_value(3.14) == 3.14

    def test_extract_value_from_list(self, processor):
        """Test extracting value from list."""
        assert processor._extract_value([11]) == 11
        assert processor._extract_value([42, 100]) == 42  # First element

    def test_extract_value_from_none(self, processor):
        """Test extracting value from None."""
        assert processor._extract_value(None) is None

    def test_extract_value_from_empty_list(self, processor):
        """Test extracting value from empty list."""
        assert processor._extract_value([]) is None

    def test_process_radio_with_list_channel(self, processor):
        """Test processing radio data where channel is a list (wine office.esx format)."""
        radio_data = {
            "id": "test-radio-1",
            "accessPointId": "test-ap-1",
            "channel": [11],  # Channel as list
            "transmitPower": 8.0,
            "antennaTypeId": "antenna-1",
            "technology": "N",
        }

        radio = processor._process_single_radio(radio_data)

        assert isinstance(radio, Radio)
        assert radio.id == "test-radio-1"
        assert radio.channel == 11  # Extracted from list
        assert radio.standard == "802.11n"

    def test_process_radio_with_int_channel(self, processor):
        """Test processing radio data where channel is an int."""
        radio_data = {
            "id": "test-radio-2",
            "accessPointId": "test-ap-2",
            "channel": 36,  # Channel as int
            "transmitPower": 10.0,
            "antennaTypeId": "antenna-2",
            "technology": "AC",
        }

        radio = processor._process_single_radio(radio_data)

        assert radio.channel == 36
        assert radio.standard == "802.11ac"

    def test_determine_frequency_band_24ghz(self, processor):
        """Test frequency band determination for 2.4GHz."""
        radio_data = {}
        assert processor._determine_frequency_band(radio_data, 11) == "2.4GHz"
        assert processor._determine_frequency_band(radio_data, 1) == "2.4GHz"
        assert processor._determine_frequency_band(radio_data, 14) == "2.4GHz"

    def test_determine_frequency_band_5ghz(self, processor):
        """Test frequency band determination for 5GHz."""
        radio_data = {}
        assert processor._determine_frequency_band(radio_data, 36) == "5GHz"
        assert processor._determine_frequency_band(radio_data, 149) == "5GHz"

    def test_determine_wifi_standard_from_technology(self, processor):
        """Test Wi-Fi standard determination from technology field."""
        assert processor._determine_wifi_standard({"technology": "N"}) == "802.11n"
        assert processor._determine_wifi_standard({"technology": "AC"}) == "802.11ac"
        assert processor._determine_wifi_standard({"technology": "AX"}) == "802.11ax"
        assert processor._determine_wifi_standard({"technology": "G"}) == "802.11g"

    def test_determine_wifi_standard_from_channel_width(self, processor):
        """Test Wi-Fi standard determination from channel width."""
        assert processor._determine_wifi_standard({}, channel_width=160) == "802.11ax"
        assert processor._determine_wifi_standard({}, channel_width=80) == "802.11ac"

    def test_process_multiple_radios(self, processor):
        """Test processing multiple radios like from wine office.esx."""
        simulated_radios_data = {
            "simulatedRadios": [
                {
                    "id": "radio-1",
                    "accessPointId": "ap-1",
                    "channel": [11],
                    "transmitPower": 8.0,
                    "antennaTypeId": "antenna-1",
                    "technology": "N",
                },
                {
                    "id": "radio-2",
                    "accessPointId": "ap-1",
                    "channel": [36],
                    "transmitPower": 10.0,
                    "antennaTypeId": "antenna-2",
                    "technology": "AC",
                },
            ]
        }

        radios = processor.process(simulated_radios_data)

        assert len(radios) == 2
        assert radios[0].channel == 11
        assert radios[0].standard == "802.11n"
        assert radios[1].channel == 36
        assert radios[1].standard == "802.11ac"

    def test_process_radio_with_missing_fields(self, processor):
        """Test processing radio with minimal data."""
        radio_data = {"id": "minimal-radio", "accessPointId": "minimal-ap"}

        radio = processor._process_single_radio(radio_data)

        assert radio.id == "minimal-radio"
        assert radio.channel is None
        assert radio.channel_width is None
        assert radio.standard is None

    def test_process_handles_invalid_radio_gracefully(self, processor):
        """Test that invalid radio data is logged but doesn't crash."""
        simulated_radios_data = {
            "simulatedRadios": [
                {"id": "invalid-1"},  # Missing required fields
                {"id": "valid-1", "accessPointId": "ap-1", "channel": [11], "technology": "N"},
            ]
        }

        # Should process the valid one and skip the invalid one
        radios = processor.process(simulated_radios_data)

        # At least the valid one should be processed
        assert len(radios) >= 1
        assert any(r.id == "valid-1" for r in radios)

    def test_process_with_exception_in_processing(self, processor):
        """Test that exceptions during radio processing are handled."""
        from unittest.mock import patch

        simulated_radios_data = {
            "simulatedRadios": [
                {"id": "radio-1", "accessPointId": "ap-1", "channel": [11], "technology": "N"},
                {"id": "radio-2", "accessPointId": "ap-2", "channel": [36], "technology": "AC"},
            ]
        }

        # Mock _process_single_radio to raise exception for second radio
        original_method = processor._process_single_radio
        call_count = [0]

        def mock_process(radio_data):
            call_count[0] += 1
            if call_count[0] == 2:  # Second call raises error
                raise ValueError("Simulated radio processing error")
            return original_method(radio_data)

        with patch.object(processor, "_process_single_radio", side_effect=mock_process):
            radios = processor.process(simulated_radios_data)

        # Should have 1 valid radio (second one failed)
        assert len(radios) == 1
        assert radios[0].id == "radio-1"
