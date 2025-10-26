#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Data models for Ekahau project entities."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProjectMetadata:
    """Represents project-level metadata from Ekahau project.

    Contains high-level information about the project such as name, customer,
    location, responsible person, and schema version.

    Attributes:
        name: Project name
        title: Project title (usually same as name)
        customer: Customer/client name
        location: Project location/address
        responsible_person: Person responsible for the project
        schema_version: Ekahau project file schema version
        note_ids: List of note IDs attached to the project
        project_ancestors: List of ancestor project IDs (for project history)
    """
    name: str = ""
    title: str = ""
    customer: str = ""
    location: str = ""
    responsible_person: str = ""
    schema_version: str = ""
    note_ids: list[str] = field(default_factory=list)
    project_ancestors: list[str] = field(default_factory=list)


@dataclass
class NoteHistory:
    """Represents history metadata for a note.

    Attributes:
        created_at: ISO 8601 timestamp when note was created
        created_by: Name of user who created the note
    """
    created_at: str = ""
    created_by: str = ""


@dataclass
class Note:
    """Represents a text note in Ekahau project.

    Text notes contain information about installation details, cable routing,
    or other important details for the project.

    Attributes:
        id: Unique identifier for the note
        text: Text content of the note
        history: Creation history (timestamp and author)
        image_ids: List of image IDs attached to this note
        status: Note status (typically "CREATED")
    """
    id: str
    text: str = ""
    history: Optional[NoteHistory] = None
    image_ids: list[str] = field(default_factory=list)
    status: str = "CREATED"


@dataclass
class Point:
    """Represents a 2D coordinate point.

    Attributes:
        x: X coordinate in project units
        y: Y coordinate in project units
    """
    x: float
    y: float


@dataclass
class CableNote:
    """Represents a cable route annotation on floor plan.

    Cable notes show the physical path of network cables through
    the building, including routes through ceiling, conduits, etc.

    Attributes:
        id: Unique identifier for the cable note
        floor_plan_id: ID of the floor where cable is routed
        points: List of coordinate points defining the cable path
        color: Color of the cable line (hex format, e.g., "#000000")
        note_ids: List of Note IDs with additional information
        status: Cable note status (typically "CREATED")
    """
    id: str
    floor_plan_id: str = ""
    points: list[Point] = field(default_factory=list)
    color: str = "#000000"
    note_ids: list[str] = field(default_factory=list)
    status: str = "CREATED"


@dataclass
class Location:
    """Represents a location on a floor plan.

    Attributes:
        floor_plan_id: ID of the floor
        x: X coordinate in project units
        y: Y coordinate in project units
    """
    floor_plan_id: str = ""
    x: float = 0.0
    y: float = 0.0


@dataclass
class PictureNote:
    """Represents a picture/image note placed on floor plan.

    Picture notes are visual markers on the floor plan that can have
    associated text notes with additional details.

    Attributes:
        id: Unique identifier for the picture note
        location: Location on floor plan (floor ID and coordinates)
        note_ids: List of Note IDs with text descriptions
        status: Picture note status (typically "CREATED")
    """
    id: str
    location: Optional[Location] = None
    note_ids: list[str] = field(default_factory=list)
    status: str = "CREATED"


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
class Radio:
    """Represents a radio configuration in Ekahau project.

    Attributes:
        id: Unique identifier for the radio
        access_point_id: ID of the access point this radio belongs to
        frequency_band: Frequency band (2.4GHz, 5GHz, 6GHz)
        channel: Channel number
        channel_width: Channel width in MHz (20, 40, 80, 160)
        tx_power: Transmit power in dBm
        antenna_type_id: ID of the antenna type used
        standard: Wi-Fi standard (802.11a/b/g/n/ac/ax/be)
        antenna_mounting: Mounting type (CEILING, WALL, FLOOR)
        antenna_direction: Antenna azimuth/direction in degrees (0-360)
        antenna_tilt: Antenna tilt in degrees
        antenna_height: Antenna height in meters
    """
    id: str
    access_point_id: str
    frequency_band: Optional[str] = None
    channel: Optional[int] = None
    channel_width: Optional[int] = None
    tx_power: Optional[float] = None
    antenna_type_id: Optional[str] = None
    standard: Optional[str] = None
    antenna_mounting: Optional[str] = None
    antenna_direction: Optional[float] = None
    antenna_tilt: Optional[float] = None
    antenna_height: Optional[float] = None

    def __hash__(self):
        """Make Radio hashable."""
        return hash(self.id)


