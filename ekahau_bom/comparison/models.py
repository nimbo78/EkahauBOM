"""Data models for project version comparison."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ChangeStatus(Enum):
    """Status of an AP change between versions."""

    ADDED = "added"  # New AP appeared
    REMOVED = "removed"  # AP was deleted
    MODIFIED = "modified"  # Config changed, position same
    MOVED = "moved"  # Position changed (may also have config changes)
    RENAMED = "renamed"  # Same position, different name
    UNCHANGED = "unchanged"  # No changes


@dataclass
class FieldChange:
    """Represents a single field change."""

    field_name: str
    category: str  # "placement", "configuration", "radio", "metadata"
    old_value: Any
    new_value: Any

    def __str__(self) -> str:
        """Human-readable change description."""
        if self.old_value is None:
            return f"{self.field_name}: {self.new_value}"
        if self.new_value is None:
            return f"{self.field_name}: {self.old_value} (removed)"
        return f"{self.field_name}: {self.old_value} → {self.new_value}"


@dataclass
class APChange:
    """Represents a change in a single access point."""

    status: ChangeStatus
    ap_name: str  # Current name (or old name if removed)
    floor_name: str

    # AP data (None if added/removed)
    old_ap: Optional[Any] = None  # AccessPoint from old project
    new_ap: Optional[Any] = None  # AccessPoint from new project

    # For renamed APs
    old_name: Optional[str] = None
    new_name: Optional[str] = None

    # For moved APs
    distance_moved: Optional[float] = None  # Meters
    old_coords: Optional[tuple[float, float]] = None  # (x, y)
    new_coords: Optional[tuple[float, float]] = None  # (x, y)

    # Detailed field changes (for modified/moved APs)
    changes: list[FieldChange] = field(default_factory=list)

    def get_details_string(self) -> str:
        """Get human-readable details for this change."""
        if self.status == ChangeStatus.ADDED:
            return ""
        if self.status == ChangeStatus.REMOVED:
            return ""
        if self.status == ChangeStatus.RENAMED:
            return f"Was: {self.old_name}"
        if self.status == ChangeStatus.MOVED:
            parts = [f"Moved {self.distance_moved:.1f}m"]
            if self.old_coords and self.new_coords:
                parts.append(
                    f"({self.old_coords[0]:.1f},{self.old_coords[1]:.1f}) → "
                    f"({self.new_coords[0]:.1f},{self.new_coords[1]:.1f})"
                )
            return ": ".join(parts)
        if self.status == ChangeStatus.MODIFIED:
            return "; ".join(str(c) for c in self.changes[:3])  # First 3 changes
        return ""


@dataclass
class InventoryChange:
    """Summary of inventory-level changes."""

    old_total_aps: int
    new_total_aps: int
    aps_added: int
    aps_removed: int
    aps_modified: int
    aps_moved: int
    aps_renamed: int
    aps_unchanged: int

    # Vendor/model distribution changes
    old_vendor_counts: dict[str, int] = field(default_factory=dict)
    new_vendor_counts: dict[str, int] = field(default_factory=dict)
    old_model_counts: dict[str, int] = field(default_factory=dict)  # "Vendor|Model" -> count
    new_model_counts: dict[str, int] = field(default_factory=dict)

    @property
    def total_changes(self) -> int:
        """Total number of changed APs (excluding unchanged)."""
        return (
            self.aps_added
            + self.aps_removed
            + self.aps_modified
            + self.aps_moved
            + self.aps_renamed
        )

    @property
    def ap_count_diff(self) -> int:
        """Difference in AP count (positive = more APs, negative = fewer)."""
        return self.new_total_aps - self.old_total_aps


@dataclass
class MetadataChange:
    """Changes in project metadata."""

    old_name: Optional[str] = None
    new_name: Optional[str] = None
    old_customer: Optional[str] = None
    new_customer: Optional[str] = None
    old_location: Optional[str] = None
    new_location: Optional[str] = None

    changed_fields: list[FieldChange] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Check if any metadata changed."""
        return len(self.changed_fields) > 0


@dataclass
class ComparisonResult:
    """Complete comparison result between two projects."""

    # Project identification
    project_a_name: str  # Old/previous project
    project_b_name: str  # New/current project
    project_a_filename: str
    project_b_filename: str
    comparison_timestamp: datetime = field(default_factory=datetime.now)

    # Summary
    inventory_change: InventoryChange = field(
        default_factory=lambda: InventoryChange(0, 0, 0, 0, 0, 0, 0, 0)
    )
    metadata_change: Optional[MetadataChange] = None

    # Detailed changes
    ap_changes: list[APChange] = field(default_factory=list)

    # Floor-level summaries
    changes_by_floor: dict[str, list[APChange]] = field(default_factory=dict)
    floors: list[str] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        """Total number of changed APs."""
        return self.inventory_change.total_changes

    @property
    def has_changes(self) -> bool:
        """Check if any changes detected."""
        return self.total_changes > 0

    def get_changes_by_status(self, status: ChangeStatus) -> list[APChange]:
        """Get all changes with a specific status."""
        return [c for c in self.ap_changes if c.status == status]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "project_a_name": self.project_a_name,
            "project_b_name": self.project_b_name,
            "project_a_filename": self.project_a_filename,
            "project_b_filename": self.project_b_filename,
            "comparison_timestamp": self.comparison_timestamp.isoformat(),
            "summary": {
                "old_total_aps": self.inventory_change.old_total_aps,
                "new_total_aps": self.inventory_change.new_total_aps,
                "ap_count_diff": self.inventory_change.ap_count_diff,
                "total_changes": self.total_changes,
                "added": self.inventory_change.aps_added,
                "removed": self.inventory_change.aps_removed,
                "modified": self.inventory_change.aps_modified,
                "moved": self.inventory_change.aps_moved,
                "renamed": self.inventory_change.aps_renamed,
                "unchanged": self.inventory_change.aps_unchanged,
            },
            "metadata_change": (
                {
                    "old_name": self.metadata_change.old_name,
                    "new_name": self.metadata_change.new_name,
                    "old_customer": self.metadata_change.old_customer,
                    "new_customer": self.metadata_change.new_customer,
                    "changes": [
                        {"field": c.field_name, "old": c.old_value, "new": c.new_value}
                        for c in self.metadata_change.changed_fields
                    ],
                }
                if self.metadata_change
                else None
            ),
            "floors": self.floors,
            "changes": [
                {
                    "status": c.status.value,
                    "ap_name": c.ap_name,
                    "floor": c.floor_name,
                    "old_name": c.old_name,
                    "new_name": c.new_name,
                    "distance_moved": c.distance_moved,
                    "old_coords": c.old_coords,
                    "new_coords": c.new_coords,
                    "details": c.get_details_string(),
                    "field_changes": [
                        {
                            "field": fc.field_name,
                            "category": fc.category,
                            "old": fc.old_value,
                            "new": fc.new_value,
                        }
                        for fc in c.changes
                    ],
                }
                for c in self.ap_changes
            ],
            "changes_by_floor": {
                floor: [
                    {
                        "status": c.status.value,
                        "ap_name": c.ap_name,
                        "details": c.get_details_string(),
                    }
                    for c in changes
                ]
                for floor, changes in self.changes_by_floor.items()
            },
        }
