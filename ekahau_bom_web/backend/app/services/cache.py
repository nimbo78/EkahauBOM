"""Cache Service - In-memory caching with TTL for API responses."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any, Callable, Optional
from uuid import UUID

from cachetools import TTLCache

logger = logging.getLogger(__name__)


class CacheService:
    """Service for managing in-memory TTL cache for API responses.

    Implements caching for expensive API calls with automatic expiration.
    Thread-safe with RLock for concurrent access.
    """

    def __init__(self):
        # Cache for projects list (5 min TTL, max 1 item)
        self.projects_cache = TTLCache(maxsize=1, ttl=300)  # 5 minutes
        self.projects_lock = RLock()

        # Cache for individual project details (10 min TTL, max 100 projects)
        self.project_details_cache = TTLCache(maxsize=100, ttl=600)  # 10 minutes
        self.project_details_lock = RLock()

        # Cache for reports list (15 min TTL, max 100 projects)
        self.reports_cache = TTLCache(maxsize=100, ttl=900)  # 15 minutes
        self.reports_lock = RLock()

        # Cache for stats (5 min TTL, max 1 item)
        self.stats_cache = TTLCache(maxsize=1, ttl=300)  # 5 minutes
        self.stats_lock = RLock()

        logger.info("CacheService initialized with TTL caches")

    def get_projects(self) -> Optional[list]:
        """Get cached projects list.

        Returns:
            Cached projects list or None if not cached/expired
        """
        with self.projects_lock:
            return self.projects_cache.get("all_projects")

    def set_projects(self, projects: list) -> None:
        """Cache projects list.

        Args:
            projects: List of projects to cache
        """
        with self.projects_lock:
            self.projects_cache["all_projects"] = projects
            logger.debug(f"Cached {len(projects)} projects (TTL: 5 min)")

    def get_project_details(self, project_id: UUID) -> Optional[dict]:
        """Get cached project details.

        Args:
            project_id: Project UUID

        Returns:
            Cached project details or None if not cached/expired
        """
        with self.project_details_lock:
            return self.project_details_cache.get(str(project_id))

    def set_project_details(self, project_id: UUID, details: dict) -> None:
        """Cache project details.

        Args:
            project_id: Project UUID
            details: Project details to cache
        """
        with self.project_details_lock:
            self.project_details_cache[str(project_id)] = details
            logger.debug(f"Cached project {project_id} details (TTL: 10 min)")

    def get_reports(self, project_id: UUID) -> Optional[dict]:
        """Get cached reports list.

        Args:
            project_id: Project UUID

        Returns:
            Cached reports list or None if not cached/expired
        """
        with self.reports_lock:
            return self.reports_cache.get(str(project_id))

    def set_reports(self, project_id: UUID, reports: dict) -> None:
        """Cache reports list.

        Args:
            project_id: Project UUID
            reports: Reports data to cache
        """
        with self.reports_lock:
            self.reports_cache[str(project_id)] = reports
            logger.debug(f"Cached project {project_id} reports (TTL: 15 min)")

    def get_stats(self) -> Optional[dict]:
        """Get cached stats.

        Returns:
            Cached stats or None if not cached/expired
        """
        with self.stats_lock:
            return self.stats_cache.get("stats")

    def set_stats(self, stats: dict) -> None:
        """Cache stats.

        Args:
            stats: Stats data to cache
        """
        with self.stats_lock:
            self.stats_cache["stats"] = stats
            logger.debug("Cached stats (TTL: 5 min)")

    # Cache invalidation methods

    def invalidate_project(self, project_id: UUID) -> None:
        """Invalidate all caches related to a specific project.

        Called when project is updated, processed, or deleted.

        Args:
            project_id: Project UUID
        """
        # Invalidate project details
        with self.project_details_lock:
            self.project_details_cache.pop(str(project_id), None)

        # Invalidate reports
        with self.reports_lock:
            self.reports_cache.pop(str(project_id), None)

        # Invalidate projects list (since it includes this project)
        self.invalidate_projects_list()

        logger.info(f"Invalidated cache for project {project_id}")

    def invalidate_projects_list(self) -> None:
        """Invalidate projects list cache.

        Called when any project is created, updated, or deleted.
        """
        with self.projects_lock:
            self.projects_cache.pop("all_projects", None)

        # Also invalidate stats since they depend on projects list
        with self.stats_lock:
            self.stats_cache.pop("stats", None)

        logger.debug("Invalidated projects list and stats cache")

    def invalidate_all(self) -> None:
        """Clear all caches.

        Use sparingly - only for major system changes.
        """
        with self.projects_lock:
            self.projects_cache.clear()

        with self.project_details_lock:
            self.project_details_cache.clear()

        with self.reports_lock:
            self.reports_cache.clear()

        with self.stats_lock:
            self.stats_cache.clear()

        logger.info("Cleared all caches")

    def get_cache_stats(self) -> dict:
        """Get cache statistics for monitoring.

        Returns:
            Dictionary with cache sizes and hit rates
        """
        with self.projects_lock:
            projects_size = len(self.projects_cache)

        with self.project_details_lock:
            project_details_size = len(self.project_details_cache)

        with self.reports_lock:
            reports_size = len(self.reports_cache)

        with self.stats_lock:
            stats_size = len(self.stats_cache)

        return {
            "projects_cache": {
                "size": projects_size,
                "maxsize": self.projects_cache.maxsize,
                "ttl": 300,
            },
            "project_details_cache": {
                "size": project_details_size,
                "maxsize": self.project_details_cache.maxsize,
                "ttl": 600,
            },
            "reports_cache": {
                "size": reports_size,
                "maxsize": self.reports_cache.maxsize,
                "ttl": 900,
            },
            "stats_cache": {
                "size": stats_size,
                "maxsize": self.stats_cache.maxsize,
                "ttl": 300,
            },
        }


# Global cache service instance
cache_service = CacheService()
