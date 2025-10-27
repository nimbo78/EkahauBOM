"""Tests for models module."""

from __future__ import annotations


import pytest
from ekahau_bom.models import Tag, Radio, AccessPoint, Antenna


class TestTagModel:
    """Tests for Tag model."""

    def test_tag_hash(self):
        """Test that Tag is hashable."""
        tag1 = Tag(key="Location", value="Office", tag_key_id="loc1")
        tag2 = Tag(key="Location", value="Office", tag_key_id="loc1")
        tag3 = Tag(key="Location", value="Warehouse", tag_key_id="loc1")

        # Same key and value should have same hash
        assert hash(tag1) == hash(tag2)

        # Different value should have different hash
        assert hash(tag1) != hash(tag3)

        # Can be used in sets
        tag_set = {tag1, tag2, tag3}
        assert len(tag_set) == 2  # tag1 and tag2 are same

    def test_tag_str(self):
        """Test Tag string representation."""
        tag = Tag(key="Location", value="Office", tag_key_id="loc1")

        assert str(tag) == "Location:Office"


class TestRadioModel:
    """Tests for Radio model."""

    def test_radio_hash(self):
        """Test that Radio is hashable."""
        radio1 = Radio(id="radio1", access_point_id="ap1")
        radio2 = Radio(id="radio1", access_point_id="ap1")  # Identical
        radio3 = Radio(id="radio2", access_point_id="ap1")

        # Same id should have same hash
        assert hash(radio1) == hash(radio2)

        # Different id should have different hash
        assert hash(radio1) != hash(radio3)

        # Can be used in sets (hash method is called)
        radio_set = {radio1, radio3}
        assert len(radio_set) == 2


class TestAccessPointModel:
    """Tests for AccessPoint model."""

    def test_access_point_hash(self):
        """Test that AccessPoint is hashable."""
        ap1 = AccessPoint(
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[],
        )
        ap2 = AccessPoint(
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[],  # Same tags for identical object
        )
        ap3 = AccessPoint(
            vendor="Aruba",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[],
        )

        # Same vendor/model/color/floor should have same hash
        assert hash(ap1) == hash(ap2)

        # Different vendor should have different hash
        assert hash(ap1) != hash(ap3)

        # Can be used in sets and Counter (which requires hashable)
        ap_set = {ap1, ap3}
        assert len(ap_set) == 2

    def test_get_tag_value_found(self):
        """Test get_tag_value when tag exists."""
        tags = [
            Tag("Location", "Office", "loc1"),
            Tag("Department", "IT", "dept1"),
        ]
        ap = AccessPoint(
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=tags,
        )

        assert ap.get_tag_value("Location") == "Office"
        assert ap.get_tag_value("Department") == "IT"

    def test_get_tag_value_not_found(self):
        """Test get_tag_value when tag doesn't exist."""
        tags = [Tag("Location", "Office", "loc1")]
        ap = AccessPoint(
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=tags,
        )

        assert ap.get_tag_value("NonExistent") is None

    def test_get_tag_value_empty_tags(self):
        """Test get_tag_value with no tags."""
        ap = AccessPoint(
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[],
        )

        assert ap.get_tag_value("Location") is None

    def test_has_tag_key_only(self):
        """Test has_tag checking for key existence only."""
        tags = [
            Tag("Location", "Office", "loc1"),
            Tag("Department", "IT", "dept1"),
        ]
        ap = AccessPoint(
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=tags,
        )

        # Check key existence
        assert ap.has_tag("Location") is True
        assert ap.has_tag("Department") is True
        assert ap.has_tag("NonExistent") is False

    def test_has_tag_with_value(self):
        """Test has_tag checking for key and value match."""
        tags = [
            Tag("Location", "Office", "loc1"),
            Tag("Department", "IT", "dept1"),
        ]
        ap = AccessPoint(
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=tags,
        )

        # Check key and value match
        assert ap.has_tag("Location", "Office") is True
        assert ap.has_tag("Location", "Warehouse") is False
        assert ap.has_tag("Department", "IT") is True
        assert ap.has_tag("NonExistent", "Value") is False

    def test_has_tag_empty_tags(self):
        """Test has_tag with no tags."""
        ap = AccessPoint(
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[],
        )

        assert ap.has_tag("Location") is False
        assert ap.has_tag("Location", "Office") is False


class TestAntennaModel:
    """Tests for Antenna model."""

    def test_antenna_hash(self):
        """Test that Antenna is hashable."""
        antenna1 = Antenna(name="Antenna1", antenna_type_id="type1")
        antenna2 = Antenna(name="Antenna1", antenna_type_id="type1")  # Identical
        antenna3 = Antenna(name="Antenna2", antenna_type_id="type1")

        # Same name and type_id should have same hash
        assert hash(antenna1) == hash(antenna2)

        # Different name should have different hash
        assert hash(antenna1) != hash(antenna3)

        # Can be used in sets and Counter (which requires hashable)
        antenna_set = {antenna1, antenna3}
        assert len(antenna_set) == 2
