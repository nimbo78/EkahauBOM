#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for analytics module."""

from __future__ import annotations


import pytest
from ekahau_bom.models import AccessPoint, Tag, Radio
from ekahau_bom.analytics import (
    GroupingAnalytics,
    CoverageAnalytics,
    MountingAnalytics,
    RadioAnalytics,
)


@pytest.fixture
def sample_aps():
    """Create sample access points for testing."""
    return [
        AccessPoint(
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[Tag(key="Location", value="Building A", tag_key_id="1")],
            mine=True,
            floor_id="f1",
        ),
        AccessPoint(
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[Tag(key="Location", value="Building A", tag_key_id="1")],
            mine=True,
            floor_id="f1",
        ),
        AccessPoint(
            vendor="Cisco",
            model="AP-635",
            color="Red",
            floor_name="Floor 2",
            tags=[Tag(key="Location", value="Building B", tag_key_id="1")],
            mine=True,
            floor_id="f2",
        ),
        AccessPoint(
            vendor="Aruba",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[Tag(key="Location", value="Building A", tag_key_id="1")],
            mine=True,
            floor_id="f1",
        ),
    ]


class TestGroupingAnalytics:
    """Test GroupingAnalytics class."""

    def test_group_by_floor(self, sample_aps):
        """Test grouping by floor."""
        result = GroupingAnalytics.group_by_floor(sample_aps)
        assert result["Floor 1"] == 3
        assert result["Floor 2"] == 1
        assert len(result) == 2

    def test_group_by_color(self, sample_aps):
        """Test grouping by color."""
        result = GroupingAnalytics.group_by_color(sample_aps)
        assert result["Yellow"] == 3
        assert result["Red"] == 1
        assert len(result) == 2

    def test_group_by_vendor(self, sample_aps):
        """Test grouping by vendor."""
        result = GroupingAnalytics.group_by_vendor(sample_aps)
        assert result["Cisco"] == 3
        assert result["Aruba"] == 1
        assert len(result) == 2

    def test_group_by_model(self, sample_aps):
        """Test grouping by model."""
        result = GroupingAnalytics.group_by_model(sample_aps)
        assert result["AP-515"] == 3
        assert result["AP-635"] == 1
        assert len(result) == 2

    def test_group_by_tag(self, sample_aps):
        """Test grouping by tag key."""
        result = GroupingAnalytics.group_by_tag(sample_aps, "Location")
        assert result["Building A"] == 3
        assert result["Building B"] == 1
        assert len(result) == 2

    def test_group_by_tag_nonexistent(self, sample_aps):
        """Test grouping by non-existent tag key."""
        result = GroupingAnalytics.group_by_tag(sample_aps, "NonExistent")
        assert len(result) == 1
        assert result["No NonExistent"] == 4  # Untagged APs get "No {tag_key}"

    def test_group_by_tag_with_untagged(self):
        """Test grouping by tag with some APs untagged."""
        aps = [
            AccessPoint(
                "Cisco",
                "AP-515",
                "Yellow",
                "Floor 1",
                tags=[Tag("Zone", "Office", "1")],
            ),
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1", tags=[]),
            AccessPoint("Aruba", "AP-635", "Red", "Floor 2", tags=[Tag("Zone", "Office", "1")]),
        ]
        result = GroupingAnalytics.group_by_tag(aps, "Zone")
        assert result["Office"] == 2
        assert result["No Zone"] == 1  # Untagged APs get "No Zone"

    def test_calculate_percentages(self):
        """Test percentage calculation."""
        counts = {"A": 10, "B": 20, "C": 70}
        result = GroupingAnalytics.calculate_percentages(counts)
        assert result["A"] == (10, 10.0)
        assert result["B"] == (20, 20.0)
        assert result["C"] == (70, 70.0)

    def test_calculate_percentages_empty(self):
        """Test percentage calculation with empty dict."""
        result = GroupingAnalytics.calculate_percentages({})
        assert result == {}

    def test_calculate_percentages_single(self):
        """Test percentage calculation with single item."""
        result = GroupingAnalytics.calculate_percentages({"A": 5})
        assert result["A"] == (5, 100.0)

    def test_group_by_empty_list(self):
        """Test grouping with empty access point list."""
        result = GroupingAnalytics.group_by_floor([])
        assert result == {}

    def test_group_by_color_with_none(self):
        """Test grouping by color when some APs have no color."""
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-515",
                color=None,
                floor_name="Floor 1",
            ),
            AccessPoint(
                id="ap2",
                vendor="Cisco",
                model="AP-515",
                color="Yellow",
                floor_name="Floor 1",
            ),
            AccessPoint(
                id="ap3",
                vendor="Aruba",
                model="AP-635",
                color=None,
                floor_name="Floor 2",
            ),
        ]
        result = GroupingAnalytics.group_by_color(aps)
        assert result["No Color"] == 2  # None colors mapped to "No Color"
        assert result["Yellow"] == 1

    def test_group_by_dimension_vendor(self, sample_aps):
        """Test group_by_dimension with vendor."""
        result = GroupingAnalytics.group_by_dimension(sample_aps, "vendor")
        assert result["Cisco"] == 3
        assert result["Aruba"] == 1

    def test_group_by_dimension_model(self, sample_aps):
        """Test group_by_dimension with model."""
        result = GroupingAnalytics.group_by_dimension(sample_aps, "model")
        assert result["AP-515"] == 3
        assert result["AP-635"] == 1

    def test_group_by_dimension_floor(self, sample_aps):
        """Test group_by_dimension with floor."""
        result = GroupingAnalytics.group_by_dimension(sample_aps, "floor")
        assert result["Floor 1"] == 3
        assert result["Floor 2"] == 1

    def test_group_by_dimension_color(self, sample_aps):
        """Test group_by_dimension with color."""
        result = GroupingAnalytics.group_by_dimension(sample_aps, "color")
        assert result["Yellow"] == 3
        assert result["Red"] == 1

    def test_group_by_dimension_tag(self, sample_aps):
        """Test group_by_dimension with tag."""
        result = GroupingAnalytics.group_by_dimension(sample_aps, "tag", tag_key="Location")
        assert result["Building A"] == 3
        assert result["Building B"] == 1

    def test_group_by_dimension_unknown(self, sample_aps):
        """Test group_by_dimension with unknown dimension."""
        result = GroupingAnalytics.group_by_dimension(sample_aps, "unknown")
        assert result == {}

    def test_group_by_vendor_and_model(self, sample_aps):
        """Test grouping by vendor and model combination."""
        result = GroupingAnalytics.group_by_vendor_and_model(sample_aps)
        assert result[("Cisco", "AP-515")] == 2
        assert result[("Cisco", "AP-635")] == 1
        assert result[("Aruba", "AP-515")] == 1
        assert len(result) == 3

    def test_multi_dimensional_grouping_floor_color(self, sample_aps):
        """Test multi-dimensional grouping with floor and color."""
        result = GroupingAnalytics.multi_dimensional_grouping(sample_aps, ["floor", "color"])
        assert result[("Floor 1", "Yellow")] == 3
        assert result[("Floor 2", "Red")] == 1

    def test_multi_dimensional_grouping_vendor_model_floor(self, sample_aps):
        """Test multi-dimensional grouping with vendor, model, and floor."""
        result = GroupingAnalytics.multi_dimensional_grouping(
            sample_aps, ["vendor", "model", "floor"]
        )
        assert result[("Cisco", "AP-515", "Floor 1")] == 2
        assert result[("Cisco", "AP-635", "Floor 2")] == 1
        assert result[("Aruba", "AP-515", "Floor 1")] == 1

    def test_multi_dimensional_grouping_with_tag(self, sample_aps):
        """Test multi-dimensional grouping with tag dimension."""
        result = GroupingAnalytics.multi_dimensional_grouping(
            sample_aps, ["floor", "tag"], tag_key="Location"
        )
        assert result[("Floor 1", "Building A")] == 3
        assert result[("Floor 2", "Building B")] == 1

    def test_multi_dimensional_grouping_unknown_dimension(self, sample_aps):
        """Test multi-dimensional grouping with unknown dimension."""
        result = GroupingAnalytics.multi_dimensional_grouping(sample_aps, ["floor", "unknown"])
        # Should still work, with "Unknown" for the bad dimension
        assert len(result) > 0


