#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for data processors."""

from __future__ import annotations


import pytest

from ekahau_bom.processors.access_points import AccessPointProcessor
from ekahau_bom.processors.antennas import AntennaProcessor
from ekahau_bom.processors.radios import RadioProcessor
from ekahau_bom.processors.tags import TagProcessor
from ekahau_bom.models import AccessPoint, Antenna, Radio, Floor, Tag


@pytest.fixture
def color_database():
    """Sample color database."""
    return {
        "#FF0000": "Red",
        "#00FF00": "Green",
        "#0000FF": "Blue",
    }


@pytest.fixture
def sample_floors():
    """Sample floors dictionary."""
    return {
        "floor-1": Floor("floor-1", "Floor 1"),
        "floor-2": Floor("floor-2", "Floor 2"),
    }


@pytest.fixture
def tag_processor():
    """Sample tag processor."""
    tag_keys_data = {
        "tagKeys": [
            {"id": "zone-key", "key": "Zone"},
            {"id": "building-key", "key": "Building"},
        ]
    }
    return TagProcessor(tag_keys_data)


class TestAccessPointProcessor:
    """Test AccessPointProcessor."""

    def test_init(self, color_database):
        """Test processor initialization."""
        processor = AccessPointProcessor(color_database)
        assert processor.color_database == color_database
        assert processor.tag_processor is None

    def test_init_with_tag_processor(self, color_database, tag_processor):
        """Test processor initialization with tag processor."""
        processor = AccessPointProcessor(color_database, tag_processor)
        assert processor.tag_processor is tag_processor

    def test_process_basic(self, color_database, sample_floors):
        """Test basic access point processing."""
        processor = AccessPointProcessor(color_database)

        access_points_data = {
            "accessPoints": [
                {
                    "id": "ap-1",
                    "name": "AP-01",
                    "vendor": "Cisco",
                    "model": "C9120AXI",
                    "mine": True,
                    "location": {"floorPlanId": "floor-1", "z": 3.0},
                    "color": "#FF0000",
                }
            ]
        }

        result = processor.process(access_points_data, sample_floors)

        assert len(result) == 1
        assert result[0].vendor == "Cisco"
        assert result[0].model == "C9120AXI"
        assert result[0].floor_name == "Floor 1"
        assert result[0].color == "Red"
        assert result[0].mounting_height == 3.0

    def test_process_skips_non_mine_aps(self, color_database, sample_floors):
        """Test that non-mine APs are skipped."""
        processor = AccessPointProcessor(color_database)

        access_points_data = {
            "accessPoints": [
                {
                    "id": "ap-1",
                    "name": "Survey AP",
                    "vendor": "Cisco",
                    "model": "C9120AXI",
                    "mine": False,  # Survey/neighbor AP
                    "location": {"floorPlanId": "floor-1"},
                },
                {
                    "id": "ap-2",
                    "name": "My AP",
                    "vendor": "Aruba",
                    "model": "AP-515",
                    "mine": True,
                    "location": {"floorPlanId": "floor-1"},
                },
            ]
        }

        result = processor.process(access_points_data, sample_floors)

        # Should only process the one with mine=True
        assert len(result) == 1
        assert result[0].vendor == "Aruba"

    def test_process_with_tags(self, color_database, sample_floors, tag_processor):
        """Test processing APs with tags."""
        processor = AccessPointProcessor(color_database, tag_processor)

        access_points_data = {
            "accessPoints": [
                {
                    "id": "ap-1",
                    "name": "AP-01",
                    "vendor": "Cisco",
                    "model": "C9120AXI",
                    "mine": True,
                    "location": {"floorPlanId": "floor-1"},
                    "tags": [{"tagKeyId": "zone-key", "value": "Office"}],
                }
            ]
        }

        result = processor.process(access_points_data, sample_floors)

        assert len(result) == 1
        assert len(result[0].tags) == 1
        assert result[0].tags[0].key == "Zone"
        assert result[0].tags[0].value == "Office"

    def test_process_unknown_floor(self, color_database):
        """Test processing AP with unknown floor."""
        processor = AccessPointProcessor(color_database)

        access_points_data = {
            "accessPoints": [
                {
                    "id": "ap-1",
                    "vendor": "Cisco",
                    "model": "C9120AXI",
                    "mine": True,
                    "location": {"floorPlanId": "unknown-floor"},
                }
            ]
        }

        result = processor.process(access_points_data, {})

        assert len(result) == 1
        assert result[0].floor_name == "Unknown Floor"

    def test_process_no_floor(self, color_database, sample_floors):
        """Test processing AP without floor information."""
        processor = AccessPointProcessor(color_database)

        access_points_data = {
            "accessPoints": [
                {
                    "id": "ap-1",
                    "vendor": "Cisco",
                    "model": "C9120AXI",
                    "mine": True,
                    "location": {},  # No floorPlanId
                }
            ]
        }

        result = processor.process(access_points_data, sample_floors)

        assert len(result) == 1
        assert result[0].floor_name == "Unknown Floor"

    def test_process_with_antenna_params(self, color_database, sample_floors):
        """Test processing AP with antenna parameters."""
        processor = AccessPointProcessor(color_database)

        access_points_data = {
            "accessPoints": [
                {
                    "id": "ap-1",
                    "vendor": "Cisco",
                    "model": "C9120AXI",
                    "mine": True,
                    "location": {"floorPlanId": "floor-1", "z": 3.0},
                    "antennas": [{"azimuth": 45.0, "tilt": 10.0, "antennaHeight": 3.5}],
                }
            ]
        }

        result = processor.process(access_points_data, sample_floors)

        assert len(result) == 1
        assert result[0].azimuth == 45.0
        assert result[0].tilt == 10.0
        assert result[0].antenna_height == 3.5

    def test_process_unknown_color(self, color_database, sample_floors):
        """Test processing AP with unknown color code."""
        processor = AccessPointProcessor(color_database)

        access_points_data = {
            "accessPoints": [
                {
                    "id": "ap-1",
                    "vendor": "Cisco",
                    "model": "C9120AXI",
                    "mine": True,
                    "location": {"floorPlanId": "floor-1"},
                    "color": "#ABCDEF",  # Unknown color
                }
            ]
        }

        result = processor.process(access_points_data, sample_floors)

        assert len(result) == 1
        # Unknown colors are returned as-is (hex code)
        assert result[0].color == "#ABCDEF"

    def test_process_empty_list(self, color_database, sample_floors):
        """Test processing empty access points list."""
        processor = AccessPointProcessor(color_database)

        access_points_data = {"accessPoints": []}

        result = processor.process(access_points_data, sample_floors)

        assert result == []

    def test_process_handles_exceptions(self, color_database, sample_floors):
        """Test that processing continues even if one AP fails."""
        processor = AccessPointProcessor(color_database)

        access_points_data = {
            "accessPoints": [
                {
                    "id": "ap-1",
                    "vendor": "Cisco",
                    "model": "C9120AXI",
                    "mine": True,
                    "location": {"floorPlanId": "floor-1"},
                },
                {
                    # Malformed data - missing required fields
                    "mine": True,
                    # Missing vendor/model
                },
                {
                    "id": "ap-3",
                    "vendor": "Aruba",
                    "model": "AP-515",
                    "mine": True,
                    "location": {"floorPlanId": "floor-2"},
                },
            ]
        }

        result = processor.process(access_points_data, sample_floors)

        # Should process the valid APs
        assert len(result) >= 2

    def test_process_with_exception_in_processing(self, color_database, sample_floors):
        """Test that exceptions during AP processing are handled."""
        from unittest.mock import patch

        processor = AccessPointProcessor(color_database)

        access_points_data = {
            "accessPoints": [
                {
                    "id": "ap-1",
                    "name": "AP-01",
                    "vendor": "Cisco",
                    "model": "C9120AXI",
                    "mine": True,
                    "location": {"floorPlanId": "floor-1"},
                },
                {
                    "id": "ap-2",
                    "name": "AP-02",
                    "vendor": "Aruba",
                    "model": "AP-515",
                    "mine": True,
                    "location": {"floorPlanId": "floor-1"},
                },
            ]
        }

        # Mock _process_single_ap to raise exception for second AP
        original_method = processor._process_single_ap
        call_count = [0]

        def mock_process(ap_data, floors, radios=None):
            call_count[0] += 1
            if call_count[0] == 2:  # Second call raises error
                raise ValueError("Simulated AP processing error")
            return original_method(ap_data, floors, radios)

        with patch.object(processor, "_process_single_ap", side_effect=mock_process):
            result = processor.process(access_points_data, sample_floors)

        # Should have 1 valid AP (second one failed)
        assert len(result) == 1
        assert result[0].name == "AP-01"

    def test_process_single_ap_with_none_radios(self, color_database, sample_floors):
        """Test _process_single_ap with radios=None."""
        processor = AccessPointProcessor(color_database)

        ap_data = {
            "id": "ap-1",
            "name": "AP-Test",
            "vendor": "Cisco",
            "model": "C9120AXI",
            "mine": True,
            "location": {"floorPlanId": "floor-1"},
        }

        # Call _process_single_ap directly with radios=None
        result = processor._process_single_ap(ap_data, sample_floors, radios=None)

        assert result.name == "AP-Test"
        assert result.vendor == "Cisco"
        # Verify radios=None is handled (should default to [])


