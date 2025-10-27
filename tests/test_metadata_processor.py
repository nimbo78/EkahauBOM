#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for ProjectMetadataProcessor."""

import pytest
from ekahau_bom.processors.metadata import ProjectMetadataProcessor
from ekahau_bom.models import ProjectMetadata


class TestProjectMetadataProcessor:
    """Test cases for ProjectMetadataProcessor."""

    @pytest.fixture
    def processor(self):
        """Create a ProjectMetadataProcessor instance."""
        return ProjectMetadataProcessor()

    def test_process_empty_metadata(self, processor):
        """Test processing empty metadata."""
        result = processor.process({})

        assert isinstance(result, ProjectMetadata)
        assert result.name == ""
        assert result.customer == ""
        assert result.location == ""
        assert result.responsible_person == ""
        assert result.schema_version == ""
        assert result.note_ids == []
        assert result.project_ancestors == []

    def test_process_none_metadata(self, processor):
        """Test processing None metadata."""
        result = processor.process(None)

        assert isinstance(result, ProjectMetadata)
        assert result.name == ""

    def test_process_full_metadata(self, processor):
        """Test processing complete metadata."""
        metadata_data = {
            "name": "Test Project",
            "title": "Test Project Title",
            "customer": "Test Customer",
            "location": "Test Location",
            "responsiblePerson": "John Doe",
            "schemaVersion": "1.4.0",
            "noteIds": ["note1", "note2"],
            "projectAncestors": ["ancestor1", "ancestor2"],
        }

        result = processor.process(metadata_data)

        assert isinstance(result, ProjectMetadata)
        assert result.name == "Test Project"
        assert result.title == "Test Project Title"
        assert result.customer == "Test Customer"
        assert result.location == "Test Location"
        assert result.responsible_person == "John Doe"
        assert result.schema_version == "1.4.0"
        assert result.note_ids == ["note1", "note2"]
        assert result.project_ancestors == ["ancestor1", "ancestor2"]

    def test_process_partial_metadata(self, processor):
        """Test processing partial metadata."""
        metadata_data = {"name": "Partial Project", "customer": "Partial Customer"}

        result = processor.process(metadata_data)

        assert result.name == "Partial Project"
        assert result.customer == "Partial Customer"
        assert result.location == ""
        assert result.responsible_person == ""
        assert result.schema_version == ""
        assert result.note_ids == []
        assert result.project_ancestors == []

    def test_process_with_missing_fields(self, processor):
        """Test processing metadata with some missing fields."""
        metadata_data = {"name": "Project Name", "schemaVersion": "1.2.0"}

        result = processor.process(metadata_data)

        assert result.name == "Project Name"
        assert result.schema_version == "1.2.0"
        assert result.customer == ""
        assert result.location == ""
        assert result.responsible_person == ""

    def test_responsible_person_field_mapping(self, processor):
        """Test that responsiblePerson from JSON maps to responsible_person in model."""
        metadata_data = {"responsiblePerson": "Jane Smith"}

        result = processor.process(metadata_data)

        assert result.responsible_person == "Jane Smith"

    def test_schema_version_field_mapping(self, processor):
        """Test that schemaVersion from JSON maps to schema_version in model."""
        metadata_data = {"schemaVersion": "2.0.0"}

        result = processor.process(metadata_data)

        assert result.schema_version == "2.0.0"

    def test_note_ids_field_mapping(self, processor):
        """Test that noteIds from JSON maps to note_ids in model."""
        metadata_data = {"noteIds": ["id1", "id2", "id3"]}

        result = processor.process(metadata_data)

        assert result.note_ids == ["id1", "id2", "id3"]

    def test_project_ancestors_field_mapping(self, processor):
        """Test that projectAncestors from JSON maps to project_ancestors in model."""
        metadata_data = {"projectAncestors": ["ancestor1"]}

        result = processor.process(metadata_data)

        assert result.project_ancestors == ["ancestor1"]

    def test_real_world_example(self, processor):
        """Test with real-world example from wine office project."""
        metadata_data = {"name": "wine office", "schemaVersion": "1.4.0"}

        result = processor.process(metadata_data)

        assert result.name == "wine office"
        assert result.schema_version == "1.4.0"
        assert result.customer == ""
        assert result.location == ""
        assert result.responsible_person == ""
