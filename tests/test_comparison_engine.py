"""Tests for the comparison engine module."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from pathlib import Path

from ekahau_bom.comparison.models import (
    APChange,
    ChangeStatus,
    ComparisonResult,
    FieldChange,
    InventoryChange,
    MetadataChange,
)
from ekahau_bom.comparison.engine import ComparisonEngine, calculate_distance, MOVE_THRESHOLD


class TestCalculateDistance:
    """Tests for calculate_distance function."""

    def test_same_point(self):
        """Distance between same point is 0."""
        assert calculate_distance(0, 0, 0, 0) == 0
        assert calculate_distance(5.5, 3.2, 5.5, 3.2) == 0

    def test_horizontal_distance(self):
        """Horizontal distance calculation."""
        assert calculate_distance(0, 0, 3, 0) == 3.0
        assert calculate_distance(0, 0, -4, 0) == 4.0

    def test_vertical_distance(self):
        """Vertical distance calculation."""
        assert calculate_distance(0, 0, 0, 5) == 5.0
        assert calculate_distance(0, 0, 0, -12) == 12.0

    def test_diagonal_distance(self):
        """Diagonal distance (Pythagorean theorem)."""
        # 3-4-5 triangle
        assert calculate_distance(0, 0, 3, 4) == 5.0
        # 5-12-13 triangle
        assert calculate_distance(0, 0, 5, 12) == 13.0

    def test_negative_coordinates(self):
        """Distance with negative coordinates."""
        # Distance from (-1, -1) to (2, 3)
        # dx=3, dy=4, distance=5
        assert calculate_distance(-1, -1, 2, 3) == 5.0


class TestFieldChange:
    """Tests for FieldChange dataclass."""

    def test_field_change_creation(self):
        """Test basic FieldChange creation."""
        change = FieldChange(
            field_name="channel",
            category="radio",
            old_value=36,
            new_value=44,
        )
        assert change.field_name == "channel"
        assert change.category == "radio"
        assert change.old_value == 36
        assert change.new_value == 44

    def test_field_change_with_none(self):
        """Test FieldChange with None values."""
        change = FieldChange(
            field_name="mounting_height",
            category="placement",
            old_value=None,
            new_value=3.0,
        )
        assert change.old_value is None
        assert change.new_value == 3.0


class TestAPChange:
    """Tests for APChange dataclass."""

    def test_added_ap(self):
        """Test APChange for added AP."""
        change = APChange(
            status=ChangeStatus.ADDED,
            ap_name="AP-101",
            floor_name="Floor 1",
            old_ap=None,
            new_ap=MagicMock(),
        )
        assert change.status == ChangeStatus.ADDED
        assert change.old_ap is None
        assert change.new_ap is not None

    def test_removed_ap(self):
        """Test APChange for removed AP."""
        change = APChange(
            status=ChangeStatus.REMOVED,
            ap_name="AP-102",
            floor_name="Floor 2",
            old_ap=MagicMock(),
            new_ap=None,
        )
        assert change.status == ChangeStatus.REMOVED
        assert change.old_ap is not None
        assert change.new_ap is None

    def test_moved_ap(self):
        """Test APChange for moved AP."""
        change = APChange(
            status=ChangeStatus.MOVED,
            ap_name="AP-103",
            floor_name="Floor 1",
            old_ap=MagicMock(),
            new_ap=MagicMock(),
            distance_moved=5.2,
            old_coords=(10.0, 20.0),
            new_coords=(15.0, 25.0),
        )
        assert change.status == ChangeStatus.MOVED
        assert change.distance_moved == 5.2
        assert change.old_coords == (10.0, 20.0)
        assert change.new_coords == (15.0, 25.0)

    def test_renamed_ap(self):
        """Test APChange for renamed AP."""
        change = APChange(
            status=ChangeStatus.RENAMED,
            ap_name="AP-NEW-104",
            floor_name="Floor 1",
            old_ap=MagicMock(),
            new_ap=MagicMock(),
            old_name="AP-OLD-104",
            new_name="AP-NEW-104",
        )
        assert change.status == ChangeStatus.RENAMED
        assert change.old_name == "AP-OLD-104"
        assert change.new_name == "AP-NEW-104"

    def test_modified_ap_with_changes(self):
        """Test APChange with field changes."""
        field_changes = [
            FieldChange("channel", "radio", 36, 44),
            FieldChange("tx_power", "radio", 15, 20),
        ]
        change = APChange(
            status=ChangeStatus.MODIFIED,
            ap_name="AP-105",
            floor_name="Floor 1",
            old_ap=MagicMock(),
            new_ap=MagicMock(),
            changes=field_changes,
        )
        assert change.status == ChangeStatus.MODIFIED
        assert len(change.changes) == 2
        assert change.changes[0].field_name == "channel"


class TestInventoryChange:
    """Tests for InventoryChange dataclass."""

    def test_inventory_change(self):
        """Test InventoryChange creation."""
        inv = InventoryChange(
            old_total_aps=50,
            new_total_aps=55,
            aps_added=8,
            aps_removed=3,
            aps_modified=10,
            aps_moved=5,
            aps_renamed=2,
            aps_unchanged=30,
            old_vendor_counts={"Cisco": 30, "Aruba": 20},
            new_vendor_counts={"Cisco": 32, "Aruba": 23},
            old_model_counts={"Cisco|C9130": 30, "Aruba|AP-535": 20},
            new_model_counts={"Cisco|C9130": 32, "Aruba|AP-535": 23},
        )
        assert inv.old_total_aps == 50
        assert inv.new_total_aps == 55
        assert inv.aps_added == 8
        assert inv.aps_removed == 3
        assert inv.aps_modified == 10
        assert inv.aps_moved == 5
        assert inv.aps_renamed == 2
        assert inv.aps_unchanged == 30


class TestMetadataChange:
    """Tests for MetadataChange dataclass."""

    def test_metadata_change(self):
        """Test MetadataChange creation."""
        meta = MetadataChange(
            old_name="Project v1",
            new_name="Project v2",
            old_customer="ACME Corp",
            new_customer="ACME Corporation",
            old_location="Building A",
            new_location="Building A",
            changed_fields=[
                FieldChange("name", "metadata", "Project v1", "Project v2"),
                FieldChange("customer", "metadata", "ACME Corp", "ACME Corporation"),
            ],
        )
        assert meta.old_name == "Project v1"
        assert meta.new_name == "Project v2"
        assert len(meta.changed_fields) == 2


class TestComparisonResult:
    """Tests for ComparisonResult dataclass."""

    def test_comparison_result_total_changes(self):
        """Test total_changes property."""
        ap_changes = [
            APChange(
                status=ChangeStatus.ADDED,
                ap_name="AP-1",
                floor_name="Floor 1",
            ),
            APChange(
                status=ChangeStatus.REMOVED,
                ap_name="AP-2",
                floor_name="Floor 1",
            ),
            APChange(
                status=ChangeStatus.MODIFIED,
                ap_name="AP-3",
                floor_name="Floor 1",
            ),
        ]
        result = ComparisonResult(
            project_a_name="Old",
            project_b_name="New",
            project_a_filename="old.esx",
            project_b_filename="new.esx",
            comparison_timestamp=datetime.now(),
            inventory_change=InventoryChange(
                old_total_aps=10,
                new_total_aps=10,
                aps_added=1,
                aps_removed=1,
                aps_modified=1,
                aps_moved=0,
                aps_renamed=0,
                aps_unchanged=7,
            ),
            ap_changes=ap_changes,
            changes_by_floor={"Floor 1": ap_changes},
            floors=["Floor 1"],
        )
        assert result.total_changes == 3

    def test_comparison_result_has_changes(self):
        """Test has_changes property."""
        # With changes
        result_with = ComparisonResult(
            project_a_name="Old",
            project_b_name="New",
            project_a_filename="old.esx",
            project_b_filename="new.esx",
            comparison_timestamp=datetime.now(),
            inventory_change=InventoryChange(
                old_total_aps=10,
                new_total_aps=10,
                aps_added=1,
                aps_removed=0,
                aps_modified=0,
                aps_moved=0,
                aps_renamed=0,
                aps_unchanged=9,
            ),
            ap_changes=[
                APChange(
                    status=ChangeStatus.ADDED,
                    ap_name="AP-1",
                    floor_name="Floor 1",
                )
            ],
        )
        assert result_with.has_changes is True

        # Without changes
        result_without = ComparisonResult(
            project_a_name="Old",
            project_b_name="New",
            project_a_filename="old.esx",
            project_b_filename="new.esx",
            comparison_timestamp=datetime.now(),
            inventory_change=InventoryChange(
                old_total_aps=10,
                new_total_aps=10,
                aps_added=0,
                aps_removed=0,
                aps_modified=0,
                aps_moved=0,
                aps_renamed=0,
                aps_unchanged=10,
            ),
            ap_changes=[],
        )
        assert result_without.has_changes is False


class TestChangeStatus:
    """Tests for ChangeStatus enum."""

    def test_enum_values(self):
        """Test all enum values exist."""
        assert ChangeStatus.ADDED.value == "added"
        assert ChangeStatus.REMOVED.value == "removed"
        assert ChangeStatus.MODIFIED.value == "modified"
        assert ChangeStatus.MOVED.value == "moved"
        assert ChangeStatus.RENAMED.value == "renamed"
        assert ChangeStatus.UNCHANGED.value == "unchanged"


class TestComparisonEngine:
    """Tests for ComparisonEngine class."""

    def test_init_default_threshold(self):
        """Test default move threshold."""
        engine = ComparisonEngine()
        assert engine.move_threshold == MOVE_THRESHOLD

    def test_init_custom_threshold(self):
        """Test custom move threshold."""
        engine = ComparisonEngine(move_threshold=1.0)
        assert engine.move_threshold == 1.0

    def test_compare_metadata_no_changes(self):
        """Test metadata comparison with no changes."""
        engine = ComparisonEngine()
        old_meta = {"name": "Project", "customer": "ACME", "location": "NYC"}
        new_meta = {"name": "Project", "customer": "ACME", "location": "NYC"}

        result = engine._compare_metadata(old_meta, new_meta)
        assert result is None

    def test_compare_metadata_with_changes(self):
        """Test metadata comparison with changes."""
        engine = ComparisonEngine()
        old_meta = {"name": "Project v1", "customer": "ACME", "location": "NYC"}
        new_meta = {"name": "Project v2", "customer": "ACME", "location": "LA"}

        result = engine._compare_metadata(old_meta, new_meta)
        assert result is not None
        assert result.old_name == "Project v1"
        assert result.new_name == "Project v2"
        assert result.old_location == "NYC"
        assert result.new_location == "LA"
        assert len(result.changed_fields) == 2

    def test_compare_radios_no_changes(self):
        """Test radio comparison with no changes."""
        engine = ComparisonEngine()

        old_radio = MagicMock()
        old_radio.frequency_band = "5GHz"
        old_radio.channel = 44
        old_radio.channel_width = 80
        old_radio.tx_power = 15

        new_radio = MagicMock()
        new_radio.frequency_band = "5GHz"
        new_radio.channel = 44
        new_radio.channel_width = 80
        new_radio.tx_power = 15

        changes = engine._compare_radios([old_radio], [new_radio])
        assert len(changes) == 0

    def test_compare_radios_channel_change(self):
        """Test radio comparison with channel change."""
        engine = ComparisonEngine()

        old_radio = MagicMock()
        old_radio.frequency_band = "5GHz"
        old_radio.channel = 36
        old_radio.channel_width = 80
        old_radio.tx_power = 15

        new_radio = MagicMock()
        new_radio.frequency_band = "5GHz"
        new_radio.channel = 44
        new_radio.channel_width = 80
        new_radio.tx_power = 15

        changes = engine._compare_radios([old_radio], [new_radio])
        assert len(changes) == 1
        assert changes[0].field_name == "5GHz_channel"
        assert changes[0].old_value == 36
        assert changes[0].new_value == 44

    def test_compare_radios_added(self):
        """Test radio comparison when radio is added."""
        engine = ComparisonEngine()

        new_radio = MagicMock()
        new_radio.frequency_band = "6GHz"
        new_radio.channel = 1
        new_radio.channel_width = 160
        new_radio.tx_power = 20

        changes = engine._compare_radios([], [new_radio])
        assert len(changes) == 1
        assert "added" in changes[0].new_value

    def test_compare_radios_removed(self):
        """Test radio comparison when radio is removed."""
        engine = ComparisonEngine()

        old_radio = MagicMock()
        old_radio.frequency_band = "2.4GHz"
        old_radio.channel = 6
        old_radio.channel_width = 20
        old_radio.tx_power = 10

        changes = engine._compare_radios([old_radio], [])
        assert len(changes) == 1
        assert "removed" in changes[0].new_value


class TestComparisonEngineIntegration:
    """Integration tests requiring mock file parsing."""

    @pytest.fixture
    def mock_ap_old(self):
        """Create mock old AP."""
        ap = MagicMock()
        ap.id = "ap-1-old"
        ap.name = "AP-101"
        ap.floor_id = "floor-1"
        ap.floor_name = "Floor 1"
        ap.location_x = 10.0
        ap.location_y = 20.0
        ap.vendor = "Cisco"
        ap.model = "C9130"
        ap.color = "Blue"
        ap.enabled = True
        ap.mounting_height = 3.0
        ap.azimuth = 0
        ap.tilt = 0
        ap.tags = {}
        return ap

    @pytest.fixture
    def mock_ap_new(self):
        """Create mock new AP."""
        ap = MagicMock()
        ap.id = "ap-1-new"
        ap.name = "AP-101"
        ap.floor_id = "floor-1"
        ap.floor_name = "Floor 1"
        ap.location_x = 10.0
        ap.location_y = 20.0
        ap.vendor = "Cisco"
        ap.model = "C9130"
        ap.color = "Blue"
        ap.enabled = True
        ap.mounting_height = 3.0
        ap.azimuth = 0
        ap.tilt = 0
        ap.tags = {}
        return ap

    def test_compare_access_points_unchanged(self, mock_ap_old, mock_ap_new):
        """Test comparing unchanged APs."""
        engine = ComparisonEngine()

        changes = engine._compare_access_points([mock_ap_old], [mock_ap_new], {}, {})
        # Unchanged APs should not appear in changes
        assert len(changes) == 0

    def test_compare_access_points_moved(self, mock_ap_old, mock_ap_new):
        """Test detecting moved AP."""
        engine = ComparisonEngine()

        # Move the AP
        mock_ap_new.location_x = 15.0
        mock_ap_new.location_y = 25.0

        changes = engine._compare_access_points([mock_ap_old], [mock_ap_new], {}, {})
        assert len(changes) == 1
        assert changes[0].status == ChangeStatus.MOVED
        assert changes[0].ap_name == "AP-101"
        # Distance should be ~7.07 meters (sqrt(25 + 25))
        assert 7.0 < changes[0].distance_moved < 7.2

    def test_compare_access_points_added(self, mock_ap_new):
        """Test detecting added AP."""
        engine = ComparisonEngine()

        changes = engine._compare_access_points([], [mock_ap_new], {}, {})
        assert len(changes) == 1
        assert changes[0].status == ChangeStatus.ADDED
        assert changes[0].ap_name == "AP-101"

    def test_compare_access_points_removed(self, mock_ap_old):
        """Test detecting removed AP."""
        engine = ComparisonEngine()

        changes = engine._compare_access_points([mock_ap_old], [], {}, {})
        assert len(changes) == 1
        assert changes[0].status == ChangeStatus.REMOVED
        assert changes[0].ap_name == "AP-101"

    def test_compare_access_points_modified(self, mock_ap_old, mock_ap_new):
        """Test detecting modified AP (config change, same position)."""
        engine = ComparisonEngine()

        # Change a config field
        mock_ap_new.color = "Yellow"

        changes = engine._compare_access_points([mock_ap_old], [mock_ap_new], {}, {})
        assert len(changes) == 1
        assert changes[0].status == ChangeStatus.MODIFIED
        assert len(changes[0].changes) == 1
        assert changes[0].changes[0].field_name == "color"

    def test_compare_access_points_renamed(self, mock_ap_old, mock_ap_new):
        """Test detecting renamed AP (same position, different name)."""
        engine = ComparisonEngine()

        # Rename the AP
        mock_ap_new.name = "AP-NEW-101"

        changes = engine._compare_access_points([mock_ap_old], [mock_ap_new], {}, {})
        assert len(changes) == 1
        assert changes[0].status == ChangeStatus.RENAMED
        assert changes[0].old_name == "AP-101"
        assert changes[0].new_name == "AP-NEW-101"

    def test_calculate_inventory_change(self, mock_ap_old, mock_ap_new):
        """Test inventory change calculation."""
        engine = ComparisonEngine()

        # Create additional APs
        added_ap = MagicMock()
        added_ap.vendor = "Aruba"
        added_ap.model = "AP-535"

        removed_ap = MagicMock()
        removed_ap.vendor = "Cisco"
        removed_ap.model = "C9120"

        ap_changes = [
            APChange(
                status=ChangeStatus.ADDED,
                ap_name="AP-102",
                floor_name="Floor 1",
                new_ap=added_ap,
            ),
            APChange(
                status=ChangeStatus.REMOVED,
                ap_name="AP-103",
                floor_name="Floor 1",
                old_ap=removed_ap,
            ),
            APChange(
                status=ChangeStatus.MODIFIED,
                ap_name="AP-104",
                floor_name="Floor 1",
            ),
        ]

        old_aps = [mock_ap_old, removed_ap]
        new_aps = [mock_ap_new, added_ap]

        inv = engine._calculate_inventory_change(old_aps, new_aps, ap_changes)

        assert inv.old_total_aps == 2
        assert inv.new_total_aps == 2
        assert inv.aps_added == 1
        assert inv.aps_removed == 1
        assert inv.aps_modified == 1


class TestMoveThresholdBehavior:
    """Tests for move threshold edge cases."""

    def test_below_threshold_not_moved(self):
        """AP moved less than threshold should not be marked as moved."""
        engine = ComparisonEngine(move_threshold=1.0)

        old_ap = MagicMock()
        old_ap.id = "ap-1"
        old_ap.name = "AP-1"
        old_ap.floor_id = "f1"
        old_ap.floor_name = "Floor 1"
        old_ap.location_x = 0.0
        old_ap.location_y = 0.0
        old_ap.vendor = "Cisco"
        old_ap.model = "C9130"
        old_ap.color = "Blue"
        old_ap.enabled = True
        old_ap.mounting_height = 3.0
        old_ap.azimuth = 0
        old_ap.tilt = 0
        old_ap.tags = {}

        new_ap = MagicMock()
        new_ap.id = "ap-1"
        new_ap.name = "AP-1"
        new_ap.floor_id = "f1"
        new_ap.floor_name = "Floor 1"
        new_ap.location_x = 0.5  # 0.5m movement - below 1.0m threshold
        new_ap.location_y = 0.5
        new_ap.vendor = "Cisco"
        new_ap.model = "C9130"
        new_ap.color = "Blue"
        new_ap.enabled = True
        new_ap.mounting_height = 3.0
        new_ap.azimuth = 0
        new_ap.tilt = 0
        new_ap.tags = {}

        changes = engine._compare_access_points([old_ap], [new_ap], {}, {})
        # Movement of ~0.7m (sqrt(0.5^2 + 0.5^2)) is below 1.0m threshold
        assert len(changes) == 0

    def test_above_threshold_is_moved(self):
        """AP moved more than threshold should be marked as moved."""
        engine = ComparisonEngine(move_threshold=0.5)

        old_ap = MagicMock()
        old_ap.id = "ap-1"
        old_ap.name = "AP-1"
        old_ap.floor_id = "f1"
        old_ap.floor_name = "Floor 1"
        old_ap.location_x = 0.0
        old_ap.location_y = 0.0
        old_ap.vendor = "Cisco"
        old_ap.model = "C9130"
        old_ap.color = "Blue"
        old_ap.enabled = True
        old_ap.mounting_height = 3.0
        old_ap.azimuth = 0
        old_ap.tilt = 0
        old_ap.tags = {}

        new_ap = MagicMock()
        new_ap.id = "ap-1"
        new_ap.name = "AP-1"
        new_ap.floor_id = "f1"
        new_ap.floor_name = "Floor 1"
        new_ap.location_x = 1.0  # 1.0m movement - above 0.5m threshold
        new_ap.location_y = 0.0
        new_ap.vendor = "Cisco"
        new_ap.model = "C9130"
        new_ap.color = "Blue"
        new_ap.enabled = True
        new_ap.mounting_height = 3.0
        new_ap.azimuth = 0
        new_ap.tilt = 0
        new_ap.tags = {}

        changes = engine._compare_access_points([old_ap], [new_ap], {}, {})
        assert len(changes) == 1
        assert changes[0].status == ChangeStatus.MOVED
        assert changes[0].distance_moved == 1.0


class TestFloorChangeDetection:
    """Tests for floor change detection."""

    def test_floor_change_is_moved(self):
        """AP moved to different floor should be marked as moved."""
        engine = ComparisonEngine()

        old_ap = MagicMock()
        old_ap.id = "ap-1"
        old_ap.name = "AP-1"
        old_ap.floor_id = "floor-1"
        old_ap.floor_name = "Floor 1"
        old_ap.location_x = 10.0
        old_ap.location_y = 20.0
        old_ap.vendor = "Cisco"
        old_ap.model = "C9130"
        old_ap.color = "Blue"
        old_ap.enabled = True
        old_ap.mounting_height = 3.0
        old_ap.azimuth = 0
        old_ap.tilt = 0
        old_ap.tags = {}

        new_ap = MagicMock()
        new_ap.id = "ap-1"
        new_ap.name = "AP-1"
        new_ap.floor_id = "floor-2"  # Different floor
        new_ap.floor_name = "Floor 2"
        new_ap.location_x = 10.0  # Same coordinates
        new_ap.location_y = 20.0
        new_ap.vendor = "Cisco"
        new_ap.model = "C9130"
        new_ap.color = "Blue"
        new_ap.enabled = True
        new_ap.mounting_height = 3.0
        new_ap.azimuth = 0
        new_ap.tilt = 0
        new_ap.tags = {}

        changes = engine._compare_access_points([old_ap], [new_ap], {}, {})
        assert len(changes) == 1
        assert changes[0].status == ChangeStatus.MOVED