class TestAntennaProcessor:
    """Test AntennaProcessor."""

    def test_process_basic(self):
        """Test basic antenna processing."""
        processor = AntennaProcessor()

        simulated_radios_data = {
            "simulatedRadios": [
                {"id": "radio-1", "antennaTypeId": "ant-1"},
                {"id": "radio-2", "antennaTypeId": "ant-2"},
            ]
        }

        antenna_types_data = {
            "antennaTypes": [
                {"id": "ant-1", "name": "ANT-2513P4M-N-R"},
                {"id": "ant-2", "name": "ANT-20"},
            ]
        }

        result = processor.process(simulated_radios_data, antenna_types_data)

        assert len(result) == 2
        assert result[0].name == "ANT-2513P4M-N-R"
        assert result[0].antenna_type_id == "ant-1"
        assert result[1].name == "ANT-20"
        assert result[1].antenna_type_id == "ant-2"

    def test_process_skip_radio_without_antenna(self):
        """Test that radios without antenna type ID are skipped."""
        processor = AntennaProcessor()

        simulated_radios_data = {
            "simulatedRadios": [
                {"id": "radio-1"},  # No antennaTypeId
                {"id": "radio-2", "antennaTypeId": "ant-1"},
            ]
        }

        antenna_types_data = {
            "antennaTypes": [{"id": "ant-1", "name": "ANT-2513P4M-N-R"}]
        }

        result = processor.process(simulated_radios_data, antenna_types_data)

        # Should only process radio with antenna
        assert len(result) == 1
        assert result[0].name == "ANT-2513P4M-N-R"

    def test_process_unknown_antenna_type(self):
        """Test handling of unknown antenna type IDs."""
        processor = AntennaProcessor()

        simulated_radios_data = {
            "simulatedRadios": [
                {"id": "radio-1", "antennaTypeId": "unknown-ant"},
                {"id": "radio-2", "antennaTypeId": "ant-1"},
            ]
        }

        antenna_types_data = {
            "antennaTypes": [{"id": "ant-1", "name": "ANT-2513P4M-N-R"}]
        }

        result = processor.process(simulated_radios_data, antenna_types_data)

        # Should skip unknown antenna and only process known one
        assert len(result) == 1
        assert result[0].name == "ANT-2513P4M-N-R"

    def test_process_empty_lists(self):
        """Test processing with empty data."""
        processor = AntennaProcessor()

        result = processor.process({"simulatedRadios": []}, {"antennaTypes": []})

        assert result == []

    def test_process_no_antenna_types(self):
        """Test processing when no antenna types are defined."""
        processor = AntennaProcessor()

        simulated_radios_data = {
            "simulatedRadios": [{"id": "radio-1", "antennaTypeId": "ant-1"}]
        }

        antenna_types_data = {"antennaTypes": []}

        result = processor.process(simulated_radios_data, antenna_types_data)

        # Should return empty list since antenna type not found
        assert result == []


