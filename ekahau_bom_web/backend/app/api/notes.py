"""Notes API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.services.storage_service import StorageService

router = APIRouter(prefix="/notes", tags=["notes"])

# Initialize services
storage_service = StorageService()


@router.get("/{project_id}")
async def get_notes(project_id: UUID) -> dict:
    """Get notes from project data.json.

    Args:
        project_id: Project UUID

    Returns:
        Dictionary with notes data (text_notes, cable_notes, picture_notes, summary)
    """
    # Check if project exists
    metadata = storage_service.load_metadata(project_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load project data
    project_data = storage_service.load_project_data(project_id)
    if not project_data:
        raise HTTPException(
            status_code=404,
            detail="Project data file not found. Process the project first.",
        )

    # Extract notes section
    notes = project_data.get("notes")
    if not notes:
        # Return empty notes structure if no notes found
        return {
            "project_id": str(project_id),
            "text_notes": [],
            "cable_notes": [],
            "picture_notes": [],
            "summary": {
                "total_text_notes": 0,
                "total_cable_notes": 0,
                "total_picture_notes": 0,
            },
        }

    return {
        "project_id": str(project_id),
        "text_notes": notes.get("text_notes", []),
        "cable_notes": notes.get("cable_notes", []),
        "picture_notes": notes.get("picture_notes", []),
        "summary": notes.get(
            "summary",
            {
                "total_text_notes": 0,
                "total_cable_notes": 0,
                "total_picture_notes": 0,
            },
        ),
    }
