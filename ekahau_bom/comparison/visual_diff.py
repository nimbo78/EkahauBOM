"""Visual diff generator for floor plan comparison.

Generates PNG images showing changes between two project versions
with colored markers and movement arrows.
"""

from __future__ import annotations

import logging
import math
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageDraw, ImageFont

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from ekahau_bom.comparison.models import APChange, ChangeStatus, ComparisonResult

logger = logging.getLogger(__name__)


# Color definitions for change types (RGBA)
COLORS = {
    ChangeStatus.ADDED: (0, 200, 0, 255),  # Green
    ChangeStatus.REMOVED: (220, 0, 0, 255),  # Red
    ChangeStatus.MODIFIED: (255, 200, 0, 255),  # Yellow
    ChangeStatus.MOVED: {
        "old": (70, 130, 180, 180),  # Steel blue (faded)
        "new": (148, 0, 211, 255),  # Purple
        "arrow": (148, 0, 211, 255),  # Purple arrow
    },
    ChangeStatus.RENAMED: (255, 140, 0, 255),  # Orange
    ChangeStatus.UNCHANGED: (128, 128, 128, 100),  # Gray (very faded)
}


class VisualDiffGenerator:
    """Generate visual diff images for floor plan comparisons."""

    def __init__(
        self,
        old_esx_path: Path,
        new_esx_path: Path,
        marker_radius: int = 20,
        show_unchanged: bool = False,
        show_labels: bool = True,
    ):
        """Initialize visual diff generator.

        Args:
            old_esx_path: Path to the old/previous .esx file
            new_esx_path: Path to the new/current .esx file (for floor plan images)
            marker_radius: Base radius for AP markers
            show_unchanged: Whether to show unchanged APs (grayed out)
            show_labels: Whether to show AP name labels
        """
        if not PIL_AVAILABLE:
            raise ImportError(
                "Pillow library is required for visual diff. " "Install it with: pip install Pillow"
            )

        self.old_esx_path = old_esx_path
        self.new_esx_path = new_esx_path
        self.marker_radius = marker_radius
        self.show_unchanged = show_unchanged
        self.show_labels = show_labels

        # Output dir will be set in generate_all_diffs
        self.output_dir = None

        # Open .esx archives
        self.old_archive = zipfile.ZipFile(old_esx_path, "r")
        self.new_archive = zipfile.ZipFile(new_esx_path, "r")

        # Load font
        self.font = self._load_font()

    def _load_font(self, size: int = 12) -> Optional[ImageFont.FreeTypeFont]:
        """Load a TrueType font for text rendering."""
        try:
            font_names = [
                "arial.ttf",
                "Arial.ttf",
                "DejaVuSans.ttf",
                "LiberationSans-Regular.ttf",
            ]
            for font_name in font_names:
                try:
                    return ImageFont.truetype(font_name, size)
                except (OSError, IOError):
                    continue
            return ImageFont.load_default()
        except Exception as e:
            logger.warning(f"Error loading font: {e}")
            return None

    def _get_floor_plan_image(
        self, floor_name: str
    ) -> Optional[tuple[Image.Image, float, float, str]]:
        """Extract floor plan image from .esx archive.

        Args:
            floor_name: Name of the floor to find

        Returns:
            Tuple of (image, scale_x, scale_y, floor_id) or None
        """
        import json

        try:
            floor_plans_data = json.loads(self.new_archive.read("floorPlans.json"))

            # Find floor plan by name
            floor_plan = None
            for fp in floor_plans_data.get("floorPlans", []):
                if fp.get("name") == floor_name:
                    floor_plan = fp
                    break

            if not floor_plan:
                logger.warning(f"Floor plan not found: {floor_name}")
                return None

            floor_id = floor_plan.get("id")
            plan_width = floor_plan.get("width", 1)
            plan_height = floor_plan.get("height", 1)

            # Get image
            image_id = floor_plan.get("bitmapImageId") or floor_plan.get("imageId")
            if not image_id:
                logger.warning(f"No image for floor: {floor_name}")
                return None

            image_filename = f"image-{image_id}"
            if image_filename not in self.new_archive.namelist():
                logger.warning(f"Image file not found: {image_filename}")
                return None

            image_data = self.new_archive.read(image_filename)
            image = Image.open(BytesIO(image_data))

            # Calculate scale factors
            actual_width, actual_height = image.size
            scale_x = actual_width / plan_width
            scale_y = actual_height / plan_height

            return (image, scale_x, scale_y, floor_id)

        except Exception as e:
            logger.error(f"Error loading floor plan: {e}")
            return None

    def _calculate_adaptive_sizes(self, image_width: int, image_height: int) -> dict:
        """Calculate adaptive marker sizes based on image dimensions."""
        avg_dimension = (image_width + image_height) / 2
        scale_factor = 0.008
        min_radius = 12

        if avg_dimension > 2000:
            base_radius = max(min_radius, int(avg_dimension * scale_factor))
        else:
            base_radius = self.marker_radius

        return {
            "radius": base_radius,
            "border_width": max(2, int(base_radius * 0.15)),
            "font_size": max(10, int(base_radius * 0.7)),
            "arrow_width": max(2, int(base_radius * 0.1)),
            "arrow_head_size": max(6, int(base_radius * 0.4)),
        }

    def _draw_circle(
        self,
        draw: ImageDraw.ImageDraw,
        x: float,
        y: float,
        color: tuple,
        radius: int,
        border_width: int = 2,
    ) -> None:
        """Draw a filled circle with border."""
        # Black border
        draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=(0, 0, 0, 255),
            outline=(0, 0, 0, 255),
        )
        # Inner colored circle
        inner_radius = radius - border_width
        draw.ellipse(
            [x - inner_radius, y - inner_radius, x + inner_radius, y + inner_radius],
            fill=color,
            outline=color,
        )

    def _draw_arrow(
        self,
        draw: ImageDraw.ImageDraw,
        start: tuple[float, float],
        end: tuple[float, float],
        color: tuple,
        width: int = 3,
        head_size: int = 10,
    ) -> None:
        """Draw an arrow from start to end point."""
        x1, y1 = start
        x2, y2 = end

        # Draw line
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

        # Calculate arrow head
        angle = math.atan2(y2 - y1, x2 - x1)
        head_angle1 = angle + math.radians(150)
        head_angle2 = angle + math.radians(-150)

        head_x1 = x2 + head_size * math.cos(head_angle1)
        head_y1 = y2 + head_size * math.sin(head_angle1)
        head_x2 = x2 + head_size * math.cos(head_angle2)
        head_y2 = y2 + head_size * math.sin(head_angle2)

        # Draw arrow head
        arrow_head = [(x2, y2), (head_x1, head_y1), (head_x2, head_y2)]
        draw.polygon(arrow_head, fill=color, outline=color)

    def _draw_label(
        self,
        draw: ImageDraw.ImageDraw,
        x: float,
        y: float,
        text: str,
        font: ImageFont.FreeTypeFont,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        """Draw text label with white outline for visibility."""
        text_x = x + offset_x
        text_y = y + offset_y

        # White outline
        outline_color = (255, 255, 255)
        text_color = (0, 0, 0)

        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                draw.text((text_x + dx, text_y + dy), text, font=font, fill=outline_color)

        # Main text
        draw.text((text_x, text_y), text, font=font, fill=text_color)

    def _draw_legend(
        self,
        image: Image.Image,
        changes_on_floor: list[APChange],
        sizes: dict,
    ) -> Image.Image:
        """Draw legend showing change types present on this floor."""
        # Count changes by status
        status_counts = {}
        for change in changes_on_floor:
            status = change.status
            status_counts[status] = status_counts.get(status, 0) + 1

        if not status_counts:
            return image

        # Legend items
        legend_items = [
            (ChangeStatus.ADDED, "Added", COLORS[ChangeStatus.ADDED]),
            (ChangeStatus.REMOVED, "Removed", COLORS[ChangeStatus.REMOVED]),
            (ChangeStatus.MODIFIED, "Modified", COLORS[ChangeStatus.MODIFIED]),
            (ChangeStatus.MOVED, "Moved", COLORS[ChangeStatus.MOVED]["new"]),
            (ChangeStatus.RENAMED, "Renamed", COLORS[ChangeStatus.RENAMED]),
        ]

        # Filter to only show present statuses
        legend_items = [(s, n, c) for s, n, c in legend_items if s in status_counts]

        if not legend_items:
            return image

        # Legend dimensions
        padding = 15
        line_height = 28
        circle_radius = 10
        legend_width = 180
        legend_height = len(legend_items) * line_height + padding * 2 + 25

        # Position in top-right
        legend_x = image.width - legend_width - 20
        legend_y = 20

        # Create legend overlay
        overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        # Background
        draw.rectangle(
            [legend_x, legend_y, legend_x + legend_width, legend_y + legend_height],
            fill=(255, 255, 255, 230),
            outline=(0, 0, 0, 255),
            width=2,
        )

        # Title
        font = self._load_font(sizes["font_size"])
        title_y = legend_y + padding
        if font:
            draw.text((legend_x + padding, title_y), "Changes", font=font, fill=(0, 0, 0, 255))

        # Draw entries
        entry_y = title_y + line_height
        for status, name, color in legend_items:
            count = status_counts[status]

            # Circle
            circle_x = legend_x + padding + circle_radius
            circle_y = entry_y + line_height // 2

            draw.ellipse(
                [
                    circle_x - circle_radius,
                    circle_y - circle_radius,
                    circle_x + circle_radius,
                    circle_y + circle_radius,
                ],
                fill=(0, 0, 0, 255),
            )
            draw.ellipse(
                [
                    circle_x - circle_radius + 2,
                    circle_y - circle_radius + 2,
                    circle_x + circle_radius - 2,
                    circle_y + circle_radius - 2,
                ],
                fill=color,
            )

            # Text
            if font:
                text_x = legend_x + padding + circle_radius * 2 + 10
                text_y = entry_y + (line_height - sizes["font_size"]) // 2
                draw.text((text_x, text_y), f"{name}: {count}", font=font, fill=(0, 0, 0, 255))

            entry_y += line_height

        # Composite
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        return Image.alpha_composite(image, overlay)

    def generate_floor_diff(
        self,
        floor_name: str,
        changes: list[APChange],
        sizes: dict = None,
    ) -> Optional[Path]:
        """Generate diff visualization for a single floor.

        Args:
            floor_name: Name of the floor
            changes: List of AP changes on this floor
            sizes: Adaptive sizes dict (optional)

        Returns:
            Path to generated image or None
        """
        # Load floor plan
        result = self._get_floor_plan_image(floor_name)
        if result is None:
            logger.warning(f"Could not load floor plan for: {floor_name}")
            return None

        image, scale_x, scale_y, floor_id = result

        # Convert to RGBA
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # Calculate adaptive sizes
        if sizes is None:
            sizes = self._calculate_adaptive_sizes(image.width, image.height)

        # Create overlay
        overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        # Load font
        font = self._load_font(sizes["font_size"])

        # Draw changes
        for change in changes:
            self._draw_change(draw, change, scale_x, scale_y, sizes, font)

        # Composite
        image = Image.alpha_composite(image, overlay)

        # Draw legend
        image = self._draw_legend(image, changes, sizes)

        # Save
        safe_name = floor_name.replace("/", "_").replace("\\", "_").replace(" ", "_")
        output_filename = f"diff_{safe_name}.png"
        output_path = self.output_dir / output_filename

        image.save(output_path, "PNG")
        logger.info(f"Saved diff visualization: {output_path}")

        return output_path

    def _draw_change(
        self,
        draw: ImageDraw.ImageDraw,
        change: APChange,
        scale_x: float,
        scale_y: float,
        sizes: dict,
        font: ImageFont.FreeTypeFont,
    ) -> None:
        """Draw a single AP change on the overlay."""
        status = change.status
        radius = sizes["radius"]
        border_width = sizes["border_width"]

        if status == ChangeStatus.ADDED:
            # Green circle at new position
            if change.new_ap and change.new_ap.location_x is not None:
                x = change.new_ap.location_x * scale_x
                y = change.new_ap.location_y * scale_y
                self._draw_circle(draw, x, y, COLORS[ChangeStatus.ADDED], radius, border_width)
                if self.show_labels and font:
                    self._draw_label(
                        draw, x, y, change.ap_name, font, radius + 5, -sizes["font_size"] // 2
                    )

        elif status == ChangeStatus.REMOVED:
            # Red circle at old position
            if change.old_ap and change.old_ap.location_x is not None:
                x = change.old_ap.location_x * scale_x
                y = change.old_ap.location_y * scale_y
                self._draw_circle(draw, x, y, COLORS[ChangeStatus.REMOVED], radius, border_width)
                if self.show_labels and font:
                    self._draw_label(
                        draw, x, y, change.ap_name, font, radius + 5, -sizes["font_size"] // 2
                    )

        elif status == ChangeStatus.MODIFIED:
            # Yellow circle at current position
            if change.new_ap and change.new_ap.location_x is not None:
                x = change.new_ap.location_x * scale_x
                y = change.new_ap.location_y * scale_y
                self._draw_circle(draw, x, y, COLORS[ChangeStatus.MODIFIED], radius, border_width)
                if self.show_labels and font:
                    self._draw_label(
                        draw, x, y, change.ap_name, font, radius + 5, -sizes["font_size"] // 2
                    )

        elif status == ChangeStatus.MOVED:
            # Blue circle at old, purple at new, arrow between
            colors = COLORS[ChangeStatus.MOVED]
            if change.old_coords and change.new_coords:
                old_x = change.old_coords[0] * scale_x
                old_y = change.old_coords[1] * scale_y
                new_x = change.new_coords[0] * scale_x
                new_y = change.new_coords[1] * scale_y

                # Old position (faded blue)
                self._draw_circle(draw, old_x, old_y, colors["old"], radius - 2, border_width)

                # Arrow from old to new
                self._draw_arrow(
                    draw,
                    (old_x, old_y),
                    (new_x, new_y),
                    colors["arrow"],
                    sizes["arrow_width"],
                    sizes["arrow_head_size"],
                )

                # New position (purple)
                self._draw_circle(draw, new_x, new_y, colors["new"], radius, border_width)

                if self.show_labels and font:
                    self._draw_label(
                        draw,
                        new_x,
                        new_y,
                        change.ap_name,
                        font,
                        radius + 5,
                        -sizes["font_size"] // 2,
                    )

        elif status == ChangeStatus.RENAMED:
            # Orange circle at position, label shows old→new name
            if change.new_ap and change.new_ap.location_x is not None:
                x = change.new_ap.location_x * scale_x
                y = change.new_ap.location_y * scale_y
                self._draw_circle(draw, x, y, COLORS[ChangeStatus.RENAMED], radius, border_width)
                if self.show_labels and font:
                    label = f"{change.old_name}→{change.new_name}"
                    self._draw_label(draw, x, y, label, font, radius + 5, -sizes["font_size"] // 2)

        elif status == ChangeStatus.UNCHANGED and self.show_unchanged:
            # Gray circle (very faded)
            if change.new_ap and change.new_ap.location_x is not None:
                x = change.new_ap.location_x * scale_x
                y = change.new_ap.location_y * scale_y
                self._draw_circle(
                    draw, x, y, COLORS[ChangeStatus.UNCHANGED], radius - 4, border_width - 1
                )

    def generate_all_diffs(self, comparison: ComparisonResult, output_dir: Path) -> dict[str, Path]:
        """Generate diff visualizations for all floors with changes.

        Args:
            comparison: ComparisonResult with changes
            output_dir: Directory where diff images will be saved

        Returns:
            Dictionary mapping floor name to output path
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        output_files = {}

        for floor_name, changes in comparison.changes_by_floor.items():
            # Filter to only actual changes (exclude unchanged unless configured)
            if not self.show_unchanged:
                changes = [c for c in changes if c.status != ChangeStatus.UNCHANGED]

            if not changes:
                continue

            output_path = self.generate_floor_diff(floor_name, changes)
            if output_path:
                output_files[floor_name] = output_path

        logger.info(f"Generated {len(output_files)} diff visualizations")
        return output_files

    def close(self):
        """Close the .esx archives."""
        if hasattr(self, "old_archive"):
            self.old_archive.close()
        if hasattr(self, "new_archive"):
            self.new_archive.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