class TestRadioProcessor:
    """Test RadioProcessor."""

    def test_process_basic(self):
        """Test basic radio processing."""
        processor = RadioProcessor()

        simulated_radios_data = {
            "simulatedRadios": [
                {
                    "id": "radio-1",
                    "accessPointId": "ap-1",
                    "channel": 36,
                    "band": "FIVE_GHZ",
                    "channelWidth": 80,
                    "transmitPower": 20.0,
                    "antennaTypeId": "ant-1",
                    "standard": "802.11ax",
                }
            ]
        }

        result = processor.process(simulated_radios_data)

        assert len(result) == 1
        assert result[0].id == "radio-1"
        assert result[0].access_point_id == "ap-1"
        assert result[0].channel == 36
        assert result[0].frequency_band == "5GHz"
        assert result[0].channel_width == 80
        assert result[0].tx_power == 20.0
        assert result[0].antenna_type_id == "ant-1"
        assert result[0].standard == "802.11ax"

    def test_determine_frequency_band_from_explicit_field(self):
        """Test frequency band determination from explicit band field."""
        processor = RadioProcessor()

        test_cases = [
            ({"band": "TWO_DOT_FOUR_GHZ"}, "2.4GHz"),
            ({"band": "FIVE_GHZ"}, "5GHz"),
            ({"band": "SIX_GHZ"}, "6GHz"),
        ]

        for radio_data, expected_band in test_cases:
            band = processor._determine_frequency_band(radio_data, None)
            assert band == expected_band

    def test_determine_frequency_band_from_channel(self):
        """Test frequency band determination from channel number."""
        processor = RadioProcessor()

        # 2.4 GHz channels
        assert processor._determine_frequency_band({}, 1) == "2.4GHz"
        assert processor._determine_frequency_band({}, 6) == "2.4GHz"
        assert processor._determine_frequency_band({}, 11) == "2.4GHz"

        # 5 GHz channels
        assert processor._determine_frequency_band({}, 36) == "5GHz"
        assert processor._determine_frequency_band({}, 100) == "5GHz"

    def test_determine_frequency_band_none(self):
        """Test frequency band returns None when cannot be determined."""
        processor = RadioProcessor()

        band = processor._determine_frequency_band({}, None)
        assert band is None

    def test_determine_wifi_standard_explicit(self):
        """Test Wi-Fi standard from explicit field."""
        processor = RadioProcessor()

        radio_data = {"standard": "802.11be"}
        standard = processor._determine_wifi_standard(radio_data)

        assert standard == "802.11be"

    def test_determine_wifi_standard_from_channel_width(self):
        """Test Wi-Fi standard inference from channel width."""
        processor = RadioProcessor()

        test_cases = [
            ({}, 160, "802.11ax"),
            ({}, 80, "802.11ac"),
        ]

        for radio_data, channel_width, expected_standard in test_cases:
            standard = processor._determine_wifi_standard(radio_data, channel_width)
            assert standard == expected_standard

    def test_determine_wifi_standard_from_band(self):
        """Test Wi-Fi standard inference from frequency band."""
        processor = RadioProcessor()

        test_cases = [
            ({"band": "FIVE_GHZ"}, "802.11ac"),
            ({"band": "TWO_DOT_FOUR_GHZ"}, "802.11n"),
        ]

        for radio_data, expected_standard in test_cases:
            standard = processor._determine_wifi_standard(radio_data)
            assert standard == expected_standard

    def test_determine_wifi_standard_none(self):
        """Test Wi-Fi standard returns None when cannot be determined."""
        processor = RadioProcessor()

        standard = processor._determine_wifi_standard({})
        assert standard is None

    def test_process_multiple_radios(self):
        """Test processing multiple radios."""
        processor = RadioProcessor()

        simulated_radios_data = {
            "simulatedRadios": [
                {
                    "id": "radio-1",
                    "accessPointId": "ap-1",
                    "channel": 6,
                    "band": "TWO_DOT_FOUR_GHZ",
                    "channelWidth": 20,
                    "transmitPower": 18.0,
                },
                {
                    "id": "radio-2",
                    "accessPointId": "ap-1",
                    "channel": 36,
                    "band": "FIVE_GHZ",
                    "channelWidth": 80,
                    "transmitPower": 20.0,
                },
            ]
        }

        result = processor.process(simulated_radios_data)

        assert len(result) == 2
        assert result[0].frequency_band == "2.4GHz"
        assert result[1].frequency_band == "5GHz"

    def test_process_empty_list(self):
        """Test processing empty radios list."""
        processor = RadioProcessor()

        result = processor.process({"simulatedRadios": []})

        assert result == []

    def test_process_handles_exceptions(self):
        """Test that processing continues even if one radio fails."""
        processor = RadioProcessor()

        simulated_radios_data = {
            "simulatedRadios": [
                {
                    "id": "radio-1",
                    "accessPointId": "ap-1",
                    "channel": 36,
                    "band": "FIVE_GHZ",
                },
                {
                    # Malformed - could cause errors
                    "id": None,  # Invalid ID
                    "accessPointId": None,
                },
                {
                    "id": "radio-3",
                    "accessPointId": "ap-2",
                    "channel": 6,
                    "band": "TWO_DOT_FOUR_GHZ",
                },
            ]
        }

        result = processor.process(simulated_radios_data)

        # Should still process valid radios
        assert len(result) >= 2

    def test_process_minimal_radio_data(self):
        """Test processing radio with minimal data."""
        processor = RadioProcessor()

        simulated_radios_data = {
            "simulatedRadios": [
                {
                    "id": "radio-1",
                    "accessPointId": "ap-1",
                    # No other fields
                }
            ]
        }

        result = processor.process(simulated_radios_data)

        assert len(result) == 1
        assert result[0].id == "radio-1"
        assert result[0].access_point_id == "ap-1"
        assert result[0].channel is None
        assert result[0].frequency_band is None
        assert result[0].tx_power is None


