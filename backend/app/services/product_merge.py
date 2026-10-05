"""Product Merge (ERP Upgrade §10) - consolidates a duplicate product into
a master product. Every table referencing products.id gets repointed in
one atomic transaction; the source product is deactivated (never deleted)
and marked with what it was merged into, so history stays traceable.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.master import Product
from app.models.product_merge import ProductMergeLog

# Every other table with a product_id (or equivalently-named) FK to
# products.id, confirmed by a full repo sweep before writing this -
# missing even one here would leave orphaned/inconsistent data after a
# merge. product_variants is handled separately (reparented, not just
# repointed) since it's products' own child table, not a transaction.
_REPOINT_TABLES: list[tuple[str, str]] = [
    ("inventory_lots", "product_id"),
    ("inventory_transactions", "product_id"),
    ("crm_quote_items", "erp_product_id"),
    ("crm_lead_products", "product_id"),
    ("purchase_order_items", "product_id"),
    ("purchase_entry_items", "product_id"),
    ("material_issue_items", "product_id"),
    ("production_outputs", "product_id"),
    ("price_list_items", "product_id"),
    ("price_history", "product_id"),
    ("quotation_items", "product_id"),
    ("sales_order_items", "product_id"),
    ("delivery_items", "product_id"),
]


class ProductMergeError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class MergeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def merge_products(
        self, company_id: UUID, source_id: UUID, target_id: UUID, user_id: UUID, notes: str | None,
    ) -> tuple[Product, ProductMergeLog]:
        if source_id == target_id:
            raise ProductMergeError("Cannot merge a product into itself.")

        source = (await self.db.execute(
            select(Product).where(Product.id == source_id, Product.company_id == company_id)
        )).scalar_one_or_none()
        if not source:
            raise ProductMergeError("Source product not found.")

        target = (await self.db.execute(
            select(Product).where(Product.id == target_id, Product.company_id == company_id)
        )).scalar_one_or_none()
        if not target:
            raise ProductMergeError("Target product not found.")

        if source.merged_into_id is not None:
            raise ProductMergeError(f"'{source.name}' was already merged into another product and cannot be merged again.")
        if not target.is_active:
            raise ProductMergeError(f"'{target.name}' is inactive (or itself merged away) and cannot be a merge target.")

        source_code, source_name = source.code, source.name
        target_code, target_name = target.code, target.name

        # Reparent the source's own variants under the target - their SKUs
        # and history survive unchanged, only their parent product moves.
        await self.db.execute(
            text("UPDATE product_variants SET product_id = :target WHERE product_id = :source"),
            {"target": str(target_id), "source": str(source_id)},
        )

        for table, column in _REPOINT_TABLES:
            await self.db.execute(
                text(f"UPDATE {table} SET {column} = :target WHERE {column} = :source"),
                {"target": str(target_id), "source": str(source_id)},
            )

        now = datetime.now(timezone.utc)
        source.is_active = False
        source.deleted_at = now
        source.merged_into_id = target_id

        log = ProductMergeLog(
            company_id=company_id,
            source_product_id=source_id, source_code=source_code, source_name=source_name,
            target_product_id=target_id, target_code=target_code, target_name=target_name,
            notes=notes, merged_by=user_id, merged_at=now,
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(target)
        return target, log

    async def list_merge_logs(self, company_id: UUID, page: int = 1, page_size: int = 50) -> tuple[list[ProductMergeLog], int]:
        from sqlalchemy import func
        q = select(ProductMergeLog).where(ProductMergeLog.company_id == company_id)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        q = q.order_by(ProductMergeLog.merged_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()
        return rows, total
