#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for FloorPlanVisualizer."""

import pytest
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
            "floor2": Floor(id="floor2", name="Floor 2")
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
                name="AP1"
            ),
            AccessPoint(
                vendor="Aruba",
                model="AP-2",
                floor_id="floor1",
                floor_name="Floor 1",
                location_x=300.0,
                location_y=400.0,
                color="Green",
                name="AP2"
            ),
            AccessPoint(
                vendor="Ubiquiti",
                model="AP-3",
                floor_id="floor2",
                floor_name="Floor 2",
                location_x=150.0,
                location_y=250.0,
                color="Blue",
                name="AP3"
            )
        ]

    def test_hex_to_rgb_valid(self, temp_esx_path, temp_output_dir):
        """Test hex to RGB conversion with valid colors."""
        with patch('zipfile.ZipFile'):
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
        with patch('zipfile.ZipFile'):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

            # Invalid hex should return black
            assert viz._hex_to_rgb("invalid") == (0, 0, 0)
            assert viz._hex_to_rgb("#") == (0, 0, 0)

            viz.close()

    def test_initialization(self, temp_esx_path, temp_output_dir):
        """Test FloorPlanVisualizer initialization."""
        with patch('zipfile.ZipFile'):
            viz = FloorPlanVisualizer(
                esx_path=temp_esx_path,
                output_dir=temp_output_dir,
                ap_circle_radius=20,
                show_ap_names=False
            )

            assert viz.esx_path == temp_esx_path
            assert viz.output_dir == temp_output_dir
            assert viz.ap_circle_radius == 20
            assert viz.show_ap_names is False
            assert viz.output_dir.exists()

            viz.close()

    def test_context_manager(self, temp_esx_path, temp_output_dir):
        """Test FloorPlanVisualizer as context manager."""
        with patch('zipfile.ZipFile'):
            with FloorPlanVisualizer(temp_esx_path, temp_output_dir) as viz:
                assert viz is not None

    def test_visualize_floor_no_image(self, temp_esx_path, temp_output_dir, sample_floors, sample_access_points):
        """Test visualization when floor plan image is not found."""
        # Create a mock archive that doesn't have the floor plan image
        with patch('zipfile.ZipFile'):
            with patch.object(FloorPlanVisualizer, '_get_floor_plan_image', return_value=None):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

                result = viz.visualize_floor(
                    floor=sample_floors["floor1"],
                    access_points=sample_access_points
                )

                assert result is None
                viz.close()

    def test_visualize_floor_ap_without_location(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test visualization with AP without location."""
        from PIL import Image

        # Create a test image
        test_image = Image.new('RGB', (100, 100), color='white')

        aps = [
            AccessPoint(
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                location_x=None,  # No location
                location_y=None,
                color="Red",
                name="AP1"
            )
        ]

        with patch('zipfile.ZipFile'):
            with patch.object(FloorPlanVisualizer, '_get_floor_plan_image', return_value=test_image):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

                result = viz.visualize_floor(
                    floor=sample_floors["floor1"],
                    access_points=aps
                )

                # Should still create the image even if no APs are drawn
                assert result is not None
                assert result.exists()
                viz.close()

    def test_visualize_all_floors_empty(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test visualization with no access points."""
        with patch('zipfile.ZipFile'):
            viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

            result = viz.visualize_all_floors(
                floors=sample_floors,
                access_points=[]
            )

            assert result == []
            viz.close()

    def test_visualize_all_floors_with_aps(self, temp_esx_path, temp_output_dir, sample_floors, sample_access_points):
        """Test visualization with multiple floors and APs."""
        from PIL import Image

        # Create a test image
        test_image = Image.new('RGB', (500, 500), color='white')

        with patch('zipfile.ZipFile'):
            with patch.object(FloorPlanVisualizer, '_get_floor_plan_image', return_value=test_image):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

                result = viz.visualize_all_floors(
                    floors=sample_floors,
                    access_points=sample_access_points
                )

                # Should generate visualizations for 2 floors
                assert len(result) == 2
                assert all(f.exists() for f in result)
                viz.close()

    def test_missing_pillow(self, temp_esx_path, temp_output_dir):
        """Test error when Pillow is not available."""
        with patch('ekahau_bom.visualizers.floor_plan.PIL_AVAILABLE', False):
            with pytest.raises(ImportError, match="Pillow library is required"):
                FloorPlanVisualizer(temp_esx_path, temp_output_dir)

    def test_ap_colors(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test that AP colors are correctly applied."""
        from PIL import Image

        # Create a test image
        test_image = Image.new('RGB', (500, 500), color='white')

        aps = [
            AccessPoint(
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                location_x=100.0,
                location_y=100.0,
                color="#FF0000",  # Red
                name="RedAP"
            ),
            AccessPoint(
                vendor="Aruba",
                model="AP-2",
                floor_id="floor1",
                floor_name="Floor 1",
                location_x=200.0,
                location_y=200.0,
                color="Blue",  # Default color
                name="DefaultAP"
            )
        ]

        with patch('zipfile.ZipFile'):
            with patch.object(FloorPlanVisualizer, '_get_floor_plan_image', return_value=test_image):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)

                result = viz.visualize_floor(
                    floor=sample_floors["floor1"],
                    access_points=aps
                )

                assert result is not None
                assert result.exists()
                viz.close()

    def test_custom_circle_radius(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test custom AP circle radius."""
        from PIL import Image

        # Create a test image
        test_image = Image.new('RGB', (500, 500), color='white')

        aps = [
            AccessPoint(
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                location_x=100.0,
                location_y=100.0,
                color="Red",
                name="AP1"
            )
        ]

        with patch('zipfile.ZipFile'):
            with patch.object(FloorPlanVisualizer, '_get_floor_plan_image', return_value=test_image):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir, ap_circle_radius=30)

                assert viz.ap_circle_radius == 30

                result = viz.visualize_floor(
                    floor=sample_floors["floor1"],
                    access_points=aps
                )

                assert result is not None
                viz.close()

    def test_no_ap_names(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test visualization without AP names."""
        from PIL import Image

        # Create a test image
        test_image = Image.new('RGB', (500, 500), color='white')

        aps = [
            AccessPoint(
                vendor="Cisco",
                model="AP-1",
                floor_id="floor1",
                floor_name="Floor 1",
                location_x=100.0,
                location_y=100.0,
                color="Red",
                name="AP1"
            )
        ]

        with patch('zipfile.ZipFile'):
            with patch.object(FloorPlanVisualizer, '_get_floor_plan_image', return_value=test_image):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir, show_ap_names=False)

                assert viz.show_ap_names is False

                result = viz.visualize_floor(
                    floor=sample_floors["floor1"],
                    access_points=aps
                )

                assert result is not None
                viz.close()

    def test_wall_mounted_aps_with_azimuth(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test visualization of wall-mounted APs with rectangle markers."""
        from PIL import Image
        from ekahau_bom.models import Radio

        test_image = Image.new('RGB', (500, 500), color='white')

        # Wall-mounted APs with azimuth
        aps = [
            AccessPoint(
                id="ap1", vendor="Cisco", model="AP-1",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=100.0, location_y=100.0,
                color="Red", name="Wall-AP-1"
            ),
            AccessPoint(
                id="ap2", vendor="Aruba", model="AP-2",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=200.0, location_y=200.0,
                color="Blue", name="Wall-AP-2"
            )
        ]

        # Create Radio objects with mounting type and azimuth
        radios = [
            Radio(
                id="radio1",
                access_point_id="ap1",
                antenna_mounting="WALL",
                antenna_direction=45.0
            ),
            Radio(
                id="radio2",
                access_point_id="ap2",
                antenna_mounting="WALL",
                antenna_direction=90.0
            )
        ]

        with patch('zipfile.ZipFile'):
            with patch.object(FloorPlanVisualizer, '_get_floor_plan_image', return_value=test_image):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
                result = viz.visualize_floor(
                    floor=sample_floors["floor1"],
                    access_points=aps,
                    radios=radios
                )

                assert result is not None
                assert result.exists()
                viz.close()

    def test_floor_mounted_aps_with_square_markers(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test visualization of floor-mounted APs with square markers."""
        from PIL import Image
        from ekahau_bom.models import Radio

        test_image = Image.new('RGB', (500, 500), color='white')

        # Floor-mounted APs
        aps = [
            AccessPoint(
                id="ap1", vendor="Cisco", model="AP-1",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=100.0, location_y=100.0,
                color="Green", name="Floor-AP-1"
            ),
            AccessPoint(
                id="ap2", vendor="Aruba", model="AP-2",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=200.0, location_y=200.0,
                color="Yellow", name="Floor-AP-2"
            )
        ]

        # Create Radio objects with FLOOR mounting type
        radios = [
            Radio(
                id="radio1",
                access_point_id="ap1",
                antenna_mounting="FLOOR"
            ),
            Radio(
                id="radio2",
                access_point_id="ap2",
                antenna_mounting="FLOOR"
            )
        ]

        with patch('zipfile.ZipFile'):
            with patch.object(FloorPlanVisualizer, '_get_floor_plan_image', return_value=test_image):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
                result = viz.visualize_floor(
                    floor=sample_floors["floor1"],
                    access_points=aps,
                    radios=radios
                )

                assert result is not None
                assert result.exists()
                viz.close()

    def test_azimuth_arrows_visualization(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test visualization with azimuth arrows enabled."""
        from PIL import Image
        from ekahau_bom.models import Radio

        test_image = Image.new('RGB', (500, 500), color='white')

        aps = [
            AccessPoint(
                id="ap1", vendor="Cisco", model="AP-1",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=100.0, location_y=100.0,
                color="Red", name="AP-1"
            ),
            AccessPoint(
                id="ap2", vendor="Aruba", model="AP-2",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=200.0, location_y=200.0,
                color="Blue", name="AP-2"
            )
        ]

        # Create Radio objects with mounting type and azimuth
        radios = [
            Radio(
                id="radio1",
                access_point_id="ap1",
                antenna_mounting="CEILING",
                antenna_direction=45.0
            ),
            Radio(
                id="radio2",
                access_point_id="ap2",
                antenna_mounting="WALL",
                antenna_direction=135.0
            )
        ]

        with patch('zipfile.ZipFile'):
            with patch.object(FloorPlanVisualizer, '_get_floor_plan_image', return_value=test_image):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir, show_azimuth_arrows=True)

                assert viz.show_azimuth_arrows is True

                result = viz.visualize_floor(
                    floor=sample_floors["floor1"],
                    access_points=aps,
                    radios=radios
                )

                assert result is not None
                assert result.exists()
                viz.close()

    def test_ap_with_zero_azimuth(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test that azimuth arrows are not drawn when azimuth is 0."""
        from PIL import Image

        test_image = Image.new('RGB', (500, 500), color='white')

        aps = [
            AccessPoint(
                id="ap1", vendor="Cisco", model="AP-1",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=100.0, location_y=100.0,
                color="Red", name="AP-1",
                azimuth=0.0  # Zero azimuth - arrow should not be drawn
            )
        ]

        with patch('zipfile.ZipFile'):
            with patch.object(FloorPlanVisualizer, '_get_floor_plan_image', return_value=test_image):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir, show_azimuth_arrows=True)
                result = viz.visualize_floor(
                    floor=sample_floors["floor1"],
                    access_points=aps
                )

                assert result is not None
                viz.close()

    def test_mixed_mounting_types(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test visualization with mixed mounting types (ceiling, wall, floor)."""
        from PIL import Image
        from ekahau_bom.models import Radio

        test_image = Image.new('RGB', (500, 500), color='white')

        aps = [
            AccessPoint(
                id="ap1", vendor="Cisco", model="AP-1",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=100.0, location_y=100.0,
                color="Red", name="Ceiling-AP"
            ),
            AccessPoint(
                id="ap2", vendor="Aruba", model="AP-2",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=200.0, location_y=200.0,
                color="Blue", name="Wall-AP"
            ),
            AccessPoint(
                id="ap3", vendor="Ubiquiti", model="AP-3",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=300.0, location_y=300.0,
                color="Green", name="Floor-AP"
            )
        ]

        # Create Radio objects with different mounting types
        radios = [
            Radio(
                id="radio1",
                access_point_id="ap1",
                antenna_mounting="CEILING"
            ),
            Radio(
                id="radio2",
                access_point_id="ap2",
                antenna_mounting="WALL",
                antenna_direction=90.0
            ),
            Radio(
                id="radio3",
                access_point_id="ap3",
                antenna_mounting="FLOOR"
            )
        ]

        with patch('zipfile.ZipFile'):
            with patch.object(FloorPlanVisualizer, '_get_floor_plan_image', return_value=test_image):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
                result = viz.visualize_floor(
                    floor=sample_floors["floor1"],
                    access_points=aps,
                    radios=radios
                )

                assert result is not None
                assert result.exists()
                viz.close()

    def test_ap_opacity_setting(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test AP marker opacity setting."""
        from PIL import Image

        test_image = Image.new('RGB', (500, 500), color='white')

        aps = [
            AccessPoint(
                id="ap1", vendor="Cisco", model="AP-1",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=100.0, location_y=100.0,
                color="Red", name="AP-1"
            )
        ]

        with patch('zipfile.ZipFile'):
            with patch.object(FloorPlanVisualizer, '_get_floor_plan_image', return_value=test_image):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir, ap_opacity=0.5)

                assert viz.ap_opacity == 0.5

                result = viz.visualize_floor(
                    floor=sample_floors["floor1"],
                    access_points=aps
                )

                assert result is not None
                viz.close()

    def test_color_name_handling(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test handling of color names (not hex codes)."""
        from PIL import Image

        test_image = Image.new('RGB', (500, 500), color='white')

        aps = [
            AccessPoint(
                id="ap1", vendor="Cisco", model="AP-1",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=100.0, location_y=100.0,
                color="Red", name="AP-Red"  # Color name, not hex
            ),
            AccessPoint(
                id="ap2", vendor="Aruba", model="AP-2",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=200.0, location_y=200.0,
                color="lightblue", name="AP-LightBlue"  # Ekahau color name
            ),
            AccessPoint(
                id="ap3", vendor="Ubiquiti", model="AP-3",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=300.0, location_y=300.0,
                color=None, name="AP-Default"  # No color (use default)
            )
        ]

        with patch('zipfile.ZipFile'):
            with patch.object(FloorPlanVisualizer, '_get_floor_plan_image', return_value=test_image):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
                result = viz.visualize_floor(
                    floor=sample_floors["floor1"],
                    access_points=aps
                )

                assert result is not None
                viz.close()

    def test_image_loading_errors(self, temp_esx_path, temp_output_dir, sample_floors):
        """Test handling of image loading errors."""
        aps = [
            AccessPoint(
                id="ap1", vendor="Cisco", model="AP-1",
                floor_id="floor1", floor_name="Floor 1", mine=True,
                location_x=100.0, location_y=100.0,
                color="Red", name="AP-1"
            )
        ]

        with patch('zipfile.ZipFile'):
            # Simulate image loading failure
            with patch.object(FloorPlanVisualizer, '_get_floor_plan_image', return_value=None):
                viz = FloorPlanVisualizer(temp_esx_path, temp_output_dir)
                result = viz.visualize_floor(
                    floor=sample_floors["floor1"],
                    access_points=aps
                )

                # Should return None when image cannot be loaded
                assert result is None
                viz.close()
