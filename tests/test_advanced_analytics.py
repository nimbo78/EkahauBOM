#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for advanced analytics (coverage and mounting)."""

from __future__ import annotations


import pytest
from ekahau_bom.analytics import (
    CoverageAnalytics,
    CoverageMetrics,
    MountingAnalytics,
    MountingMetrics,
)
from ekahau_bom.models import AccessPoint, Tag


@pytest.fixture
def sample_aps_with_mounting():
    """Create sample APs with mounting data."""
    return [
        AccessPoint(
            id="ap1",
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[],
            mine=True,
            floor_id="f1",
            mounting_height=3.0,
            azimuth=45.0,
            tilt=10.0,
        ),
        AccessPoint(
            id="ap2",
            vendor="Cisco",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[],
            mine=True,
            floor_id="f1",
            mounting_height=3.2,
            azimuth=90.0,
            tilt=15.0,
        ),
        AccessPoint(
            id="ap3",
            vendor="Cisco",
            model="AP-635",
            color="Red",
            floor_name="Floor 2",
            tags=[],
            mine=True,
            floor_id="f2",
            mounting_height=2.8,
            azimuth=180.0,
            tilt=5.0,
        ),
        AccessPoint(
            id="ap4",
            vendor="Aruba",
            model="AP-515",
            color="Yellow",
            floor_name="Floor 1",
            tags=[],
            mine=True,
            floor_id="f1",
            mounting_height=None,
            azimuth=None,
            tilt=None,
        ),
        AccessPoint(
            id="ap5",
            vendor="Aruba",
            model="AP-635",
            color="Blue",
            floor_name="Floor 2",
            tags=[],
            mine=True,
            floor_id="f2",
            mounting_height=4.5,
            azimuth=270.0,
            tilt=20.0,
        ),
    ]


@pytest.fixture
def sample_measured_areas():
    """Create sample measured areas data."""
    return {
        "measuredAreas": [
            {
                "id": "area1",
                "name": "Coverage Zone 1",
                "size": 500.0,
                "excluded": False,
            },  # 500 m²
            {
                "id": "area2",
                "name": "Coverage Zone 2",
                "size": 300.0,
                "excluded": False,
            },  # 300 m²
            {
                "id": "area3",
                "name": "Excluded Zone",
                "size": 100.0,
                "excluded": True,
            },  # 100 m²
        ]
    }


