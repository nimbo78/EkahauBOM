#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for pricing module."""

from __future__ import annotations


import pytest
from pathlib import Path
from ekahau_bom.pricing import PricingDatabase, CostCalculator, PriceInfo, CostSummary
from ekahau_bom.models import AccessPoint, Antenna


@pytest.fixture
def pricing_db(tmp_path):
    """Create test pricing database."""
    pricing_file = tmp_path / "test_pricing.yaml"
    pricing_file.write_text(
        """
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
"""
    )
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
            discount_percent=10,
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
            discount_percent=0,
        )

        assert price.subtotal == 3000
        assert price.discount_amount == 0
        assert price.total == 3000


class TestPricingDatabase:
    """Test PricingDatabase class."""

    def test_load_pricing(self, pricing_db):
        """Test pricing database loads correctly."""
        assert "Cisco" in pricing_db.prices
        assert "Huawei" in pricing_db.prices
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
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-515",
                color="Yellow",
                floor_name="Floor 1",
            ),
            AccessPoint(
                id="ap2",
                vendor="Cisco",
                model="AP-515",
                color="Yellow",
                floor_name="Floor 1",
            ),
            AccessPoint(
                id="ap3",
                vendor="Cisco",
                model="AP-635",
                color="Red",
                floor_name="Floor 2",
            ),
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
        aps = [
            AccessPoint(
                id=f"ap{i}",
                vendor="Cisco",
                model="AP-515",
                color="Yellow",
                floor_name="Floor 1",
            )
            for i in range(25)
        ]

        calculator = CostCalculator(pricing_db, custom_discount=0, apply_volume_discounts=True)
        summary = calculator.calculate_access_points_cost(aps)

        assert summary.subtotal == 25000  # 25*1000
        assert summary.total_discount == 2500  # 10% of 25000
        assert summary.grand_total == 22500

    def test_calculate_with_custom_discount(self, pricing_db):
        """Test calculating with custom discount."""
        aps = [
            AccessPoint(
                id=f"ap{i}",
                vendor="Cisco",
                model="AP-515",
                color="Yellow",
                floor_name="Floor 1",
            )
            for i in range(5)
        ]

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
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-515",
                color="Yellow",
                floor_name="Floor 1",
            ),
            AccessPoint(
                id="ap2",
                vendor="Cisco",
                model="AP-515",
                color="Yellow",
                floor_name="Floor 1",
            ),
        ]
        antennas = [
            Antenna("ANT-20", "ant1"),
        ]

        calculator = CostCalculator(pricing_db, custom_discount=0, apply_volume_discounts=False)
        ap_summary, antenna_summary, combined_summary = calculator.calculate_total_cost(
            aps, antennas
        )

        assert ap_summary.grand_total == 2000
        assert antenna_summary.grand_total == 100
        assert combined_summary.grand_total == 2100
        assert combined_summary.items_with_prices == 2

    def test_unknown_equipment_zero_price(self, pricing_db):
        """Test that unknown equipment gets $0 price."""
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Unknown",
                model="Model123",
                color="Yellow",
                floor_name="Floor 1",
            )
        ]

        calculator = CostCalculator(pricing_db)
        summary = calculator.calculate_access_points_cost(aps)

        assert summary.items_with_prices == 0
        assert summary.items_without_prices == 1
        assert summary.grand_total == 0

    def test_coverage_percentage(self, pricing_db):
        """Test coverage percentage calculation."""
        aps = [
            AccessPoint(
                id="ap1",
                vendor="Cisco",
                model="AP-515",
                color="Yellow",
                floor_name="Floor 1",
            ),  # Known
            AccessPoint(
                id="ap2",
                vendor="Unknown",
                model="Model",
                color="Yellow",
                floor_name="Floor 1",
            ),  # Unknown
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

    def test_pricing_db_default_file_exists(self):
        """Test PricingDatabase with None uses default file path."""
        # Default pricing file exists in config directory
        db = PricingDatabase(None)
        # Should load successfully from default file
        assert isinstance(db.prices, dict)
        assert isinstance(db.antenna_prices, dict)
        # Default file should have some vendors
        assert len(db.prices) > 0

    def test_pricing_db_default_file_not_found_warning(self, tmp_path, monkeypatch):
        """Test PricingDatabase logs warning when default file doesn't exist."""
        from pathlib import Path
        from unittest.mock import Mock

        # Mock Path(__file__).parent.parent to point to tmp directory without pricing.yaml
        def mock_file_property():
            return tmp_path / "fake_pricing.py"

        # Patch __file__ for pricing module
        monkeypatch.setattr("ekahau_bom.pricing.__file__", str(tmp_path / "pricing.py"))

        db = PricingDatabase(None)

        # Should handle missing default file gracefully
        assert db.prices == {}
        assert db.antenna_prices == {}

    def test_pricing_db_file_not_exists(self, tmp_path):
        """Test PricingDatabase when file doesn't exist."""
        nonexistent_file = tmp_path / "nonexistent.yaml"
        db = PricingDatabase(nonexistent_file)

        # Should not raise error, just log warnings
        assert db.prices == {}
        assert db.antenna_prices == {}

    def test_pricing_db_invalid_yaml(self, tmp_path):
        """Test PricingDatabase with invalid YAML file."""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("{ invalid yaml [[[", encoding="utf-8")

        db = PricingDatabase(invalid_file)

        # Should handle exception gracefully
        assert db.prices == {}
        assert db.antenna_prices == {}

    def test_get_antenna_price_not_found(self, pricing_db):
        """Test get_antenna_price for unknown antenna."""
        price = pricing_db.get_antenna_price("Unknown-Antenna-XYZ")
        assert price is None

    def test_get_volume_discount_no_tier_match(self, pricing_db):
        """Test get_volume_discount when quantity doesn't match any tier."""
        # All tiers in test data: 1-9 (0%), 10-49 (10%), 50+ (20%)
        # Quantity 0 doesn't match any tier
        discount = pricing_db.get_volume_discount(0)
        assert discount == 0.0

    def test_calculate_antennas_cost_without_price(self, pricing_db):
        """Test calculate_antennas_cost with antenna that has no price."""
        antennas = [
            Antenna("Unknown-Antenna-123", None),  # Unknown antenna without price
            Antenna("ANT-20", None),  # Known antenna with price
        ]

        calculator = CostCalculator(pricing_db)
        summary = calculator.calculate_antennas_cost(antennas)

        # Should include both antennas, one with $0 price
        assert len(summary.items) == 2
        assert summary.items_without_prices == 1  # Unknown antenna
        assert summary.items_with_prices == 1  # ANT-20
