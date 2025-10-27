#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for tag processor module."""

import pytest
from ekahau_bom.processors.tags import TagProcessor
from ekahau_bom.models import Tag, TagKey


@pytest.fixture
def sample_tag_keys_data():
    """Sample tag keys data from Ekahau project."""
    return {
        "tagKeys": [
            {"id": "tk1", "key": "Location"},
            {"id": "tk2", "key": "Zone"},
            {"id": "tk3", "key": "Department"},
        ]
    }


@pytest.fixture
def sample_ap_tags():
    """Sample AP tags data from Ekahau project."""
    return [
        {"tagKeyId": "tk1", "value": "Building A"},
        {"tagKeyId": "tk2", "value": "Office"},
    ]


class TestTagProcessor:
    """Test TagProcessor class."""

    def test_init_with_tag_keys(self, sample_tag_keys_data):
        """Test initialization with tag keys."""
        processor = TagProcessor(sample_tag_keys_data)
        assert len(processor.tag_keys_map) == 3
        assert processor.tag_keys_map["tk1"] == "Location"
        assert processor.tag_keys_map["tk2"] == "Zone"
        assert processor.tag_keys_map["tk3"] == "Department"

    def test_init_empty_tag_keys(self):
        """Test initialization with empty tag keys."""
        processor = TagProcessor({"tagKeys": []})
        assert len(processor.tag_keys_map) == 0
        assert processor.tag_keys == []

    def test_init_no_tag_keys(self):
        """Test initialization with no tag keys key."""
        processor = TagProcessor({})
        assert len(processor.tag_keys_map) == 0
        assert processor.tag_keys == []

    def test_get_tag_key_names(self, sample_tag_keys_data):
        """Test getting tag key names."""
        processor = TagProcessor(sample_tag_keys_data)
        names = processor.get_tag_key_names()
        assert len(names) == 3
        assert "Location" in names
        assert "Zone" in names
        assert "Department" in names

    def test_get_tag_key_names_empty(self):
        """Test getting tag key names when empty."""
        processor = TagProcessor({})
        names = processor.get_tag_key_names()
        assert names == []

    def test_process_ap_tags(self, sample_tag_keys_data, sample_ap_tags):
        """Test processing AP tags."""
        processor = TagProcessor(sample_tag_keys_data)
        tags = processor.process_ap_tags(sample_ap_tags)

        assert len(tags) == 2
        assert tags[0].key == "Location"
        assert tags[0].value == "Building A"
        assert tags[0].tag_key_id == "tk1"
        assert tags[1].key == "Zone"
        assert tags[1].value == "Office"
        assert tags[1].tag_key_id == "tk2"

    def test_process_ap_tags_empty(self, sample_tag_keys_data):
        """Test processing empty AP tags."""
        processor = TagProcessor(sample_tag_keys_data)
        tags = processor.process_ap_tags([])
        assert tags == []

    def test_process_ap_tags_unknown_key_id(self, sample_tag_keys_data):
        """Test processing AP tags with unknown tag key ID."""
        processor = TagProcessor(sample_tag_keys_data)
        ap_tags = [{"tagKeyId": "unknown_id", "value": "Some Value"}]
        tags = processor.process_ap_tags(ap_tags)

        assert len(tags) == 1
        assert tags[0].key == "Unknown"  # Unknown tag keys get "Unknown"
        assert tags[0].value == "Some Value"
        assert tags[0].tag_key_id == "unknown_id"

    def test_process_ap_tags_missing_fields(self, sample_tag_keys_data):
        """Test processing AP tags with missing fields."""
        processor = TagProcessor(sample_tag_keys_data)
        ap_tags = [
            {"tagKeyId": "tk1"},  # Missing value
            {"value": "Some Value"},  # Missing tagKeyId
            {},  # Missing both
        ]
        tags = processor.process_ap_tags(ap_tags)

        # Should handle missing fields gracefully
        assert len(tags) == 3
        assert tags[0].value == ""  # Default empty value
        assert tags[1].tag_key_id == ""  # Default empty tagKeyId

    def test_tag_key_model(self):
        """Test TagKey dataclass."""
        tag_key = TagKey(id="tk1", key="Location")
        assert tag_key.id == "tk1"
        assert tag_key.key == "Location"

    def test_tag_model(self):
        """Test Tag dataclass."""
        tag = Tag(key="Location", value="Building A", tag_key_id="tk1")
        assert tag.key == "Location"
        assert tag.value == "Building A"
        assert tag.tag_key_id == "tk1"

    def test_tag_str(self):
        """Test Tag string representation."""
        tag = Tag(key="Location", value="Building A", tag_key_id="tk1")
        assert str(tag) == "Location:Building A"

    def test_tag_hash(self):
        """Test Tag is hashable."""
        tag1 = Tag(key="Location", value="Building A", tag_key_id="tk1")
        tag2 = Tag(key="Location", value="Building A", tag_key_id="tk1")
        tag3 = Tag(key="Location", value="Building B", tag_key_id="tk2")

        # Same key and value should have same hash
        assert hash(tag1) == hash(tag2)
        # Different value should have different hash
        assert hash(tag1) != hash(tag3)

        # Should be usable in sets
        tag_set = {tag1, tag2, tag3}
        assert len(tag_set) == 2  # tag1 and tag2 are duplicates

    def test_processor_with_malformed_data(self):
        """Test processor handles malformed data gracefully."""
        malformed_data = {
            "tagKeys": [
                {"id": "tk1"},  # Missing key
                {"key": "Location"},  # Missing id
                "not a dict",  # Invalid format
            ]
        }
        # Should not raise exception
        processor = TagProcessor(malformed_data)
        # Should have processed what it could
        assert isinstance(processor.tag_keys_map, dict)

    def test_has_tag_key_exists(self, sample_tag_keys_data):
        """Test has_tag_key when tag key exists."""
        processor = TagProcessor(sample_tag_keys_data)
        assert processor.has_tag_key("Location") is True
        assert processor.has_tag_key("Zone") is True
        assert processor.has_tag_key("Department") is True

    def test_has_tag_key_not_exists(self, sample_tag_keys_data):
        """Test has_tag_key when tag key does not exist."""
        processor = TagProcessor(sample_tag_keys_data)
        assert processor.has_tag_key("NonExistent") is False
        assert processor.has_tag_key("Building") is False

    def test_has_tag_key_empty_processor(self):
        """Test has_tag_key on empty processor."""
        processor = TagProcessor({})
        assert processor.has_tag_key("Location") is False
