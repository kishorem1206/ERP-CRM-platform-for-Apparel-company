from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass
class RuleResult:
    valid: bool
    reason: str | None = None


class BusinessRulesError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class BusinessRulesEngine:
    """
    Deterministic rule enforcement layer.
    Sits between agent tools / API endpoints and domain services.
    Rules here are Python logic — never LLM-driven.
    """

    # ── Inventory ──────────────────────────────────────────────

    def validate_stock_issue(
        self,
        available: Decimal,
        requested: Decimal,
        negative_stock_allowed: bool = False,
    ) -> RuleResult:
        if requested <= 0:
            return RuleResult(False, "Issue quantity must be greater than zero.")
        if not negative_stock_allowed and requested > available:
            return RuleResult(
                False,
                f"Insufficient stock. Available: {available}, Requested: {requested}.",
            )
        return RuleResult(True)

    def validate_stock_transfer(
        self,
        from_warehouse_id: UUID,
        to_warehouse_id: UUID,
        available: Decimal,
        requested: Decimal,
        negative_stock_allowed: bool = False,
    ) -> RuleResult:
        if from_warehouse_id == to_warehouse_id:
            return RuleResult(False, "Source and destination warehouse must be different.")
        return self.validate_stock_issue(available, requested, negative_stock_allowed)

    def validate_stock_adjustment(self, new_qty: Decimal) -> RuleResult:
        if new_qty < 0:
            return RuleResult(False, "Adjusted quantity cannot be negative.")
        return RuleResult(True)

    # ── Sales ──────────────────────────────────────────────────

    def validate_quotation_conversion(self, quotation_status: str) -> RuleResult:
        allowed = {"draft", "sent", "approved"}
        if quotation_status not in allowed:
            return RuleResult(
                False,
                f"Cannot convert quotation in '{quotation_status}' status. Must be draft, sent, or approved.",
            )
        return RuleResult(True)

    def validate_delivery_quantity(
        self, ordered: Decimal, already_delivered: Decimal, now_delivering: Decimal
    ) -> RuleResult:
        if now_delivering <= 0:
            return RuleResult(False, "Delivery quantity must be greater than zero.")
        remaining = ordered - already_delivered
        if now_delivering > remaining:
            return RuleResult(
                False,
                f"Cannot deliver {now_delivering}. Only {remaining} remaining on order.",
            )
        return RuleResult(True)

    def validate_invoice_creation(self, sales_order_status: str) -> RuleResult:
        if sales_order_status == "cancelled":
            return RuleResult(False, "Cannot invoice a cancelled sales order.")
        return RuleResult(True)

    # ── Purchase ──────────────────────────────────────────────

    def validate_purchase_receipt(
        self, ordered: Decimal, already_received: Decimal, now_receiving: Decimal
    ) -> RuleResult:
        if now_receiving <= 0:
            return RuleResult(False, "Receipt quantity must be greater than zero.")
        remaining = ordered - already_received
        if now_receiving > remaining:
            return RuleResult(
                False,
                f"Cannot receive {now_receiving}. Only {remaining} outstanding on PO.",
            )
        return RuleResult(True)

    # ── Production ────────────────────────────────────────────

    def validate_lot_closure(
        self, has_incomplete_required_stages: bool
    ) -> RuleResult:
        if has_incomplete_required_stages:
            return RuleResult(
                False,
                "Cannot close production lot: required stages are not yet completed.",
            )
        return RuleResult(True)

    def validate_material_issue(
        self,
        available: Decimal,
        requested: Decimal,
        planned: Decimal,
        variance_pct_allowed: Decimal,
        variance_permission: bool = False,
        negative_stock_allowed: bool = False,
    ) -> RuleResult:
        # First check stock
        stock_result = self.validate_stock_issue(available, requested, negative_stock_allowed)
        if not stock_result.valid:
            return stock_result
        # Check variance against BOM
        if planned > 0:
            variance = abs(requested - planned) / planned * 100
            if variance > variance_pct_allowed and not variance_permission:
                return RuleResult(
                    False,
                    f"Material issue exceeds allowed variance ({variance:.1f}% > {variance_pct_allowed}%). "
                    "Requires variance permission.",
                )
        return RuleResult(True)

    def validate_production_lot_reopen(self, status: str) -> RuleResult:
        if status == "completed":
            return RuleResult(False, "Cannot reopen a completed production lot.")
        return RuleResult(True)

    # ── Finance ───────────────────────────────────────────────

    def validate_financial_deletion(self) -> RuleResult:
        return RuleResult(False, "Financial transactions cannot be deleted.")

    def validate_payment_modification(self, status: str) -> RuleResult:
        if status == "completed":
            return RuleResult(False, "Cannot modify a completed payment.")
        return RuleResult(True)

    # ── General ───────────────────────────────────────────────

    def validate_self_approval(
        self, created_by: UUID, approving_user: UUID, sod_enabled: bool
    ) -> RuleResult:
        if sod_enabled and created_by == approving_user:
            return RuleResult(
                False,
                "Segregation of duties: you cannot approve your own transaction.",
            )
        return RuleResult(True)


# Singleton
business_rules = BusinessRulesEngine()
