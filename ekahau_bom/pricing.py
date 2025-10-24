#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Pricing and cost calculation module for equipment BOM."""

import logging
import yaml
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from collections import Counter

from .models import AccessPoint, Antenna

logger = logging.getLogger(__name__)


@dataclass
class PriceInfo:
    """Information about equipment price.

    Attributes:
        vendor: Equipment vendor
        model: Equipment model
        unit_price: Price per unit in USD
        quantity: Number of units
        subtotal: Total before discounts
        discount_percent: Applied discount percentage
        discount_amount: Discount amount in USD
        total: Final total after discounts
    """
    vendor: str
    model: str
    unit_price: float
    quantity: int
    subtotal: float = 0.0
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    total: float = 0.0

    def __post_init__(self):
        """Calculate totals after initialization."""
        self.subtotal = self.unit_price * self.quantity
        self.discount_amount = self.subtotal * (self.discount_percent / 100)
        self.total = self.subtotal - self.discount_amount


@dataclass
class CostSummary:
    """Summary of project costs.

    Attributes:
        items: List of priced items
        subtotal: Total before discounts
        total_discount: Total discount amount
        grand_total: Final total after all discounts
        currency: Currency code (default: USD)
        items_with_prices: Number of items with known prices
        items_without_prices: Number of items without prices
        coverage_percent: Percentage of items with prices
    """
    items: list[PriceInfo] = field(default_factory=list)
    subtotal: float = 0.0
    total_discount: float = 0.0
    grand_total: float = 0.0
    currency: str = "USD"
    items_with_prices: int = 0
    items_without_prices: int = 0
    coverage_percent: float = 0.0

    def calculate_totals(self):
        """Calculate summary totals from items."""
        self.subtotal = sum(item.subtotal for item in self.items)
        self.total_discount = sum(item.discount_amount for item in self.items)
        self.grand_total = sum(item.total for item in self.items)

        total_items = self.items_with_prices + self.items_without_prices
        if total_items > 0:
            self.coverage_percent = (self.items_with_prices / total_items) * 100


