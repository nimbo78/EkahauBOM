"""ETag utility functions for static file caching."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional


def generate_etag(file_path: Path) -> str:
    """Generate ETag for a file using MD5 hash.

    Args:
        file_path: Path to the file

    Returns:
        ETag string (MD5 hash of file contents)

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    md5_hash = hashlib.md5()

    # Read file in chunks to handle large files efficiently
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5_hash.update(chunk)

    # Return ETag in quoted format (required by HTTP spec)
    return f'"{md5_hash.hexdigest()}"'


def etag_matches(etag: str, if_none_match: Optional[str]) -> bool:
    """Check if ETag matches the If-None-Match header value.

    Args:
        etag: Current ETag value
        if_none_match: If-None-Match header value from request

    Returns:
        True if ETags match (client has fresh copy), False otherwise
    """
    if not if_none_match:
        return False

    # Handle multiple ETags in If-None-Match header
    # e.g., If-None-Match: "abc123", "def456"
    requested_etags = [tag.strip() for tag in if_none_match.split(",")]

    return etag in requested_etags


def should_return_304(etag: str, if_none_match: Optional[str]) -> bool:
    """Determine if should return 304 Not Modified response.

    Args:
        etag: Current ETag value for the file
        if_none_match: If-None-Match header value from request

    Returns:
        True if should return 304 Not Modified, False to return full file
    """
    return etag_matches(etag, if_none_match)