class TestCoverageAnalytics:
    """Test CoverageAnalytics class."""

    def test_calculate_coverage_metrics_with_areas(
        self, sample_aps_with_mounting, sample_measured_areas
    ):
        """Test coverage metrics calculation with measured areas."""
        metrics = CoverageAnalytics.calculate_coverage_metrics(
            sample_aps_with_mounting, sample_measured_areas
        )

        assert isinstance(metrics, CoverageMetrics)
        assert metrics.total_area == 800.0  # 500 + 300
        assert metrics.excluded_area == 100.0
        assert metrics.ap_count == 5
        # Effective area = 800 - 100 = 700 m²
        # Density = 5 / 700 * 1000 = 7.14 APs/1000m²
        assert abs(metrics.ap_density - 7.14) < 0.01
        # Avg coverage = 700 / 5 = 140 m²/AP
        assert metrics.average_coverage_per_ap == 140.0

    def test_calculate_coverage_metrics_without_areas(self, sample_aps_with_mounting):
        """Test coverage metrics without measured areas."""
        metrics = CoverageAnalytics.calculate_coverage_metrics(
            sample_aps_with_mounting, None
        )

        assert isinstance(metrics, CoverageMetrics)
        assert metrics.total_area == 0.0
        assert metrics.excluded_area == 0.0
        assert metrics.ap_count == 5
        assert metrics.ap_density == 0.0
        assert metrics.average_coverage_per_ap == 0.0

    def test_calculate_coverage_metrics_empty_areas(self, sample_aps_with_mounting):
        """Test coverage metrics with empty areas dict."""
        metrics = CoverageAnalytics.calculate_coverage_metrics(
            sample_aps_with_mounting, {"measuredAreas": []}
        )

        assert metrics.total_area == 0.0
        assert metrics.excluded_area == 0.0

    def test_calculate_coverage_metrics_no_aps(self, sample_measured_areas):
        """Test coverage metrics with no APs."""
        metrics = CoverageAnalytics.calculate_coverage_metrics(
            [], sample_measured_areas
        )

        assert metrics.ap_count == 0
        assert metrics.ap_density == 0.0
        assert metrics.average_coverage_per_ap == 0.0

    def test_group_by_floor_with_density(self, sample_aps_with_mounting):
        """Test floor grouping with density calculation."""
        floor_areas = {"Floor 1": 400.0, "Floor 2": 300.0}

        result = CoverageAnalytics.group_by_floor_with_density(
            sample_aps_with_mounting, floor_areas
        )

        assert "Floor 1" in result
        assert "Floor 2" in result

        floor1 = result["Floor 1"]
        assert floor1["ap_count"] == 3
        assert floor1["area"] == 400.0
        # Density = 3 / 400 * 1000 = 7.5 APs/1000m²
        assert abs(floor1["density"] - 7.5) < 0.01

        floor2 = result["Floor 2"]
        assert floor2["ap_count"] == 2
        assert floor2["area"] == 300.0
        # Density = 2 / 300 * 1000 = 6.67 APs/1000m²
        assert abs(floor2["density"] - 6.67) < 0.01

    def test_group_by_floor_without_areas(self, sample_aps_with_mounting):
        """Test floor grouping without area data."""
        result = CoverageAnalytics.group_by_floor_with_density(
            sample_aps_with_mounting, None
        )

        assert "Floor 1" in result
        assert "Floor 2" in result
        assert result["Floor 1"]["area"] == 0
        assert result["Floor 1"]["density"] == 0
        assert result["Floor 2"]["area"] == 0
        assert result["Floor 2"]["density"] == 0


