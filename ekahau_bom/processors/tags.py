#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Processor for tags data from Ekahau projects."""

import logging
from typing import Any

from ..models import Tag, TagKey

logger = logging.getLogger(__name__)


class TagProcessor:
    """Process tags data from Ekahau project.

    Tags are key-value pairs that can be applied to access points for
    categorization and filtering. Introduced in Ekahau v10.2+.
    """

    def __init__(self, tag_keys_data: dict[str, Any]):
        """Initialize processor with tag keys data.

        Args:
            tag_keys_data: Raw tag keys data from tagKeys.json
        """
        self.tag_keys: list[TagKey] = []
        self.tag_keys_map: dict[str, str] = {}

        # Parse tag keys
        for tag_key_data in tag_keys_data.get("tagKeys", []):
            # Skip malformed entries
            if not isinstance(tag_key_data, dict):
                logger.warning(f"Skipping malformed tag key data: {tag_key_data}")
                continue

            tag_key = TagKey(id=tag_key_data.get("id", ""), key=tag_key_data.get("key", "Unknown"))
            self.tag_keys.append(tag_key)
            self.tag_keys_map[tag_key.id] = tag_key.key

        logger.info(f"Loaded {len(self.tag_keys)} tag key definitions")

    def process_ap_tags(self, ap_tags: list[dict[str, Any]]) -> list[Tag]:
        """Convert raw AP tags to Tag objects.

        Args:
            ap_tags: List of tag dictionaries from accessPoints.json

        Returns:
            List of Tag objects
        """
        tags = []

        for tag_data in ap_tags:
            tag_key_id = tag_data.get("tagKeyId", "")
            value = tag_data.get("value", "")

            # Look up the tag key name
            key = self.tag_keys_map.get(tag_key_id, "Unknown")

            if key == "Unknown":
                logger.debug(f"Unknown tag key ID: {tag_key_id}")

            tag = Tag(key=key, value=value, tag_key_id=tag_key_id)
            tags.append(tag)

        return tags

    def get_tag_key_names(self) -> list[str]:
        """Get list of all available tag key names.

        Returns:
            List of tag key names (e.g., ["Location", "Zone", "Building"])
        """
        return [tk.key for tk in self.tag_keys]

    def has_tag_key(self, tag_key_name: str) -> bool:
        """Check if a specific tag key exists in the project.

        Args:
            tag_key_name: Name of the tag key to check

        Returns:
            True if tag key exists
        """
        return tag_key_name in [tk.key for tk in self.tag_keys]
