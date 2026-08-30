"""Unit tests for BusinessRulesEngine — no DB, no I/O."""
import pytest
from decimal import Decimal
from uuid import uuid4
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.domain.business_rules import BusinessRulesEngine

pytestmark = pytest.mark.unit


@pytest.fixture
def rules():
    return BusinessRulesEngine()


class TestStockIssue:
    def test_sufficient_stock_passes(self, rules):
        result = rules.validate_stock_issue(
            available=Decimal("100"), requested=Decimal("50"), negative_stock_allowed=False
        )
        assert result.valid

    def test_exact_stock_passes(self, rules):
        result = rules.validate_stock_issue(
            available=Decimal("100"), requested=Decimal("100"), negative_stock_allowed=False
        )
        assert result.valid

    def test_insufficient_stock_fails(self, rules):
        result = rules.validate_stock_issue(
            available=Decimal("40"), requested=Decimal("50"), negative_stock_allowed=False
        )
        assert not result.valid
        assert "stock" in result.reason.lower()

    def test_negative_stock_allowed_passes_when_insufficient(self, rules):
        result = rules.validate_stock_issue(
            available=Decimal("5"), requested=Decimal("50"), negative_stock_allowed=True
        )
        assert result.valid

    def test_zero_available_fails(self, rules):
        result = rules.validate_stock_issue(
            available=Decimal("0"), requested=Decimal("1"), negative_stock_allowed=False
        )
        assert not result.valid


class TestStockTransfer:
    def test_same_warehouse_fails(self, rules):
        wh = uuid4()
        result = rules.validate_stock_transfer(
            from_warehouse_id=wh,
            to_warehouse_id=wh,
            available=Decimal("100"),
            requested=Decimal("10"),
        )
        assert not result.valid

    def test_insufficient_quantity_fails(self, rules):
        result = rules.validate_stock_transfer(
            from_warehouse_id=uuid4(),
            to_warehouse_id=uuid4(),
            available=Decimal("5"),
            requested=Decimal("20"),
        )
        assert not result.valid

    def test_valid_transfer_passes(self, rules):
        result = rules.validate_stock_transfer(
            from_warehouse_id=uuid4(),
            to_warehouse_id=uuid4(),
            available=Decimal("100"),
            requested=Decimal("50"),
        )
        assert result.valid


class TestSelfApproval:
    def test_same_user_rejected(self, rules):
        uid = uuid4()
        result = rules.validate_self_approval(
            created_by=uid, approving_user=uid, sod_enabled=True
        )
        assert not result.valid

    def test_same_user_sod_disabled_passes(self, rules):
        uid = uuid4()
        result = rules.validate_self_approval(
            created_by=uid, approving_user=uid, sod_enabled=False
        )
        assert result.valid

    def test_different_user_passes(self, rules):
        result = rules.validate_self_approval(
            created_by=uuid4(), approving_user=uuid4(), sod_enabled=True
        )
        assert result.valid


class TestFinancialDeletion:
    def test_always_blocked(self, rules):
        result = rules.validate_financial_deletion()
        assert not result.valid


class TestQuotationConversion:
    def test_draft_can_convert(self, rules):
        result = rules.validate_quotation_conversion(quotation_status="draft")
        assert result.valid

    def test_approved_can_convert(self, rules):
        result = rules.validate_quotation_conversion(quotation_status="approved")
        assert result.valid

    def test_cancelled_cannot_convert(self, rules):
        result = rules.validate_quotation_conversion(quotation_status="cancelled")
        assert not result.valid

    def test_completed_cannot_convert(self, rules):
        result = rules.validate_quotation_conversion(quotation_status="completed")
        assert not result.valid


class TestMaterialIssue:
    def test_within_variance_passes(self, rules):
        result = rules.validate_material_issue(
            available=Decimal("100"),
            requested=Decimal("52"),
            planned=Decimal("50"),
            variance_pct_allowed=Decimal("5"),
            variance_permission=False,
            negative_stock_allowed=False,
        )
        assert result.valid

    def test_exceeds_variance_fails(self, rules):
        result = rules.validate_material_issue(
            available=Decimal("100"),
            requested=Decimal("60"),
            planned=Decimal("50"),
            variance_pct_allowed=Decimal("5"),
            variance_permission=False,
            negative_stock_allowed=False,
        )
        assert not result.valid

    def test_insufficient_stock_fails_regardless_of_variance(self, rules):
        result = rules.validate_material_issue(
            available=Decimal("10"),
            requested=Decimal("12"),
            planned=Decimal("50"),
            variance_pct_allowed=Decimal("5"),
            variance_permission=False,
            negative_stock_allowed=False,
        )
        assert not result.valid
