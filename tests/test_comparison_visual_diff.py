"""Tests for the comparison visual diff module."""

import math
import pytest
import zipfile
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from ekahau_bom.comparison.models import (
    APChange,
    ChangeStatus,
    ComparisonResult,
    InventoryChange,
)

# Check if PIL is available
try:
    from PIL import Image, ImageDraw

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


pytestmark = pytest.mark.skipif(not PIL_AVAILABLE, reason="Pillow not available")


class TestColors:
    """Tests for color definitions."""

    def test_colors_import(self):
        """Test color constants are defined."""
        from ekahau_bom.comparison.visual_diff import COLORS

        assert ChangeStatus.ADDED in COLORS
        assert ChangeStatus.REMOVED in COLORS
        assert ChangeStatus.MODIFIED in COLORS
        assert ChangeStatus.MOVED in COLORS
        assert ChangeStatus.RENAMED in COLORS
        assert ChangeStatus.UNCHANGED in COLORS

    def test_moved_color_is_dict(self):
        """Test moved status has sub-colors."""
        from ekahau_bom.comparison.visual_diff import COLORS

        moved_colors = COLORS[ChangeStatus.MOVED]
        assert isinstance(moved_colors, dict)
        assert "old" in moved_colors
        assert "new" in moved_colors
        assert "arrow" in moved_colors


class TestVisualDiffGeneratorInit:
    """Tests for VisualDiffGenerator initialization."""

    @pytest.fixture
    def mock_esx_files(self, tmp_path):
        """Create minimal mock .esx files."""
        old_esx = tmp_path / "old.esx"
        new_esx = tmp_path / "new.esx"

        # Create minimal zip files
        for esx_path in [old_esx, new_esx]:
            with zipfile.ZipFile(esx_path, "w") as zf:
                zf.writestr("floorPlans.json", json.dumps({"floorPlans": []}))

        return old_esx, new_esx

    def test_init_with_pil(self, mock_esx_files):
        """Test initialization with PIL available."""
        from ekahau_bom.comparison.visual_diff import VisualDiffGenerator

        old_esx, new_esx = mock_esx_files

        gen = VisualDiffGenerator(old_esx, new_esx)

        assert gen.old_esx_path == old_esx
        assert gen.new_esx_path == new_esx
        assert gen.marker_radius == 20  # default
        assert gen.show_unchanged is False
        assert gen.show_labels is True

        gen.close()

    def test_init_custom_options(self, mock_esx_files):
        """Test initialization with custom options."""
        from ekahau_bom.comparison.visual_diff import VisualDiffGenerator

        old_esx, new_esx = mock_esx_files

        gen = VisualDiffGenerator(
            old_esx,
            new_esx,
            marker_radius=30,
            show_unchanged=True,
            show_labels=False,
        )

        assert gen.marker_radius == 30
        assert gen.show_unchanged is True
        assert gen.show_labels is False

        gen.close()

    def test_context_manager(self, mock_esx_files):
        """Test context manager usage."""
        from ekahau_bom.comparison.visual_diff import VisualDiffGenerator

        old_esx, new_esx = mock_esx_files

        with VisualDiffGenerator(old_esx, new_esx) as gen:
            assert gen.old_archive is not None
            assert gen.new_archive is not None


class TestCalculateAdaptiveSizes:
    """Tests for adaptive size calculation."""

    @pytest.fixture
    def generator(self, tmp_path):
        """Create generator with mock files."""
        from ekahau_bom.comparison.visual_diff import VisualDiffGenerator

        old_esx = tmp_path / "old.esx"
        new_esx = tmp_path / "new.esx"

        for esx_path in [old_esx, new_esx]:
            with zipfile.ZipFile(esx_path, "w") as zf:
                zf.writestr("floorPlans.json", json.dumps({"floorPlans": []}))

        gen = VisualDiffGenerator(old_esx, new_esx)
        yield gen
        gen.close()

    def test_small_image_sizes(self, generator):
        """Test sizes for small images."""
        sizes = generator._calculate_adaptive_sizes(800, 600)

        assert "radius" in sizes
        assert "border_width" in sizes
        assert "font_size" in sizes
        assert "arrow_width" in sizes
        assert "arrow_head_size" in sizes

        # For small images, should use default marker radius
        assert sizes["radius"] == generator.marker_radius

    def test_large_image_sizes(self, generator):
        """Test sizes scale up for large images."""
        sizes = generator._calculate_adaptive_sizes(4000, 3000)

        # For large images, radius should be larger than default
        assert sizes["radius"] > generator.marker_radius
        assert sizes["border_width"] >= 2
        assert sizes["font_size"] >= 10


