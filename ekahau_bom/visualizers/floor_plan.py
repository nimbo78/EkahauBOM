#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Floor plan visualization with AP placement overlay."""

from __future__ import annotations


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
        font_size: int = 12,
        show_azimuth_arrows: bool = False,
        ap_opacity: float = 0.6,
        include_text_notes: bool = False,
        include_picture_notes: bool = False,
        include_cable_notes: bool = False,
        text_notes: list = None,
        picture_notes: list = None,
        cable_notes: list = None,
    ):
        """Initialize floor plan visualizer.

        Args:
            esx_path: Path to Ekahau .esx project file
            output_dir: Directory where visualization images will be saved
            ap_circle_radius: Radius of AP marker circles (default: 15)
            ap_border_width: Width of circle border (default: 3)
            show_ap_names: Whether to show AP names next to markers (default: True)
            font_size: Font size for AP names (default: 12)
            show_azimuth_arrows: Whether to show azimuth direction arrows on AP markers (default: False)
            ap_opacity: Opacity for AP markers (0.0-1.0, default: 0.6 = 60%)
            include_text_notes: Whether to display text notes on floor plans (default: False)
            include_picture_notes: Whether to display picture note markers on floor plans (default: False)
            include_cable_notes: Whether to display cable routing paths on floor plans (default: False)
            text_notes: List of Note objects with text content
            picture_notes: List of PictureNote objects with location markers
            cable_notes: List of CableNote objects with routing paths
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
        self.show_azimuth_arrows = show_azimuth_arrows
        self.ap_opacity = max(0.0, min(1.0, ap_opacity))  # Clamp between 0.0 and 1.0

        # Notes visualization options
        self.include_text_notes = include_text_notes
        self.include_picture_notes = include_picture_notes
        self.include_cable_notes = include_cable_notes
        self.text_notes = text_notes or []
        self.picture_notes = picture_notes or []
        self.cable_notes = cable_notes or []

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Open .esx archive
        self.archive = zipfile.ZipFile(esx_path, "r")

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
                "LiberationSans-Regular.ttf",
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

    def _calculate_adaptive_sizes(self, image_width: int, image_height: int) -> dict:
        """Calculate adaptive marker sizes based on image dimensions.

        For large high-resolution images (e.g., 5000x3534), fixed pixel sizes become
        microscopic. This method scales marker sizes proportionally to image size.

        Formula: base_radius = max(min_radius, avg_dimension * scale_factor)
        where avg_dimension = (width + height) / 2

        Args:
            image_width: Width of floor plan image in pixels
            image_height: Height of floor plan image in pixels

        Returns:
            dict with adaptive sizes: radius, border_width, font_size, arrow_length
        """
        # Average dimension for scaling
        avg_dimension = (image_width + image_height) / 2

        # Scale factor: ~0.8% of average dimension
        # Examples:
        #   - 1000px avg → 8px radius (but min 10)
        #   - 2500px avg → 20px radius
        #   - 5000px avg → 40px radius
        scale_factor = 0.008
        min_radius = 10

        # Calculate adaptive radius (override user-provided radius for large images)
        if avg_dimension > 2000:  # Only apply adaptive sizing for large images
            base_radius = max(min_radius, int(avg_dimension * scale_factor))
        else:
            # For small images, use user-provided radius
            base_radius = self.ap_circle_radius

        # Scale other elements proportionally
        border_width = max(2, int(base_radius * 0.15))  # 15% of radius
        font_size = max(10, int(base_radius * 0.8))  # 80% of radius
        arrow_length = int(base_radius * 2.0)  # 2x radius

        logger.debug(
            f"Adaptive sizes for {image_width}x{image_height}: "
            f"radius={base_radius}px, border={border_width}px, "
            f"font={font_size}pt, arrow={arrow_length}px"
        )

        return {
            "radius": base_radius,
            "border_width": border_width,
            "font_size": font_size,
            "arrow_length": arrow_length,
        }

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        """Convert hex color to RGB tuple.

        Supports:
        - Hex colors: "#FF0000", "FF0000", "#F00", "F00"
        - Standard color names: "Red", "Blue", "Green", "Yellow", etc.
        - Common typos: "RReedd" -> "Red"

        Args:
            hex_color: Hex color string or color name

        Returns:
            RGB tuple (r, g, b)
        """
        # Standard color name mapping
        color_names = {
            # Basic colors
            "red": "FF0000",
            "green": "00FF00",
            "blue": "0000FF",
            "yellow": "FFFF00",
            "orange": "FFA500",
            "purple": "800080",
            "pink": "FFC0CB",
            "brown": "A52A2A",
            "gray": "808080",
            "grey": "808080",
            "black": "000000",
            "white": "FFFFFF",
            "cyan": "00FFFF",
            "magenta": "FF00FF",
            # Common Ekahau colors
            "lightblue": "87CEEB",
            "darkblue": "00008B",
            "lightgreen": "90EE90",
            "darkgreen": "006400",
            "lightyellow": "FFFFE0",
            "mint": "98FF98",
            "turquoise": "40E0D0",
            "lavender": "E6E6FA",
            "violet": "C297FF",
        }

        # Normalize the color string
        original_color = hex_color
        hex_color_normalized = hex_color.lower().strip()

        # First, try exact match with normalized name
        if hex_color_normalized in color_names:
            hex_color = color_names[hex_color_normalized]
            logger.debug(
                f"Converted color name '{original_color}' to hex: #{hex_color}"
            )
        # If not found, try fixing common typos (RReedd -> red, BBllue -> blue, etc.)
        else:
            import re

            # Pattern: remove duplicate characters (only if 3+ in a row to preserve "yellow", "green")
            fixed_color = re.sub(r"(.)\1{2,}", r"\1", hex_color_normalized)

            # Check if fixed version is a known color name
            if fixed_color != hex_color_normalized and fixed_color in color_names:
                hex_color = color_names[fixed_color]
                logger.debug(
                    f"Fixed typo: '{original_color}' -> '{fixed_color}' to hex: #{hex_color}"
                )
            else:
                # Not a color name, treat as hex code
                # Remove '#' if present
                hex_color = hex_color.lstrip("#")

                # Handle short form (#FFF -> #FFFFFF)
                if len(hex_color) == 3:
                    hex_color = "".join([c * 2 for c in hex_color])

        # Convert to RGB
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (r, g, b)
        except (ValueError, IndexError):
            logger.warning(f"Invalid hex color: {original_color}, using black")
            return (0, 0, 0)

    def _draw_ap_marker(
        self,
        draw: ImageDraw.ImageDraw,
        x: float,
        y: float,
        fill_color: tuple,
        mounting_type: str = "CEILING",
        azimuth: float = 0.0,
        adaptive_sizes: dict = None,
    ) -> None:
        """Draw AP marker based on mounting type.

        Args:
            draw: ImageDraw context
            x, y: Center coordinates
            fill_color: RGBA color tuple
            mounting_type: CEILING, WALL, or FLOOR
            azimuth: Direction in degrees (0=N, 90=E, 180=S, 270=W)
            adaptive_sizes: dict with adaptive sizes (radius, border_width, etc.)
        """
        if mounting_type == "CEILING":
            self._draw_circle(draw, x, y, fill_color, adaptive_sizes)
        elif mounting_type == "WALL":
            self._draw_oriented_rectangle(
                draw, x, y, fill_color, azimuth, adaptive_sizes
            )
        elif mounting_type == "FLOOR":
            self._draw_square(draw, x, y, fill_color, adaptive_sizes)
        else:
            # Default to circle
            self._draw_circle(draw, x, y, fill_color, adaptive_sizes)

        # Note: Arrows are now drawn separately after compositing for better visibility
        # This method only draws the shapes (circles, rectangles, squares)

    def _draw_circle(
        self,
        draw: ImageDraw.ImageDraw,
        x: float,
        y: float,
        fill_color: tuple,
        adaptive_sizes: dict = None,
    ) -> None:
        """Draw circular AP marker (for ceiling-mounted APs).

        Args:
            draw: ImageDraw context
            x, y: Center coordinates
            fill_color: RGBA color tuple
            adaptive_sizes: dict with adaptive sizes (radius, border_width, etc.)
        """
        # Use adaptive sizes if provided, otherwise use defaults
        radius = adaptive_sizes["radius"] if adaptive_sizes else self.ap_circle_radius
        border_width = (
            adaptive_sizes["border_width"] if adaptive_sizes else self.ap_border_width
        )

        # Outer circle (border) - always fully opaque for clear visibility
        border_color = (0, 0, 0, 255)  # Black border, fully opaque
        draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=border_color,
            outline=border_color,
        )

        # Inner circle (AP color)
        inner_radius = radius - border_width
        draw.ellipse(
            [x - inner_radius, y - inner_radius, x + inner_radius, y + inner_radius],
            fill=fill_color,
            outline=fill_color,
        )

    def _draw_oriented_rectangle(
        self,
        draw: ImageDraw.ImageDraw,
        x: float,
        y: float,
        fill_color: tuple,
        azimuth: float,
        adaptive_sizes: dict = None,
    ) -> None:
        """Draw rotated rectangle for wall-mounted AP.

        The long edge of the rectangle points in the azimuth direction.

        Args:
            draw: ImageDraw context
            x, y: Center coordinates
            fill_color: RGBA color tuple
            azimuth: Direction in degrees (0=N, 90=E, 180=S, 270=W)
            adaptive_sizes: dict with adaptive sizes (radius, border_width, etc.)
        """
        import math

        # Use adaptive sizes if provided, otherwise use defaults
        radius = adaptive_sizes["radius"] if adaptive_sizes else self.ap_circle_radius
        border_width = (
            adaptive_sizes["border_width"] if adaptive_sizes else self.ap_border_width
        )

        # Rectangle dimensions (2:1 ratio)
        width = radius * 2  # Long dimension
        height = radius  # Short dimension

        # Convert azimuth to radians (note: 0° = North = up, clockwise)
        # Need to adjust: image coords have Y increasing downward
        # Add 90° so that the LONG edge points in the azimuth direction
        angle_rad = math.radians(azimuth)  # Direct azimuth mapping for long edge

        # Calculate corner points (centered at origin)
        half_w = width / 2
        half_h = height / 2
        corners = [
            (-half_w, -half_h),  # Top-left
            (half_w, -half_h),  # Top-right
            (half_w, half_h),  # Bottom-right
            (-half_w, half_h),  # Bottom-left
        ]

        # Rotate and translate corners
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        rotated_corners = []
        for cx, cy in corners:
            # Apply rotation matrix
            rx = cx * cos_a - cy * sin_a
            ry = cx * sin_a + cy * cos_a
            # Translate to actual position
            rotated_corners.append((x + rx, y + ry))

        # Draw border - always fully opaque for clear visibility
        border_color = (0, 0, 0, 255)  # Black border, fully opaque
        draw.polygon(rotated_corners, fill=border_color, outline=border_color)

        # Draw inner rectangle (smaller for border effect)
        border_offset = border_width
        inner_corners = []
        for cx, cy in corners:
            # Shrink corners by scaling from center
            scale_x = (half_w - border_offset) / half_w if half_w > 0 else 0
            scale_y = (half_h - border_offset) / half_h if half_h > 0 else 0
            cx_inner = cx * scale_x
            cy_inner = cy * scale_y
            # Rotate
            rx = cx_inner * cos_a - cy_inner * sin_a
            ry = cx_inner * sin_a + cy_inner * cos_a
            # Translate
            inner_corners.append((x + rx, y + ry))

        draw.polygon(inner_corners, fill=fill_color, outline=fill_color)

    def _draw_square(
        self,
        draw: ImageDraw.ImageDraw,
        x: float,
        y: float,
        fill_color: tuple,
        adaptive_sizes: dict = None,
    ) -> None:
        """Draw square AP marker (for floor-mounted APs).

        Args:
            draw: ImageDraw context
            x, y: Center coordinates
            fill_color: RGBA color tuple
            adaptive_sizes: dict with adaptive sizes (radius, border_width, etc.)
        """
        # Use adaptive sizes if provided, otherwise use defaults
        radius = adaptive_sizes["radius"] if adaptive_sizes else self.ap_circle_radius
        border_width = (
            adaptive_sizes["border_width"] if adaptive_sizes else self.ap_border_width
        )

        # Use circle radius as half-side length
        half_side = radius

        # Draw border square - always fully opaque for clear visibility
        border_color = (0, 0, 0, 255)  # Black border, fully opaque
        draw.rectangle(
            [x - half_side, y - half_side, x + half_side, y + half_side],
            fill=border_color,
            outline=border_color,
        )

        # Draw inner square
        inner_half = half_side - border_width
        draw.rectangle(
            [x - inner_half, y - inner_half, x + inner_half, y + inner_half],
            fill=fill_color,
            outline=fill_color,
        )

    def _draw_azimuth_arrow(
        self,
        draw: ImageDraw.ImageDraw,
        x: float,
        y: float,
        azimuth: float,
        color: tuple = (255, 0, 0, 255),
        arrow_length: float = None,
        arrow_head_size: float = None,
        line_width: int = None,
    ) -> None:
        """Draw an arrow indicating azimuth direction.

        Args:
            draw: ImageDraw context
            x, y: Center coordinates (start of arrow)
            azimuth: Direction in degrees (0=N, 90=E, 180=S, 270=W)
            color: Arrow color (default: red)
            arrow_length: Length of arrow (default: 2 * ap_circle_radius)
            arrow_head_size: Size of arrow head (default: adaptive or 6)
            line_width: Width of arrow line (default: adaptive or 3)
        """
        import math

        if arrow_length is None:
            arrow_length = self.ap_circle_radius * 2  # Default arrow length

        if arrow_head_size is None:
            # Scale arrow head with arrow length (15% of length)
            arrow_head_size = max(4, int(arrow_length * 0.15))

        if line_width is None:
            # Scale line width with arrow length (7.5% of length)
            line_width = max(2, int(arrow_length * 0.075))

        # Convert azimuth to radians (adjust for image coordinates)
        # 0° = North = up, but in image coords Y increases downward
        angle_rad = math.radians(azimuth - 90)  # -90 to align with image coords

        # Calculate end point of arrow line
        end_x = x + arrow_length * math.cos(angle_rad)
        end_y = y + arrow_length * math.sin(angle_rad)

        # Draw arrow line
        draw.line([(x, y), (end_x, end_y)], fill=color, width=line_width)

        # Calculate arrow head points (triangle)
        # Create two points at 150 degrees from the main line
        head_angle1 = angle_rad + math.radians(150)
        head_angle2 = angle_rad + math.radians(-150)

        head_x1 = end_x + arrow_head_size * math.cos(head_angle1)
        head_y1 = end_y + arrow_head_size * math.sin(head_angle1)
        head_x2 = end_x + arrow_head_size * math.cos(head_angle2)
        head_y2 = end_y + arrow_head_size * math.sin(head_angle2)

        # Draw arrow head as filled triangle
        arrow_head = [(end_x, end_y), (head_x1, head_y1), (head_x2, head_y2)]
        draw.polygon(arrow_head, fill=color, outline=color)

    def _draw_legend(
        self,
        image: Image.Image,
        access_points: list,
    ) -> Image.Image:
        """Draw color legend on the visualization and return new image.

        Args:
            image: Image to draw legend on
            access_points: List of access points to analyze

        Returns:
            New image with legend drawn
        """
        if not access_points:
            return image

        image_size = image.size

        # Collect color statistics
        from collections import Counter

        color_counts = Counter()
        for ap in access_points:
            color_name = ap.color if ap.color else "Default"
            color_counts[color_name] += 1

        if not color_counts:
            return image

        # Legend parameters
        legend_padding = 15
        legend_line_height = 25
        legend_circle_radius = 8
        legend_text_offset = 20

        # Calculate legend dimensions
        legend_height = len(color_counts) * legend_line_height + legend_padding * 2 + 20
        legend_width = 180

        # Position in top-right corner
        legend_x = image_size[0] - legend_width - 20
        legend_y = 20

        # Draw semi-transparent background
        # Create a new image for the legend with transparency
        from PIL import Image

        legend_overlay = Image.new("RGBA", image_size, (255, 255, 255, 0))
        legend_draw = ImageDraw.Draw(legend_overlay)

        # Draw white background with transparency
        legend_draw.rectangle(
            [legend_x, legend_y, legend_x + legend_width, legend_y + legend_height],
            fill=(255, 255, 255, 230),
            outline=(0, 0, 0, 255),
            width=2,
        )

        # Draw title
        title_y = legend_y + legend_padding
        if self.font:
            legend_draw.text(
                (legend_x + legend_padding, title_y),
                "Access Points",
                font=self.font,
                fill=(0, 0, 0, 255),
            )

        # Draw each color entry
        entry_y = title_y + legend_line_height
        for color_name, count in sorted(color_counts.items()):
            # Determine color
            if color_name == "Default":
                fill_color = (100, 149, 237, 255)  # Cornflower blue
            else:
                rgb = self._hex_to_rgb(color_name)
                fill_color = (*rgb, 255)

            # Draw circle
            circle_x = legend_x + legend_padding + legend_circle_radius
            circle_y = entry_y + legend_line_height // 2

            # Border
            legend_draw.ellipse(
                [
                    circle_x - legend_circle_radius,
                    circle_y - legend_circle_radius,
                    circle_x + legend_circle_radius,
                    circle_y + legend_circle_radius,
                ],
                fill=(0, 0, 0, 255),
                outline=(0, 0, 0, 255),
            )

            # Inner circle
            inner_r = legend_circle_radius - 2
            legend_draw.ellipse(
                [
                    circle_x - inner_r,
                    circle_y - inner_r,
                    circle_x + inner_r,
                    circle_y + inner_r,
                ],
                fill=fill_color,
                outline=fill_color,
            )

            # Draw text
            text_x = legend_x + legend_padding + legend_text_offset
            text_y = entry_y + (legend_line_height - self.font_size) // 2

            if self.font:
                legend_draw.text(
                    (text_x, text_y),
                    f"{color_name}: {count}",
                    font=self.font,
                    fill=(0, 0, 0, 255),
                )

            entry_y += legend_line_height

        # Composite the legend onto the image
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # Composite the legend
        image = Image.alpha_composite(image, legend_overlay)

        # Return the new image with legend
        return image

    def _draw_picture_notes(
        self,
        draw: ImageDraw.ImageDraw,
        floor_id: str,
        scale_x: float,
        scale_y: float,
        adaptive_sizes: dict = None,
    ) -> None:
        """Draw picture note markers on floor plan.

        Picture notes are visual markers (pins) placed on the floor plan at specific coordinates.

        Args:
            draw: ImageDraw context
            floor_id: Floor ID to filter notes
            scale_x: X-coordinate scale factor
            scale_y: Y-coordinate scale factor
            adaptive_sizes: dict with adaptive sizes (for marker radius)
        """
        if not self.include_picture_notes or not self.picture_notes:
            return

        # Filter picture notes for this floor
        floor_picture_notes = [
            note
            for note in self.picture_notes
            if note.location and note.location.floor_plan_id == floor_id
        ]

        if not floor_picture_notes:
            return

        # Smaller marker - half the size (0.3x instead of 0.6x)
        marker_radius = (
            adaptive_sizes["radius"] * 0.3
            if adaptive_sizes
            else self.ap_circle_radius * 0.3
        )
        marker_radius = int(marker_radius)

        logger.info(
            f"Drawing {len(floor_picture_notes)} picture notes on floor {floor_id}"
        )

        for note in floor_picture_notes:
            if not note.location or note.location.x is None or note.location.y is None:
                continue

            # Scale coordinates
            x = note.location.x * scale_x
            y = note.location.y * scale_y

            # Draw simple red circle (no border)
            pin_color = (255, 107, 107, 255)  # Red (FF6B6B)

            # Single circle - just the red pin
            draw.ellipse(
                [
                    x - marker_radius,
                    y - marker_radius,
                    x + marker_radius,
                    y + marker_radius,
                ],
                fill=pin_color,
                outline=pin_color,
            )

    def _draw_dashed_line(
        self,
        draw: ImageDraw.ImageDraw,
        points: list,
        color: tuple,
        width: int = 3,
        dash_length: int = 10,
        gap_length: int = 5,
    ) -> None:
        """Draw a dashed line through multiple points.

        Args:
            draw: ImageDraw context
            points: List of (x, y) tuples representing the polyline
            color: Line color as RGBA tuple
            width: Line width in pixels
            dash_length: Length of each dash in pixels
            gap_length: Length of gap between dashes in pixels
        """
        import math

        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]

            # Calculate segment length and direction
            dx = x2 - x1
            dy = y2 - y1
            segment_length = math.sqrt(dx**2 + dy**2)

            if segment_length == 0:
                continue

            # Normalize direction vector
            dx_norm = dx / segment_length
            dy_norm = dy / segment_length

            # Draw dashes along the segment
            current_distance = 0
            while current_distance < segment_length:
                # Start of dash
                dash_start_x = x1 + dx_norm * current_distance
                dash_start_y = y1 + dy_norm * current_distance

                # End of dash (or end of segment if dash would exceed)
                dash_end_distance = min(current_distance + dash_length, segment_length)
                dash_end_x = x1 + dx_norm * dash_end_distance
                dash_end_y = y1 + dy_norm * dash_end_distance

                # Draw the dash
                draw.line(
                    [(dash_start_x, dash_start_y), (dash_end_x, dash_end_y)],
                    fill=color,
                    width=width,
                )

                # Move to next dash (skip gap)
                current_distance += dash_length + gap_length

    def _draw_cable_notes(
        self,
        draw: ImageDraw.ImageDraw,
        floor_id: str,
        scale_x: float,
        scale_y: float,
        adaptive_sizes: dict = None,
    ) -> None:
        """Draw cable routing paths on floor plan.

        Cable notes show polyline paths representing cable routes through the building.

        Args:
            draw: ImageDraw context
            floor_id: Floor ID to filter notes
            scale_x: X-coordinate scale factor
            scale_y: Y-coordinate scale factor
            adaptive_sizes: dict with adaptive sizes (for line width)
        """
        if not self.include_cable_notes or not self.cable_notes:
            return

        # Filter cable notes for this floor
        floor_cable_notes = [
            note for note in self.cable_notes if note.floor_plan_id == floor_id
        ]

        if not floor_cable_notes:
            return

        # Line width scales with image size
        line_width = max(2, adaptive_sizes["border_width"]) if adaptive_sizes else 3

        logger.info(f"Drawing {len(floor_cable_notes)} cable notes on floor {floor_id}")

        for note in floor_cable_notes:
            if not note.points or len(note.points) < 2:
                continue

            # Scale all points
            scaled_points = []
            for point in note.points:
                x = (point.x if hasattr(point, "x") else point.get("x", 0)) * scale_x
                y = (point.y if hasattr(point, "y") else point.get("y", 0)) * scale_y
                scaled_points.append((x, y))

            # Determine line color
            if note.color and note.color != "#000000":
                # Use note's color if specified and not black
                rgb = self._hex_to_rgb(note.color)
                line_color = (*rgb, 255)
            else:
                # Default cable color: purple (like Ekahau)
                line_color = (139, 92, 246, 255)  # Nice purple color

            # Draw dashed polyline (like Ekahau)
            self._draw_dashed_line(
                draw,
                scaled_points,
                color=line_color,
                width=line_width,
                dash_length=10,
                gap_length=5,
            )

    def _draw_text_notes(
        self,
        draw: ImageDraw.ImageDraw,
        floor_id: str,
        scale_x: float,
        scale_y: float,
        font: ImageFont.FreeTypeFont = None,
        adaptive_sizes: dict = None,
    ) -> None:
        """Draw text notes on floor plan.

        Text notes are displayed as labels with text content, similar to AP names.
        Currently, text notes don't have explicit floor_id or coordinates in the model,
        so they are linked via picture_notes. This method draws text for picture notes
        that have associated text note IDs.

        Args:
            draw: ImageDraw context
            floor_id: Floor ID to filter notes
            scale_x: X-coordinate scale factor
            scale_y: Y-coordinate scale factor
            font: Font to use for text rendering
            adaptive_sizes: dict with adaptive sizes (for font size)
        """
        if not self.include_text_notes or not self.text_notes:
            return

        # Create text note lookup by ID
        text_notes_by_id = {note.id: note for note in self.text_notes}

        # Find picture notes on this floor that have linked text notes
        floor_picture_notes = [
            note
            for note in self.picture_notes
            if note.location
            and note.location.floor_plan_id == floor_id
            and note.note_ids
        ]

        if not floor_picture_notes:
            return

        # Use same marker radius as picture notes (0.3x)
        marker_radius = (
            adaptive_sizes["radius"] * 0.3
            if adaptive_sizes
            else self.ap_circle_radius * 0.3
        )

        logger.info(
            f"Drawing text notes for {len(floor_picture_notes)} picture notes on floor {floor_id}"
        )

        for picture_note in floor_picture_notes:
            if (
                not picture_note.location
                or picture_note.location.x is None
                or picture_note.location.y is None
            ):
                continue

            # Get text from linked notes
            texts = []
            for note_id in picture_note.note_ids:
                if note_id in text_notes_by_id:
                    text_note = text_notes_by_id[note_id]
                    if text_note.text:
                        texts.append(text_note.text)

            if not texts:
                continue

            # Combine multiple texts with line breaks
            combined_text = "\n".join(texts)

            # Limit text length to avoid cluttering the visualization
            if len(combined_text) > 100:
                combined_text = combined_text[:97] + "..."

            # Scale coordinates
            x = picture_note.location.x * scale_x
            y = picture_note.location.y * scale_y

            # Calculate text width for centering
            bbox = draw.textbbox((0, 0), combined_text, font=font)
            text_width = bbox[2] - bbox[0]

            # Position text below the picture note marker, centered
            text_x = x - (text_width / 2)  # Center horizontally
            text_y = y + marker_radius + 5

            # Draw text with white outline for visibility (similar to AP names)
            outline_color = (255, 255, 255)  # White outline
            text_color = (0, 0, 0)  # Black text

            outline_width = 1

            # Draw outline
            for dx in [-outline_width, 0, outline_width]:
                for dy in [-outline_width, 0, outline_width]:
                    if dx == 0 and dy == 0:
                        continue
                    draw.text(
                        (text_x + dx, text_y + dy),
                        combined_text,
                        font=font,
                        fill=outline_color,
                    )

            # Main text on top
            draw.text((text_x, text_y), combined_text, font=font, fill=text_color)

    def _get_floor_plan_image(
        self, floor: Floor
    ) -> Optional[tuple[Image.Image, float, float]]:
        """Extract floor plan image from .esx archive with coordinate scale factors.

        Ekahau stores coordinates relative to the floor plan dimensions in floorPlans.json.
        When using bitmapImageId (high-res JPEG/PNG) instead of imageId (SVG), we need
        to scale coordinates to match the actual image dimensions.

        Args:
            floor: Floor object with floor plan metadata

        Returns:
            Tuple of (image, scale_x, scale_y) or None if not found
            - image: PIL Image object
            - scale_x: X-coordinate scale factor (actual_width / plan_width)
            - scale_y: Y-coordinate scale factor (actual_height / plan_height)
        """
        try:
            # Floor plans metadata
            import json

            floor_plans_data = json.loads(self.archive.read("floorPlans.json"))

            # Find floor plan by ID
            floor_plan = None
            for fp in floor_plans_data.get("floorPlans", []):
                if fp.get("id") == floor.id:
                    floor_plan = fp
                    break

            if not floor_plan:
                logger.warning(f"Floor plan not found for floor: {floor.name}")
                return None

            # Get floor plan dimensions (these are the coordinate system dimensions)
            plan_width = floor_plan.get("width", 0)
            plan_height = floor_plan.get("height", 0)

            if plan_width == 0 or plan_height == 0:
                logger.warning(
                    f"Invalid floor plan dimensions for {floor.name}: "
                    f"{plan_width}x{plan_height}"
                )
                # Fall back to 1:1 scaling
                plan_width = plan_height = 1

            # Get bitmap image ID (JPEG/PNG) for compatibility with Pillow
            # bitmapImageId contains raster version, imageId may contain SVG
            image_id = floor_plan.get("bitmapImageId")
            if not image_id:
                # Fallback to imageId for projects without bitmap version
                image_id = floor_plan.get("imageId")
                if not image_id:
                    logger.warning(f"No image ID for floor: {floor.name}")
                    return None
                logger.debug(
                    f"Using imageId for floor {floor.name} "
                    f"(no bitmapImageId, may fail for SVG)"
                )

            # Read image file from archive
            image_filename = f"image-{image_id}"
            if image_filename not in self.archive.namelist():
                logger.warning(f"Image file not found: {image_filename}")
                return None

            # Load image
            image_data = self.archive.read(image_filename)
            image = Image.open(BytesIO(image_data))

            # Calculate scale factors
            actual_width, actual_height = image.size
            scale_x = actual_width / plan_width
            scale_y = actual_height / plan_height

            logger.info(
                f"Loaded floor plan for {floor.name}: {image.size} "
                f"(plan dims: {plan_width}x{plan_height}, "
                f"scale: {scale_x:.3f}x{scale_y:.3f})"
            )

            return (image, scale_x, scale_y)

        except Exception as e:
            logger.error(f"Error loading floor plan image for {floor.name}: {e}")
            return None

    def visualize_floor(
        self, floor: Floor, access_points: list[AccessPoint], radios: list = None
    ) -> Optional[Path]:
        """Create visualization for a single floor.

        Args:
            floor: Floor object
            access_points: List of access points on this floor
            radios: List of Radio objects (optional) for mounting type and azimuth

        Returns:
            Path to generated image file or None if failed
        """
        # Get floor plan image with coordinate scale factors
        result = self._get_floor_plan_image(floor)
        if result is None:
            return None

        image, scale_x, scale_y = result

        # Convert to RGBA for transparency support
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # Calculate adaptive marker sizes based on image dimensions
        adaptive_sizes = self._calculate_adaptive_sizes(image.width, image.height)

        # Create adaptive font based on calculated font size
        adaptive_font = None
        try:
            font_names = [
                "arial.ttf",
                "Arial.ttf",
                "DejaVuSans.ttf",
                "LiberationSans-Regular.ttf",
            ]
            for font_name in font_names:
                try:
                    adaptive_font = ImageFont.truetype(
                        font_name, adaptive_sizes["font_size"]
                    )
                    break
                except (OSError, IOError):
                    continue
            if adaptive_font is None:
                adaptive_font = ImageFont.load_default()
        except Exception as e:
            logger.debug(f"Error loading adaptive font: {e}")
            adaptive_font = self.font  # Fallback to default font

        # Create a transparent overlay for AP markers (for proper alpha blending)
        overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        # Filter APs for this floor
        floor_aps = [ap for ap in access_points if ap.floor_id == floor.id]

        logger.info(f"Drawing {len(floor_aps)} APs on floor: {floor.name}")

        # Create AP -> Radio mapping for quick lookup
        ap_radio_map = {}
        if radios:
            for radio in radios:
                if radio.access_point_id not in ap_radio_map:
                    ap_radio_map[radio.access_point_id] = []
                ap_radio_map[radio.access_point_id].append(radio)

        # Collect arrow data to draw later (after compositing)
        arrows_to_draw = []

        # Draw each AP on the overlay
        for ap in floor_aps:
            if ap.location_x is None or ap.location_y is None:
                logger.warning(f"AP {ap.name} has no location, skipping")
                continue

            # Scale coordinates from floor plan dimensions to actual image dimensions
            x, y = ap.location_x * scale_x, ap.location_y * scale_y

            # Determine AP color with configured opacity
            opacity_value = int(255 * self.ap_opacity)  # Convert 0.0-1.0 to 0-255

            if ap.color:
                rgb = self._hex_to_rgb(ap.color)
                fill_color = (*rgb, opacity_value)  # Apply configured opacity
            else:
                # Default color: pale blue with configured opacity
                fill_color = (
                    173,
                    216,
                    230,
                    opacity_value,
                )  # Light blue with configured opacity

            # Get mounting type and azimuth from radios
            mounting_type = "CEILING"  # default
            azimuth = 0.0  # default

            if ap.id in ap_radio_map:
                # Use first radio's mounting data
                first_radio = ap_radio_map[ap.id][0]
                if first_radio.antenna_mounting:
                    mounting_type = first_radio.antenna_mounting
                if first_radio.antenna_direction is not None:
                    azimuth = first_radio.antenna_direction

            # Collect arrow data if needed
            # For WALL mounted APs, always show arrow (even for azimuth=0 which means North)
            # For other types, only show if azimuth is non-zero
            show_arrow = self.show_azimuth_arrows and (
                mounting_type == "WALL" or abs(azimuth) > 0.01
            )

            if show_arrow:
                logger.debug(
                    f"Will draw arrow for AP {ap.name}: azimuth={azimuth}°, mounting={mounting_type}"
                )
                # Store arrow data for later drawing (include ap_id for Wi-Fi standard detection)
                arrows_to_draw.append(
                    {
                        "x": x,
                        "y": y,
                        "azimuth": azimuth,
                        "fill_color": fill_color,
                        "ap_id": ap.id,  # For radio lookup
                        "ap_name": ap.name,
                        "ap_model": ap.model,
                        "ap_vendor": ap.vendor,
                        "mounting_type": mounting_type,
                        "adaptive_radius": adaptive_sizes[
                            "radius"
                        ],  # For arrow scaling
                    }
                )

            # Draw AP marker on overlay for proper transparency (without arrows)
            self._draw_ap_marker(
                overlay_draw,
                x,
                y,
                fill_color,
                mounting_type=mounting_type,
                azimuth=azimuth,
                adaptive_sizes=adaptive_sizes,
            )

        # Composite the overlay onto the base image
        # Note: Fill colors have opacity applied, borders are fully opaque for clarity
        image = Image.alpha_composite(image, overlay)

        logger.info(f"After composite, image mode: {image.mode}")

        # Now create a new draw context for text labels and arrows (after compositing)
        draw = ImageDraw.Draw(image)

        # Draw arrows on the final image (after compositing for better visibility)
        logger.info(f"Drawing {len(arrows_to_draw)} arrows on final image")
        for arrow_data in arrows_to_draw:
            x = arrow_data["x"]
            y = arrow_data["y"]
            azimuth = arrow_data["azimuth"]
            fill_color = arrow_data["fill_color"]
            ap_model = arrow_data.get("ap_model", "")
            mounting_type = arrow_data.get("mounting_type", "CEILING")

            # Determine Wi-Fi standard from radio data (prioritize 5GHz, fallback to 2.4GHz)
            ap_id = arrow_data.get("ap_id")
            wifi_standard = "802.11n"  # Default
            arrow_color = (255, 0, 255, 255)  # Default: Magenta

            if ap_id and ap_id in ap_radio_map:
                ap_radios = ap_radio_map[ap_id]

                # Prioritize 5GHz radio
                selected_radio = None
                for radio in ap_radios:
                    if radio.frequency_band and "5" in radio.frequency_band:
                        selected_radio = radio
                        break

                # Fallback to 2.4GHz if no 5GHz found
                if not selected_radio and ap_radios:
                    selected_radio = ap_radios[0]

                # Get Wi-Fi standard from selected radio
                if selected_radio and selected_radio.standard:
                    wifi_standard = selected_radio.standard

                    # Determine arrow color by Wi-Fi standard
                    if "be" in wifi_standard.lower():  # 802.11be (Wi-Fi 7)
                        arrow_color = (255, 165, 0, 255)  # Orange
                    elif "ax" in wifi_standard.lower():  # 802.11ax (Wi-Fi 6/6E)
                        arrow_color = (0, 255, 255, 255)  # Cyan
                    elif "ac" in wifi_standard.lower():  # 802.11ac (Wi-Fi 5)
                        arrow_color = (255, 0, 255, 255)  # Magenta
                    else:  # 802.11n and older
                        arrow_color = (255, 0, 255, 255)  # Magenta

            # Get adaptive radius for this AP (scales with image size and --ap-circle-radius)
            adaptive_radius = arrow_data.get("adaptive_radius", self.ap_circle_radius)

            # Adjust arrow length based on mounting type (using adaptive radius for scaling)
            if mounting_type == "WALL":
                # For rectangles, make arrow length similar to the long side (2 * radius)
                arrow_length = adaptive_radius * 2
            else:
                arrow_length = adaptive_radius * 2.5

            logger.debug(
                f"Drawing arrow at ({x}, {y}) with azimuth={azimuth}°, standard={wifi_standard}, "
                f"arrow_length={arrow_length:.1f}px (adaptive_radius={adaptive_radius}px)"
            )
            self._draw_azimuth_arrow(
                draw, x, y, azimuth, arrow_color, arrow_length=arrow_length
            )

        # Draw notes on the floor plan (after arrows, before AP names)
        # Order: cable notes (polylines) → picture notes (markers) → text notes (labels)
        self._draw_cable_notes(draw, floor.id, scale_x, scale_y, adaptive_sizes)
        self._draw_picture_notes(draw, floor.id, scale_x, scale_y, adaptive_sizes)
        self._draw_text_notes(
            draw, floor.id, scale_x, scale_y, adaptive_font, adaptive_sizes
        )

        # Draw AP names on top of the composited image
        for ap in floor_aps:
            if ap.location_x is None or ap.location_y is None:
                continue

            # Scale coordinates from floor plan dimensions to actual image dimensions
            x, y = ap.location_x * scale_x, ap.location_y * scale_y

            # Draw AP name if enabled
            if self.show_ap_names and adaptive_font:
                # Position text to the right of the circle (using adaptive radius)
                text_offset = max(5, int(adaptive_sizes["radius"] * 0.3))
                text_x = x + adaptive_sizes["radius"] + text_offset
                text_y = y - adaptive_sizes["font_size"] // 2

                # Draw text with white outline for better visibility
                outline_color = (255, 255, 255)  # White outline
                text_color = (0, 0, 0)  # Black text

                # Outline width (scaled with font size, but keep it small)
                outline_width = max(1, int(adaptive_sizes["font_size"] * 0.08))

                # Draw outline by rendering text in 8 directions
                for dx in [-outline_width, 0, outline_width]:
                    for dy in [-outline_width, 0, outline_width]:
                        if dx == 0 and dy == 0:
                            continue  # Skip center (will draw main text there)
                        draw.text(
                            (text_x + dx, text_y + dy),
                            ap.name,
                            font=adaptive_font,
                            fill=outline_color,
                        )

                # Main text on top
                draw.text(
                    (text_x, text_y), ap.name, font=adaptive_font, fill=text_color
                )

        # Draw legend (returns new image with legend)
        # TEMPORARILY DISABLED FOR DEBUGGING
        # image = self._draw_legend(image, floor_aps)

        # Save image
        floor_name = floor.name.replace("/", "_").replace("\\", "_")
        output_filename = f"{floor_name}_visualization.png"
        output_path = self.output_dir / output_filename

        logger.info(f"Final image mode before save: {image.mode}")
        image.save(output_path, "PNG")
        logger.info(f"Saved floor plan visualization: {output_path}")

        return output_path

    def visualize_all_floors(
        self,
        floors: dict[str, Floor],
        access_points: list[AccessPoint],
        radios: list = None,
    ) -> list[Path]:
        """Create visualizations for all floors with APs.

        Args:
            floors: Dictionary mapping floor IDs to Floor objects
            access_points: List of all access points in project
            radios: List of Radio objects (optional) for mounting type and azimuth

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
            output_path = self.visualize_floor(floor, access_points, radios)

            if output_path:
                output_files.append(output_path)

        logger.info(f"Generated {len(output_files)} floor plan visualizations")
        return output_files

    def close(self):
        """Close the .esx archive."""
        if hasattr(self, "archive"):
            self.archive.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
