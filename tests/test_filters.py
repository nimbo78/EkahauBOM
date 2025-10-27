#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for filters module."""

import pytest
from ekahau_bom.models import AccessPoint, Tag
from ekahau_bom.filters import APFilter


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
            model="AP-635",
            color="Red",
            floor_name="Floor 2",
            tags=[
                Tag(key="Location", value="Building A", tag_key_id="1"),
                Tag(key="Zone", value="Office", tag_key_id="2"),
            ],
            mine=True,
            floor_id="f2",
        ),
        AccessPoint(
            vendor="Aruba",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[Tag(key="Location", value="Building B", tag_key_id="1")],
            mine=True,
            floor_id="f1",
        ),
        AccessPoint(
            vendor="Aruba",
            model="AP-635",
            color="Blue",
            floor_name="Floor 3",
            tags=[],
            mine=True,
            floor_id="f3",
        ),
    ]


class TestAPFilter:
    """Test APFilter class."""

    def test_by_floors(self, sample_aps):
        """Test filtering by floors."""
        result = APFilter.by_floors(sample_aps, ["Floor 1"])
        assert len(result) == 2
        assert all(ap.floor_name == "Floor 1" for ap in result)

    def test_by_floors_multiple(self, sample_aps):
        """Test filtering by multiple floors."""
        result = APFilter.by_floors(sample_aps, ["Floor 1", "Floor 2"])
        assert len(result) == 3

    def test_by_floors_empty_list(self, sample_aps):
        """Test filtering with empty floor list returns all."""
        result = APFilter.by_floors(sample_aps, [])
        assert len(result) == 4

    def test_by_colors(self, sample_aps):
        """Test filtering by colors."""
        result = APFilter.by_colors(sample_aps, ["Yellow"])
        assert len(result) == 2
        assert all(ap.color == "Yellow" for ap in result)

    def test_by_colors_multiple(self, sample_aps):
        """Test filtering by multiple colors."""
        result = APFilter.by_colors(sample_aps, ["Yellow", "Red"])
        assert len(result) == 3

    def test_by_vendors(self, sample_aps):
        """Test filtering by vendors."""
        result = APFilter.by_vendors(sample_aps, ["Cisco"])
        assert len(result) == 2
        assert all(ap.vendor == "Cisco" for ap in result)

    def test_by_models(self, sample_aps):
        """Test filtering by models."""
        result = APFilter.by_models(sample_aps, ["AP-515"])
        assert len(result) == 2
        assert all(ap.model == "AP-515" for ap in result)

    def test_by_tag(self, sample_aps):
        """Test filtering by tag key-value."""
        result = APFilter.by_tag(sample_aps, "Location", ["Building A"])
        assert len(result) == 2
        for ap in result:
            assert any(tag.key == "Location" and tag.value == "Building A" for tag in ap.tags)

    def test_by_tag_multiple_values(self, sample_aps):
        """Test filtering by tag with multiple values."""
        result = APFilter.by_tag(sample_aps, "Location", ["Building A", "Building B"])
        assert len(result) == 3

    def test_by_tag_no_match(self, sample_aps):
        """Test filtering by non-existent tag."""
        result = APFilter.by_tag(sample_aps, "Location", ["Building C"])
        assert len(result) == 0

    def test_by_tags_multiple(self, sample_aps):
        """Test filtering by multiple tag filters (AND logic)."""
        tag_filters = {"Location": ["Building A"], "Zone": ["Office"]}
        result = APFilter.by_tags(sample_aps, tag_filters)
        assert len(result) == 1
        assert result[0].vendor == "Cisco"
        assert result[0].model == "AP-635"

    def test_exclude_floors(self, sample_aps):
        """Test excluding floors."""
        result = APFilter.exclude_floors(sample_aps, ["Floor 1"])
        assert len(result) == 2
        assert all(ap.floor_name != "Floor 1" for ap in result)

    def test_exclude_colors(self, sample_aps):
        """Test excluding colors."""
        result = APFilter.exclude_colors(sample_aps, ["Yellow"])
        assert len(result) == 2
        assert all(ap.color != "Yellow" for ap in result)

    def test_exclude_vendors(self, sample_aps):
        """Test excluding vendors."""
        result = APFilter.exclude_vendors(sample_aps, ["Cisco"])
        assert len(result) == 2
        assert all(ap.vendor != "Cisco" for ap in result)

    def test_apply_filters_combined(self, sample_aps):
        """Test applying multiple filters together."""
        result = APFilter.apply_filters(
            sample_aps,
            include_floors=["Floor 1", "Floor 2"],
            include_colors=["Yellow", "Red"],
            exclude_vendors=["Aruba"],
        )
        assert len(result) == 2
        assert all(ap.vendor == "Cisco" for ap in result)
        assert all(ap.floor_name in ["Floor 1", "Floor 2"] for ap in result)
        assert all(ap.color in ["Yellow", "Red"] for ap in result)

    def test_apply_filters_with_tags(self, sample_aps):
        """Test applying filters with tag filtering."""
        result = APFilter.apply_filters(sample_aps, include_tags={"Location": ["Building A"]})
        assert len(result) == 2

    def test_apply_filters_empty(self, sample_aps):
        """Test apply_filters with no filters returns all."""
        result = APFilter.apply_filters(sample_aps)
        assert len(result) == 4

    def test_by_colors_empty_list(self, sample_aps):
        """Test by_colors with empty list returns all."""
        result = APFilter.by_colors(sample_aps, [])
        assert len(result) == 4

    def test_by_vendors_empty_list(self, sample_aps):
        """Test by_vendors with empty list returns all."""
        result = APFilter.by_vendors(sample_aps, [])
        assert len(result) == 4

    def test_by_models_empty_list(self, sample_aps):
        """Test by_models with empty list returns all."""
        result = APFilter.by_models(sample_aps, [])
        assert len(result) == 4

    def test_by_tag_empty_values(self, sample_aps):
        """Test by_tag with empty values list returns all."""
        result = APFilter.by_tag(sample_aps, "Location", [])
        assert len(result) == 4

    def test_by_tags_empty_dict(self, sample_aps):
        """Test by_tags with empty dict returns all."""
        result = APFilter.by_tags(sample_aps, {})
        assert len(result) == 4

    def test_exclude_floors_empty_list(self, sample_aps):
        """Test exclude_floors with empty list returns all."""
        result = APFilter.exclude_floors(sample_aps, [])
        assert len(result) == 4

    def test_exclude_colors_empty_list(self, sample_aps):
        """Test exclude_colors with empty list returns all."""
        result = APFilter.exclude_colors(sample_aps, [])
        assert len(result) == 4

    def test_exclude_vendors_empty_list(self, sample_aps):
        """Test exclude_vendors with empty list returns all."""
        result = APFilter.exclude_vendors(sample_aps, [])
        assert len(result) == 4

    def test_apply_filters_with_include_vendors(self, sample_aps):
        """Test apply_filters with include_vendors."""
        result = APFilter.apply_filters(sample_aps, include_vendors=["Cisco"])
        assert len(result) == 2

    def test_apply_filters_with_include_models(self, sample_aps):
        """Test apply_filters with include_models."""
        result = APFilter.apply_filters(sample_aps, include_models=["AP-515"])
        assert len(result) == 2

    def test_apply_filters_with_exclude_floors(self, sample_aps):
        """Test apply_filters with exclude_floors."""
        result = APFilter.apply_filters(sample_aps, exclude_floors=["Floor 1"])
        assert len(result) == 2

    def test_apply_filters_with_exclude_colors(self, sample_aps):
        """Test apply_filters with exclude_colors."""
        result = APFilter.apply_filters(sample_aps, exclude_colors=["Yellow"])
        assert len(result) == 2