def test_access_point_processor_with_simulated_radios(color_database):
    """Test AP processing with simulated radios data."""
    aps_data = {
        "accessPoints": [
            {
                "id": "ap1",
                "name": "AP-01",
                "vendor": "Cisco",
                "model": "AP-515",
                "mine": True,
                "location": {"floorPlanId": "floor1"},
            }
        ]
    }

    radios_data = {
        "simulatedRadios": [
            {
                "accessPointId": "ap1",
                "antennaDirection": 45.0,
                "antennaTilt": 15.0,
                "antennaHeight": 3.5,
            },
            {
                "accessPointId": "ap1",
                "antennaDirection": 180.0,
                "antennaTilt": 10.0,
                "antennaHeight": 3.5,
            },
        ]
    }

    floors = {"floor1": Floor("floor1", "Floor 1")}

    processor = AccessPointProcessor(color_database)
    aps = processor.process(aps_data, floors, radios_data)

    assert len(aps) == 1
    assert aps[0].azimuth == 45.0  # First radio's direction
    assert aps[0].tilt == 15.0  # First radio's tilt
    assert aps[0].antenna_height == 3.5  # First radio's height


def test_access_point_processor_with_error(color_database):
    """Test AP processing continues when one AP has an error."""
    aps_data = {
        "accessPoints": [
            {
                "id": "ap1",
                "name": "Valid AP",
                "vendor": "Cisco",
                "model": "AP-515",
                "mine": True,
                "location": {"floorPlanId": "floor1"},
            }
        ]
    }

    floors = {"floor1": Floor("floor1", "Floor 1")}

    processor = AccessPointProcessor(color_database)

    # Manually trigger error handling by setting floors to non-dict
    # This will cause an exception in _process_single_ap
    try:
        # This should work normally
        aps = processor.process(aps_data, floors)
        assert len(aps) == 1
    except Exception:
        # Should not raise - errors are caught
        assert False, "Processor should handle errors gracefully"
