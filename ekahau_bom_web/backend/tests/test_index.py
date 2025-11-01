"""Tests for Index Service."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app.models import ProcessingStatus, ProjectMetadata
from app.services.index import IndexService


@pytest.fixture
def temp_index(tmp_path):
    """Create temporary index service."""
    index = IndexService()
    index.index_file = tmp_path / "index.json"
    return index


@pytest.fixture
def sample_projects():
    """Create sample project metadata."""
    return [
        ProjectMetadata(
            project_id=uuid4(),
            filename="project1.esx",
            file_size=1024,
            processing_status=ProcessingStatus.COMPLETED,
            project_name="Test Project 1",
            aps_count=10,
            original_file="projects/1/original.esx",
            upload_date=datetime(2025, 1, 1, tzinfo=UTC),
        ),
        ProjectMetadata(
            project_id=uuid4(),
            filename="project2.esx",
            file_size=2048,
            processing_status=ProcessingStatus.PENDING,
            project_name="Test Project 2",
            aps_count=5,
            original_file="projects/2/original.esx",
            upload_date=datetime(2025, 1, 2, tzinfo=UTC),
        ),
        ProjectMetadata(
            project_id=uuid4(),
            filename="office.esx",
            file_size=3072,
            processing_status=ProcessingStatus.COMPLETED,
            project_name="Office Network",
            aps_count=20,
            original_file="projects/3/original.esx",
            upload_date=datetime(2025, 1, 3, tzinfo=UTC),
            short_link="abc123",
        ),
    ]


def test_add_and_get(temp_index, sample_projects):
    """Test adding and retrieving projects."""
    project = sample_projects[0]

    # Add project
    temp_index.add(project)

    # Get project
    retrieved = temp_index.get(project.project_id)

    assert retrieved is not None
    assert retrieved.project_id == project.project_id
    assert retrieved.filename == project.filename


def test_get_nonexistent(temp_index):
    """Test getting non-existent project."""
    result = temp_index.get(uuid4())
    assert result is None


def test_remove(temp_index, sample_projects):
    """Test removing project."""
    project = sample_projects[0]

    # Add and verify
    temp_index.add(project)
    assert temp_index.get(project.project_id) is not None

    # Remove
    temp_index.remove(project.project_id)

    # Verify removed
    assert temp_index.get(project.project_id) is None


def test_get_by_short_link(temp_index, sample_projects):
    """Test getting project by short link."""
    project = sample_projects[2]  # Has short_link="abc123"

    temp_index.add(project)

    # Get by short link
    retrieved = temp_index.get_by_short_link("abc123")

    assert retrieved is not None
    assert retrieved.project_id == project.project_id
    assert retrieved.short_link == "abc123"


def test_get_by_nonexistent_short_link(temp_index):
    """Test getting project by non-existent short link."""
    result = temp_index.get_by_short_link("nonexistent")
    assert result is None


def test_list_all(temp_index, sample_projects):
    """Test listing all projects."""
    # Add all projects
    for project in sample_projects:
        temp_index.add(project)

    # List all
    projects = temp_index.list_all()

    assert len(projects) == 3
    # Should be sorted by upload_date (newest first)
    assert projects[0].filename == "office.esx"  # 2025-01-03
    assert projects[1].filename == "project2.esx"  # 2025-01-02
    assert projects[2].filename == "project1.esx"  # 2025-01-01


def test_list_all_with_status_filter(temp_index, sample_projects):
    """Test listing projects filtered by status."""
    # Add all projects
    for project in sample_projects:
        temp_index.add(project)

    # Filter by COMPLETED status
    completed = temp_index.list_all(status=ProcessingStatus.COMPLETED)

    assert len(completed) == 2
    assert all(p.processing_status == ProcessingStatus.COMPLETED for p in completed)


def test_list_all_with_limit(temp_index, sample_projects):
    """Test listing projects with limit."""
    # Add all projects
    for project in sample_projects:
        temp_index.add(project)

    # Limit to 2
    projects = temp_index.list_all(limit=2)

    assert len(projects) == 2


def test_search(temp_index, sample_projects):
    """Test searching projects."""
    # Add all projects
    for project in sample_projects:
        temp_index.add(project)

    # Search by project name
    results = temp_index.search("Office")

    assert len(results) == 1
    assert results[0].project_name == "Office Network"

    # Search by filename
    results = temp_index.search("project")

    assert len(results) == 2


def test_search_case_insensitive(temp_index, sample_projects):
    """Test search is case-insensitive."""
    # Add all projects
    for project in sample_projects:
        temp_index.add(project)

    # Search with different case
    results = temp_index.search("OFFICE")

    assert len(results) == 1
    assert results[0].project_name == "Office Network"


def test_count(temp_index, sample_projects):
    """Test counting projects."""
    # Add all projects
    for project in sample_projects:
        temp_index.add(project)

    # Total count
    assert temp_index.count() == 3

    # Count by status
    assert temp_index.count(status=ProcessingStatus.COMPLETED) == 2
    assert temp_index.count(status=ProcessingStatus.PENDING) == 1
    assert temp_index.count(status=ProcessingStatus.FAILED) == 0


def test_save_and_load_from_disk(temp_index, sample_projects):
    """Test saving and loading index from disk."""
    # Add all projects
    for project in sample_projects:
        temp_index.add(project)

    # Save to disk
    temp_index.save_to_disk()

    # Verify file exists
    assert temp_index.index_file.exists()

    # Create new index and load
    new_index = IndexService()
    new_index.index_file = temp_index.index_file
    new_index.load_from_disk()

    # Verify all projects loaded
    assert new_index.count() == 3
    for project in sample_projects:
        loaded = new_index.get(project.project_id)
        assert loaded is not None
        assert loaded.filename == project.filename


def test_load_from_nonexistent_file(temp_index):
    """Test loading from non-existent index file."""
    # Should not raise exception
    temp_index.load_from_disk()

    # Index should be empty
    assert temp_index.count() == 0


def test_update_project(temp_index, sample_projects):
    """Test updating existing project."""
    project = sample_projects[0]

    # Add project
    temp_index.add(project)

    # Modify and re-add
    project.processing_status = ProcessingStatus.COMPLETED
    project.aps_count = 15
    temp_index.add(project)

    # Verify updated
    retrieved = temp_index.get(project.project_id)
    assert retrieved.processing_status == ProcessingStatus.COMPLETED
    assert retrieved.aps_count == 15


def test_remove_with_short_link(temp_index, sample_projects):
    """Test removing project with short link."""
    project = sample_projects[2]  # Has short_link

    # Add project
    temp_index.add(project)
    assert temp_index.get_by_short_link("abc123") is not None

    # Remove
    temp_index.remove(project.project_id)

    # Verify short link also removed
    assert temp_index.get_by_short_link("abc123") is None
