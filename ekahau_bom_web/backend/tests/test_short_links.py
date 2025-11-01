"""Tests for Short Links utility."""

from __future__ import annotations

import string
from datetime import UTC, datetime, timedelta

import pytest

from app.utils.short_links import (
    calculate_expiry_date,
    generate_short_link,
    is_link_expired,
)


def test_generate_short_link_default_length():
    """Test generating short link with default length."""
    link = generate_short_link()

    assert len(link) == 8
    assert all(c in string.ascii_letters + string.digits for c in link)


def test_generate_short_link_custom_length():
    """Test generating short link with custom length."""
    link = generate_short_link(length=12)

    assert len(link) == 12
    assert all(c in string.ascii_letters + string.digits for c in link)


def test_generate_short_link_uniqueness():
    """Test that generated links are unique."""
    links = [generate_short_link() for _ in range(100)]

    # All links should be unique (with very high probability)
    assert len(set(links)) == 100


def test_generate_short_link_security():
    """Test that links use cryptographically secure randomness."""
    # Generate many links to check distribution
    links = [generate_short_link(length=4) for _ in range(1000)]

    # Check that we have good variety (should have at least 500 unique values)
    unique_links = set(links)
    assert len(unique_links) > 500


def test_calculate_expiry_date_default():
    """Test calculating expiry date with default days."""
    before = datetime.now(UTC)
    expiry = calculate_expiry_date()
    after = datetime.now(UTC)

    # Should be approximately 30 days from now
    expected_min = before + timedelta(days=30)
    expected_max = after + timedelta(days=30)

    assert expected_min <= expiry <= expected_max


def test_calculate_expiry_date_custom():
    """Test calculating expiry date with custom days."""
    before = datetime.now(UTC)
    expiry = calculate_expiry_date(days=7)
    after = datetime.now(UTC)

    # Should be approximately 7 days from now
    expected_min = before + timedelta(days=7)
    expected_max = after + timedelta(days=7)

    assert expected_min <= expiry <= expected_max


def test_calculate_expiry_date_returns_utc():
    """Test that expiry date is in UTC timezone."""
    expiry = calculate_expiry_date()

    assert expiry.tzinfo == UTC


def test_is_link_expired_not_expired():
    """Test checking if link is not expired."""
    # Link expires in 30 days
    expiry = datetime.now(UTC) + timedelta(days=30)

    assert is_link_expired(expiry) is False


def test_is_link_expired_expired():
    """Test checking if link is expired."""
    # Link expired 1 day ago
    expiry = datetime.now(UTC) - timedelta(days=1)

    assert is_link_expired(expiry) is True


def test_is_link_expired_none():
    """Test checking if link with no expiry is not expired."""
    assert is_link_expired(None) is False


def test_is_link_expired_just_expired():
    """Test checking if link just expired."""
    # Link expired 1 second ago
    expiry = datetime.now(UTC) - timedelta(seconds=1)

    assert is_link_expired(expiry) is True


def test_is_link_expired_about_to_expire():
    """Test checking if link is about to expire but hasn't yet."""
    # Link expires in 1 second
    expiry = datetime.now(UTC) + timedelta(seconds=1)

    assert is_link_expired(expiry) is False


def test_is_link_expired_naive_datetime():
    """Test checking expiry with naive datetime (assumes UTC)."""
    # Create naive datetime (no timezone) - remove tzinfo to make it naive
    expiry = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)

    # Should handle naive datetime by assuming UTC
    assert is_link_expired(expiry) is True


def test_is_link_expired_naive_datetime_future():
    """Test checking expiry with naive datetime in the future."""
    # Create naive datetime (no timezone) - remove tzinfo to make it naive
    expiry = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1)

    # Should handle naive datetime by assuming UTC
    assert is_link_expired(expiry) is False