class TestMountingAnalytics:
    """Test MountingAnalytics class."""

    def test_calculate_mounting_metrics_basic(self):
        """Test basic mounting metrics calculation."""
        aps = [
            AccessPoint(
                "Cisco",
                "AP-515",
                "Yellow",
                "Floor 1",
                mounting_height=3.0,
                azimuth=45.0,
                tilt=10.0,
            ),
            AccessPoint(
                "Cisco",
                "AP-635",
                "Red",
                "Floor 2",
                mounting_height=4.0,
                azimuth=90.0,
                tilt=15.0,
            ),
            AccessPoint(
                "Aruba",
                "AP-515",
                "Blue",
                "Floor 1",
                mounting_height=3.5,
                azimuth=180.0,
                tilt=5.0,
            ),
        ]

        metrics = MountingAnalytics.calculate_mounting_metrics(aps)

        assert metrics.avg_height == 3.5
        assert metrics.min_height == 3.0
        assert metrics.max_height == 4.0
        assert metrics.aps_with_height == 3
        assert metrics.avg_azimuth == 105.0  # (45+90+180)/3
        assert metrics.avg_tilt == 10.0  # (10+15+5)/3

    def test_calculate_mounting_metrics_none_values(self):
        """Test mounting metrics with None values."""
        aps = [
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1", mounting_height=None),
            AccessPoint("Cisco", "AP-635", "Red", "Floor 2", mounting_height=3.0),
        ]

        metrics = MountingAnalytics.calculate_mounting_metrics(aps)

        assert metrics.avg_height == 3.0
        assert metrics.aps_with_height == 1

    def test_group_by_height_range(self):
        """Test grouping APs by height range."""
        aps = [
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1", mounting_height=2.0),  # < 2.5m
            AccessPoint("Cisco", "AP-635", "Red", "Floor 2", mounting_height=3.0),  # 2.5-3.5m
            AccessPoint("Aruba", "AP-515", "Blue", "Floor 1", mounting_height=4.0),  # 3.5-4.5m
            AccessPoint("Cisco", "C9120", "Yellow", "Floor 3", mounting_height=5.0),  # 4.5-6.0m
            AccessPoint("Aruba", "AP-635", "Red", "Floor 4", mounting_height=7.0),  # > 6.0m
            AccessPoint("Cisco", "AP-515", "Blue", "Floor 5", mounting_height=None),  # Unknown
        ]

        result = MountingAnalytics.group_by_height_range(aps)

        assert result["< 2.5m"] == 1
        assert result["2.5-3.5m"] == 1
        assert result["3.5-4.5m"] == 1
        assert result["4.5-6.0m"] == 1
        assert result["> 6.0m"] == 1
        assert result["Unknown"] == 1


