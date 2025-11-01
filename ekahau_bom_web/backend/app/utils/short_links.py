"""Short link generation utilities."""

from __future__ import annotations

import secrets
import string
from datetime import UTC, datetime, timedelta


def generate_short_link(length: int = 8) -> str:
    """Generate a random short link.

    Args:
        length: Length of the short link (default: 8)

    Returns:
        Random alphanumeric string suitable for use as a short link
    """
    # Use URL-safe characters: lowercase, uppercase, digits
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def calculate_expiry_date(days: int = 30) -> datetime:
    """Calculate expiry date for short link.

    Args:
        days: Number of days until expiry (default: 30)

    Returns:
        datetime object representing the expiry date (UTC)
    """
    return datetime.now(UTC) + timedelta(days=days)


def is_link_expired(expiry_date: datetime | None) -> bool:
    """Check if a short link has expired.

    Args:
        expiry_date: The expiry datetime (None means never expires)

    Returns:
        True if the link has expired, False otherwise
    """
    if expiry_date is None:
        return False

    # Ensure we're comparing timezone-aware datetimes
    now = datetime.now(UTC)

    # If expiry_date is naive, assume it's UTC
    if expiry_date.tzinfo is None:
        expiry_date = expiry_date.replace(tzinfo=UTC)

    return now > expiry_date
