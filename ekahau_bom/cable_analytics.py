#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Cable analytics and calculations for Ekahau projects."""

import logging
import math
from dataclasses import dataclass, field
from typing import Optional
from collections import Counter

from .models import CableNote, Floor

logger = logging.getLogger(__name__)


@dataclass
class CableMetrics:
    """Metrics for cable infrastructure analysis.

    Attributes:
        total_cables: Total number of cable routes
        total_length: Total cable length in project units (pixels)
        total_length_m: Total cable length in meters (if scale available)
        avg_length: Average cable length
        min_length: Minimum cable length
        max_length: Maximum cable length
        cables_by_floor: Dictionary of cable counts per floor
        length_by_floor: Dictionary of total length per floor
        scale_factor: Scale factor from project units to meters
    """

    total_cables: int = 0
    total_length: float = 0.0
    total_length_m: Optional[float] = None
    avg_length: float = 0.0
    min_length: float = 0.0
    max_length: float = 0.0
    cables_by_floor: dict[str, int] = field(default_factory=dict)
    length_by_floor: dict[str, float] = field(default_factory=dict)
    scale_factor: Optional[float] = None


class CableAnalytics:
    """Analytics for cable infrastructure in Ekahau projects."""

    @staticmethod
    def calculate_cable_length(cable_note: CableNote) -> float:
        """Calculate the total length of a cable route.

        Uses Euclidean distance between consecutive points to calculate
        the total cable length in project units (typically pixels).

        Args:
            cable_note: CableNote with list of coordinate points

        Returns:
            Total cable length in project units
        """
        if not cable_note.points or len(cable_note.points) < 2:
            return 0.0

        total_length = 0.0
        for i in range(len(cable_note.points) - 1):
            p1 = cable_note.points[i]
            p2 = cable_note.points[i + 1]

            # Euclidean distance: sqrt((x2-x1)^2 + (y2-y1)^2)
            distance = math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)
            total_length += distance

        return total_length

    @staticmethod
    def calculate_cable_metrics(
        cable_notes: list[CableNote], floors: dict[str, Floor], scale_factor: Optional[float] = None
    ) -> CableMetrics:
        """Calculate comprehensive cable infrastructure metrics.

        Args:
            cable_notes: List of cable notes from the project
            floors: Dictionary mapping floor IDs to Floor objects
            scale_factor: Optional scale factor to convert project units to meters
                         (e.g., pixels per meter)

        Returns:
            CableMetrics object with all calculated metrics
        """
        if not cable_notes:
            logger.info("No cable notes found, returning empty metrics")
            return CableMetrics()

        # Calculate length for each cable
        cable_lengths = []
        cables_by_floor = Counter()
        length_by_floor = {}

        for cable in cable_notes:
            length = CableAnalytics.calculate_cable_length(cable)
            cable_lengths.append(length)

            # Track by floor
            floor_id = cable.floor_plan_id
            if floor_id:
                floor_name = floors.get(floor_id).name if floor_id in floors else floor_id
                cables_by_floor[floor_name] += 1
                length_by_floor[floor_name] = length_by_floor.get(floor_name, 0.0) + length

        # Calculate aggregate metrics
        total_length = sum(cable_lengths)
        avg_length = total_length / len(cable_lengths) if cable_lengths else 0.0
        min_length = min(cable_lengths) if cable_lengths else 0.0
        max_length = max(cable_lengths) if cable_lengths else 0.0

        # Convert to meters if scale factor provided
        total_length_m = None
        if scale_factor and scale_factor > 0:
            total_length_m = total_length / scale_factor

        metrics = CableMetrics(
            total_cables=len(cable_notes),
            total_length=total_length,
            total_length_m=total_length_m,
            avg_length=avg_length,
            min_length=min_length,
            max_length=max_length,
            cables_by_floor=dict(cables_by_floor),
            length_by_floor=length_by_floor,
            scale_factor=scale_factor,
        )

        logger.info(f"Cable metrics: {len(cable_notes)} cables analyzed")
        logger.info(f"Total cable length: {total_length:.1f} units")
        if total_length_m:
            logger.info(f"Total cable length: {total_length_m:.1f} meters")
        logger.info(f"Average cable length: {avg_length:.1f} units")

        return metrics

    @staticmethod
    def estimate_cable_cost(
        cable_metrics: CableMetrics,
        cost_per_meter: float = 2.0,
        installation_cost_per_meter: float = 5.0,
        overage_factor: float = 1.2,
    ) -> dict[str, float]:
        """Estimate total cable infrastructure cost.

        Args:
            cable_metrics: Calculated cable metrics
            cost_per_meter: Cost of cable per meter (default: $2/m)
            installation_cost_per_meter: Installation labor cost per meter (default: $5/m)
            overage_factor: Factor for cable overage/waste (default: 1.2 = 20% extra)

        Returns:
            Dictionary with cost breakdown:
                - cable_material: Cost of cable material
                - installation: Installation labor cost
                - total: Total estimated cost
        """
        if not cable_metrics.total_length_m:
            logger.warning("Cannot calculate cable cost: no length in meters available")
            return {"cable_material": 0.0, "installation": 0.0, "total": 0.0}

        # Apply overage factor for waste, slack, etc.
        effective_length = cable_metrics.total_length_m * overage_factor

        cable_material_cost = effective_length * cost_per_meter
        installation_cost = cable_metrics.total_length_m * installation_cost_per_meter
        total_cost = cable_material_cost + installation_cost

        logger.info(
            f"Cable cost estimate: ${total_cost:.2f} ({effective_length:.1f}m @ ${cost_per_meter}/m + installation)"
        )

        return {
            "cable_material": cable_material_cost,
            "installation": installation_cost,
            "total": total_cost,
            "length_meters": cable_metrics.total_length_m,
            "effective_length_meters": effective_length,
            "overage_factor": overage_factor,
        }

    @staticmethod
    def generate_cable_bom(
        cable_metrics: CableMetrics,
        cable_type: str = "Cat6A UTP",
        connector_type: str = "RJ45",
        connectors_per_cable: int = 2,
    ) -> list[dict[str, any]]:
        """Generate Bill of Materials for cable infrastructure.

        Args:
            cable_metrics: Calculated cable metrics
            cable_type: Type of cable (default: Cat6A UTP)
            connector_type: Type of connector (default: RJ45)
            connectors_per_cable: Number of connectors per cable route (default: 2)

        Returns:
            List of BOM items with description, quantity, and unit
        """
        bom = []

        if cable_metrics.total_length_m:
            # Cable in meters (rounded up to nearest meter)
            cable_length_rounded = math.ceil(cable_metrics.total_length_m)
            bom.append(
                {
                    "description": f"{cable_type} Network Cable",
                    "quantity": cable_length_rounded,
                    "unit": "meters",
                    "category": "Cable",
                }
            )

        # Connectors
        total_connectors = cable_metrics.total_cables * connectors_per_cable
        bom.append(
            {
                "description": f"{connector_type} Connectors",
                "quantity": total_connectors,
                "unit": "pieces",
                "category": "Connectors",
            }
        )

        # Cable routes (logical count)
        bom.append(
            {
                "description": "Cable Routes/Runs",
                "quantity": cable_metrics.total_cables,
                "unit": "routes",
                "category": "Infrastructure",
            }
        )

        logger.info(f"Generated cable BOM: {len(bom)} items")

        return bom