class TestRadioAnalytics:
    """Test RadioAnalytics class."""

    def test_calculate_radio_metrics_basic(self):
        """Test basic radio metrics calculation."""
        radios = [
            Radio("r1", "ap1", "2.4 GHz", 6, 20, 18.0, standard="802.11n"),
            Radio("r2", "ap2", "5 GHz", 36, 80, 20.0, standard="802.11ac"),
            Radio("r3", "ap3", "5 GHz", 100, 80, 22.0, standard="802.11ax"),
        ]

        metrics = RadioAnalytics.calculate_radio_metrics(radios)

        assert metrics.total_radios == 3
        assert metrics.band_distribution["2.4 GHz"] == 1
        assert metrics.band_distribution["5 GHz"] == 2
        assert metrics.avg_tx_power == 20.0  # (18+20+22)/3
        assert metrics.min_tx_power == 18.0
        assert metrics.max_tx_power == 22.0

    def test_get_tx_power_distribution(self):
        """Test TX power distribution."""
        radios = [
            Radio("r1", "ap1", "2.4 GHz", 6, 20, 8.0),  # < 10 dBm
            Radio("r2", "ap2", "5 GHz", 36, 80, 12.0),  # 10-15 dBm
            Radio("r3", "ap3", "5 GHz", 100, 80, 18.0),  # 15-20 dBm
            Radio("r4", "ap4", "5 GHz", 149, 80, 22.0),  # 20-25 dBm
            Radio("r5", "ap5", "6 GHz", 37, 160, 28.0),  # > 25 dBm
        ]

        result = RadioAnalytics.get_tx_power_distribution(radios)

        assert result["< 10 dBm"] == 1
        assert result["10-15 dBm"] == 1
        assert result["15-20 dBm"] == 1
        assert result["20-25 dBm"] == 1
        assert result["> 25 dBm"] == 1

    def test_group_by_frequency_band(self):
        """Test grouping radios by frequency band."""
        radios = [
            Radio("r1", "ap1", "2.4 GHz", 6, 20, 18.0),
            Radio("r2", "ap2", "5 GHz", 36, 80, 20.0),
            Radio("r3", "ap3", "5 GHz", 100, 80, 22.0),
            Radio("r4", "ap4", "6 GHz", 37, 160, 15.0),
        ]

        result = RadioAnalytics.group_by_frequency_band(radios)

        assert result["2.4 GHz"] == 1
        assert result["5 GHz"] == 2
        assert result["6 GHz"] == 1