@dataclass
class AccessPoint:
    """Represents an access point in Ekahau project.

    Attributes:
        id: Unique identifier of the access point
        vendor: Manufacturer of the access point
        model: Model name/number of the access point
        color: Color code or name for visual identification
        floor_name: Name of the floor where AP is located
        tags: List of tags applied to this access point
        mine: Whether this AP belongs to the project (not neighbor/survey)
        floor_id: ID of the floor where AP is located
        name: Name/identifier of the access point
        location_x: X coordinate of AP location in meters
        location_y: Y coordinate of AP location in meters
        mounting_height: Height of AP above floor in meters
        azimuth: Horizontal rotation angle in degrees (0-360)
        tilt: Vertical tilt angle in degrees
        antenna_height: Antenna height above ground in meters
        enabled: Whether the AP is enabled in the design
    """
    id: Optional[str] = None
    vendor: str = ""
    model: str = ""
    color: Optional[str] = None
    floor_name: str = ""
    tags: list[Tag] = field(default_factory=list)
    mine: bool = True
    floor_id: Optional[str] = None
    name: Optional[str] = None
    location_x: Optional[float] = None
    location_y: Optional[float] = None
    mounting_height: Optional[float] = None
    azimuth: Optional[float] = None
    tilt: Optional[float] = None
    antenna_height: Optional[float] = None
    enabled: bool = True

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
class DataRate:
    """Represents a data rate configuration (802.11 a/b/g rates).

    Attributes:
        rate: Rate identifier (e.g., "R1", "R2", "R6", "R54")
        state: Rate state ("MANDATORY", "DISABLED", "SUPPORTED")
    """
    rate: str
    state: str


@dataclass
class NetworkCapacitySettings:
    """Represents network capacity settings for a frequency band.

    Contains SSID configuration, client limits, and data rate settings
    for either 2.4 GHz or 5 GHz band.

    Attributes:
        frequency_band: Frequency band ("2.4GHz" or "5GHz")
        number_of_ssids: Number of SSIDs configured
        rts_cts_enabled: Whether RTS/CTS is enabled
        max_associated_clients: Maximum number of associated clients
        data_rates: List of data rate configurations
    """
    frequency_band: str
    number_of_ssids: int = 1
    rts_cts_enabled: bool = False
    max_associated_clients: int = 200
    data_rates: list[DataRate] = field(default_factory=list)


@dataclass
class ProjectData:
    """Container for all parsed project data.

    Attributes:
        access_points: List of access points in the project
        antennas: List of antennas used in the project
        floors: Dictionary mapping floor IDs to Floor objects
        project_name: Name of the project file
        radios: List of radio configurations in the project
        metadata: Project metadata (name, customer, location, etc.)
        notes: List of text notes in the project
        cable_notes: List of cable route annotations
        picture_notes: List of picture notes on floor plans
        network_settings: List of network capacity settings (SSID, rates, etc.)
    """
    access_points: list[AccessPoint]
    antennas: list[Antenna]
    floors: dict[str, Floor]
    project_name: str
    radios: list[Radio] = field(default_factory=list)
    metadata: Optional[ProjectMetadata] = None
    notes: list[Note] = field(default_factory=list)
    cable_notes: list[CableNote] = field(default_factory=list)
    picture_notes: list[PictureNote] = field(default_factory=list)
    network_settings: list[NetworkCapacitySettings] = field(default_factory=list)