class PricingDatabase:
    """Manage equipment pricing database."""

    def __init__(self, pricing_file: Optional[Path] = None):
        """Initialize pricing database.

        Args:
            pricing_file: Path to pricing YAML file. If None, uses default.
        """
        self.pricing_file = pricing_file or self._get_default_pricing_file()
        self.prices = {}
        self.antenna_prices = {}
        self.volume_discounts = []
        self.currency = "USD"

        self._load_pricing()

    def _get_default_pricing_file(self) -> Path:
        """Get path to default pricing file."""
        # Look in config directory
        current_dir = Path(__file__).parent.parent
        config_file = current_dir / "config" / "pricing.yaml"

        if config_file.exists():
            return config_file

        logger.warning(f"Default pricing file not found at {config_file}")
        return config_file

    def _load_pricing(self):
        """Load pricing data from YAML file."""
        if not self.pricing_file.exists():
            logger.warning(f"Pricing file not found: {self.pricing_file}")
            logger.warning("Cost calculations will show $0 for unknown items")
            return

        try:
            with open(self.pricing_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # Load vendor prices
            for vendor in ['Cisco', 'Huawei', 'MikroTik', 'Ubiquiti', 'Ruckus']:
                if vendor in data:
                    self.prices[vendor] = data[vendor]

            # Load antenna prices
            if 'Antennas' in data:
                self.antenna_prices = data['Antennas']

            # Load volume discounts
            if 'discounts' in data and 'volume' in data['discounts']:
                self.volume_discounts = data['discounts']['volume']

            # Load currency
            self.currency = data.get('currency', 'USD')

            logger.info(f"Loaded pricing for {len(self.prices)} vendors")
            logger.info(f"Loaded {len(self.antenna_prices)} antenna prices")
            logger.info(f"Loaded {len(self.volume_discounts)} volume discount tiers")

        except Exception as e:
            logger.error(f"Failed to load pricing file: {e}")
            logger.warning("Cost calculations will show $0 for unknown items")

    def get_price(self, vendor: str, model: str) -> Optional[float]:
        """Get price for specific vendor/model.

        Args:
            vendor: Equipment vendor
            model: Equipment model

        Returns:
            Price in USD or None if not found
        """
        if vendor in self.prices and model in self.prices[vendor]:
            return float(self.prices[vendor][model])
        return None

    def get_antenna_price(self, antenna_name: str) -> Optional[float]:
        """Get price for antenna.

        Args:
            antenna_name: Antenna model name

        Returns:
            Price in USD or None if not found
        """
        if antenna_name in self.antenna_prices:
            return float(self.antenna_prices[antenna_name])
        return None

    def get_volume_discount(self, quantity: int) -> float:
        """Get volume discount percentage for quantity.

        Args:
            quantity: Total quantity

        Returns:
            Discount percentage (0-100)
        """
        for tier in self.volume_discounts:
            min_qty = tier['min_quantity']
            max_qty = tier.get('max_quantity')

            if max_qty is None:
                # Unlimited tier
                if quantity >= min_qty:
                    return float(tier['discount_percent'])
            else:
                # Range tier
                if min_qty <= quantity <= max_qty:
                    return float(tier['discount_percent'])

        return 0.0


class CostCalculator:
    """Calculate costs for project BOM."""

    def __init__(
        self,
        pricing_db: PricingDatabase,
        custom_discount: float = 0.0,
        apply_volume_discounts: bool = True
    ):
        """Initialize cost calculator.

        Args:
            pricing_db: Pricing database instance
            custom_discount: Additional custom discount percentage (0-100)
            apply_volume_discounts: Whether to apply volume discounts
        """
        self.pricing_db = pricing_db
        self.custom_discount = custom_discount
        self.apply_volume_discounts = apply_volume_discounts

    def calculate_access_points_cost(
        self,
        access_points: list[AccessPoint]
    ) -> CostSummary:
        """Calculate cost for access points.

        Args:
            access_points: List of access points

        Returns:
            Cost summary with pricing details
        """
        # Count access points by vendor/model
        ap_counts = Counter()
        for ap in access_points:
            key = (ap.vendor, ap.model)
            ap_counts[key] += 1

        # Calculate total quantity for volume discount
        total_quantity = sum(ap_counts.values())
        volume_discount = 0.0
        if self.apply_volume_discounts:
            volume_discount = self.pricing_db.get_volume_discount(total_quantity)

        # Combine discounts (volume + custom)
        total_discount = min(volume_discount + self.custom_discount, 100.0)

        # Calculate costs for each item
        items = []
        items_with_prices = 0
        items_without_prices = 0

        for (vendor, model), quantity in sorted(ap_counts.items()):
            unit_price = self.pricing_db.get_price(vendor, model)

            if unit_price is not None:
                price_info = PriceInfo(
                    vendor=vendor,
                    model=model,
                    unit_price=unit_price,
                    quantity=quantity,
                    discount_percent=total_discount
                )
                items.append(price_info)
                items_with_prices += 1
            else:
                # Item without price
                price_info = PriceInfo(
                    vendor=vendor,
                    model=model,
                    unit_price=0.0,
                    quantity=quantity,
                    discount_percent=0.0
                )
                items.append(price_info)
                items_without_prices += 1
                logger.warning(f"No price found for {vendor} {model}")

        # Create summary
        summary = CostSummary(
            items=items,
            currency=self.pricing_db.currency,
            items_with_prices=items_with_prices,
            items_without_prices=items_without_prices
        )
        summary.calculate_totals()

        return summary

    def calculate_antennas_cost(
        self,
        antennas: list[Antenna]
    ) -> CostSummary:
        """Calculate cost for antennas.

        Args:
            antennas: List of antennas

        Returns:
            Cost summary with pricing details
        """
        # Count antennas by model
        antenna_counts = Counter(antenna.name for antenna in antennas)

        # Calculate costs for each antenna
        items = []
        items_with_prices = 0
        items_without_prices = 0

        for antenna_name, quantity in sorted(antenna_counts.items()):
            unit_price = self.pricing_db.get_antenna_price(antenna_name)

            # Apply custom discount only (no volume discount for antennas)
            discount = self.custom_discount

            if unit_price is not None:
                price_info = PriceInfo(
                    vendor="Antenna",
                    model=antenna_name,
                    unit_price=unit_price,
                    quantity=quantity,
                    discount_percent=discount
                )
                items.append(price_info)
                items_with_prices += 1
            else:
                # Antenna without price
                price_info = PriceInfo(
                    vendor="Antenna",
                    model=antenna_name,
                    unit_price=0.0,
                    quantity=quantity,
                    discount_percent=0.0
                )
                items.append(price_info)
                items_without_prices += 1
                logger.debug(f"No price found for antenna {antenna_name}")

        # Create summary
        summary = CostSummary(
            items=items,
            currency=self.pricing_db.currency,
            items_with_prices=items_with_prices,
            items_without_prices=items_without_prices
        )
        summary.calculate_totals()

        return summary

    def calculate_total_cost(
        self,
        access_points: list[AccessPoint],
        antennas: list[Antenna]
    ) -> tuple[CostSummary, CostSummary, CostSummary]:
        """Calculate total project cost.

        Args:
            access_points: List of access points
            antennas: List of antennas

        Returns:
            Tuple of (ap_summary, antenna_summary, combined_summary)
        """
        ap_summary = self.calculate_access_points_cost(access_points)
        antenna_summary = self.calculate_antennas_cost(antennas)

        # Combine summaries
        combined = CostSummary(
            items=ap_summary.items + antenna_summary.items,
            currency=self.pricing_db.currency,
            items_with_prices=ap_summary.items_with_prices + antenna_summary.items_with_prices,
            items_without_prices=ap_summary.items_without_prices + antenna_summary.items_without_prices
        )
        combined.calculate_totals()

        return ap_summary, antenna_summary, combined
