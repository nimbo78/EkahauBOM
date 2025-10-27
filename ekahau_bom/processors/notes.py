#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Processor for Ekahau project notes (text, cable, and picture notes)."""

import logging
from typing import Any

from ..models import Note, NoteHistory, CableNote, PictureNote, Point, Location, Floor

logger = logging.getLogger(__name__)


class NotesProcessor:
    """Process notes from Ekahau project data.

    Handles three types of notes:
    - Text notes (notes.json): General text annotations
    - Cable notes (cableNotes.json): Cable routing paths
    - Picture notes (pictureNotes.json): Image markers on floor plans
    """

    def process_notes(self, notes_data: dict[str, Any]) -> list[Note]:
        """Process text notes from notes.json.

        Args:
            notes_data: Raw notes data from parser

        Returns:
            List of Note objects
        """
        if not notes_data or "notes" not in notes_data:
            logger.info("No text notes found in project")
            return []

        notes_list = notes_data.get("notes", [])
        processed_notes = []

        for note_data in notes_list:
            try:
                note = self._process_single_note(note_data)
                processed_notes.append(note)
            except Exception as e:
                logger.warning(f"Failed to process note {note_data.get('id', 'unknown')}: {e}")
                continue

        logger.info(f"Processed {len(processed_notes)}/{len(notes_list)} text notes")
        return processed_notes

    def _process_single_note(self, note_data: dict[str, Any]) -> Note:
        """Process a single text note.

        Args:
            note_data: Raw note data dictionary

        Returns:
            Note object
        """
        # Extract history
        history_data = note_data.get("history", {})
        history = None
        if history_data:
            history = NoteHistory(
                created_at=history_data.get("createdAt", ""),
                created_by=history_data.get("createdBy", ""),
            )

        note = Note(
            id=note_data.get("id", ""),
            text=note_data.get("text", ""),
            history=history,
            image_ids=note_data.get("imageIds", []),
            status=note_data.get("status", "CREATED"),
        )

        return note

    def process_cable_notes(
        self, cable_notes_data: dict[str, Any], floors: dict[str, Floor]
    ) -> list[CableNote]:
        """Process cable notes from cableNotes.json.

        Args:
            cable_notes_data: Raw cable notes data from parser
            floors: Dictionary mapping floor IDs to Floor objects

        Returns:
            List of CableNote objects
        """
        if not cable_notes_data or "cableNotes" not in cable_notes_data:
            logger.info("No cable notes found in project")
            return []

        cable_notes_list = cable_notes_data.get("cableNotes", [])
        processed_cable_notes = []

        for cable_note_data in cable_notes_list:
            try:
                cable_note = self._process_single_cable_note(cable_note_data, floors)
                processed_cable_notes.append(cable_note)
            except Exception as e:
                logger.warning(
                    f"Failed to process cable note {cable_note_data.get('id', 'unknown')}: {e}"
                )
                continue

        logger.info(f"Processed {len(processed_cable_notes)}/{len(cable_notes_list)} cable notes")
        return processed_cable_notes

    def _process_single_cable_note(
        self, cable_note_data: dict[str, Any], floors: dict[str, Floor]
    ) -> CableNote:
        """Process a single cable note.

        Args:
            cable_note_data: Raw cable note data dictionary
            floors: Dictionary mapping floor IDs to Floor objects

        Returns:
            CableNote object
        """
        # Extract points
        points_data = cable_note_data.get("points", [])
        points = []
        for point_data in points_data:
            point = Point(x=point_data.get("x", 0.0), y=point_data.get("y", 0.0))
            points.append(point)

        cable_note = CableNote(
            id=cable_note_data.get("id", ""),
            floor_plan_id=cable_note_data.get("floorPlanId", ""),
            points=points,
            color=cable_note_data.get("color", "#000000"),
            note_ids=cable_note_data.get("noteIds", []),
            status=cable_note_data.get("status", "CREATED"),
        )

        return cable_note

    def process_picture_notes(
        self, picture_notes_data: dict[str, Any], floors: dict[str, Floor]
    ) -> list[PictureNote]:
        """Process picture notes from pictureNotes.json.

        Args:
            picture_notes_data: Raw picture notes data from parser
            floors: Dictionary mapping floor IDs to Floor objects

        Returns:
            List of PictureNote objects
        """
        if not picture_notes_data or "pictureNotes" not in picture_notes_data:
            logger.info("No picture notes found in project")
            return []

        picture_notes_list = picture_notes_data.get("pictureNotes", [])
        processed_picture_notes = []

        for picture_note_data in picture_notes_list:
            try:
                picture_note = self._process_single_picture_note(picture_note_data, floors)
                processed_picture_notes.append(picture_note)
            except Exception as e:
                logger.warning(
                    f"Failed to process picture note {picture_note_data.get('id', 'unknown')}: {e}"
                )
                continue

        logger.info(
            f"Processed {len(processed_picture_notes)}/{len(picture_notes_list)} picture notes"
        )
        return processed_picture_notes

    def _process_single_picture_note(
        self, picture_note_data: dict[str, Any], floors: dict[str, Floor]
    ) -> PictureNote:
        """Process a single picture note.

        Args:
            picture_note_data: Raw picture note data dictionary
            floors: Dictionary mapping floor IDs to Floor objects

        Returns:
            PictureNote object
        """
        # Extract location
        location_data = picture_note_data.get("location", {})
        location = None
        if location_data:
            coord_data = location_data.get("coord", {})
            location = Location(
                floor_plan_id=location_data.get("floorPlanId", ""),
                x=coord_data.get("x", 0.0),
                y=coord_data.get("y", 0.0),
            )

        picture_note = PictureNote(
            id=picture_note_data.get("id", ""),
            location=location,
            note_ids=picture_note_data.get("noteIds", []),
            status=picture_note_data.get("status", "CREATED"),
        )

        return picture_note
