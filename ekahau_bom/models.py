#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Data models for Ekahau project entities."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Tag:
    """Represents a tag key-value pair in Ekahau project.

    Tags are custom metadata that can be applied to access points.
    Introduced in Ekahau v10.2+.

    Attributes:
        key: Tag name/category (e.g., "Location", "Zone", "Building")
        value: Tag value (e.g., "Building A", "Office", "Floor 1")
        tag_key_id: UUID reference to tagKeys.json
    """
    key: str
    value: str
    tag_key_id: str

    def __hash__(self):
        """Make Tag hashable."""
        return hash((self.key, self.value))

    def __str__(self):
        """String representation for display."""
        return f"{self.key}:{self.value}"


@dataclass
class TagKey:
    """Represents a tag key definition from tagKeys.json.

    Attributes:
        id: UUID identifier for the tag key
        key: Human-readable tag name (e.g., "Location", "Zone")
    """
    id: str
    key: str


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
        tags: List of tags applied to this access point
        mine: Whether this AP belongs to the project (not neighbor/survey)
        floor_id: ID of the floor where AP is located
        mounting_height: Height of AP above floor in meters
        azimuth: Horizontal rotation angle in degrees (0-360)
        tilt: Vertical tilt angle in degrees
        antenna_height: Antenna height above ground in meters
    """
    vendor: str
    model: str
    color: Optional[str]
    floor_name: str
    tags: list[Tag] = field(default_factory=list)
    mine: bool = True
    floor_id: Optional[str] = None
    mounting_height: Optional[float] = None
    azimuth: Optional[float] = None
    tilt: Optional[float] = None
    antenna_height: Optional[float] = None

    def __hash__(self):
        """Make AccessPoint hashable for use in Counter.

        Note: Tags are not included in hash to allow grouping by
        vendor/model/color/floor regardless of tags.
        """
        return hash((self.vendor, self.model, self.color, self.floor_name))

    def get_tag_value(self, tag_key: str) -> Optional[str]:
        """Get value of a specific tag by key name.

        Args:
            tag_key: Name of the tag key to find

        Returns:
            Tag value if found, None otherwise
        """
        for tag in self.tags:
            if tag.key == tag_key:
                return tag.value
        return None

    def has_tag(self, tag_key: str, tag_value: Optional[str] = None) -> bool:
        """Check if access point has a specific tag.

        Args:
            tag_key: Name of the tag key
            tag_value: Optional value to match. If None, checks only key existence.

        Returns:
            True if tag exists (and matches value if specified)
        """
        for tag in self.tags:
            if tag.key == tag_key:
                if tag_value is None:
                    return True
                return tag.value == tag_value
        return False


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
