"""
Thumbnail generation utility for floor plan visualizations.

Generates small (200x150) and medium (800x600) thumbnails from PNG images
to optimize loading times in the frontend.
"""

from pathlib import Path
from typing import Literal, Optional
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# Thumbnail sizes
THUMBNAIL_SIZES = {
    "small": (200, 150),  # For preview/list views
    "medium": (800, 600),  # For modal/detail views
}

ThumbnailSize = Literal["small", "medium"]


def generate_thumbnail(
    image_path: Path, output_path: Path, size: ThumbnailSize = "small", quality: int = 85
) -> None:
    """
    Generate a thumbnail from an image file.

    Args:
        image_path: Path to the original image
        output_path: Path where thumbnail will be saved
        size: Thumbnail size ('small' or 'medium')
        quality: JPEG quality (1-100), default 85

    Raises:
        FileNotFoundError: If image_path does not exist
        ValueError: If size is invalid
        PIL.UnidentifiedImageError: If image cannot be opened
    """
    if size not in THUMBNAIL_SIZES:
        raise ValueError(f"Invalid size '{size}'. Must be one of: {list(THUMBNAIL_SIZES.keys())}")

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    try:
        # Open image
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (handles RGBA, palette modes, etc.)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Get target size
            target_size = THUMBNAIL_SIZES[size]

            # Create thumbnail maintaining aspect ratio
            img.thumbnail(target_size, Image.Resampling.LANCZOS)

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save thumbnail
            img.save(output_path, "PNG", optimize=True, quality=quality)

            logger.info(
                f"Generated {size} thumbnail: {output_path.name} ({img.size[0]}x{img.size[1]})"
            )

    except Exception as e:
        logger.error(f"Failed to generate thumbnail for {image_path.name}: {e}")
        raise


def generate_all_thumbnails(image_path: Path, thumbs_dir: Path) -> dict[ThumbnailSize, Path]:
    """
    Generate all thumbnail sizes for an image.

    Args:
        image_path: Path to the original image
        thumbs_dir: Directory where thumbnails will be saved

    Returns:
        Dictionary mapping size names to thumbnail paths

    Example:
        >>> thumbs = generate_all_thumbnails(
        ...     Path("visualizations/floor1.png"),
        ...     Path("visualizations/thumbs")
        ... )
        >>> thumbs
        {'small': Path('visualizations/thumbs/floor1_small.png'),
         'medium': Path('visualizations/thumbs/floor1_medium.png')}
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    thumbnail_paths = {}
    base_name = image_path.stem  # filename without extension

    for size in THUMBNAIL_SIZES.keys():
        thumb_filename = f"{base_name}_{size}.png"
        thumb_path = thumbs_dir / thumb_filename

        try:
            generate_thumbnail(image_path, thumb_path, size=size)
            thumbnail_paths[size] = thumb_path
        except Exception as e:
            logger.error(f"Failed to generate {size} thumbnail for {image_path.name}: {e}")
            # Continue generating other sizes even if one fails

    return thumbnail_paths


def get_thumbnail_path(
    original_path: Path, size: ThumbnailSize, thumbs_dir: Optional[Path] = None
) -> Path:
    """
    Get the expected path for a thumbnail.

    Args:
        original_path: Path to the original image
        size: Thumbnail size
        thumbs_dir: Directory where thumbnails are stored.
                   If None, uses 'thumbs' subdirectory next to original

    Returns:
        Path to the thumbnail file

    Example:
        >>> get_thumbnail_path(
        ...     Path("projects/abc/visualizations/floor1.png"),
        ...     "small"
        ... )
        Path('projects/abc/visualizations/thumbs/floor1_small.png')
    """
    if size not in THUMBNAIL_SIZES:
        raise ValueError(f"Invalid size '{size}'. Must be one of: {list(THUMBNAIL_SIZES.keys())}")

    if thumbs_dir is None:
        thumbs_dir = original_path.parent / "thumbs"

    base_name = original_path.stem
    thumb_filename = f"{base_name}_{size}.png"

    return thumbs_dir / thumb_filename


def thumbnail_exists(original_path: Path, size: ThumbnailSize) -> bool:
    """
    Check if a thumbnail already exists for an image.

    Args:
        original_path: Path to the original image
        size: Thumbnail size to check

    Returns:
        True if thumbnail exists, False otherwise
    """
    thumb_path = get_thumbnail_path(original_path, size)
    return thumb_path.exists()
