"""Shared SKU-generation logic — kept in one place so every call site
(manual variant creation, Style-driven auto-generation) produces the
identical {code}-{SIZE}-{COLOUR} format."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.master import Colour, Size


async def build_variant_sku(
    db: AsyncSession, product_code: str, size_id: UUID | None, colour_id: UUID | None,
) -> str:
    sku_parts = [product_code]
    if size_id:
        sz = await db.execute(select(Size).where(Size.id == size_id))
        sz_obj = sz.scalar_one_or_none()
        sku_parts.append(sz_obj.name if sz_obj else str(size_id)[:4])
    if colour_id:
        col = await db.execute(select(Colour).where(Colour.id == colour_id))
        col_obj = col.scalar_one_or_none()
        sku_parts.append(col_obj.name.upper()[:3] if col_obj else str(colour_id)[:4])
    return "-".join(sku_parts)
