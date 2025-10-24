#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for pricing module."""

import pytest
from pathlib import Path
from ekahau_bom.pricing import PricingDatabase, CostCalculator, PriceInfo, CostSummary
from ekahau_bom.models import AccessPoint, Antenna


@pytest.fixture
def pricing_db(tmp_path):
    """Create test pricing database."""
    pricing_file = tmp_path / "test_pricing.yaml"
    pricing_file.write_text("""
Cisco:
  AP-515: 1000
  AP-635: 1500

Huawei:
  AirEngine5760-10: 500

Antennas:
  ANT-20: 100
  Internal: 0

discounts:
  volume:
    - min_quantity: 1
      max_quantity: 9
      discount_percent: 0
    - min_quantity: 10
      max_quantity: 49
      discount_percent: 10
    - min_quantity: 50
      max_quantity: null
      discount_percent: 20

currency: USD
""")
    return PricingDatabase(pricing_file)


class TestPriceInfo:
    """Test PriceInfo class."""

    def test_price_info_creation(self):
        """Test PriceInfo calculates correctly."""
        price = PriceInfo(
            vendor="Cisco",
            model="AP-515",
            unit_price=1000,
            quantity=5,
            discount_percent=10
        )

        assert price.subtotal == 5000
        assert price.discount_amount == 500
        assert price.total == 4500

    def test_price_info_no_discount(self):
        """Test PriceInfo without discount."""
        price = PriceInfo(
            vendor="Cisco",
            model="AP-515",
            unit_price=1000,
            quantity=3,
            discount_percent=0
        )

        assert price.subtotal == 3000
        assert price.discount_amount == 0
        assert price.total == 3000


class TestPricingDatabase:
    """Test PricingDatabase class."""

    def test_load_pricing(self, pricing_db):
        """Test pricing database loads correctly."""
        assert 'Cisco' in pricing_db.prices
        assert 'Huawei' in pricing_db.prices
        assert pricing_db.currency == "USD"

    def test_get_price_found(self, pricing_db):
        """Test getting price for known item."""
        price = pricing_db.get_price("Cisco", "AP-515")
        assert price == 1000

    def test_get_price_not_found(self, pricing_db):
        """Test getting price for unknown item."""
        price = pricing_db.get_price("Unknown", "Model")
        assert price is None

    def test_get_antenna_price(self, pricing_db):
        """Test getting antenna price."""
        price = pricing_db.get_antenna_price("ANT-20")
        assert price == 100

    def test_get_volume_discount_tier1(self, pricing_db):
        """Test volume discount for tier 1."""
        discount = pricing_db.get_volume_discount(5)
        assert discount == 0

    def test_get_volume_discount_tier2(self, pricing_db):
        """Test volume discount for tier 2."""
        discount = pricing_db.get_volume_discount(25)
        assert discount == 10

    def test_get_volume_discount_tier3(self, pricing_db):
        """Test volume discount for tier 3 (unlimited)."""
        discount = pricing_db.get_volume_discount(100)
        assert discount == 20


class TestCostCalculator:
    """Test CostCalculator class."""

    def test_calculate_access_points_cost(self, pricing_db):
        """Test calculating cost for access points."""
        aps = [
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1"),
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1"),
            AccessPoint("Cisco", "AP-635", "Red", "Floor 2"),
        ]

        calculator = CostCalculator(pricing_db, custom_discount=0, apply_volume_discounts=False)
        summary = calculator.calculate_access_points_cost(aps)

        assert summary.items_with_prices == 2
        assert summary.items_without_prices == 0
        assert summary.subtotal == 3500  # 2*1000 + 1*1500
        assert summary.grand_total == 3500

    def test_calculate_with_volume_discount(self, pricing_db):
        """Test calculating with volume discount."""
        # Create 25 APs to trigger 10% discount
        aps = [AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1") for _ in range(25)]

        calculator = CostCalculator(pricing_db, custom_discount=0, apply_volume_discounts=True)
        summary = calculator.calculate_access_points_cost(aps)

        assert summary.subtotal == 25000  # 25*1000
        assert summary.total_discount == 2500  # 10% of 25000
        assert summary.grand_total == 22500

    def test_calculate_with_custom_discount(self, pricing_db):
        """Test calculating with custom discount."""
        aps = [AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1") for _ in range(5)]

        calculator = CostCalculator(pricing_db, custom_discount=15, apply_volume_discounts=False)
        summary = calculator.calculate_access_points_cost(aps)

        assert summary.subtotal == 5000
        assert summary.total_discount == 750  # 15% of 5000
        assert summary.grand_total == 4250

    def test_calculate_antennas_cost(self, pricing_db):
        """Test calculating cost for antennas."""
        antennas = [
            Antenna("ANT-20", "ant1"),
            Antenna("ANT-20", "ant1"),
            Antenna("Internal", "ant2"),
        ]

        calculator = CostCalculator(pricing_db)
        summary = calculator.calculate_antennas_cost(antennas)

        assert summary.items_with_prices == 2
        assert summary.subtotal == 200  # 2*100 + 1*0
        assert summary.grand_total == 200

    def test_calculate_total_cost(self, pricing_db):
        """Test calculating total project cost."""
        aps = [
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1"),
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1"),
        ]
        antennas = [
            Antenna("ANT-20", "ant1"),
        ]

        calculator = CostCalculator(pricing_db, custom_discount=0, apply_volume_discounts=False)
        ap_summary, antenna_summary, combined_summary = calculator.calculate_total_cost(aps, antennas)

        assert ap_summary.grand_total == 2000
        assert antenna_summary.grand_total == 100
        assert combined_summary.grand_total == 2100
        assert combined_summary.items_with_prices == 2

    def test_unknown_equipment_zero_price(self, pricing_db):
        """Test that unknown equipment gets $0 price."""
        aps = [AccessPoint("Unknown", "Model123", "Yellow", "Floor 1")]

        calculator = CostCalculator(pricing_db)
        summary = calculator.calculate_access_points_cost(aps)

        assert summary.items_with_prices == 0
        assert summary.items_without_prices == 1
        assert summary.grand_total == 0

    def test_coverage_percentage(self, pricing_db):
        """Test coverage percentage calculation."""
        aps = [
            AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1"),  # Known
            AccessPoint("Unknown", "Model", "Yellow", "Floor 1"),  # Unknown
        ]

        calculator = CostCalculator(pricing_db)
        summary = calculator.calculate_access_points_cost(aps)

        assert summary.items_with_prices == 1
        assert summary.items_without_prices == 1
        assert summary.coverage_percent == 50.0


class TestCostSummary:
    """Test CostSummary class."""

    def test_calculate_totals(self):
        """Test CostSummary totals calculation."""
        items = [
            PriceInfo("Cisco", "AP-515", 1000, 5, discount_percent=10),
            PriceInfo("Cisco", "AP-635", 1500, 3, discount_percent=10),
        ]

        summary = CostSummary(items=items, items_with_prices=2, items_without_prices=0)
        summary.calculate_totals()

        assert summary.subtotal == 9500  # 5000 + 4500
        assert summary.total_discount == 950  # 500 + 450
        assert summary.grand_total == 8550
        assert summary.coverage_percent == 100.0

    def test_empty_summary(self):
        """Test empty cost summary."""
        summary = CostSummary()
        summary.calculate_totals()

        assert summary.subtotal == 0
        assert summary.grand_total == 0
        assert summary.coverage_percent == 0
