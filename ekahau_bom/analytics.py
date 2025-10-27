#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Analytics and grouping utilities for access points."""

from __future__ import annotations


import logging
from collections import Counter, defaultdict
from typing import Any, Optional
from dataclasses import dataclass

from .models import AccessPoint, Radio

logger = logging.getLogger(__name__)


@dataclass
class CoverageMetrics:
    """Coverage metrics for project analysis.

    Attributes:
        total_area: Total coverage area in square meters
        excluded_area: Excluded area in square meters
        ap_count: Number of access points
        ap_density: Access points per 1000 square meters
        average_coverage_per_ap: Average coverage area per AP in square meters
    """

    total_area: float
    excluded_area: float
    ap_count: int
    ap_density: float
    average_coverage_per_ap: float


@dataclass
class MountingMetrics:
    """Mounting parameter metrics.

    Attributes:
        avg_height: Average mounting height in meters
        min_height: Minimum mounting height in meters
        max_height: Maximum mounting height in meters
        height_variance: Variance in mounting heights
        aps_with_height: Number of APs with height data
        avg_azimuth: Average azimuth angle
        avg_tilt: Average tilt angle
    """

    avg_height: Optional[float]
    min_height: Optional[float]
    max_height: Optional[float]
    height_variance: Optional[float]
    aps_with_height: int
    avg_azimuth: Optional[float]
    avg_tilt: Optional[float]


