#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for NotesProcessor."""

from __future__ import annotations


import pytest
from ekahau_bom.processors.notes import NotesProcessor
from ekahau_bom.models import (
    Note,
    NoteHistory,
    CableNote,
    PictureNote,
    Point,
    Location,
    Floor,
)


class TestNotesProcessor:
    """Test suite for NotesProcessor."""

    @pytest.fixture
    def processor(self):
        """Create NotesProcessor instance."""
        return NotesProcessor()

    @pytest.fixture
    def sample_floors(self):
        """Create sample floors dictionary."""
        return {
            "floor1": Floor(id="floor1", name="Floor 1"),
            "floor2": Floor(id="floor2", name="Floor 2"),
        }

    def test_process_notes_empty(self, processor):
        """Test processing empty notes data."""
        result = processor.process_notes({})
        assert result == []

    def test_process_notes_no_notes_key(self, processor):
        """Test processing notes data without 'notes' key."""
        result = processor.process_notes({"other": "data"})
        assert result == []

    def test_process_single_note(self, processor):
        """Test processing single note."""
        notes_data = {
            "notes": [
                {
                    "id": "note1",
                    "text": "Test note",
                    "history": {
                        "createdAt": "2021-06-15T20:14:11.234Z",
                        "createdBy": "Test User",
                    },
                    "imageIds": [],
                    "status": "CREATED",
                }
            ]
        }

        result = processor.process_notes(notes_data)

        assert len(result) == 1
        assert isinstance(result[0], Note)
        assert result[0].id == "note1"
        assert result[0].text == "Test note"
        assert result[0].history is not None
        assert result[0].history.created_at == "2021-06-15T20:14:11.234Z"
        assert result[0].history.created_by == "Test User"
        assert result[0].image_ids == []
        assert result[0].status == "CREATED"

    def test_process_note_without_history(self, processor):
        """Test processing note without history."""
        notes_data = {
            "notes": [
                {
                    "id": "note1",
                    "text": "Test note",
                    "imageIds": [],
                    "status": "CREATED",
                }
            ]
        }

        result = processor.process_notes(notes_data)

        assert len(result) == 1
        assert result[0].history is None

    def test_process_note_with_image_ids(self, processor):
        """Test processing note with image IDs."""
        notes_data = {
            "notes": [
                {
                    "id": "note1",
                    "text": "Test note",
                    "imageIds": ["img1", "img2"],
                    "status": "CREATED",
                }
            ]
        }

        result = processor.process_notes(notes_data)

        assert len(result) == 1
        assert result[0].image_ids == ["img1", "img2"]

    def test_process_multiple_notes(self, processor):
        """Test processing multiple notes."""
        notes_data = {
            "notes": [
                {"id": "note1", "text": "Note 1", "status": "CREATED"},
                {"id": "note2", "text": "Note 2", "status": "CREATED"},
                {"id": "note3", "text": "Note 3", "status": "CREATED"},
            ]
        }

        result = processor.process_notes(notes_data)

        assert len(result) == 3
        assert result[0].id == "note1"
        assert result[1].id == "note2"
        assert result[2].id == "note3"

    def test_process_cable_notes_empty(self, processor, sample_floors):
        """Test processing empty cable notes data."""
        result = processor.process_cable_notes({}, sample_floors)
        assert result == []

    def test_process_single_cable_note(self, processor, sample_floors):
        """Test processing single cable note."""
        cable_notes_data = {
            "cableNotes": [
                {
                    "id": "cable1",
                    "floorPlanId": "floor1",
                    "points": [{"x": 100.5, "y": 200.3}, {"x": 150.7, "y": 250.9}],
                    "color": "#FF0000",
                    "noteIds": ["note1"],
                    "status": "CREATED",
                }
            ]
        }

        result = processor.process_cable_notes(cable_notes_data, sample_floors)

        assert len(result) == 1
        assert isinstance(result[0], CableNote)
        assert result[0].id == "cable1"
        assert result[0].floor_plan_id == "floor1"
        assert len(result[0].points) == 2
        assert isinstance(result[0].points[0], Point)
        assert result[0].points[0].x == 100.5
        assert result[0].points[0].y == 200.3
        assert result[0].color == "#FF0000"
        assert result[0].note_ids == ["note1"]
        assert result[0].status == "CREATED"

    def test_process_cable_note_multiple_points(self, processor, sample_floors):
        """Test processing cable note with multiple points."""
        cable_notes_data = {
            "cableNotes": [
                {
                    "id": "cable1",
                    "floorPlanId": "floor1",
                    "points": [
                        {"x": 100.0, "y": 100.0},
                        {"x": 200.0, "y": 100.0},
                        {"x": 200.0, "y": 200.0},
                        {"x": 100.0, "y": 200.0},
                    ],
                    "color": "#000000",
                    "noteIds": [],
                    "status": "CREATED",
                }
            ]
        }

        result = processor.process_cable_notes(cable_notes_data, sample_floors)

        assert len(result) == 1
        assert len(result[0].points) == 4

    def test_process_picture_notes_empty(self, processor, sample_floors):
        """Test processing empty picture notes data."""
        result = processor.process_picture_notes({}, sample_floors)
        assert result == []

    def test_process_single_picture_note(self, processor, sample_floors):
        """Test processing single picture note."""
        picture_notes_data = {
            "pictureNotes": [
                {
                    "id": "pic1",
                    "location": {
                        "floorPlanId": "floor1",
                        "coord": {"x": 300.5, "y": 400.7},
                    },
                    "noteIds": ["note1", "note2"],
                    "status": "CREATED",
                }
            ]
        }

        result = processor.process_picture_notes(picture_notes_data, sample_floors)

        assert len(result) == 1
        assert isinstance(result[0], PictureNote)
        assert result[0].id == "pic1"
        assert result[0].location is not None
        assert isinstance(result[0].location, Location)
        assert result[0].location.floor_plan_id == "floor1"
        assert result[0].location.x == 300.5
        assert result[0].location.y == 400.7
        assert result[0].note_ids == ["note1", "note2"]
        assert result[0].status == "CREATED"

    def test_process_picture_note_without_location(self, processor, sample_floors):
        """Test processing picture note without location."""
        picture_notes_data = {
            "pictureNotes": [{"id": "pic1", "noteIds": [], "status": "CREATED"}]
        }

        result = processor.process_picture_notes(picture_notes_data, sample_floors)

        assert len(result) == 1
        assert result[0].location is None

    def test_process_multiple_cable_notes(self, processor, sample_floors):
        """Test processing multiple cable notes."""
        cable_notes_data = {
            "cableNotes": [
                {
                    "id": f"cable{i}",
                    "floorPlanId": "floor1",
                    "points": [{"x": i * 10.0, "y": i * 20.0}],
                    "color": "#000000",
                    "noteIds": [],
                    "status": "CREATED",
                }
                for i in range(5)
            ]
        }

        result = processor.process_cable_notes(cable_notes_data, sample_floors)

        assert len(result) == 5

    def test_process_multiple_picture_notes(self, processor, sample_floors):
        """Test processing multiple picture notes."""
        picture_notes_data = {
            "pictureNotes": [
                {
                    "id": f"pic{i}",
                    "location": {
                        "floorPlanId": "floor1",
                        "coord": {"x": i * 10.0, "y": i * 20.0},
                    },
                    "noteIds": [],
                    "status": "CREATED",
                }
                for i in range(3)
            ]
        }

        result = processor.process_picture_notes(picture_notes_data, sample_floors)

        assert len(result) == 3

    def test_process_notes_with_real_data(self, processor):
        """Test processing notes with real-world data structure."""
        notes_data = {
            "notes": [
                {
                    "text": "Проход над подвесным потолком",
                    "history": {
                        "createdAt": "2021-06-15T20:14:11.234Z",
                        "createdBy": "Network Team",
                    },
                    "imageIds": [],
                    "id": "5590b2bc-f8dc-4819-bdac-8d468878534a",
                    "status": "CREATED",
                }
            ]
        }

        result = processor.process_notes(notes_data)

        assert len(result) == 1
        assert result[0].text == "Проход над подвесным потолком"
        assert result[0].history.created_by == "Network Team"

    def test_process_notes_with_error_handling(self):
        """Test that notes processor handles errors gracefully."""
        from unittest.mock import patch

        processor = NotesProcessor()

        notes_data = {
            "notes": [
                {"id": "valid-note", "text": "Valid note", "status": "CREATED"},
                {"id": "bad-note", "text": "This will fail", "status": "CREATED"},
            ]
        }

        # Mock _process_single_note to raise exception for second note
        original_method = processor._process_single_note
        call_count = [0]

        def mock_process(note_data):
            call_count[0] += 1
            if call_count[0] == 2:  # Second call raises error
                raise ValueError("Simulated processing error")
            return original_method(note_data)

        with patch.object(processor, "_process_single_note", side_effect=mock_process):
            result = processor.process_notes(notes_data)

        # Should have 1 valid note (second one failed)
        assert len(result) == 1
        assert result[0].id == "valid-note"

    def test_process_cable_notes_with_error_handling(self):
        """Test that cable notes processor handles errors gracefully."""
        processor = NotesProcessor()
        floors = {"floor1": Floor(id="floor1", name="Floor 1")}

        cable_notes_data = {
            "cableNotes": [
                {
                    "id": "valid-cable",
                    "floorPlanId": "floor1",
                    "points": [{"x": 0, "y": 0}, {"x": 10, "y": 10}],
                    "color": "#FF0000",
                    "status": "CREATED",
                },
                {
                    "id": "invalid-cable",
                    # Missing floorPlanId which might cause issues
                    "points": None,  # Invalid points
                    "status": "CREATED",
                },
                {
                    "id": "another-valid-cable",
                    "floorPlanId": "floor1",
                    "points": [{"x": 5, "y": 5}],
                    "color": "#00FF00",
                    "status": "CREATED",
                },
            ]
        }

        # Should process valid cable notes and skip invalid ones
        result = processor.process_cable_notes(cable_notes_data, floors)

        # Should have at least 1 valid cable note (invalid ones skipped)
        assert len(result) >= 1

    def test_process_picture_notes_with_error_handling(self):
        """Test that picture notes processor handles errors gracefully."""
        from unittest.mock import patch

        processor = NotesProcessor()
        floors = {"floor1": Floor(id="floor1", name="Floor 1")}

        picture_notes_data = {
            "pictureNotes": [
                {
                    "id": "valid-picture",
                    "location": {
                        "floorPlanId": "floor1",
                        "coord": {"x": 100, "y": 200},
                    },
                    "noteIds": ["note1"],
                    "status": "CREATED",
                },
                {
                    "id": "bad-picture",
                    "location": {
                        "floorPlanId": "floor1",
                        "coord": {"x": 150, "y": 250},
                    },
                    "status": "CREATED",
                },
            ]
        }

        # Mock _process_single_picture_note to raise exception for second note
        original_method = processor._process_single_picture_note
        call_count = [0]

        def mock_process(note_data, floors_dict):
            call_count[0] += 1
            if call_count[0] == 2:  # Second call raises error
                raise ValueError("Simulated picture note processing error")
            return original_method(note_data, floors_dict)

        with patch.object(
            processor, "_process_single_picture_note", side_effect=mock_process
        ):
            result = processor.process_picture_notes(picture_notes_data, floors)

        # Should have 1 valid picture note (second one failed)
        assert len(result) == 1
        assert result[0].id == "valid-picture"
