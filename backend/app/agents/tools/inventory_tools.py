"""
Inventory agent tools.
All write tools require a two-step flow: first call returns requires_confirmation=True,
second call (with confirmed=True) executes.
"""
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.base import ToolResult, permission_denied, rule_violation
from app.domain.business_rules import business_rules, BusinessRulesError
from app.services.inventory import InventoryService


async def tool_get_stock(
    *,
    db: AsyncSession,
    company_id: UUID,
    product_id: UUID,
    warehouse_id: UUID | None,
    permissions: list[str],
) -> ToolResult:
    if "inventory.view" not in permissions:
        return permission_denied("inventory.view")

    service = InventoryService(db)

    if warehouse_id:
        qty = await service.get_balance(company_id, product_id, warehouse_id)
        return ToolResult(success=True, data={"quantity": float(qty), "warehouse_id": str(warehouse_id)})

    # All warehouses — aggregate
    from sqlalchemy import text
    result = await db.execute(
        text("""
            SELECT warehouse_id, SUM(quantity * direction) as qty,
                   SUM(total_cost * direction) as value
            FROM inventory_transactions
            WHERE company_id = :cid AND product_id = :pid
            GROUP BY warehouse_id
        """),
        {"cid": str(company_id), "pid": str(product_id)},
    )
    rows = result.all()
    return ToolResult(success=True, data={
        "warehouses": [
            {"warehouse_id": str(r[0]), "quantity": float(r[1]), "value": float(r[2])}
            for r in rows
        ],
        "total_qty": float(sum(r[1] for r in rows)),
    })


async def tool_create_stock_transfer(
    *,
    db: AsyncSession,
    company_id: UUID,
    user_id: UUID,
    product_id: UUID,
    from_warehouse_id: UUID,
    to_warehouse_id: UUID,
    quantity: Decimal,
    unit_id: UUID,
    unit_cost: Decimal,
    transaction_date: date,
    notes: str | None,
    permissions: list[str],
    confirmed: bool,
    negative_stock_allowed: bool = False,
) -> ToolResult:
    if "inventory.transfer" not in permissions:
        return permission_denied("inventory.transfer")

    service = InventoryService(db)
    available = await service.get_balance(company_id, product_id, from_warehouse_id)

    result = business_rules.validate_stock_transfer(
        from_warehouse_id, to_warehouse_id, available, quantity, negative_stock_allowed
    )
    if not result.valid:
        return rule_violation(result.reason)

    if not confirmed:
        return ToolResult(
            success=True,
            requires_confirmation=True,
            confirmation_summary=(
                f"Transfer {quantity} units of product {product_id}\n"
                f"From: Warehouse {from_warehouse_id}\n"
                f"To: Warehouse {to_warehouse_id}\n"
                f"Date: {transaction_date}"
            ),
        )

    from app.schemas.inventory import TransferParams
    params = TransferParams(
        company_id=company_id,
        product_id=product_id,
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        quantity=quantity,
        unit_id=unit_id,
        unit_cost=unit_cost,
        transaction_date=transaction_date,
        material_type="finished_good",
        notes=notes,
    )
    out_tx, in_tx = await service.transfer(params, user_id, negative_stock_allowed)
    return ToolResult(
        success=True,
        data={"out_tx_id": str(out_tx.id), "in_tx_id": str(in_tx.id)},
        audit_action="inventory_transfer",
    )