class GroupingAnalytics:
    """Analytics and grouping for project data.

    Provides methods for grouping access points by various dimensions
    and calculating statistics.
    """

    @staticmethod
    def group_by_dimension(
        access_points: list[AccessPoint], dimension: str, tag_key: str | None = None
    ) -> dict[str, int]:
        """Group access points by specified dimension.

        Args:
            access_points: List of access points to group
            dimension: Dimension to group by ("vendor", "model", "floor", "color", "tag")
            tag_key: Tag key name (required if dimension is "tag")

        Returns:
            Dictionary mapping dimension value to count
        """
        if dimension == "vendor":
            return GroupingAnalytics.group_by_vendor(access_points)
        elif dimension == "model":
            return GroupingAnalytics.group_by_model(access_points)
        elif dimension == "floor":
            return GroupingAnalytics.group_by_floor(access_points)
        elif dimension == "color":
            return GroupingAnalytics.group_by_color(access_points)
        elif dimension == "tag" and tag_key:
            return GroupingAnalytics.group_by_tag(access_points, tag_key)
        else:
            logger.warning(f"Unknown dimension: {dimension}")
            return {}

    @staticmethod
    def group_by_floor(access_points: list[AccessPoint]) -> dict[str, int]:
        """Group access points by floor with counts.

        Args:
            access_points: List of access points to group

        Returns:
            Dictionary mapping floor name to count
        """
        counts = Counter(ap.floor_name for ap in access_points)
        logger.info(f"Grouped {len(access_points)} APs by floor: {len(counts)} unique floors")
        return dict(counts)

    @staticmethod
    def group_by_color(access_points: list[AccessPoint]) -> dict[str, int]:
        """Group access points by color with counts.

        Args:
            access_points: List of access points to group

        Returns:
            Dictionary mapping color name to count
        """
        counts = Counter(ap.color or "No Color" for ap in access_points)
        logger.info(f"Grouped {len(access_points)} APs by color: {len(counts)} unique colors")
        return dict(counts)

    @staticmethod
    def group_by_vendor(access_points: list[AccessPoint]) -> dict[str, int]:
        """Group access points by vendor with counts.

        Args:
            access_points: List of access points to group

        Returns:
            Dictionary mapping vendor name to count
        """
        counts = Counter(ap.vendor for ap in access_points)
        logger.info(f"Grouped {len(access_points)} APs by vendor: {len(counts)} unique vendors")
        return dict(counts)

    @staticmethod
    def group_by_model(access_points: list[AccessPoint]) -> dict[str, int]:
        """Group access points by model with counts.

        Args:
            access_points: List of access points to group

        Returns:
            Dictionary mapping model name to count
        """
        counts = Counter(ap.model for ap in access_points)
        logger.info(f"Grouped {len(access_points)} APs by model: {len(counts)} unique models")
        return dict(counts)

    @staticmethod
    def group_by_tag(access_points: list[AccessPoint], tag_key: str) -> dict[str, int]:
        """Group access points by specific tag key.

        Args:
            access_points: List of access points to group
            tag_key: Name of the tag key to group by

        Returns:
            Dictionary mapping tag value to count
        """
        tag_values = []
        for ap in access_points:
            value_found = False
            for tag in ap.tags:
                if tag.key == tag_key:
                    tag_values.append(tag.value)
                    value_found = True
                    break
            if not value_found:
                tag_values.append(f"No {tag_key}")

        counts = Counter(tag_values)
        logger.info(
            f"Grouped {len(access_points)} APs by tag '{tag_key}': {len(counts)} unique values"
        )
        return dict(counts)

    @staticmethod
    def group_by_vendor_and_model(
        access_points: list[AccessPoint],
    ) -> dict[tuple[str, str], int]:
        """Group access points by vendor and model combination.

        Args:
            access_points: List of access points to group

        Returns:
            Dictionary mapping (vendor, model) tuple to count
        """
        counts = Counter((ap.vendor, ap.model) for ap in access_points)
        logger.info(
            f"Grouped {len(access_points)} APs by vendor+model: {len(counts)} unique combinations"
        )
        return dict(counts)

    @staticmethod
    def multi_dimensional_grouping(
        access_points: list[AccessPoint],
        dimensions: list[str],
        tag_key: str | None = None,
    ) -> dict[tuple, int]:
        """Multi-dimensional grouping of access points.

        Args:
            access_points: List of access points to group
            dimensions: List of dimensions to group by.
                       Valid values: "floor", "color", "vendor", "model", "tag"
            tag_key: Tag key name (required if "tag" in dimensions)

        Returns:
            Dictionary mapping tuple of values to count

        Example:
            >>> group_multi(aps, ["floor", "color"])
            {("Floor 1", "Yellow"): 10, ("Floor 1", "Red"): 5, ...}
        """
        groups = defaultdict(int)

        for ap in access_points:
            key = []
            for dim in dimensions:
                if dim == "floor":
                    key.append(ap.floor_name)
                elif dim == "color":
                    key.append(ap.color or "No Color")
                elif dim == "vendor":
                    key.append(ap.vendor)
                elif dim == "model":
                    key.append(ap.model)
                elif dim == "tag" and tag_key:
                    value = ap.get_tag_value(tag_key)
                    key.append(value or f"No {tag_key}")
                else:
                    logger.warning(f"Unknown dimension: {dim}")
                    key.append("Unknown")

            groups[tuple(key)] += 1

        logger.info(
            f"Multi-dimensional grouping ({'+'.join(dimensions)}): {len(groups)} unique combinations"
        )
        return dict(groups)

    @staticmethod
    def calculate_percentages(counts: dict[Any, int]) -> dict[Any, tuple[int, float]]:
        """Calculate percentages for each group.

        Args:
            counts: Dictionary of counts

        Returns:
            Dictionary mapping key to (count, percentage) tuple
        """
        total = sum(counts.values())
        if total == 0:
            return {key: (0, 0.0) for key in counts.keys()}

        return {key: (count, (count / total * 100)) for key, count in counts.items()}

    @staticmethod
    def get_summary_statistics(access_points: list[AccessPoint]) -> dict[str, Any]:
        """Get summary statistics for access points.

        Args:
            access_points: List of access points

        Returns:
            Dictionary with various statistics
        """
        if not access_points:
            return {
                "total": 0,
                "unique_vendors": 0,
                "unique_models": 0,
                "unique_floors": 0,
                "unique_colors": 0,
                "with_tags": 0,
            }

        return {
            "total": len(access_points),
            "unique_vendors": len(set(ap.vendor for ap in access_points)),
            "unique_models": len(set(ap.model for ap in access_points)),
            "unique_floors": len(set(ap.floor_name for ap in access_points)),
            "unique_colors": len(set(ap.color for ap in access_points if ap.color)),
            "with_tags": sum(1 for ap in access_points if ap.tags),
        }

    @staticmethod
    def print_grouped_results(
        grouped_data: dict[Any, int],
        title: str = "Grouping Results",
        show_percentages: bool = True,
    ) -> None:
        """Print grouped results to logger in a formatted way.

        Args:
            grouped_data: Dictionary of grouped counts
            title: Title for the output
            show_percentages: Whether to show percentages
        """
        logger.info("=" * 60)
        logger.info(title)
        logger.info("=" * 60)

        if not grouped_data:
            logger.info("No data to display")
            return

        # Calculate percentages if needed
        if show_percentages:
            percentages = GroupingAnalytics.calculate_percentages(grouped_data)
            # Sort by count (descending)
            sorted_data = sorted(percentages.items(), key=lambda x: x[1][0], reverse=True)

            for key, (count, pct) in sorted_data:
                logger.info(f"  {key}: {count} ({pct:.1f}%)")
        else:
            # Sort by count (descending)
            sorted_data = sorted(grouped_data.items(), key=lambda x: x[1], reverse=True)

            for key, count in sorted_data:
                logger.info(f"  {key}: {count}")

        logger.info("=" * 60)


