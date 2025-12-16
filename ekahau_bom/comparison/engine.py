"""Core comparison engine for Ekahau projects."""

import logging
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from ekahau_bom.comparison.models import (
    APChange,
    ChangeStatus,
    ComparisonResult,
    FieldChange,
    InventoryChange,
    MetadataChange,
)
from ekahau_bom.models import AccessPoint, Floor
from ekahau_bom.parser import EkahauParser
from ekahau_bom.processors.access_points import AccessPointProcessor
from ekahau_bom.processors.metadata import ProjectMetadataProcessor
from ekahau_bom.processors.radios import RadioProcessor
from ekahau_bom.processors.tags import TagProcessor
from ekahau_bom.utils import load_color_database

logger = logging.getLogger(__name__)

# Threshold for considering an AP as "moved" (in meters)
MOVE_THRESHOLD = 0.5


def calculate_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate Euclidean distance between two points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


class ComparisonEngine:
    """Engine for comparing two Ekahau project files."""

    def __init__(self, move_threshold: float = MOVE_THRESHOLD):
        """Initialize comparison engine.

        Args:
            move_threshold: Distance threshold (meters) for detecting moved APs
        """
        self.move_threshold = move_threshold

    def compare_files(self, old_file: Path, new_file: Path) -> ComparisonResult:
        """Compare two .esx files and return comparison result.

        Args:
            old_file: Path to the old/previous .esx file
            new_file: Path to the new/current .esx file

        Returns:
            ComparisonResult with all detected changes
        """
        logger.info(f"Comparing {old_file.name} with {new_file.name}")

        # Parse both files
        old_data = self._parse_project(old_file)
        new_data = self._parse_project(new_file)

        # Extract project metadata
        old_metadata = old_data.get("metadata", {})
        new_metadata = new_data.get("metadata", {})

        # Get access points with their radios
        old_aps = old_data.get("access_points", [])
        new_aps = new_data.get("access_points", [])
        old_radios = old_data.get("radios", {})  # ap_id -> list of radios
        new_radios = new_data.get("radios", {})
        # Get floors for meters_per_unit conversion (use new_data as reference)
        floors = new_data.get("floors", {})

        # Compare
        ap_changes = self._compare_access_points(old_aps, new_aps, old_radios, new_radios, floors)
        metadata_change = self._compare_metadata(old_metadata, new_metadata)
        inventory_change = self._calculate_inventory_change(old_aps, new_aps, ap_changes)

        # Group changes by floor
        changes_by_floor = defaultdict(list)
        floors = set()
        for change in ap_changes:
            changes_by_floor[change.floor_name].append(change)
            floors.add(change.floor_name)

        result = ComparisonResult(
            project_a_name=old_metadata.get("name", old_file.stem),
            project_b_name=new_metadata.get("name", new_file.stem),
            project_a_filename=old_file.name,
            project_b_filename=new_file.name,
            comparison_timestamp=datetime.now(),
            inventory_change=inventory_change,
            metadata_change=metadata_change,
            ap_changes=ap_changes,
            changes_by_floor=dict(changes_by_floor),
            floors=sorted(floors),
        )

        logger.info(
            f"Comparison complete: {result.total_changes} changes detected "
            f"(+{inventory_change.aps_added}, -{inventory_change.aps_removed}, "
            f"~{inventory_change.aps_modified}, ↔{inventory_change.aps_moved}, "
            f"⟳{inventory_change.aps_renamed})"
        )

        return result

    def _parse_project(self, file_path: Path) -> dict:
        """Parse .esx file and extract relevant data."""
        with EkahauParser(file_path) as parser:
            # Get raw data from parser
            access_points_data = parser.get_access_points()
            floor_plans_data = parser.get_floor_plans()
            simulated_radios_data = parser.get_simulated_radios()
            tag_keys_data = parser.get_tag_keys()
            project_metadata_data = parser.get_project_metadata()
            building_floors_data = parser.get_building_floors()

            # Create floor number mapping
            floor_number_map = {
                bf["floorPlanId"]: bf.get("floorNumber", 0)
                for bf in building_floors_data.get("buildingFloors", [])
            }

            # Build floor lookup dictionary
            floors = {
                floor["id"]: Floor(
                    id=floor["id"],
                    name=floor["name"],
                    floor_number=floor_number_map.get(floor["id"], 0),
                    meters_per_unit=floor.get("metersPerUnit", 1.0),
                    width=floor.get("width", 0.0),
                    height=floor.get("height", 0.0),
                )
                for floor in floor_plans_data.get("floorPlans", [])
            }

            # Process metadata
            metadata_processor = ProjectMetadataProcessor()
            metadata = metadata_processor.process(project_metadata_data)

            # Process tags
            tag_processor = TagProcessor(tag_keys_data)

            # Process access points
            color_db = load_color_database()
            ap_processor = AccessPointProcessor(color_db, tag_processor)
            access_points = ap_processor.process(access_points_data, floors, simulated_radios_data)

            # Get radios grouped by AP
            radio_processor = RadioProcessor()
            all_radios = radio_processor.process(simulated_radios_data)
            radios_by_ap = defaultdict(list)
            for radio in all_radios:
                radios_by_ap[radio.access_point_id].append(radio)

            return {
                "metadata": {
                    "name": metadata.name or metadata.title,
                    "customer": metadata.customer,
                    "location": metadata.location,
                    "responsible_person": metadata.responsible_person,
                },
                "access_points": access_points,
                "radios": dict(radios_by_ap),
                "floors": floors,
            }

    def _compare_access_points(
        self,
        old_aps: list[AccessPoint],
        new_aps: list[AccessPoint],
        old_radios: dict,
        new_radios: dict,
        floors: dict = None,
    ) -> list[APChange]:
        """Compare access points between two projects."""
        changes = []
        floors = floors or {}

        # Create dictionaries by name
        old_by_name = {ap.name: ap for ap in old_aps}
        new_by_name = {ap.name: ap for ap in new_aps}

        # Find matched, only-old, only-new names
        matched_names = set(old_by_name.keys()) & set(new_by_name.keys())
        only_old_names = set(old_by_name.keys()) - set(new_by_name.keys())
        only_new_names = set(new_by_name.keys()) - set(old_by_name.keys())

        # Process matched APs (same name in both)
        for name in matched_names:
            old_ap = old_by_name[name]
            new_ap = new_by_name[name]
            change = self._compare_single_ap(
                old_ap, new_ap, old_radios.get(old_ap.id, []), new_radios.get(new_ap.id, []), floors
            )
            if change:
                changes.append(change)

        # Process potentially removed/renamed APs
        removed_candidates = [(name, old_by_name[name]) for name in only_old_names]
        added_candidates = [(name, new_by_name[name]) for name in only_new_names]

        # Try to detect renames (same position, different name)
        renamed_old = set()
        renamed_new = set()

        for old_name, old_ap in removed_candidates:
            for new_name, new_ap in added_candidates:
                if new_name in renamed_new:
                    continue
                # Check if same floor and close coordinates
                if old_ap.floor_id == new_ap.floor_id:
                    distance_units = calculate_distance(
                        old_ap.location_x or 0,
                        old_ap.location_y or 0,
                        new_ap.location_x or 0,
                        new_ap.location_y or 0,
                    )
                    # Convert to meters
                    floor = floors.get(new_ap.floor_id)
                    meters_per_unit = floor.meters_per_unit if floor else 1.0
                    distance = distance_units * meters_per_unit
                    if distance < self.move_threshold:
                        # Likely renamed
                        changes.append(
                            APChange(
                                status=ChangeStatus.RENAMED,
                                ap_name=new_name,
                                floor_name=new_ap.floor_name or "Unknown",
                                old_ap=old_ap,
                                new_ap=new_ap,
                                old_name=old_name,
                                new_name=new_name,
                            )
                        )
                        renamed_old.add(old_name)
                        renamed_new.add(new_name)
                        break

        # Remaining only-old are removed
        for name in only_old_names:
            if name not in renamed_old:
                old_ap = old_by_name[name]
                changes.append(
                    APChange(
                        status=ChangeStatus.REMOVED,
                        ap_name=name,
                        floor_name=old_ap.floor_name or "Unknown",
                        old_ap=old_ap,
                        new_ap=None,
                    )
                )

        # Remaining only-new are added
        for name in only_new_names:
            if name not in renamed_new:
                new_ap = new_by_name[name]
                changes.append(
                    APChange(
                        status=ChangeStatus.ADDED,
                        ap_name=name,
                        floor_name=new_ap.floor_name or "Unknown",
                        old_ap=None,
                        new_ap=new_ap,
                    )
                )

        return changes

    def _compare_single_ap(
        self,
        old_ap: AccessPoint,
        new_ap: AccessPoint,
        old_radios: list,
        new_radios: list,
        floors: dict = None,
    ) -> Optional[APChange]:
        """Compare a single AP between versions."""
        field_changes = []
        floors = floors or {}

        # Check position change
        old_x = old_ap.location_x or 0
        old_y = old_ap.location_y or 0
        new_x = new_ap.location_x or 0
        new_y = new_ap.location_y or 0
        distance_units = calculate_distance(old_x, old_y, new_x, new_y)

        # Convert distance from units to meters using floor's meters_per_unit
        floor = floors.get(new_ap.floor_id) or floors.get(old_ap.floor_id)
        meters_per_unit = floor.meters_per_unit if floor else 1.0
        distance = distance_units * meters_per_unit

        position_changed = distance > self.move_threshold

        # Check floor change
        floor_changed = old_ap.floor_id != new_ap.floor_id

        # Compare placement fields
        placement_fields = [
            ("mounting_height", "placement"),
            ("azimuth", "placement"),
            ("tilt", "placement"),
        ]
        for field, category in placement_fields:
            old_val = getattr(old_ap, field, None)
            new_val = getattr(new_ap, field, None)
            if old_val != new_val:
                field_changes.append(FieldChange(field, category, old_val, new_val))

        # Compare configuration fields
        config_fields = [
            ("vendor", "configuration"),
            ("model", "configuration"),
            ("color", "configuration"),
            ("enabled", "configuration"),
        ]
        for field, category in config_fields:
            old_val = getattr(old_ap, field, None)
            new_val = getattr(new_ap, field, None)
            if old_val != new_val:
                field_changes.append(FieldChange(field, category, old_val, new_val))

        # Compare tags
        old_tags = old_ap.tags or {}
        new_tags = new_ap.tags or {}
        if old_tags != new_tags:
            field_changes.append(FieldChange("tags", "configuration", old_tags, new_tags))

        # Compare radios
        radio_changes = self._compare_radios(old_radios, new_radios)
        field_changes.extend(radio_changes)

        # Determine status
        if not field_changes and not position_changed and not floor_changed:
            return None  # Unchanged

        if position_changed or floor_changed:
            return APChange(
                status=ChangeStatus.MOVED,
                ap_name=new_ap.name,
                floor_name=new_ap.floor_name or "Unknown",
                old_ap=old_ap,
                new_ap=new_ap,
                distance_moved=distance,
                old_coords=(old_x, old_y),
                new_coords=(new_x, new_y),
                changes=field_changes,
            )
        else:
            return APChange(
                status=ChangeStatus.MODIFIED,
                ap_name=new_ap.name,
                floor_name=new_ap.floor_name or "Unknown",
                old_ap=old_ap,
                new_ap=new_ap,
                changes=field_changes,
            )

    def _compare_radios(self, old_radios: list, new_radios: list) -> list[FieldChange]:
        """Compare radio configurations."""
        changes = []

        # Group by frequency band for comparison
        def group_by_band(radios):
            result = {}
            for r in radios:
                band = getattr(r, "frequency_band", None) or "unknown"
                result[band] = r
            return result

        old_by_band = group_by_band(old_radios)
        new_by_band = group_by_band(new_radios)

        all_bands = set(old_by_band.keys()) | set(new_by_band.keys())

        for band in all_bands:
            old_r = old_by_band.get(band)
            new_r = new_by_band.get(band)

            if old_r and new_r:
                # Compare radio fields
                radio_fields = ["channel", "channel_width", "tx_power"]
                for field in radio_fields:
                    old_val = getattr(old_r, field, None)
                    new_val = getattr(new_r, field, None)
                    if old_val != new_val:
                        changes.append(FieldChange(f"{band}_{field}", "radio", old_val, new_val))
            elif old_r and not new_r:
                changes.append(FieldChange(f"{band}_radio", "radio", "present", "removed"))
            elif new_r and not old_r:
                changes.append(FieldChange(f"{band}_radio", "radio", "absent", "added"))

        return changes

    def _compare_metadata(self, old_meta: dict, new_meta: dict) -> Optional[MetadataChange]:
        """Compare project metadata."""
        changes = []

        fields = ["name", "customer", "location", "responsible_person"]
        for field in fields:
            old_val = old_meta.get(field)
            new_val = new_meta.get(field)
            if old_val != new_val:
                changes.append(FieldChange(field, "metadata", old_val, new_val))

        if not changes:
            return None

        return MetadataChange(
            old_name=old_meta.get("name"),
            new_name=new_meta.get("name"),
            old_customer=old_meta.get("customer"),
            new_customer=new_meta.get("customer"),
            old_location=old_meta.get("location"),
            new_location=new_meta.get("location"),
            changed_fields=changes,
        )

    def _calculate_inventory_change(
        self,
        old_aps: list[AccessPoint],
        new_aps: list[AccessPoint],
        ap_changes: list[APChange],
    ) -> InventoryChange:
        """Calculate inventory-level statistics."""
        # Count by status
        counts = defaultdict(int)
        for change in ap_changes:
            counts[change.status] += 1

        # Unchanged = total new - all changes (since unchanged APs aren't in ap_changes)
        unchanged = len(new_aps) - sum(
            1
            for c in ap_changes
            if c.status
            in (ChangeStatus.ADDED, ChangeStatus.MODIFIED, ChangeStatus.MOVED, ChangeStatus.RENAMED)
        )

        # Vendor/model counts
        def count_vendors_models(aps):
            vendor_counts = defaultdict(int)
            model_counts = defaultdict(int)
            for ap in aps:
                vendor = ap.vendor or "Unknown"
                model = ap.model or "Unknown"
                vendor_counts[vendor] += 1
                model_counts[f"{vendor}|{model}"] += 1
            return dict(vendor_counts), dict(model_counts)

        old_vendors, old_models = count_vendors_models(old_aps)
        new_vendors, new_models = count_vendors_models(new_aps)

        return InventoryChange(
            old_total_aps=len(old_aps),
            new_total_aps=len(new_aps),
            aps_added=counts[ChangeStatus.ADDED],
            aps_removed=counts[ChangeStatus.REMOVED],
            aps_modified=counts[ChangeStatus.MODIFIED],
            aps_moved=counts[ChangeStatus.MOVED],
            aps_renamed=counts[ChangeStatus.RENAMED],
            aps_unchanged=unchanged,
            old_vendor_counts=old_vendors,
            new_vendor_counts=new_vendors,
            old_model_counts=old_models,
            new_model_counts=new_models,
        )
