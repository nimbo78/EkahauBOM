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