class CoverageAnalytics:
    """Analytics for coverage areas and AP density.

    Provides metrics for Wi-Fi engineers to analyze:
    - Total coverage area
    - Excluded areas
    - AP density (APs per 1000 m²)
    - Average coverage per AP
    """

    @staticmethod
    def calculate_coverage_metrics(
        access_points: list[AccessPoint],
        measured_areas: Optional[dict[str, Any]] = None,
    ) -> CoverageMetrics:
        """Calculate coverage metrics from access points and measured areas.

        Args:
            access_points: List of access points
            measured_areas: Optional measured areas data from Ekahau

        Returns:
            CoverageMetrics object with calculated values
        """
        ap_count = len(access_points)
        total_area = 0.0
        excluded_area = 0.0

        # Calculate areas from measured areas if available
        if measured_areas and "measuredAreas" in measured_areas:
            for area in measured_areas["measuredAreas"]:
                area_size = area.get("size", 0)  # Area in square meters
                if area.get("excluded", False):
                    excluded_area += area_size
                else:
                    total_area += area_size

        # Calculate metrics
        effective_area = total_area - excluded_area
        ap_density = (ap_count / effective_area * 1000) if effective_area > 0 else 0
        avg_coverage_per_ap = (effective_area / ap_count) if ap_count > 0 else 0

        logger.info(
            f"Coverage metrics: {ap_count} APs, {total_area:.1f}m² total, {excluded_area:.1f}m² excluded"
        )
        logger.info(
            f"AP density: {ap_density:.2f} APs/1000m², avg coverage: {avg_coverage_per_ap:.1f}m²/AP"
        )

        return CoverageMetrics(
            total_area=total_area,
            excluded_area=excluded_area,
            ap_count=ap_count,
            ap_density=ap_density,
            average_coverage_per_ap=avg_coverage_per_ap,
        )

    @staticmethod
    def group_by_floor_with_density(
        access_points: list[AccessPoint], floor_areas: Optional[dict[str, float]] = None
    ) -> dict[str, dict[str, Any]]:
        """Group APs by floor and calculate density per floor.

        Args:
            access_points: List of access points
            floor_areas: Optional dictionary mapping floor name to area in m²

        Returns:
            Dictionary with floor-level metrics
        """
        floor_counts = Counter(ap.floor_name for ap in access_points)
        result = {}

        for floor_name, count in floor_counts.items():
            metrics = {
                "ap_count": count,
                "area": floor_areas.get(floor_name, 0) if floor_areas else 0,
                "density": 0,
            }

            if floor_areas and floor_name in floor_areas and floor_areas[floor_name] > 0:
                metrics["density"] = count / floor_areas[floor_name] * 1000

            result[floor_name] = metrics

        return result


