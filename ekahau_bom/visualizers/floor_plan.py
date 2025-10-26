#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Floor plan visualization with AP placement overlay."""

import logging
import zipfile
from pathlib import Path
from typing import Optional
from io import BytesIO

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from ..models import AccessPoint, Floor

logger = logging.getLogger(__name__)


class FloorPlanVisualizer:
    """Visualize access point placement on floor plan images.

    Extracts floor plan images from Ekahau .esx files and overlays
    AP positions with colored circles matching their Ekahau colors.
    """

    def __init__(
        self,
        esx_path: Path,
        output_dir: Path,
        ap_circle_radius: int = 15,
        ap_border_width: int = 3,
        show_ap_names: bool = True,
        font_size: int = 12
    ):
        """Initialize floor plan visualizer.

        Args:
            esx_path: Path to Ekahau .esx project file
            output_dir: Directory where visualization images will be saved
            ap_circle_radius: Radius of AP marker circles (default: 15)
            ap_border_width: Width of circle border (default: 3)
            show_ap_names: Whether to show AP names next to markers (default: True)
            font_size: Font size for AP names (default: 12)
        """
        if not PIL_AVAILABLE:
            raise ImportError(
                "Pillow library is required for floor plan visualization. "
                "Install it with: pip install Pillow"
            )

        self.esx_path = esx_path
        self.output_dir = output_dir
        self.ap_circle_radius = ap_circle_radius
        self.ap_border_width = ap_border_width
        self.show_ap_names = show_ap_names
        self.font_size = font_size

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Open .esx archive
        self.archive = zipfile.ZipFile(esx_path, 'r')

        # Try to load a decent font, fall back to default if unavailable
        self.font = self._load_font()

    def _load_font(self) -> Optional[ImageFont.FreeTypeFont]:
        """Load a TrueType font for text rendering.

        Returns:
            ImageFont object or None if unavailable
        """
        try:
            # Try common system fonts
            font_names = [
                "arial.ttf",
                "Arial.ttf",
                "DejaVuSans.ttf",
                "LiberationSans-Regular.ttf"
            ]

            for font_name in font_names:
                try:
                    return ImageFont.truetype(font_name, self.font_size)
                except (OSError, IOError):
                    continue

            # If no font found, use default
            logger.warning("Could not load TrueType font, using default")
            return ImageFont.load_default()
        except Exception as e:
            logger.warning(f"Error loading font: {e}")
            return None

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        """Convert hex color to RGB tuple.

        Args:
            hex_color: Hex color string (e.g., "#FF0000" or "FF0000")

        Returns:
            RGB tuple (r, g, b)
        """
        # Remove '#' if present
        hex_color = hex_color.lstrip('#')

        # Handle short form (#FFF -> #FFFFFF)
        if len(hex_color) == 3:
            hex_color = ''.join([c * 2 for c in hex_color])

        # Convert to RGB
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (r, g, b)
        except (ValueError, IndexError):
            logger.warning(f"Invalid hex color: {hex_color}, using black")
            return (0, 0, 0)

    def _get_floor_plan_image(self, floor: Floor) -> Optional[Image.Image]:
        """Extract floor plan image from .esx archive.

        Args:
            floor: Floor object with floor plan metadata

        Returns:
            PIL Image object or None if not found
        """
        try:
            # Floor plans metadata
            import json
            floor_plans_data = json.loads(self.archive.read('floorPlans.json'))

            # Find floor plan by ID
            floor_plan = None
            for fp in floor_plans_data.get('floorPlans', []):
                if fp.get('id') == floor.id:
                    floor_plan = fp
                    break

            if not floor_plan:
                logger.warning(f"Floor plan not found for floor: {floor.name}")
                return None

            # Get image ID
            image_id = floor_plan.get('imageId')
            if not image_id:
                logger.warning(f"No image ID for floor: {floor.name}")
                return None

            # Read image file from archive
            image_filename = f"image-{image_id}"
            if image_filename not in self.archive.namelist():
                logger.warning(f"Image file not found: {image_filename}")
                return None

            # Load image
            image_data = self.archive.read(image_filename)
            image = Image.open(BytesIO(image_data))

            logger.info(f"Loaded floor plan image for {floor.name}: {image.size}")
            return image

        except Exception as e:
            logger.error(f"Error loading floor plan image for {floor.name}: {e}")
            return None

    def visualize_floor(
        self,
        floor: Floor,
        access_points: list[AccessPoint]
    ) -> Optional[Path]:
        """Create visualization for a single floor.

        Args:
            floor: Floor object
            access_points: List of access points on this floor

        Returns:
            Path to generated image file or None if failed
        """
        # Get floor plan image
        image = self._get_floor_plan_image(floor)
        if image is None:
            return None

        # Convert to RGB if necessary (for drawing)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Create drawing context
        draw = ImageDraw.Draw(image)

        # Filter APs for this floor
        floor_aps = [ap for ap in access_points if ap.floor_id == floor.id]

        logger.info(f"Drawing {len(floor_aps)} APs on floor: {floor.name}")

        # Draw each AP
        for ap in floor_aps:
            if ap.location_x is None or ap.location_y is None:
                logger.warning(f"AP {ap.name} has no location, skipping")
                continue

            x, y = ap.location_x, ap.location_y

            # Determine AP color
            if ap.color:
                fill_color = self._hex_to_rgb(ap.color)
            else:
                # Default color if none specified
                fill_color = (100, 149, 237)  # Cornflower blue

            # Draw circle with border
            # Outer circle (border)
            border_color = (0, 0, 0)  # Black border
            draw.ellipse(
                [
                    x - self.ap_circle_radius,
                    y - self.ap_circle_radius,
                    x + self.ap_circle_radius,
                    y + self.ap_circle_radius
                ],
                fill=border_color,
                outline=border_color
            )

            # Inner circle (AP color)
            inner_radius = self.ap_circle_radius - self.ap_border_width
            draw.ellipse(
                [
                    x - inner_radius,
                    y - inner_radius,
                    x + inner_radius,
                    y + inner_radius
                ],
                fill=fill_color,
                outline=fill_color
            )

            # Draw AP name if enabled
            if self.show_ap_names and self.font:
                # Position text to the right of the circle
                text_x = x + self.ap_circle_radius + 5
                text_y = y - self.font_size // 2

                # Draw text with shadow for better visibility
                shadow_color = (255, 255, 255)  # White shadow
                text_color = (0, 0, 0)  # Black text

                # Shadow
                draw.text(
                    (text_x + 1, text_y + 1),
                    ap.name,
                    font=self.font,
                    fill=shadow_color
                )

                # Main text
                draw.text(
                    (text_x, text_y),
                    ap.name,
                    font=self.font,
                    fill=text_color
                )

        # Save image
        output_filename = f"{floor.name.replace('/', '_').replace('\\', '_')}_visualization.png"
        output_path = self.output_dir / output_filename

        image.save(output_path, 'PNG')
        logger.info(f"Saved floor plan visualization: {output_path}")

        return output_path

    def visualize_all_floors(
        self,
        floors: dict[str, Floor],
        access_points: list[AccessPoint]
    ) -> list[Path]:
        """Create visualizations for all floors with APs.

        Args:
            floors: Dictionary mapping floor IDs to Floor objects
            access_points: List of all access points in project

        Returns:
            List of paths to generated image files
        """
        output_files = []

        # Group APs by floor
        floors_with_aps = set()
        for ap in access_points:
            if ap.floor_id and ap.location_x is not None and ap.location_y is not None:
                floors_with_aps.add(ap.floor_id)

        logger.info(f"Generating visualizations for {len(floors_with_aps)} floors")

        # Process each floor
        for floor_id in floors_with_aps:
            if floor_id not in floors:
                logger.warning(f"Floor ID {floor_id} not found in floors dict")
                continue

            floor = floors[floor_id]
            output_path = self.visualize_floor(floor, access_points)

            if output_path:
                output_files.append(output_path)

        logger.info(f"Generated {len(output_files)} floor plan visualizations")
        return output_files

    def close(self):
        """Close the .esx archive."""
        if hasattr(self, 'archive'):
            self.archive.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
