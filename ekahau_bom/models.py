#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Data models for Ekahau project entities."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Floor:
    """Represents a floor plan in Ekahau project.

    Attributes:
        id: Unique identifier for the floor
        name: Human-readable name of the floor
    """
    id: str
    name: str


@dataclass
class AccessPoint:
    """Represents an access point in Ekahau project.

    Attributes:
        vendor: Manufacturer of the access point
        model: Model name/number of the access point
        color: Color code or name for visual identification
        floor_name: Name of the floor where AP is located
        mine: Whether this AP belongs to the project (not neighbor/survey)
        floor_id: ID of the floor where AP is located
    """
    vendor: str
    model: str
    color: Optional[str]
    floor_name: str
    mine: bool = True
    floor_id: Optional[str] = None

    def __hash__(self):
        """Make AccessPoint hashable for use in Counter."""
        return hash((self.vendor, self.model, self.color, self.floor_name))


@dataclass
class Antenna:
    """Represents an antenna in Ekahau project.

    Attributes:
        name: Model name of the antenna
        antenna_type_id: Unique identifier for the antenna type
    """
    name: str
    antenna_type_id: str

    def __hash__(self):
        """Make Antenna hashable for use in Counter."""
        return hash(self.name)


@dataclass
class ProjectData:
    """Container for all parsed project data.

    Attributes:
        access_points: List of access points in the project
        antennas: List of antennas used in the project
        floors: Dictionary mapping floor IDs to Floor objects
        project_name: Name of the project file
    """
    access_points: list[AccessPoint]
    antennas: list[Antenna]
    floors: dict[str, Floor]
    project_name: str
