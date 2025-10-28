#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for FloorPlanVisualizer."""

from __future__ import annotations


import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from ekahau_bom.visualizers.floor_plan import FloorPlanVisualizer, PIL_AVAILABLE
from ekahau_bom.models import AccessPoint, Floor

# Skip all tests if PIL is not available
pytestmark = pytest.mark.skipif(not PIL_AVAILABLE, reason="Pillow not installed")


class TestFloorPlanVisualizer:
    """Test suite for FloorPlanVisualizer."""

    @pytest.fixture
    def temp_esx_path(self, tmp_path):
        """Create a temporary .esx file path."""
        esx_file = tmp_path / "test.esx"
        esx_file.touch()
        return esx_file

    @pytest.fixture
    def temp_output_dir(self, tmp_path):
        """Create a temporary output directory."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        return output_dir

    @pytest.fixture
    def sample_floors(self):
        """Create sample floors dictionary."""
        return {
            "floor1": Floor(id="floor1", name="Floor 1"),
            "floor2": Floor(id="floor2", name="Floor 2"),
        }

    @pytest.fixture
    def sample_access_points(self):
        """Create sample access points."""
        return [
            AccessPoint(
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                location_x=100.0,
                location_y=200.0,
                color="Red",
                name="AP1",
            ),
            AccessPoint(
                vendor="Aruba",
                model="AP-2",
                floor_id="floor1",
                floor_name="Floor 1",
                location_x=300.0,
                location_y=400.0,
                color="Green",
                name="AP2",
            ),
            AccessPoint(
                vendor="Ubiquiti",
                model="AP-3",
                floor_id="floor2",
                floor_name="Floor 2",
                location_x=150.0,
                location_y=250.0,
                color="Blue",
                name="AP3",
            ),
        ]

    def test_hex_to_rgb_valid(self, temp_esx_path, temp_output_dir):
        """Test hex to RGB conversion with valid colors."""
        with patch("zipfile.ZipFile"):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

            # Test with # prefix
            assert viz._hex_to_rgb("#FF0000") == (255, 0, 0)
            assert viz._hex_to_rgb("#00FF00") == (0, 255, 0)
            assert viz._hex_to_rgb("#0000FF") == (0, 0, 255)

            # Test without # prefix
            assert viz._hex_to_rgb("FF0000") == (255, 0, 0)

            # Test short form
            assert viz._hex_to_rgb("#F00") == (255, 0, 0)

            viz.close()

    def test_hex_to_rgb_invalid(self, temp_esx_path, temp_output_dir):
        """Test hex to RGB conversion with invalid colors."""
        with patch("zipfile.ZipFile"):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

            # Invalid hex should return black
            assert viz._hex_to_rgb("invalid") == (0, 0, 0)
            assert viz._hex_to_rgb("#") == (0, 0, 0)

            viz.close()

    def test_initialization(self, temp_esx_path, temp_output_dir):
        """Test FloorPlanVisualizer initialization."""
        with patch("zipfile.ZipFile"):
            viz = FloorPlanVisualizer(
                esx_path=temp_esx_path,
                output_dir=temp_output_dir,
                ap_circle_radius=20,
                show_ap_names=False,
            )

            assert viz.esx_path == temp_esx_path
            assert viz.output_dir == temp_output_dir
            assert viz.ap_circle_radius == 20
            assert viz.show_ap_names is False
            assert viz.output_dir.exists()

            viz.close()

    def test_context_manager(self, temp_esx_path, temp_output_dir):
        """Test FloorPlanVisualizer as context manager."""
        with patch("zipfile.ZipFile"):
            with FloorPlanVisualizer(temp_esx_path, temp_output_dir) as viz:
                assert viz is not None

    def test_visualize_floor_no_image(
        self, temp_esx_path, temp_output_dir, sample_floors, sample_access_points
    ):
        """Test visualization when floor plan image is not found."""
        # Create a mock archive that doesn't have the floor plan image
        with patch("zipfile.ZipFile"):
            with patch.object(FloorPlanVisualizer, "_get_floor_plan_image", return_value=None):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

                result = viz.visualize_floor(
                    floor=sample_floors["floor1"], access_points=sample_access_points
                )

                assert result is None
                viz.close()

    def test_visualize_floor_ap_without_location(
        self, temp_esx_path, temp_output_dir, sample_floors
    ):
        """Test visualization with AP without location."""
        from PIL import Image

        # Create a test image
        test_image = Image.new("RGB", (100, 100), color="white")

        aps = [
            AccessPoint(
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                location_x=None,  # No location
                location_y=None,
                color="Red",
                name="AP1",
            )
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

                result = viz.visualize_floor(floor=sample_floors["floor1"], access_points=aps)

                # Should still create the image even if no APs are drawn
                assert result is not None
                assert result.exists()
                viz.close()

    def test_visualize_all_floors_empty(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test visualization with no access points."""
        with patch("zipfile.ZipFile"):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

            result = viz.visualize_all_floors(floors=sample_floors, access_points=[])

            assert result == []
            viz.close()

    def test_visualize_all_floors_with_aps(
        self, temp_esx_path, temp_output_dir, sample_floors, sample_access_points
    ):
        """Test visualization with multiple floors and APs."""
        from PIL import Image

        # Create a test image
        test_image = Image.new("RGB", (500, 500), color="white")

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

                result = viz.visualize_all_floors(
                    floors=sample_floors, access_points=sample_access_points
                )

                # Should generate visualizations for 2 floors
                assert len(result) == 2
                assert all(f.exists() for f in result)
                viz.close()

    def test_missing_pillow(self, temp_esx_path, temp_output_dir):
        """Test error when Pillow is not available."""
        with patch("ekahau_bom.visualizers.floor_plan.PIL_AVAILABLE", False):
            with pytest.raises(ImportError, match="Pillow library is required"):
                FloorPlanVisualizer(temp_esx_path, temp_output_dir)

    def test_ap_colors(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test that AP colors are correctly applied."""
        from PIL import Image

        # Create a test image
        test_image = Image.new("RGB", (500, 500), color="white")

        aps = [
            AccessPoint(
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                location_x=100.0,
                location_y=100.0,
                color="#FF0000",  # Red
                name="RedAP",
            ),
            AccessPoint(
                vendor="Aruba",
                model="AP-2",
                floor_id="floor1",
                floor_name="Floor 1",
                location_x=200.0,
                location_y=200.0,
                color="Blue",  # Default color
                name="DefaultAP",
            ),
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

                result = viz.visualize_floor(floor=sample_floors["floor1"], access_points=aps)

                assert result is not None
                assert result.exists()
                viz.close()

    def test_custom_circle_radius(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test custom AP circle radius."""
        from PIL import Image

        # Create a test image
        test_image = Image.new("RGB", (500, 500), color="white")

        aps = [
            AccessPoint(
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                location_x=100.0,
                location_y=100.0,
                color="Red",
                name="AP1",
            )
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir, ap_circle_radius=30)

                assert viz.ap_circle_radius == 30

                result = viz.visualize_floor(floor=sample_floors["floor1"], access_points=aps)

                assert result is not None
                viz.close()

    def test_no_ap_names(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test visualization without AP names."""
        from PIL import Image

        # Create a test image
        test_image = Image.new("RGB", (500, 500), color="white")

        aps = [
            AccessPoint(
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                location_x=100.0,
                location_y=100.0,
                color="Red",
                name="AP1",
            )
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir, show_ap_names=False)

                assert viz.show_ap_names is False

                result = viz.visualize_floor(floor=sample_floors["floor1"], access_points=aps)

                assert result is not None
                viz.close()

    def test_wall_mounted_aps_with_azimuth(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test visualization of wall-mounted APs with rectangle markers."""
        from PIL import Image
        from ekahau_bom.models import Radio

        test_image = Image.new("RGB", (500, 500), color="white")

        # Wall-mounted APs with azimuth
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=100.0,
                location_y=100.0,
                color="Red",
                name="Wall-AP-1",
            ),
            AccessPoint(
                id="ap2",
                vendor="Aruba",
                model="AP-2",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=200.0,
                location_y=200.0,
                color="Blue",
                name="Wall-AP-2",
            ),
        ]

        # Create Radio objects with mounting type and azimuth
        radios = [
            Radio(
                id="radio1",
                access_point_id="ap1",
                antenna_mounting="WALL",
                antenna_direction=45.0,
            ),
            Radio(
                id="radio2",
                access_point_id="ap2",
                antenna_mounting="WALL",
                antenna_direction=90.0,
            ),
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
                result = viz.visualize_floor(
                    floor=sample_floors["floor1"], access_points=aps, radios=radios
                )

                assert result is not None
                assert result.exists()
                viz.close()

    def test_floor_mounted_aps_with_square_markers(
        self, temp_esx_path, temp_output_dir, sample_floors
    ):
        """Test visualization of floor-mounted APs with square markers."""
        from PIL import Image
        from ekahau_bom.models import Radio

        test_image = Image.new("RGB", (500, 500), color="white")

        # Floor-mounted APs
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=100.0,
                location_y=100.0,
                color="Green",
                name="Floor-AP-1",
            ),
            AccessPoint(
                id="ap2",
                vendor="Aruba",
                model="AP-2",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=200.0,
                location_y=200.0,
                color="Yellow",
                name="Floor-AP-2",
            ),
        ]

        # Create Radio objects with FLOOR mounting type
        radios = [
            Radio(id="radio1", access_point_id="ap1", antenna_mounting="FLOOR"),
            Radio(id="radio2", access_point_id="ap2", antenna_mounting="FLOOR"),
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
                result = viz.visualize_floor(
                    floor=sample_floors["floor1"], access_points=aps, radios=radios
                )

                assert result is not None
                assert result.exists()
                viz.close()

    def test_azimuth_arrows_visualization(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test visualization with azimuth arrows enabled."""
        from PIL import Image
        from ekahau_bom.models import Radio

        test_image = Image.new("RGB", (500, 500), color="white")

        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=100.0,
                location_y=100.0,
                color="Red",
                name="AP-1",
            ),
            AccessPoint(
                id="ap2",
                vendor="Aruba",
                model="AP-2",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=200.0,
                location_y=200.0,
                color="Blue",
                name="AP-2",
            ),
        ]

        # Create Radio objects with mounting type and azimuth
        radios = [
            Radio(
                id="radio1",
                access_point_id="ap1",
                antenna_mounting="CEILING",
                antenna_direction=45.0,
            ),
            Radio(
                id="radio2",
                access_point_id="ap2",
                antenna_mounting="WALL",
                antenna_direction=135.0,
            ),
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir, show_azimuth_arrows=True)

                assert viz.show_azimuth_arrows is True

                result = viz.visualize_floor(
                    floor=sample_floors["floor1"], access_points=aps, radios=radios
                )

                assert result is not None
                assert result.exists()
                viz.close()

    def test_ap_with_zero_azimuth(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test that azimuth arrows are not drawn when azimuth is 0."""
        from PIL import Image

        test_image = Image.new("RGB", (500, 500), color="white")

        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=100.0,
                location_y=100.0,
                color="Red",
                name="AP-1",
                azimuth=0.0,  # Zero azimuth - arrow should not be drawn
            )
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir, show_azimuth_arrows=True)
                result = viz.visualize_floor(floor=sample_floors["floor1"], access_points=aps)

                assert result is not None
                viz.close()

    def test_mixed_mounting_types(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test visualization with mixed mounting types (ceiling, wall, floor)."""
        from PIL import Image
        from ekahau_bom.models import Radio

        test_image = Image.new("RGB", (500, 500), color="white")

        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=100.0,
                location_y=100.0,
                color="Red",
                name="Ceiling-AP",
            ),
            AccessPoint(
                id="ap2",
                vendor="Aruba",
                model="AP-2",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=200.0,
                location_y=200.0,
                color="Blue",
                name="Wall-AP",
            ),
            AccessPoint(
                id="ap3",
                vendor="Ubiquiti",
                model="AP-3",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=300.0,
                location_y=300.0,
                color="Green",
                name="Floor-AP",
            ),
        ]

        # Create Radio objects with different mounting types
        radios = [
            Radio(id="radio1", access_point_id="ap1", antenna_mounting="CEILING"),
            Radio(
                id="radio2",
                access_point_id="ap2",
                antenna_mounting="WALL",
                antenna_direction=90.0,
            ),
            Radio(id="radio3", access_point_id="ap3", antenna_mounting="FLOOR"),
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
                result = viz.visualize_floor(
                    floor=sample_floors["floor1"], access_points=aps, radios=radios
                )

                assert result is not None
                assert result.exists()
                viz.close()

    def test_ap_opacity_setting(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test AP marker opacity setting."""
        from PIL import Image

        test_image = Image.new("RGB", (500, 500), color="white")

        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=100.0,
                location_y=100.0,
                color="Red",
                name="AP-1",
            )
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir, ap_opacity=0.5)

                assert viz.ap_opacity == 0.5

                result = viz.visualize_floor(floor=sample_floors["floor1"], access_points=aps)

                assert result is not None
                viz.close()

    def test_color_name_handling(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test handling of color names (not hex codes)."""
        from PIL import Image

        test_image = Image.new("RGB", (500, 500), color="white")

        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=100.0,
                location_y=100.0,
                color="Red",
                name="AP-Red",  # Color name, not hex
            ),
            AccessPoint(
                id="ap2",
                vendor="Aruba",
                model="AP-2",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=200.0,
                location_y=200.0,
                color="lightblue",
                name="AP-LightBlue",  # Ekahau color name
            ),
            AccessPoint(
                id="ap3",
                vendor="Ubiquiti",
                model="AP-3",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=300.0,
                location_y=300.0,
                color=None,
                name="AP-Default",  # No color (use default)
            ),
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
                result = viz.visualize_floor(floor=sample_floors["floor1"], access_points=aps)

                assert result is not None
                viz.close()

    def test_image_loading_errors(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test handling of image loading errors."""
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=100.0,
                location_y=100.0,
                color="Red",
                name="AP-1",
            )
        ]

        with patch("zipfile.ZipFile"):
            # Simulate image loading failure
            with patch.object(FloorPlanVisualizer, "_get_floor_plan_image", return_value=None):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
                result = viz.visualize_floor(floor=sample_floors["floor1"], access_points=aps)

                # Should return None when image cannot be loaded
                assert result is None
                viz.close()

    def test_get_floor_plan_image_floor_not_found(
        self, temp_esx_path, temp_output_dir, sample_floors
    ):
        """Test _get_floor_plan_image when floor plan is not found in metadata."""
        import json

        # Mock archive with floorPlans.json that doesn't contain our floor
        mock_archive = Mock()
        floor_plans_data = {"floorPlans": []}  # Empty list - floor not found
        mock_archive.read.return_value = json.dumps(floor_plans_data).encode()

        with patch("zipfile.ZipFile", return_value=mock_archive):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
            viz.archive = mock_archive

            result = viz._get_floor_plan_image(sample_floors["floor1"])

            # Should return None when floor plan not found
            assert result is None
            viz.close()

    def test_get_floor_plan_image_no_image_id(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test _get_floor_plan_image when floor plan has no imageId."""
        import json

        # Mock archive with floor plan but no imageId
        mock_archive = Mock()
        floor_plans_data = {
            "floorPlans": [
                {
                    "id": "floor1",
                    "name": "Floor 1",
                    # Missing 'imageId' field
                }
            ]
        }
        mock_archive.read.return_value = json.dumps(floor_plans_data).encode()

        with patch("zipfile.ZipFile", return_value=mock_archive):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
            viz.archive = mock_archive

            result = viz._get_floor_plan_image(sample_floors["floor1"])

            # Should return None when no imageId
            assert result is None
            viz.close()

    def test_get_floor_plan_image_file_not_in_archive(
        self, temp_esx_path, temp_output_dir, sample_floors
    ):
        """Test _get_floor_plan_image when image file is not in archive."""
        import json

        # Mock archive with floor plan but image file missing
        mock_archive = Mock()
        floor_plans_data = {
            "floorPlans": [{"id": "floor1", "name": "Floor 1", "imageId": "test-image-123"}]
        }
        mock_archive.read.return_value = json.dumps(floor_plans_data).encode()
        mock_archive.namelist.return_value = []  # Empty - image file not found

        with patch("zipfile.ZipFile", return_value=mock_archive):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
            viz.archive = mock_archive

            result = viz._get_floor_plan_image(sample_floors["floor1"])

            # Should return None when image file not in archive
            assert result is None
            viz.close()

    def test_get_floor_plan_image_general_exception(
        self, temp_esx_path, temp_output_dir, sample_floors
    ):
        """Test _get_floor_plan_image when general exception occurs."""
        # Mock archive that raises exception when reading
        mock_archive = Mock()
        mock_archive.read.side_effect = Exception("Archive read error")

        with patch("zipfile.ZipFile", return_value=mock_archive):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
            viz.archive = mock_archive

            result = viz._get_floor_plan_image(sample_floors["floor1"])

            # Should return None when exception occurs
            assert result is None
            viz.close()

    def test_font_loading_all_fonts_fail(self, temp_esx_path, temp_output_dir):
        """Test font loading when all TrueType fonts fail to load."""
        from PIL import ImageFont

        # Mock ImageFont.truetype to always fail with OSError
        with patch("zipfile.ZipFile"):
            with patch.object(ImageFont, "truetype", side_effect=OSError("Font not found")):
                with patch.object(ImageFont, "load_default", return_value=Mock()):
                    viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

                    # Font should fall back to default
                    assert viz.font is not None
                    viz.close()

    def test_font_loading_exception_in_outer_try(self, temp_esx_path, temp_output_dir):
        """Test font loading when exception occurs in outer try block."""
        from PIL import ImageFont

        # Mock ImageFont.load_default to raise exception
        with patch("zipfile.ZipFile"):
            with patch.object(ImageFont, "truetype", side_effect=OSError("Font not found")):
                with patch.object(
                    ImageFont,
                    "load_default",
                    side_effect=Exception("Font system error"),
                ):
                    viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

                    # Font should be None when all loading fails
                    assert viz.font is None
                    viz.close()

    def test_color_typo_fixing(self, temp_esx_path, temp_output_dir):
        """Test color name typo fixing (e.g., RRReeeddd -> Red)."""
        with patch("zipfile.ZipFile"):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

            # Test typo fixing with 3+ consecutive characters (rrr, eee, ddd)
            result = viz._hex_to_rgb("RRReeeddd")
            assert result == (255, 0, 0)  # Should be recognized as Red

            viz.close()

    def test_draw_ap_marker_unknown_mounting_type(self, temp_esx_path, temp_output_dir):
        """Test _draw_ap_marker with unknown mounting type defaults to circle."""
        from PIL import Image, ImageDraw

        with patch("zipfile.ZipFile"):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

            # Create test image
            test_image = Image.new("RGBA", (500, 500), color=(255, 255, 255, 255))
            draw = ImageDraw.Draw(test_image)

            # Draw with unknown mounting type
            viz._draw_ap_marker(
                draw,
                100,
                100,
                fill_color=(255, 0, 0, 255),
                mounting_type="UNKNOWN",  # Unknown type - should default to circle
            )

            viz.close()

    def test_draw_azimuth_arrow_with_default_length(self, temp_esx_path, temp_output_dir):
        """Test _draw_azimuth_arrow with default arrow_length (None)."""
        from PIL import Image, ImageDraw

        with patch("zipfile.ZipFile"):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

            # Create test image
            test_image = Image.new("RGBA", (500, 500), color=(255, 255, 255, 255))
            draw = ImageDraw.Draw(test_image)

            # Draw arrow with arrow_length=None (should use default)
            viz._draw_azimuth_arrow(
                draw,
                100,
                100,
                azimuth=45.0,
                arrow_length=None,  # None - should use default calculation
            )

            viz.close()

    def test_draw_legend_empty_access_points(self, temp_esx_path, temp_output_dir):
        """Test _draw_legend with empty access points list."""
        from PIL import Image, ImageDraw

        with patch("zipfile.ZipFile"):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

            # Create test image
            test_image = Image.new("RGB", (500, 500), color=(255, 255, 255))

            # Draw legend with empty list - should return early
            result_image = viz._draw_legend(test_image, [])

            viz.close()

    def test_draw_legend_with_non_rgba_image(self, temp_esx_path, temp_output_dir):
        """Test _draw_legend with non-RGBA image (RGB mode)."""
        from PIL import Image, ImageDraw

        with patch("zipfile.ZipFile"):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

            # Create RGB image (not RGBA)
            test_image = Image.new("RGB", (500, 500), color=(255, 255, 255))

            aps = [
                AccessPoint(
                    vendor="Cisco",
                    model="AP-1",
                    floor_id="floor1",
                    floor_name="Floor 1",
                    location_x=100.0,
                    location_y=100.0,
                    color="Red",
                    name="AP-1",
                )
            ]

            # Draw legend on RGB image - should convert to RGBA
            result_image = viz._draw_legend(test_image, aps)

            viz.close()

    def test_wifi_6e_detection_in_arrows(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test Wi-Fi 6E detection in azimuth arrows."""
        from PIL import Image
        from ekahau_bom.models import Radio

        test_image = Image.new("RGB", (500, 500), color="white")

        # AP with Wi-Fi 6E model name
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="Catalyst 9136-WI-FI 6E",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=100.0,
                location_y=100.0,
                color="Red",
                name="AP-6E",
            )
        ]

        radios = [
            Radio(
                id="radio1",
                access_point_id="ap1",
                antenna_mounting="CEILING",
                antenna_direction=45.0,
            )
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir, show_azimuth_arrows=True)
                result = viz.visualize_floor(sample_floors["floor1"], aps, radios)

                assert result is not None
                viz.close()

    def test_wifi_6_detection_in_arrows(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test Wi-Fi 6 detection in azimuth arrows."""
        from PIL import Image
        from ekahau_bom.models import Radio

        test_image = Image.new("RGB", (500, 500), color="white")

        # AP with Wi-Fi 6 model name
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="Catalyst 9120AXI-WI-FI 6",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=100.0,
                location_y=100.0,
                color="Blue",
                name="AP-6",
            )
        ]

        radios = [
            Radio(
                id="radio1",
                access_point_id="ap1",
                antenna_mounting="CEILING",
                antenna_direction=90.0,
            )
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir, show_azimuth_arrows=True)
                result = viz.visualize_floor(sample_floors["floor1"], aps, radios)

                assert result is not None
                viz.close()

    def test_wifi_ac_detection_in_arrows(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test Wi-Fi 5 (802.11ac) detection in azimuth arrows."""
        from PIL import Image
        from ekahau_bom.models import Radio

        test_image = Image.new("RGB", (500, 500), color="white")

        # AP with 802.11ac model name
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="Catalyst 9120AX-AC",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=100.0,
                location_y=100.0,
                color="Green",
                name="AP-AC",
            )
        ]

        radios = [
            Radio(
                id="radio1",
                access_point_id="ap1",
                antenna_mounting="CEILING",
                antenna_direction=135.0,
            )
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir, show_azimuth_arrows=True)
                result = viz.visualize_floor(sample_floors["floor1"], aps, radios)

                assert result is not None
                viz.close()

    def test_visualize_all_floors_floor_id_not_found(
        self, temp_esx_path, temp_output_dir, sample_floors
    ):
        """Test visualize_all_floors when AP references non-existent floor."""
        from PIL import Image

        test_image = Image.new("RGB", (500, 500), color="white")

        # AP with non-existent floor_id
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-1",
                floor_id="nonexistent_floor",  # Floor ID not in floors dict
                floor_name="Unknown Floor",
                mine=True,
                location_x=100.0,
                location_y=100.0,
                color="Red",
                name="AP-1",
            )
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
                result = viz.visualize_all_floors(sample_floors, aps)

                # Should return empty list (floor not found)
                assert result == []
                viz.close()

    def test_get_floor_plan_image_success(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test _get_floor_plan_image successful image loading."""
        import json
        from PIL import Image
        from io import BytesIO

        # Create a valid PNG image
        test_image = Image.new("RGB", (100, 100), color="white")
        image_bytes = BytesIO()
        test_image.save(image_bytes, format="PNG")
        image_data = image_bytes.getvalue()

        # Mock archive with complete valid data
        mock_archive = Mock()
        floor_plans_data = {
            "floorPlans": [
                {
                    "id": "floor1",
                    "name": "Floor 1",
                    "imageId": "test-image-123",
                    "width": 100,
                    "height": 100,
                }
            ]
        }

        def mock_read(filename):
            if filename == "floorPlans.json":
                return json.dumps(floor_plans_data).encode()
            elif filename == "image-test-image-123":
                return image_data
            raise KeyError(f"File not found: {filename}")

        mock_archive.read.side_effect = mock_read
        mock_archive.namelist.return_value = ["floorPlans.json", "image-test-image-123"]

        with patch("zipfile.ZipFile", return_value=mock_archive):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
            viz.archive = mock_archive

            result = viz._get_floor_plan_image(sample_floors["floor1"])

            # Should successfully return tuple of (image, scale_x, scale_y)
            assert result is not None
            image, scale_x, scale_y = result
            assert image.size == (100, 100)
            assert scale_x == 1.0  # 100 / 100
            assert scale_y == 1.0  # 100 / 100
            viz.close()

    def test_wifi_ac_in_model_name(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test Wi-Fi 5 (802.11ac) detection with 'ac' in model name."""
        from PIL import Image
        from ekahau_bom.models import Radio

        test_image = Image.new("RGB", (500, 500), color="white")

        # AP with 'ac' in model name (lowercase)
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AIR-AP1815I-AC-K9",
                floor_id="floor1",
                floor_name="Floor 1",
                mine=True,
                location_x=100.0,
                location_y=100.0,
                color="Yellow",
                name="AP-AC-K9",
            )
        ]

        radios = [
            Radio(
                id="radio1",
                access_point_id="ap1",
                antenna_mounting="CEILING",
                antenna_direction=180.0,
            )
        ]

        with patch("zipfile.ZipFile"):
            with patch.object(
                FloorPlanVisualizer,
                "_get_floor_plan_image",
                return_value=(test_image, 1.0, 1.0),
            ):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir, show_azimuth_arrows=True)
                result = viz.visualize_floor(sample_floors["floor1"], aps, radios)

                assert result is not None
                viz.close()