class TestCoverageAnalytics:
    """Test CoverageAnalytics class."""

    def test_calculate_coverage_metrics_basic(self):
        """Test basic coverage metrics calculation."""
        aps = [
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1"),
            AccessPoint("Cisco", "AP-635", "Red", "Floor 2"),
            AccessPoint("Aruba", "AP-515", "Blue", "Floor 1"),
        ]

        # Without measured areas
        metrics = CoverageAnalytics.calculate_coverage_metrics(aps, None)

        assert metrics.ap_count == 3
        # Without measured areas, total_area should be 0
        assert metrics.total_area == 0.0

    def test_calculate_coverage_metrics_with_measured_areas(self):
        """Test coverage metrics with measured areas."""
        aps = [
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1"),
            AccessPoint("Cisco", "AP-635", "Red", "Floor 2"),
        ]

        measured_areas = {
            "measuredAreas": [
                {
                    "id": "area1",
                    "size": 500.0,  # Field is called 'size', not 'area'
                    "excluded": False,
                },
                {"id": "area2", "size": 300.0, "excluded": False},
            ]
        }

        metrics = CoverageAnalytics.calculate_coverage_metrics(aps, measured_areas)

        assert metrics.ap_count == 2
        assert metrics.total_area == 800.0  # 500 + 300

    def test_calculate_coverage_metrics_empty_aps(self):
        """Test coverage metrics with empty AP list."""
        metrics = CoverageAnalytics.calculate_coverage_metrics([], None)

        assert metrics.ap_count == 0

    def test_get_summary_statistics_empty(self):
        """Test get_summary_statistics with empty AP list."""
        stats = GroupingAnalytics.get_summary_statistics([])

        assert stats["total"] == 0
        assert stats["unique_vendors"] == 0
        assert stats["unique_models"] == 0
        assert stats["unique_floors"] == 0
        assert stats["unique_colors"] == 0
        assert stats["with_tags"] == 0

    def test_get_summary_statistics_with_data(self, sample_aps):
        """Test get_summary_statistics with AP data."""
        stats = GroupingAnalytics.get_summary_statistics(sample_aps)

        assert stats["total"] == 4
        assert stats["unique_vendors"] == 2  # Cisco, Aruba
        assert stats["unique_models"] == 2  # AP-515, AP-635
        assert stats["unique_floors"] == 2  # Floor 1, Floor 2
        assert stats["unique_colors"] == 2  # Yellow, Red
        assert stats["with_tags"] == 4  # All have tags

    def test_print_grouped_results_with_data(self, caplog):
        """Test print_grouped_results with data."""
        import logging

        caplog.set_level(logging.INFO)

        grouped_data = {"Cisco": 10, "Aruba": 5, "Ubiquiti": 3}
        GroupingAnalytics.print_grouped_results(
            grouped_data, title="Test Grouping", show_percentages=True
        )

        # Check that logger was called with correct messages
        assert "Test Grouping" in caplog.text
        assert "Cisco:" in caplog.text
        assert "Aruba:" in caplog.text
        assert "Ubiquiti:" in caplog.text

    def test_print_grouped_results_empty(self, caplog):
        """Test print_grouped_results with empty data."""
        import logging

        caplog.set_level(logging.INFO)

        GroupingAnalytics.print_grouped_results({}, title="Empty Test")

        assert "Empty Test" in caplog.text
        assert "No data to display" in caplog.text

    def test_print_grouped_results_without_percentages(self, caplog):
        """Test print_grouped_results without percentages."""
        import logging

        caplog.set_level(logging.INFO)

        grouped_data = {"Cisco": 10, "Aruba": 5}
        GroupingAnalytics.print_grouped_results(
            grouped_data, title="No Percentages", show_percentages=False
        )

        assert "No Percentages" in caplog.text
        assert "Cisco:" in caplog.text


