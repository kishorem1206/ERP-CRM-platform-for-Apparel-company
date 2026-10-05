from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.business_rules import business_rules, BusinessRulesError
from app.models.inventory import InventoryTransaction
from app.models.master import Product, ProductVariant, Warehouse
from app.models.user import User
from app.schemas.inventory import AdjustParams, IssueParams, ReceiveParams, TransferParams


class InventoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_balance(
        self,
        company_id: UUID,
        product_id: UUID,
        warehouse_id: UUID,
        variant_id: UUID | None = None,
    ) -> Decimal:
        result = await self.db.execute(
            text("""
                SELECT COALESCE(SUM(quantity * direction), 0)
                FROM inventory_transactions
                WHERE company_id = :company_id
                  AND product_id = :product_id
                  AND warehouse_id = :warehouse_id
                  AND (CAST(:variant_id AS UUID) IS NULL OR variant_id = CAST(:variant_id AS UUID))
            """),
            {
                "company_id": str(company_id),
                "product_id": str(product_id),
                "warehouse_id": str(warehouse_id),
                "variant_id": str(variant_id) if variant_id else None,
            },
        )
        return Decimal(result.scalar() or 0)

    async def get_total_balance(
        self,
        company_id: UUID,
        product_id: UUID,
        variant_id: UUID | None = None,
    ) -> Decimal:
        """Physical balance across ALL warehouses - used for the Sales Order
        availability check (ERP Upgrade §2), where a warehouse hasn't been
        chosen yet (that only happens at Delivery time)."""
        result = await self.db.execute(
            text("""
                SELECT COALESCE(SUM(quantity * direction), 0)
                FROM inventory_transactions
                WHERE company_id = :company_id
                  AND product_id = :product_id
                  AND (CAST(:variant_id AS UUID) IS NULL OR variant_id = CAST(:variant_id AS UUID))
            """),
            {
                "company_id": str(company_id),
                "product_id": str(product_id),
                "variant_id": str(variant_id) if variant_id else None,
            },
        )
        return Decimal(result.scalar() or 0)

    async def receive(self, params: ReceiveParams, user_id: UUID) -> InventoryTransaction:
        tx = InventoryTransaction(
            company_id=params.company_id,
            transaction_type="stock_in",
            reference_type=params.reference_type,
            reference_id=params.reference_id,
            material_type=params.material_type,
            product_id=params.product_id,
            variant_id=params.variant_id,
            warehouse_id=params.warehouse_id,
            lot_id=params.lot_id,
            quantity=params.quantity,
            unit_id=params.unit_id,
            unit_cost=params.unit_cost,
            total_cost=params.quantity * params.unit_cost,
            direction=1,
            transaction_date=params.transaction_date,
            notes=params.notes,
            created_by=user_id,
        )
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def issue(
        self,
        params: IssueParams,
        user_id: UUID,
        negative_stock_allowed: bool = False,
    ) -> InventoryTransaction:
        available = await self.get_balance(
            params.company_id, params.product_id, params.warehouse_id, params.variant_id
        )
        result = business_rules.validate_stock_issue(available, params.quantity, negative_stock_allowed)
        if not result.valid:
            raise BusinessRulesError("INSUFFICIENT_STOCK", result.reason)

        tx = InventoryTransaction(
            company_id=params.company_id,
            transaction_type="stock_out",
            reference_type=params.reference_type,
            reference_id=params.reference_id,
            material_type=params.material_type,
            product_id=params.product_id,
            variant_id=params.variant_id,
            warehouse_id=params.warehouse_id,
            lot_id=params.lot_id,
            quantity=params.quantity,
            unit_id=params.unit_id,
            unit_cost=params.unit_cost,
            total_cost=params.quantity * params.unit_cost,
            direction=-1,
            transaction_date=params.transaction_date,
            notes=params.notes,
            created_by=user_id,
        )
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def transfer(
        self,
        params: TransferParams,
        user_id: UUID,
        negative_stock_allowed: bool = False,
    ) -> tuple[InventoryTransaction, InventoryTransaction]:
        available = await self.get_balance(
            params.company_id, params.product_id, params.from_warehouse_id, params.variant_id
        )
        result = business_rules.validate_stock_transfer(
            params.from_warehouse_id,
            params.to_warehouse_id,
            available,
            params.quantity,
            negative_stock_allowed,
        )
        if not result.valid:
            raise BusinessRulesError("TRANSFER_INVALID", result.reason)

        # Shared group id - both sides of one transfer stay correlated by a
        # hard value, not by matching quantity/date/notes after the fact.
        group_id = uuid4()

        out_tx = InventoryTransaction(
            company_id=params.company_id,
            transaction_type="transfer_out",
            material_type=params.material_type,
            product_id=params.product_id,
            variant_id=params.variant_id,
            warehouse_id=params.from_warehouse_id,
            quantity=params.quantity,
            unit_id=params.unit_id,
            unit_cost=params.unit_cost,
            total_cost=params.quantity * params.unit_cost,
            direction=-1,
            transaction_date=params.transaction_date,
            notes=params.notes,
            transfer_group_id=group_id,
            created_by=user_id,
        )
        in_tx = InventoryTransaction(
            company_id=params.company_id,
            transaction_type="transfer_in",
            material_type=params.material_type,
            product_id=params.product_id,
            variant_id=params.variant_id,
            warehouse_id=params.to_warehouse_id,
            quantity=params.quantity,
            unit_id=params.unit_id,
            unit_cost=params.unit_cost,
            total_cost=params.quantity * params.unit_cost,
            direction=1,
            transaction_date=params.transaction_date,
            notes=params.notes,
            transfer_group_id=group_id,
            created_by=user_id,
        )
        self.db.add(out_tx)
        self.db.add(in_tx)
        await self.db.flush()
        return out_tx, in_tx

    async def adjust(self, params: AdjustParams, user_id: UUID) -> InventoryTransaction | None:
        """Unified Add/Reduce/Replace (ERP Upgrade §8) - one workflow, one
        endpoint. `quantity` means the amount to add/reduce, or the target
        balance itself for `replace`."""
        current = await self.get_balance(
            params.company_id, params.product_id, params.warehouse_id, params.variant_id
        )
        if params.adjustment_type == "add":
            new_balance = current + params.quantity
        elif params.adjustment_type == "reduce":
            new_balance = current - params.quantity
        else:  # replace
            new_balance = params.quantity

        result = business_rules.validate_stock_adjustment(new_balance)
        if not result.valid:
            raise BusinessRulesError("NEGATIVE_BALANCE", result.reason)

        delta = new_balance - current
        if delta == Decimal("0"):
            return None
        direction = 1 if delta > 0 else -1
        tx = InventoryTransaction(
            company_id=params.company_id,
            transaction_type="adjustment",
            material_type=params.material_type,
            product_id=params.product_id,
            variant_id=params.variant_id,
            warehouse_id=params.warehouse_id,
            quantity=abs(delta),
            unit_id=params.unit_id,
            unit_cost=params.unit_cost,
            total_cost=abs(delta) * params.unit_cost,
            direction=direction,
            transaction_date=params.transaction_date,
            notes=params.reason,
            previous_balance=current,
            new_balance=new_balance,
            adjustment_type=params.adjustment_type,
            created_by=user_id,
        )
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def list_transactions(
        self,
        company_id: UUID,
        product_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        transaction_type: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list, int]:
        """Returns (InventoryTransaction, product_name, sku, warehouse_name,
        created_by_name) tuples - ERP Upgrade §12 needs the Transaction Log
        to show real names, not raw UUIDs (confirmed the frontend was
        literally rendering product_id/warehouse_id as text)."""
        base = select(InventoryTransaction).where(InventoryTransaction.company_id == company_id)
        if product_id:
            base = base.where(InventoryTransaction.product_id == product_id)
        if warehouse_id:
            base = base.where(InventoryTransaction.warehouse_id == warehouse_id)
        if transaction_type:
            base = base.where(InventoryTransaction.transaction_type == transaction_type)
        if from_date:
            base = base.where(InventoryTransaction.transaction_date >= from_date)
        if to_date:
            base = base.where(InventoryTransaction.transaction_date <= to_date)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0

        q = (
            select(
                InventoryTransaction,
                Product.name,
                ProductVariant.sku,
                Warehouse.name,
                User.full_name,
            )
            .select_from(InventoryTransaction)
            .join(Product, Product.id == InventoryTransaction.product_id)
            .outerjoin(ProductVariant, ProductVariant.id == InventoryTransaction.variant_id)
            .join(Warehouse, Warehouse.id == InventoryTransaction.warehouse_id)
            .outerjoin(User, User.id == InventoryTransaction.created_by)
            .where(InventoryTransaction.company_id == company_id)
        )
        if product_id:
            q = q.where(InventoryTransaction.product_id == product_id)
        if warehouse_id:
            q = q.where(InventoryTransaction.warehouse_id == warehouse_id)
        if transaction_type:
            q = q.where(InventoryTransaction.transaction_type == transaction_type)
        if from_date:
            q = q.where(InventoryTransaction.transaction_date >= from_date)
        if to_date:
            q = q.where(InventoryTransaction.transaction_date <= to_date)
        q = q.order_by(InventoryTransaction.transaction_date.desc(), InventoryTransaction.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(q)).all()
        return rows, total

    async def get_stock_balance(
        self,
        company_id: UUID,
        product_id: UUID | None = None,
        category_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        customer_id: UUID | None = None,
        status: str = "all",
    ) -> list[dict]:
        having = {
            "in_stock": "HAVING SUM(it.quantity * it.direction) > 0",
            "out_of_stock": "HAVING SUM(it.quantity * it.direction) <= 0",
        }.get(status, "")
        result = await self.db.execute(
            text(f"""
                SELECT
                    p.id::text   AS product_id,
                    p.name       AS product_name,
                    p.product_type,
                    p.category_id::text AS category_id,
                    c.name       AS category_name,
                    it.variant_id::text AS variant_id,
                    v.sku        AS sku,
                    w.id::text   AS warehouse_id,
                    w.name       AS warehouse_name,
                    u.abbreviation     AS unit_symbol,
                    SUM(it.quantity * it.direction) AS balance,
                    SUM(it.quantity * it.direction * it.unit_cost) AS stock_value
                FROM inventory_transactions it
                JOIN products   p ON p.id = it.product_id
                JOIN warehouses w ON w.id = it.warehouse_id
                JOIN units      u ON u.id = it.unit_id
                LEFT JOIN categories        c ON c.id = p.category_id
                LEFT JOIN product_variants  v ON v.id = it.variant_id
                WHERE it.company_id = :cid
                  AND (CAST(:product_id AS UUID) IS NULL OR p.id = CAST(:product_id AS UUID))
                  AND (CAST(:category_id AS UUID) IS NULL OR p.category_id = CAST(:category_id AS UUID))
                  AND (CAST(:warehouse_id AS UUID) IS NULL OR w.id = CAST(:warehouse_id AS UUID))
                  AND (
                    CAST(:customer_id AS UUID) IS NULL OR EXISTS (
                        SELECT 1 FROM sales_order_items soi
                        JOIN sales_orders so ON so.id = soi.sales_order_id
                        WHERE so.customer_id = CAST(:customer_id AS UUID)
                          AND so.status != 'cancelled'
                          AND soi.product_id = p.id
                    )
                  )
                GROUP BY p.id, p.name, p.product_type, p.category_id, c.name,
                         it.variant_id, v.sku, w.id, w.name, u.abbreviation
                {having}
                ORDER BY w.name, p.name
            """),
            {
                "cid": str(company_id),
                "product_id": str(product_id) if product_id else None,
                "category_id": str(category_id) if category_id else None,
                "warehouse_id": str(warehouse_id) if warehouse_id else None,
                "customer_id": str(customer_id) if customer_id else None,
            },
        )
        return [dict(row._mapping) for row in result]
