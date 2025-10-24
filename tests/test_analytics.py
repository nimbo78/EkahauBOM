#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for analytics module."""

import pytest
from ekahau_bom.models import AccessPoint, Tag
from ekahau_bom.analytics import GroupingAnalytics


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
            floor_id="f1"
        ),
        AccessPoint(
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[Tag(key="Location", value="Building A", tag_key_id="1")],
            mine=True,
            floor_id="f1"
        ),
        AccessPoint(
            vendor="Cisco",
            model="AP-635",
            color="Red",
            floor_name="Floor 2",
            tags=[Tag(key="Location", value="Building B", tag_key_id="1")],
            mine=True,
            floor_id="f2"
        ),
        AccessPoint(
            vendor="Aruba",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[Tag(key="Location", value="Building A", tag_key_id="1")],
            mine=True,
            floor_id="f1"
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
        assert result["Not Tagged"] == 4

    def test_group_by_tag_with_untagged(self):
        """Test grouping by tag with some APs untagged."""
        aps = [
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1",
                       tags=[Tag("Zone", "Office", "1")]),
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1",
                       tags=[]),
            AccessPoint("Aruba", "AP-635", "Red", "Floor 2",
                       tags=[Tag("Zone", "Office", "1")]),
        ]
        result = GroupingAnalytics.group_by_tag(aps, "Zone")
        assert result["Office"] == 2
        assert result["Not Tagged"] == 1

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
            AccessPoint("Cisco", "AP-515", None, "Floor 1"),
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1"),
            AccessPoint("Aruba", "AP-635", None, "Floor 2"),
        ]
        result = GroupingAnalytics.group_by_color(aps)
        assert result[None] == 2
        assert result["Yellow"] == 1
