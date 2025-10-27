#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for CableAnalytics."""

from __future__ import annotations


import pytest
import math
from ekahau_bom.cable_analytics import CableAnalytics, CableMetrics
from ekahau_bom.models import CableNote, Point, Floor


class TestCableAnalytics:
    """Test suite for CableAnalytics."""

    @pytest.fixture
    def sample_floors(self):
        """Create sample floors dictionary."""
        return {
            "floor1": Floor(id="floor1", name="Floor 1"),
            "floor2": Floor(id="floor2", name="Floor 2"),
        }

    def test_calculate_cable_length_empty(self):
        """Test cable length calculation with no points."""
        cable = CableNote(id="cable1", points=[])
        length = CableAnalytics.calculate_cable_length(cable)
        assert length == 0.0

    def test_calculate_cable_length_single_point(self):
        """Test cable length calculation with single point."""
        cable = CableNote(id="cable1", points=[Point(x=100.0, y=200.0)])
        length = CableAnalytics.calculate_cable_length(cable)
        assert length == 0.0

    def test_calculate_cable_length_two_points(self):
        """Test cable length calculation with two points."""
        cable = CableNote(
            id="cable1",
            points=[Point(x=0.0, y=0.0), Point(x=3.0, y=4.0)],  # 3-4-5 right triangle
        )
        length = CableAnalytics.calculate_cable_length(cable)
        assert length == 5.0

    def test_calculate_cable_length_horizontal_line(self):
        """Test cable length for horizontal line."""
        cable = CableNote(id="cable1", points=[Point(x=0.0, y=0.0), Point(x=100.0, y=0.0)])
        length = CableAnalytics.calculate_cable_length(cable)
        assert length == 100.0

    def test_calculate_cable_length_vertical_line(self):
        """Test cable length for vertical line."""
        cable = CableNote(id="cable1", points=[Point(x=0.0, y=0.0), Point(x=0.0, y=100.0)])
        length = CableAnalytics.calculate_cable_length(cable)
        assert length == 100.0

    def test_calculate_cable_length_multiple_segments(self):
        """Test cable length with multiple segments."""
        cable = CableNote(
            id="cable1",
            points=[
                Point(x=0.0, y=0.0),
                Point(x=10.0, y=0.0),  # 10 units
                Point(x=10.0, y=10.0),  # 10 units
                Point(x=0.0, y=10.0),  # 10 units
            ],
        )
        length = CableAnalytics.calculate_cable_length(cable)
        assert length == 30.0

    def test_calculate_cable_length_diagonal(self):
        """Test cable length with diagonal segment."""
        cable = CableNote(
            id="cable1",
            points=[
                Point(x=0.0, y=0.0),
                Point(x=10.0, y=10.0),
            ],  # sqrt(200) = 14.142...
        )
        length = CableAnalytics.calculate_cable_length(cable)
        expected = math.sqrt(200)
        assert abs(length - expected) < 0.001

    def test_calculate_cable_metrics_empty(self, sample_floors):
        """Test cable metrics with no cables."""
        metrics = CableAnalytics.calculate_cable_metrics([], sample_floors)
        assert metrics.total_cables == 0
        assert metrics.total_length == 0.0
        assert metrics.avg_length == 0.0

    def test_calculate_cable_metrics_single_cable(self, sample_floors):
        """Test cable metrics with single cable."""
        cables = [
            CableNote(
                id="cable1",
                floor_plan_id="floor1",
                points=[Point(x=0.0, y=0.0), Point(x=100.0, y=0.0)],
            )
        ]
        metrics = CableAnalytics.calculate_cable_metrics(cables, sample_floors)

        assert metrics.total_cables == 1
        assert metrics.total_length == 100.0
        assert metrics.avg_length == 100.0
        assert metrics.min_length == 100.0
        assert metrics.max_length == 100.0
        assert metrics.cables_by_floor == {"Floor 1": 1}
        assert metrics.length_by_floor["Floor 1"] == 100.0

    def test_calculate_cable_metrics_multiple_cables(self, sample_floors):
        """Test cable metrics with multiple cables."""
        cables = [
            CableNote(
                id="cable1",
                floor_plan_id="floor1",
                points=[Point(x=0.0, y=0.0), Point(x=50.0, y=0.0)],
            ),
            CableNote(
                id="cable2",
                floor_plan_id="floor1",
                points=[Point(x=0.0, y=0.0), Point(x=100.0, y=0.0)],
            ),
            CableNote(
                id="cable3",
                floor_plan_id="floor2",
                points=[Point(x=0.0, y=0.0), Point(x=75.0, y=0.0)],
            ),
        ]
        metrics = CableAnalytics.calculate_cable_metrics(cables, sample_floors)

        assert metrics.total_cables == 3
        assert metrics.total_length == 225.0  # 50 + 100 + 75
        assert metrics.avg_length == 75.0
        assert metrics.min_length == 50.0
        assert metrics.max_length == 100.0
        assert metrics.cables_by_floor == {"Floor 1": 2, "Floor 2": 1}
        assert metrics.length_by_floor["Floor 1"] == 150.0
        assert metrics.length_by_floor["Floor 2"] == 75.0

    def test_calculate_cable_metrics_with_scale_factor(self, sample_floors):
        """Test cable metrics with scale factor conversion."""
        cables = [
            CableNote(
                id="cable1",
                floor_plan_id="floor1",
                points=[Point(x=0.0, y=0.0), Point(x=100.0, y=0.0)],
            )
        ]
        # Scale factor: 10 units = 1 meter
        metrics = CableAnalytics.calculate_cable_metrics(cables, sample_floors, scale_factor=10.0)

        assert metrics.total_length == 100.0
        assert metrics.total_length_m == 10.0  # 100 / 10
        assert metrics.scale_factor == 10.0

    def test_estimate_cable_cost_no_meters(self):
        """Test cable cost estimation without meters."""
        metrics = CableMetrics(total_cables=10, total_length=1000.0, total_length_m=None)
        cost = CableAnalytics.estimate_cable_cost(metrics)

        assert cost["cable_material"] == 0.0
        assert cost["installation"] == 0.0
        assert cost["total"] == 0.0

    def test_estimate_cable_cost_with_defaults(self):
        """Test cable cost estimation with default prices."""
        metrics = CableMetrics(total_cables=1, total_length=100.0, total_length_m=10.0)
        cost = CableAnalytics.estimate_cable_cost(metrics)

        # Default: $2/m cable, $5/m installation, 1.2x overage
        expected_cable = 10.0 * 1.2 * 2.0  # 24.0
        expected_install = 10.0 * 5.0  # 50.0
        expected_total = expected_cable + expected_install  # 74.0

        assert cost["cable_material"] == expected_cable
        assert cost["installation"] == expected_install
        assert cost["total"] == expected_total
        assert cost["length_meters"] == 10.0
        assert cost["effective_length_meters"] == 12.0
        assert cost["overage_factor"] == 1.2

    def test_estimate_cable_cost_custom_prices(self):
        """Test cable cost estimation with custom prices."""
        metrics = CableMetrics(total_cables=1, total_length=100.0, total_length_m=10.0)
        cost = CableAnalytics.estimate_cable_cost(
            metrics,
            cost_per_meter=3.0,
            installation_cost_per_meter=10.0,
            overage_factor=1.5,
        )

        expected_cable = 10.0 * 1.5 * 3.0  # 45.0
        expected_install = 10.0 * 10.0  # 100.0
        expected_total = 145.0

        assert cost["cable_material"] == expected_cable
        assert cost["installation"] == expected_install
        assert cost["total"] == expected_total

    def test_generate_cable_bom_no_meters(self):
        """Test BOM generation without length in meters."""
        metrics = CableMetrics(total_cables=5, total_length=500.0, total_length_m=None)
        bom = CableAnalytics.generate_cable_bom(metrics)

        # Should have connectors and routes, but no cable length
        assert len(bom) == 2
        assert any(item["description"] == "RJ45 Connectors" for item in bom)
        assert any(item["description"] == "Cable Routes/Runs" for item in bom)

        connector_item = next(item for item in bom if "Connectors" in item["description"])
        assert connector_item["quantity"] == 10  # 5 cables * 2 connectors
        assert connector_item["unit"] == "pieces"

    def test_generate_cable_bom_with_meters(self):
        """Test BOM generation with length in meters."""
        metrics = CableMetrics(total_cables=5, total_length=500.0, total_length_m=50.5)
        bom = CableAnalytics.generate_cable_bom(metrics, cable_type="Cat6A UTP")

        assert len(bom) == 3  # Cable length + connectors + routes

        cable_item = next(item for item in bom if "Cable" in item["description"])
        assert cable_item["quantity"] == 51  # Rounded up from 50.5
        assert cable_item["unit"] == "meters"
        assert "Cat6A UTP" in cable_item["description"]

    def test_generate_cable_bom_custom_connector_count(self):
        """Test BOM generation with custom connector count."""
        metrics = CableMetrics(total_cables=3, total_length=300.0, total_length_m=30.0)
        bom = CableAnalytics.generate_cable_bom(
            metrics, connector_type="GG45", connectors_per_cable=4
        )

        connector_item = next(item for item in bom if "Connectors" in item["description"])
        assert connector_item["quantity"] == 12  # 3 cables * 4 connectors
        assert "GG45" in connector_item["description"]

    def test_cable_metrics_dataclass(self):
        """Test CableMetrics dataclass initialization."""
        metrics = CableMetrics(total_cables=10, total_length=1000.0, avg_length=100.0)

        assert metrics.total_cables == 10
        assert metrics.total_length == 1000.0
        assert metrics.avg_length == 100.0
        assert metrics.total_length_m is None
        assert metrics.cables_by_floor == {}
