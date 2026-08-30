"""Unit tests for PricingService and TaxService — pure arithmetic, no DB."""
import pytest
from decimal import Decimal
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.services.pricing import PricingService, TaxService

pytestmark = pytest.mark.unit


class TestCostSheet:
    def test_basic_cost_sheet(self):
        svc = PricingService()
        components = [
            {"name": "Fabric", "qty": Decimal("2.5"), "unit_cost": Decimal("100")},
            {"name": "Thread", "qty": Decimal("1"), "unit_cost": Decimal("20")},
        ]
        sheet = svc.calculate_cost_sheet(
            components=components,
            wastage_pct=Decimal("5"),
            overhead_pct=Decimal("10"),
            margin_pct=Decimal("20"),
        )
        raw = Decimal("2.5") * Decimal("100") + Decimal("1") * Decimal("20")  # 270
        wastage_amt = (raw * Decimal("5") / 100).quantize(Decimal("0.01"))
        cost_after_wastage = raw + wastage_amt  # 283.50
        overhead_amt = (cost_after_wastage * Decimal("10") / 100).quantize(Decimal("0.01"))
        total_cost = cost_after_wastage + overhead_amt  # 311.85
        selling = (total_cost / (1 - Decimal("20") / 100)).quantize(Decimal("0.01"))

        assert sheet.raw_material_cost == raw
        assert sheet.cost_after_wastage == cost_after_wastage
        assert sheet.total_cost == total_cost
        assert sheet.selling_price == selling

    def test_zero_margin_returns_cost_as_price(self):
        svc = PricingService()
        components = [{"name": "Material", "qty": Decimal("1"), "unit_cost": Decimal("500")}]
        sheet = svc.calculate_cost_sheet(
            components=components,
            wastage_pct=Decimal("0"),
            overhead_pct=Decimal("0"),
            margin_pct=Decimal("0"),
        )
        assert sheet.selling_price == Decimal("500.00")

    def test_no_float_used(self):
        """selling_price and total_cost must always be Decimal, never float."""
        svc = PricingService()
        components = [{"name": "X", "qty": Decimal("3"), "unit_cost": Decimal("33.33")}]
        sheet = svc.calculate_cost_sheet(
            components=components,
            wastage_pct=Decimal("2"),
            overhead_pct=Decimal("8"),
            margin_pct=Decimal("15"),
        )
        assert isinstance(sheet.selling_price, Decimal)
        assert isinstance(sheet.total_cost, Decimal)


class TestTaxDetermination:
    """TaxService.determine_tax is async and requires DB; test the sync helpers here."""

    def test_intrastate_same_state(self):
        svc = TaxService()
        assert svc.is_intrastate("27", "27") is True

    def test_interstate_different_states(self):
        svc = TaxService()
        assert svc.is_intrastate("27", "29") is False

    def test_split_rate_intrastate(self):
        svc = TaxService()
        cgst, sgst, igst = svc.split_rate(Decimal("12"), intrastate=True)
        assert cgst == Decimal("6")
        assert sgst == Decimal("6")
        assert igst == Decimal("0")

    def test_split_rate_interstate(self):
        svc = TaxService()
        cgst, sgst, igst = svc.split_rate(Decimal("18"), intrastate=False)
        assert cgst == Decimal("0")
        assert sgst == Decimal("0")
        assert igst == Decimal("18")

    def test_tax_amounts_use_decimal(self):
        svc = TaxService()
        taxable = Decimal("10000")
        cgst, sgst, igst = svc.split_rate(Decimal("5"), intrastate=True)
        cgst_amt = (taxable * cgst / 100).quantize(Decimal("0.01"))
        assert isinstance(cgst_amt, Decimal)
        assert cgst_amt == Decimal("250.00")