class TestMountingAnalytics:
    """Test MountingAnalytics class."""

    def test_calculate_mounting_metrics(self, sample_aps_with_mounting):
        """Test mounting metrics calculation."""
        metrics = MountingAnalytics.calculate_mounting_metrics(sample_aps_with_mounting)

        assert isinstance(metrics, MountingMetrics)
        assert metrics.aps_with_height == 4  # 4 APs have height data
        # Average height = (3.0 + 3.2 + 2.8 + 4.5) / 4 = 3.375
        assert abs(metrics.avg_height - 3.375) < 0.01
        assert metrics.min_height == 2.8
        assert metrics.max_height == 4.5
        assert metrics.height_variance is not None
        # Average azimuth = (45 + 90 + 180 + 270) / 4 = 146.25
        assert abs(metrics.avg_azimuth - 146.25) < 0.01
        # Average tilt = (10 + 15 + 5 + 20) / 4 = 12.5
        assert abs(metrics.avg_tilt - 12.5) < 0.01

    def test_calculate_mounting_metrics_no_data(self):
        """Test mounting metrics with no data."""
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-515",
                color="Yellow",
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
            )
        ]
        metrics = MountingAnalytics.calculate_mounting_metrics(aps)

        assert metrics.aps_with_height == 0
        assert metrics.avg_height is None
        assert metrics.min_height is None
        assert metrics.max_height is None
        assert metrics.height_variance is None
        assert metrics.avg_azimuth is None
        assert metrics.avg_tilt is None

    def test_group_by_height_range(self, sample_aps_with_mounting):
        """Test height range grouping."""
        ranges = MountingAnalytics.group_by_height_range(sample_aps_with_mounting)

        assert ranges["< 2.5m"] == 0
        assert ranges["2.5-3.5m"] == 3  # 3.0, 3.2, 2.8
        assert ranges["3.5-4.5m"] == 0
        assert ranges["4.5-6.0m"] == 1  # 4.5
        assert ranges["> 6.0m"] == 0
        assert ranges["Unknown"] == 1  # One AP without height

    def test_group_by_height_range_edge_cases(self):
        """Test height range grouping edge cases."""
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-1",
                color=None,
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
                mounting_height=2.4,
            ),
            AccessPoint(
                id="ap2",
                vendor="Cisco",
                model="AP-2",
                color=None,
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
                mounting_height=2.5,
            ),
            AccessPoint(
                id="ap3",
                vendor="Cisco",
                model="AP-3",
                color=None,
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
                mounting_height=3.5,
            ),
            AccessPoint(
                id="ap4",
                vendor="Cisco",
                model="AP-4",
                color=None,
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
                mounting_height=4.5,
            ),
            AccessPoint(
                id="ap5",
                vendor="Cisco",
                model="AP-5",
                color=None,
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
                mounting_height=6.0,
            ),
            AccessPoint(
                id="ap6",
                vendor="Cisco",
                model="AP-6",
                color=None,
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
                mounting_height=6.1,
            ),
        ]

        ranges = MountingAnalytics.group_by_height_range(aps)

        assert ranges["< 2.5m"] == 1  # 2.4
        assert ranges["2.5-3.5m"] == 1  # 2.5
        assert ranges["3.5-4.5m"] == 1  # 3.5
        assert ranges["4.5-6.0m"] == 2  # 4.5, 6.0
        assert ranges["> 6.0m"] == 1  # 6.1

    def test_get_installation_summary(self, sample_aps_with_mounting):
        """Test installation summary generation."""
        summary = MountingAnalytics.get_installation_summary(sample_aps_with_mounting)

        assert summary["total_aps"] == 5
        assert isinstance(summary["mounting_metrics"], MountingMetrics)
        assert isinstance(summary["height_distribution"], dict)
        assert summary["aps_with_tilt"] == 4
        assert summary["aps_with_azimuth"] == 4
        # APs requiring adjustment: None in this sample (all heights are 2.5-6.0m)
        assert summary["aps_requiring_height_adjustment"] == 0

    def test_get_installation_summary_with_adjustments(self):
        """Test installation summary with APs requiring adjustment."""
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-1",
                color=None,
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
                mounting_height=2.0,
            ),
            AccessPoint(
                id="ap2",
                vendor="Cisco",
                model="AP-2",
                color=None,
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
                mounting_height=7.0,
            ),
            AccessPoint(
                id="ap3",
                vendor="Cisco",
                model="AP-3",
                color=None,
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
                mounting_height=3.0,
            ),
        ]

        summary = MountingAnalytics.get_installation_summary(aps)

        # 2 APs require adjustment (< 2.5m or > 6.0m)
        assert summary["aps_requiring_height_adjustment"] == 2

    def test_height_variance_calculation(self):
        """Test variance calculation for heights."""
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-1",
                color=None,
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
                mounting_height=3.0,
            ),
            AccessPoint(
                id="ap2",
                vendor="Cisco",
                model="AP-2",
                color=None,
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
                mounting_height=3.0,
            ),
            AccessPoint(
                id="ap3",
                vendor="Cisco",
                model="AP-3",
                color=None,
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
                mounting_height=3.0,
            ),
        ]

        metrics = MountingAnalytics.calculate_mounting_metrics(aps)

        # All heights are the same, variance should be 0
        assert metrics.height_variance == 0.0

    def test_mixed_data_availability(self):
        """Test with mixed availability of mounting data."""
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-1",
                color=None,
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
                mounting_height=3.0,
                azimuth=None,
                tilt=10.0,
            ),
            AccessPoint(
                id="ap2",
                vendor="Cisco",
                model="AP-2",
                color=None,
                floor_name="Floor 1",
                tags=[],
                mine=True,
                floor_id="f1",
                mounting_height=None,
                azimuth=45.0,
                tilt=None,
            ),
        ]

        metrics = MountingAnalytics.calculate_mounting_metrics(aps)

        assert metrics.aps_with_height == 1
        assert metrics.avg_height == 3.0
        assert metrics.avg_azimuth == 45.0
        assert metrics.avg_tilt == 10.0
