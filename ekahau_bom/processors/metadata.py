#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Processor for project metadata."""

from __future__ import annotations


import logging
from typing import Any

from ..models import ProjectMetadata

logger = logging.getLogger(__name__)


class ProjectMetadataProcessor:
    """Process project metadata from Ekahau project."""

    def process(self, metadata_data: dict[str, Any]) -> ProjectMetadata:
        """Process raw project metadata into ProjectMetadata object.

        Args:
            metadata_data: Raw project metadata from parser

        Returns:
            ProjectMetadata object
        """
        if not metadata_data:
            logger.info("No project metadata found, returning empty metadata")
            return ProjectMetadata()

        metadata = ProjectMetadata(
            name=metadata_data.get("name", ""),
            title=metadata_data.get("title", ""),
            customer=metadata_data.get("customer", ""),
            location=metadata_data.get("location", ""),
            responsible_person=metadata_data.get("responsiblePerson", ""),
            schema_version=metadata_data.get("schemaVersion", ""),
            note_ids=metadata_data.get("noteIds", []),
            project_ancestors=metadata_data.get("projectAncestors", []),
        )

        logger.info(f"Processed project metadata: {metadata.name or 'Unnamed'}")
        if metadata.customer:
            logger.info(f"  Customer: {metadata.customer}")
        if metadata.location:
            logger.info(f"  Location: {metadata.location}")
        if metadata.responsible_person:
            logger.info(f"  Responsible: {metadata.responsible_person}")

        return metadata