class MountingAnalytics:
    """Analytics for mounting parameters.

    Provides metrics for installation teams:
    - Average mounting height
    - Height variance
    - Azimuth distribution
    - Tilt angle distribution
    """

    @staticmethod
    def calculate_mounting_metrics(access_points: list[AccessPoint]) -> MountingMetrics:
        """Calculate mounting parameter statistics.

        Args:
            access_points: List of access points

        Returns:
            MountingMetrics object with calculated values
        """
        # Filter APs with height data
        heights = [ap.mounting_height for ap in access_points if ap.mounting_height is not None]
        azimuths = [ap.azimuth for ap in access_points if ap.azimuth is not None]
        tilts = [ap.tilt for ap in access_points if ap.tilt is not None]

        # Calculate height statistics
        avg_height = sum(heights) / len(heights) if heights else None
        min_height = min(heights) if heights else None
        max_height = max(heights) if heights else None

        # Calculate variance
        height_variance = None
        if heights and avg_height is not None:
            variance_sum = sum((h - avg_height) ** 2 for h in heights)
            height_variance = variance_sum / len(heights)

        # Calculate angle averages
        avg_azimuth = sum(azimuths) / len(azimuths) if azimuths else None
        avg_tilt = sum(tilts) / len(tilts) if tilts else None

        logger.info(f"Mounting metrics: {len(heights)} APs with height data")
        if avg_height:
            logger.info(
                f"Height: avg={avg_height:.2f}m, min={min_height:.2f}m, max={max_height:.2f}m"
            )
        if avg_azimuth:
            logger.info(f"Azimuth: avg={avg_azimuth:.1f}°")
        if avg_tilt:
            logger.info(f"Tilt: avg={avg_tilt:.1f}°")

        return MountingMetrics(
            avg_height=avg_height,
            min_height=min_height,
            max_height=max_height,
            height_variance=height_variance,
            aps_with_height=len(heights),
            avg_azimuth=avg_azimuth,
            avg_tilt=avg_tilt,
        )

    @staticmethod
    def group_by_height_range(access_points: list[AccessPoint]) -> dict[str, int]:
        """Group APs by mounting height ranges.

        Args:
            access_points: List of access points

        Returns:
            Dictionary mapping height range to count
        """
        ranges = {
            "< 2.5m": 0,
            "2.5-3.5m": 0,
            "3.5-4.5m": 0,
            "4.5-6.0m": 0,
            "> 6.0m": 0,
            "Unknown": 0,
        }

        for ap in access_points:
            if ap.mounting_height is None:
                ranges["Unknown"] += 1
            elif ap.mounting_height < 2.5:
                ranges["< 2.5m"] += 1
            elif ap.mounting_height < 3.5:
                ranges["2.5-3.5m"] += 1
            elif ap.mounting_height < 4.5:
                ranges["3.5-4.5m"] += 1
            elif ap.mounting_height <= 6.0:  # Include 6.0 in this range
                ranges["4.5-6.0m"] += 1
            else:
                ranges["> 6.0m"] += 1

        return ranges

    @staticmethod
    def get_installation_summary(access_points: list[AccessPoint]) -> dict[str, Any]:
        """Get summary of installation parameters.

        Args:
            access_points: List of access points

        Returns:
            Dictionary with installation-relevant metrics
        """
        metrics = MountingAnalytics.calculate_mounting_metrics(access_points)
        height_distribution = MountingAnalytics.group_by_height_range(access_points)

        return {
            "total_aps": len(access_points),
            "mounting_metrics": metrics,
            "height_distribution": height_distribution,
            "aps_requiring_height_adjustment": sum(
                1
                for ap in access_points
                if ap.mounting_height and (ap.mounting_height < 2.5 or ap.mounting_height > 6.0)
            ),
            "aps_with_tilt": sum(1 for ap in access_points if ap.tilt is not None),
            "aps_with_azimuth": sum(1 for ap in access_points if ap.azimuth is not None),
        }


@dataclass
class RadioMetrics:
    """Radio configuration metrics.

    Attributes:
        total_radios: Total number of radios
        band_distribution: Distribution by frequency band
        channel_distribution: Distribution by channel number
        channel_width_distribution: Distribution by channel width
        standard_distribution: Distribution by Wi-Fi standard
        avg_tx_power: Average transmit power in dBm
        min_tx_power: Minimum transmit power
        max_tx_power: Maximum transmit power
    """

    total_radios: int
    band_distribution: dict[str, int]
    channel_distribution: dict[int, int]
    channel_width_distribution: dict[int, int]
    standard_distribution: dict[str, int]
    avg_tx_power: Optional[float]
    min_tx_power: Optional[float]
    max_tx_power: Optional[float]