class TestRadioAnalyticsExtended:
    """Extended tests for RadioAnalytics class to improve coverage."""

    def test_group_by_channel_width(self):
        """Test grouping radios by channel width."""
        radios = [
            Radio(id="r1", access_point_id="ap1", channel_width=20),
            Radio(id="r2", access_point_id="ap2", channel_width=40),
            Radio(id="r3", access_point_id="ap3", channel_width=80),
            Radio(id="r4", access_point_id="ap4", channel_width=80),
            Radio(id="r5", access_point_id="ap5", channel_width=None),
        ]

        result = RadioAnalytics.group_by_channel_width(radios)

        assert result["20 MHz"] == 1
        assert result["40 MHz"] == 1
        assert result["80 MHz"] == 2
        assert "None MHz" not in result  # None values are filtered out

    def test_group_by_wifi_standard(self):
        """Test grouping radios by Wi-Fi standard."""
        radios = [
            Radio(id="r1", access_point_id="ap1", standard="802.11ax"),
            Radio(id="r2", access_point_id="ap2", standard="802.11ax"),
            Radio(id="r3", access_point_id="ap3", standard="802.11ac"),
            Radio(id="r4", access_point_id="ap4", standard="802.11n"),
            Radio(id="r5", access_point_id="ap5", standard=None),
        ]

        result = RadioAnalytics.group_by_wifi_standard(radios)

        assert result["802.11ax"] == 2
        assert result["802.11ac"] == 1
        assert result["802.11n"] == 1
        assert None not in result  # None values are filtered out

    def test_analyze_channel_usage_with_band_filter(self):
        """Test analyze_channel_usage with band filter."""
        radios = [
            Radio(id="r1", access_point_id="ap1", frequency_band="2.4GHz", channel=1),
            Radio(id="r2", access_point_id="ap2", frequency_band="2.4GHz", channel=6),
            Radio(id="r3", access_point_id="ap3", frequency_band="5GHz", channel=36),
            Radio(id="r4", access_point_id="ap4", frequency_band="5GHz", channel=36),
            Radio(id="r5", access_point_id="ap5", frequency_band="5GHz", channel=40),
        ]

        # Test with 5GHz filter
        result_5ghz = RadioAnalytics.analyze_channel_usage(radios, band="5GHz")

        assert result_5ghz["total_radios"] == 3
        assert result_5ghz["unique_channels"] == 2  # ch 36, 40
        assert result_5ghz["channel_distribution"][36] == 2
        assert result_5ghz["channel_distribution"][40] == 1

        # Test with 2.4GHz filter
        result_24ghz = RadioAnalytics.analyze_channel_usage(radios, band="2.4GHz")

        assert result_24ghz["total_radios"] == 2
        assert result_24ghz["unique_channels"] == 2  # ch 1, 6

    def test_analyze_channel_usage_no_filter(self):
        """Test analyze_channel_usage without band filter."""
        radios = [
            Radio(id="r1", access_point_id="ap1", frequency_band="2.4GHz", channel=1),
            Radio(id="r2", access_point_id="ap2", frequency_band="5GHz", channel=36),
            Radio(id="r3", access_point_id="ap3", frequency_band="5GHz", channel=36),
        ]

        result = RadioAnalytics.analyze_channel_usage(radios)

        assert result["total_radios"] == 3
        assert result["unique_channels"] == 2  # ch 1, 36
        assert len(result["most_used_channels"]) > 0
        assert result["avg_radios_per_channel"] == 1.5  # 3 radios / 2 channels

    def test_get_tx_power_distribution_with_none(self):
        """Test tx_power distribution with None values."""
        radios = [
            Radio(id="r1", access_point_id="ap1", tx_power=5.0),
            Radio(id="r2", access_point_id="ap2", tx_power=12.0),
            Radio(id="r3", access_point_id="ap3", tx_power=18.0),
            Radio(id="r4", access_point_id="ap4", tx_power=22.0),
            Radio(id="r5", access_point_id="ap5", tx_power=30.0),
            Radio(id="r6", access_point_id="ap6", tx_power=None),
        ]

        result = RadioAnalytics.get_tx_power_distribution(radios)

        assert result["< 10 dBm"] == 1  # 5.0
        assert result["10-15 dBm"] == 1  # 12.0
        assert result["15-20 dBm"] == 1  # 18.0
        assert result["20-25 dBm"] == 1  # 22.0
        assert result["> 25 dBm"] == 1  # 30.0
        assert result["Unknown"] == 1  # None

    def test_get_radio_summary(self):
        """Test comprehensive radio summary."""
        radios = [
            Radio(
                id="r1",
                access_point_id="ap1",
                frequency_band="5GHz",
                channel=36,
                channel_width=80,
                tx_power=20.0,
                standard="802.11ax",
            ),
            Radio(
                id="r2",
                access_point_id="ap2",
                frequency_band="2.4GHz",
                channel=6,
                channel_width=40,
                tx_power=15.0,
                standard="802.11n",
            ),
        ]

        summary = RadioAnalytics.get_radio_summary(radios)

        assert summary["total_radios"] == 2
        assert "5GHz" in summary["frequency_bands"]
        assert "2.4GHz" in summary["frequency_bands"]
        assert "80 MHz" in summary["channel_widths"]
        assert "40 MHz" in summary["channel_widths"]
        assert "802.11ax" in summary["wifi_standards"]
        assert "802.11n" in summary["wifi_standards"]
        assert summary["avg_tx_power"] == 17.5  # (20 + 15) / 2
        assert summary["min_tx_power"] == 15.0
        assert summary["max_tx_power"] == 20.0