class TestDrawingFunctions:
    """Tests for drawing helper functions."""

    @pytest.fixture
    def generator_and_image(self, tmp_path):
        """Create generator and blank image for drawing."""
        from ekahau_bom.comparison.visual_diff import VisualDiffGenerator

        old_esx = tmp_path / "old.esx"
        new_esx = tmp_path / "new.esx"

        for esx_path in [old_esx, new_esx]:
            with zipfile.ZipFile(esx_path, "w") as zf:
                zf.writestr("floorPlans.json", json.dumps({"floorPlans": []}))

        gen = VisualDiffGenerator(old_esx, new_esx)
        image = Image.new("RGBA", (500, 500), (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)

        yield gen, image, draw
        gen.close()

    def test_draw_circle(self, generator_and_image):
        """Test circle drawing."""
        gen, image, draw = generator_and_image

        # Should not raise
        gen._draw_circle(draw, 100, 100, (255, 0, 0, 255), 20, 3)

        # Check pixel at center-ish is colored
        pixel = image.getpixel((100, 100))
        # Should be red (inner circle)
        assert pixel[0] > 200  # Red channel high

    def test_draw_arrow(self, generator_and_image):
        """Test arrow drawing."""
        gen, image, draw = generator_and_image

        # Should not raise
        gen._draw_arrow(draw, (50, 50), (200, 200), (0, 0, 255, 255), 3, 10)

        # Check pixel along arrow line
        pixel = image.getpixel((125, 125))  # Middle of arrow
        assert pixel[2] > 200  # Blue channel high

    def test_draw_label(self, generator_and_image):
        """Test label drawing."""
        gen, image, draw = generator_and_image

        font = gen._load_font(12)
        # Should not raise
        gen._draw_label(draw, 100, 100, "AP-101", font, 25, 0)


class TestDrawChange:
    """Tests for _draw_change method with different statuses."""

    @pytest.fixture
    def setup_drawing(self, tmp_path):
        """Setup generator and drawing context."""
        from ekahau_bom.comparison.visual_diff import VisualDiffGenerator

        old_esx = tmp_path / "old.esx"
        new_esx = tmp_path / "new.esx"

        for esx_path in [old_esx, new_esx]:
            with zipfile.ZipFile(esx_path, "w") as zf:
                zf.writestr("floorPlans.json", json.dumps({"floorPlans": []}))

        gen = VisualDiffGenerator(old_esx, new_esx)
        image = Image.new("RGBA", (500, 500), (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)
        font = gen._load_font(12)
        sizes = gen._calculate_adaptive_sizes(500, 500)

        yield gen, draw, font, sizes
        gen.close()

    def test_draw_added_change(self, setup_drawing):
        """Test drawing added AP."""
        gen, draw, font, sizes = setup_drawing

        mock_new_ap = MagicMock()
        mock_new_ap.location_x = 100.0
        mock_new_ap.location_y = 100.0

        change = APChange(
            status=ChangeStatus.ADDED,
            ap_name="AP-NEW",
            floor_name="Floor 1",
            new_ap=mock_new_ap,
        )

        # Should not raise
        gen._draw_change(draw, change, 1.0, 1.0, sizes, font)

    def test_draw_removed_change(self, setup_drawing):
        """Test drawing removed AP."""
        gen, draw, font, sizes = setup_drawing

        mock_old_ap = MagicMock()
        mock_old_ap.location_x = 150.0
        mock_old_ap.location_y = 150.0

        change = APChange(
            status=ChangeStatus.REMOVED,
            ap_name="AP-OLD",
            floor_name="Floor 1",
            old_ap=mock_old_ap,
        )

        gen._draw_change(draw, change, 1.0, 1.0, sizes, font)

    def test_draw_modified_change(self, setup_drawing):
        """Test drawing modified AP."""
        gen, draw, font, sizes = setup_drawing

        mock_ap = MagicMock()
        mock_ap.location_x = 200.0
        mock_ap.location_y = 200.0

        change = APChange(
            status=ChangeStatus.MODIFIED,
            ap_name="AP-MOD",
            floor_name="Floor 1",
            old_ap=mock_ap,
            new_ap=mock_ap,
        )

        gen._draw_change(draw, change, 1.0, 1.0, sizes, font)

    def test_draw_moved_change(self, setup_drawing):
        """Test drawing moved AP with arrow."""
        gen, draw, font, sizes = setup_drawing

        change = APChange(
            status=ChangeStatus.MOVED,
            ap_name="AP-MOVE",
            floor_name="Floor 1",
            old_coords=(50.0, 50.0),
            new_coords=(250.0, 250.0),
            distance_moved=283.0,
        )

        gen._draw_change(draw, change, 1.0, 1.0, sizes, font)

    def test_draw_renamed_change(self, setup_drawing):
        """Test drawing renamed AP."""
        gen, draw, font, sizes = setup_drawing

        mock_ap = MagicMock()
        mock_ap.location_x = 300.0
        mock_ap.location_y = 300.0

        change = APChange(
            status=ChangeStatus.RENAMED,
            ap_name="AP-NEW-NAME",
            floor_name="Floor 1",
            old_ap=mock_ap,
            new_ap=mock_ap,
            old_name="AP-OLD-NAME",
            new_name="AP-NEW-NAME",
        )

        gen._draw_change(draw, change, 1.0, 1.0, sizes, font)


class TestDrawLegend:
    """Tests for legend drawing."""

    @pytest.fixture
    def generator(self, tmp_path):
        """Create generator."""
        from ekahau_bom.comparison.visual_diff import VisualDiffGenerator

        old_esx = tmp_path / "old.esx"
        new_esx = tmp_path / "new.esx"

        for esx_path in [old_esx, new_esx]:
            with zipfile.ZipFile(esx_path, "w") as zf:
                zf.writestr("floorPlans.json", json.dumps({"floorPlans": []}))

        gen = VisualDiffGenerator(old_esx, new_esx)
        yield gen
        gen.close()

    def test_draw_legend_with_changes(self, generator):
        """Test legend drawing with various change types."""
        image = Image.new("RGBA", (500, 500), (255, 255, 255, 255))
        sizes = generator._calculate_adaptive_sizes(500, 500)

        changes = [
            APChange(status=ChangeStatus.ADDED, ap_name="AP-1", floor_name="F1"),
            APChange(status=ChangeStatus.ADDED, ap_name="AP-2", floor_name="F1"),
            APChange(status=ChangeStatus.REMOVED, ap_name="AP-3", floor_name="F1"),
        ]

        result = generator._draw_legend(image, changes, sizes)

        # Should return an image
        assert isinstance(result, Image.Image)

    def test_draw_legend_empty_changes(self, generator):
        """Test legend with no changes."""
        image = Image.new("RGBA", (500, 500), (255, 255, 255, 255))
        sizes = generator._calculate_adaptive_sizes(500, 500)

        result = generator._draw_legend(image, [], sizes)

        # Should return original image
        assert result is image


class TestGetFloorPlanImage:
    """Tests for floor plan image extraction."""

    @pytest.fixture
    def generator_with_floor_plan(self, tmp_path):
        """Create generator with a real floor plan."""
        from ekahau_bom.comparison.visual_diff import VisualDiffGenerator

        # Create a simple test image
        test_image = Image.new("RGB", (400, 300), (200, 200, 200))
        img_buffer = BytesIO()
        test_image.save(img_buffer, format="PNG")
        img_data = img_buffer.getvalue()

        floor_plans_data = {
            "floorPlans": [
                {
                    "id": "floor-1",
                    "name": "Test Floor",
                    "width": 40.0,
                    "height": 30.0,
                    "bitmapImageId": "img-1",
                }
            ]
        }

        old_esx = tmp_path / "old.esx"
        new_esx = tmp_path / "new.esx"

        for esx_path in [old_esx, new_esx]:
            with zipfile.ZipFile(esx_path, "w") as zf:
                zf.writestr("floorPlans.json", json.dumps(floor_plans_data))
                zf.writestr("image-img-1", img_data)

        gen = VisualDiffGenerator(old_esx, new_esx)
        yield gen
        gen.close()

    def test_get_floor_plan_success(self, generator_with_floor_plan):
        """Test successful floor plan extraction."""
        result = generator_with_floor_plan._get_floor_plan_image("Test Floor")

        assert result is not None
        image, scale_x, scale_y, floor_id = result
        assert isinstance(image, Image.Image)
        assert floor_id == "floor-1"
        # scale_x = 400 / 40.0 = 10
        assert scale_x == 10.0
        # scale_y = 300 / 30.0 = 10
        assert scale_y == 10.0

    def test_get_floor_plan_not_found(self, generator_with_floor_plan):
        """Test floor plan not found."""
        result = generator_with_floor_plan._get_floor_plan_image("Nonexistent Floor")
        assert result is None


class TestGenerateFloorDiff:
    """Tests for floor diff generation."""

    @pytest.fixture
    def generator_with_floor(self, tmp_path):
        """Create generator with floor plan."""
        from ekahau_bom.comparison.visual_diff import VisualDiffGenerator

        # Create test image
        test_image = Image.new("RGB", (800, 600), (240, 240, 240))
        img_buffer = BytesIO()
        test_image.save(img_buffer, format="PNG")
        img_data = img_buffer.getvalue()

        floor_plans_data = {
            "floorPlans": [
                {
                    "id": "floor-1",
                    "name": "Office Floor",
                    "width": 80.0,
                    "height": 60.0,
                    "bitmapImageId": "img-1",
                }
            ]
        }

        old_esx = tmp_path / "old.esx"
        new_esx = tmp_path / "new.esx"

        for esx_path in [old_esx, new_esx]:
            with zipfile.ZipFile(esx_path, "w") as zf:
                zf.writestr("floorPlans.json", json.dumps(floor_plans_data))
                zf.writestr("image-img-1", img_data)

        gen = VisualDiffGenerator(old_esx, new_esx)
        gen.output_dir = tmp_path / "output"
        gen.output_dir.mkdir()

        yield gen
        gen.close()

    def test_generate_floor_diff(self, generator_with_floor):
        """Test generating diff for a floor."""
        mock_ap = MagicMock()
        mock_ap.location_x = 40.0
        mock_ap.location_y = 30.0

        changes = [
            APChange(
                status=ChangeStatus.ADDED,
                ap_name="AP-101",
                floor_name="Office Floor",
                new_ap=mock_ap,
            ),
        ]

        result = generator_with_floor.generate_floor_diff("Office Floor", changes)

        assert result is not None
        assert result.exists()
        assert result.name == "diff_Office_Floor.png"

    def test_generate_floor_diff_not_found(self, generator_with_floor):
        """Test generating diff for nonexistent floor."""
        result = generator_with_floor.generate_floor_diff("Unknown Floor", [])
        assert result is None


class TestGenerateAllDiffs:
    """Tests for generating all floor diffs."""

    @pytest.fixture
    def generator_multi_floor(self, tmp_path):
        """Create generator with multiple floors."""
        from ekahau_bom.comparison.visual_diff import VisualDiffGenerator

        # Create test images
        img1 = Image.new("RGB", (400, 300), (240, 240, 240))
        img2 = Image.new("RGB", (400, 300), (230, 230, 230))

        img1_buffer = BytesIO()
        img1.save(img1_buffer, format="PNG")

        img2_buffer = BytesIO()
        img2.save(img2_buffer, format="PNG")

        floor_plans_data = {
            "floorPlans": [
                {
                    "id": "floor-1",
                    "name": "Floor 1",
                    "width": 40.0,
                    "height": 30.0,
                    "bitmapImageId": "img-1",
                },
                {
                    "id": "floor-2",
                    "name": "Floor 2",
                    "width": 40.0,
                    "height": 30.0,
                    "bitmapImageId": "img-2",
                },
            ]
        }

        old_esx = tmp_path / "old.esx"
        new_esx = tmp_path / "new.esx"

        for esx_path in [old_esx, new_esx]:
            with zipfile.ZipFile(esx_path, "w") as zf:
                zf.writestr("floorPlans.json", json.dumps(floor_plans_data))
                zf.writestr("image-img-1", img1_buffer.getvalue())
                zf.writestr("image-img-2", img2_buffer.getvalue())

        gen = VisualDiffGenerator(old_esx, new_esx)
        yield gen, tmp_path
        gen.close()

    def test_generate_all_diffs(self, generator_multi_floor):
        """Test generating diffs for all floors."""
        gen, tmp_path = generator_multi_floor
        output_dir = tmp_path / "output"

        mock_ap1 = MagicMock()
        mock_ap1.location_x = 20.0
        mock_ap1.location_y = 15.0

        mock_ap2 = MagicMock()
        mock_ap2.location_x = 25.0
        mock_ap2.location_y = 20.0

        comparison = ComparisonResult(
            project_a_name="Old",
            project_b_name="New",
            project_a_filename="old.esx",
            project_b_filename="new.esx",
            comparison_timestamp=datetime.now(),
            inventory_change=InventoryChange(
                old_total_aps=2,
                new_total_aps=2,
                aps_added=1,
                aps_removed=0,
                aps_modified=1,
                aps_moved=0,
                aps_renamed=0,
                aps_unchanged=0,
            ),
            ap_changes=[
                APChange(
                    status=ChangeStatus.ADDED,
                    ap_name="AP-1",
                    floor_name="Floor 1",
                    new_ap=mock_ap1,
                ),
                APChange(
                    status=ChangeStatus.MODIFIED,
                    ap_name="AP-2",
                    floor_name="Floor 2",
                    new_ap=mock_ap2,
                ),
            ],
            changes_by_floor={
                "Floor 1": [
                    APChange(
                        status=ChangeStatus.ADDED,
                        ap_name="AP-1",
                        floor_name="Floor 1",
                        new_ap=mock_ap1,
                    )
                ],
                "Floor 2": [
                    APChange(
                        status=ChangeStatus.MODIFIED,
                        ap_name="AP-2",
                        floor_name="Floor 2",
                        new_ap=mock_ap2,
                    )
                ],
            },
        )

        results = gen.generate_all_diffs(comparison, output_dir)

        assert len(results) == 2
        assert "Floor 1" in results
        assert "Floor 2" in results
        assert results["Floor 1"].exists()
        assert results["Floor 2"].exists()


class TestLoadFont:
    """Tests for font loading."""

    @pytest.fixture
    def generator(self, tmp_path):
        """Create generator."""
        from ekahau_bom.comparison.visual_diff import VisualDiffGenerator

        old_esx = tmp_path / "old.esx"
        new_esx = tmp_path / "new.esx"

        for esx_path in [old_esx, new_esx]:
            with zipfile.ZipFile(esx_path, "w") as zf:
                zf.writestr("floorPlans.json", json.dumps({"floorPlans": []}))

        gen = VisualDiffGenerator(old_esx, new_esx)
        yield gen
        gen.close()

    def test_load_font(self, generator):
        """Test font loading returns something."""
        font = generator._load_font(12)
        # Should return either a TrueType font or default
        assert font is not None

    def test_load_font_different_sizes(self, generator):
        """Test loading fonts at different sizes."""
        font_small = generator._load_font(8)
        font_large = generator._load_font(24)

        # Both should work
        assert font_small is not None
        assert font_large is not None