class RadioAnalytics:
    """Analytics for radio configurations.

    Provides metrics for Wi-Fi engineers to analyze:
    - Frequency band distribution (2.4/5/6 GHz)
    - Channel allocation and distribution
    - Channel width usage (20/40/80/160 MHz)
    - Wi-Fi standards (802.11a/b/g/n/ac/ax/be)
    - Transmit power analysis
    """

    @staticmethod
    def calculate_radio_metrics(radios: list[Radio]) -> RadioMetrics:
        """Calculate radio configuration statistics.

        Args:
            radios: List of radios

        Returns:
            RadioMetrics object with calculated values
        """
        total_radios = len(radios)

        # Band distribution
        band_counts = Counter(r.frequency_band for r in radios if r.frequency_band)

        # Channel distribution
        channel_counts = Counter(r.channel for r in radios if r.channel)

        # Channel width distribution
        width_counts = Counter(r.channel_width for r in radios if r.channel_width)

        # Standard distribution
        standard_counts = Counter(r.standard for r in radios if r.standard)

        # Tx Power statistics
        tx_powers = [r.tx_power for r in radios if r.tx_power is not None]
        avg_tx_power = sum(tx_powers) / len(tx_powers) if tx_powers else None
        min_tx_power = min(tx_powers) if tx_powers else None
        max_tx_power = max(tx_powers) if tx_powers else None

        logger.info(f"Radio metrics: {total_radios} radios analyzed")
        logger.info(f"Band distribution: {dict(band_counts)}")
        logger.info(f"Standards: {dict(standard_counts)}")

        return RadioMetrics(
            total_radios=total_radios,
            band_distribution=dict(band_counts),
            channel_distribution=dict(channel_counts),
            channel_width_distribution=dict(width_counts),
            standard_distribution=dict(standard_counts),
            avg_tx_power=avg_tx_power,
            min_tx_power=min_tx_power,
            max_tx_power=max_tx_power,
        )

    @staticmethod
    def group_by_frequency_band(radios: list[Radio]) -> dict[str, int]:
        """Group radios by frequency band.

        Args:
            radios: List of radios

        Returns:
            Dictionary mapping frequency band to count
        """
        bands = Counter(r.frequency_band for r in radios if r.frequency_band)
        return dict(bands)

    @staticmethod
    def group_by_channel_width(radios: list[Radio]) -> dict[str, int]:
        """Group radios by channel width.

        Args:
            radios: List of radios

        Returns:
            Dictionary mapping channel width to count
        """
        widths = {}
        for radio in radios:
            if radio.channel_width:
                key = f"{radio.channel_width} MHz"
                widths[key] = widths.get(key, 0) + 1

        return widths

    @staticmethod
    def group_by_wifi_standard(radios: list[Radio]) -> dict[str, int]:
        """Group radios by Wi-Fi standard.

        Args:
            radios: List of radios

        Returns:
            Dictionary mapping Wi-Fi standard to count
        """
        standards = Counter(r.standard for r in radios if r.standard)
        return dict(standards)

    @staticmethod
    def analyze_channel_usage(radios: list[Radio], band: Optional[str] = None) -> dict[str, Any]:
        """Analyze channel usage for specific band or all bands.

        Args:
            radios: List of radios
            band: Optional frequency band to filter (e.g., "2.4GHz", "5GHz")

        Returns:
            Dictionary with channel usage analysis
        """
        # Filter by band if specified
        if band:
            radios = [r for r in radios if r.frequency_band == band]

        channel_counts = Counter(r.channel for r in radios if r.channel)
        total_radios = len([r for r in radios if r.channel])

        # Find most used and least used channels
        most_common = channel_counts.most_common(3) if channel_counts else []
        least_common = channel_counts.most_common()[:-4:-1] if len(channel_counts) > 3 else []

        # Calculate channel distribution statistics
        unique_channels = len(channel_counts)
        avg_radios_per_channel = total_radios / unique_channels if unique_channels > 0 else 0

        return {
            "total_radios": total_radios,
            "unique_channels": unique_channels,
            "avg_radios_per_channel": avg_radios_per_channel,
            "most_used_channels": most_common,
            "least_used_channels": least_common,
            "channel_distribution": dict(channel_counts),
        }

    @staticmethod
    def get_tx_power_distribution(radios: list[Radio]) -> dict[str, int]:
        """Group radios by transmit power ranges.

        Args:
            radios: List of radios

        Returns:
            Dictionary mapping power range to count
        """
        ranges = {
            "< 10 dBm": 0,
            "10-15 dBm": 0,
            "15-20 dBm": 0,
            "20-25 dBm": 0,
            "> 25 dBm": 0,
            "Unknown": 0,
        }

        for radio in radios:
            if radio.tx_power is None:
                ranges["Unknown"] += 1
            elif radio.tx_power < 10:
                ranges["< 10 dBm"] += 1
            elif radio.tx_power < 15:
                ranges["10-15 dBm"] += 1
            elif radio.tx_power < 20:
                ranges["15-20 dBm"] += 1
            elif radio.tx_power < 25:
                ranges["20-25 dBm"] += 1
            else:
                ranges["> 25 dBm"] += 1

        return ranges

    @staticmethod
    def get_radio_summary(radios: list[Radio]) -> dict[str, Any]:
        """Get comprehensive radio summary.

        Args:
            radios: List of radios

        Returns:
            Dictionary with radio summary metrics
        """
        metrics = RadioAnalytics.calculate_radio_metrics(radios)
        band_dist = RadioAnalytics.group_by_frequency_band(radios)
        width_dist = RadioAnalytics.group_by_channel_width(radios)
        standard_dist = RadioAnalytics.group_by_wifi_standard(radios)
        power_dist = RadioAnalytics.get_tx_power_distribution(radios)

        return {
            "total_radios": metrics.total_radios,
            "frequency_bands": band_dist,
            "channel_widths": width_dist,
            "wifi_standards": standard_dist,
            "tx_power_ranges": power_dist,
            "avg_tx_power": metrics.avg_tx_power,
            "min_tx_power": metrics.min_tx_power,
            "max_tx_power": metrics.max_tx_power,
        }
