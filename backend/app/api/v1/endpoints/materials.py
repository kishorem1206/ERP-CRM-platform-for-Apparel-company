"""Materials endpoints: yarn, fabric, trims, fabric runs, lots."""
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.v1.deps import AuthUser, DBSession
from app.models.inventory import InventoryTransaction
from app.models.master import Brand, Product
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.materials import (
    FabricCreate, FabricRunCreate, FabricRunOut,
    LotOut, TrimCreate, YarnCreate,
)
from app.services.materials import MaterialsService

router = APIRouter(prefix="/materials", tags=["materials"])


async def _resolve_product_name(db: DBSession, product_id: UUID | None) -> str | None:
    if not product_id:
        return None
    return (await db.execute(select(Product.name).where(Product.id == product_id))).scalar_one_or_none()


async def _resolve_brand_name(db: DBSession, brand_id: UUID | None) -> str | None:
    if not brand_id:
        return None
    return (await db.execute(select(Brand.name).where(Brand.id == brand_id))).scalar_one_or_none()


@router.post("/yarn", status_code=201)
async def add_yarn(body: YarnCreate, db: DBSession, user: AuthUser):
    user.require("materials.create")
    svc = MaterialsService(db)
    lot = await svc.create_yarn(body, user.company_id, user.user_id)
    await db.commit()
    await db.refresh(lot)
    out = LotOut.model_validate(lot)
    out.product_name = await _resolve_product_name(db, lot.product_id)
    out.brand_name = await _resolve_brand_name(db, lot.brand_id)
    return ApiResponse(success=True, data=out)


@router.post("/fabric", status_code=201)
async def add_fabric(body: FabricCreate, db: DBSession, user: AuthUser):
    user.require("materials.create")
    svc = MaterialsService(db)
    lot = await svc.create_fabric(body, user.company_id, user.user_id)
    await db.commit()
    await db.refresh(lot)
    out = LotOut.model_validate(lot)
    out.product_name = await _resolve_product_name(db, lot.product_id)
    out.brand_name = await _resolve_brand_name(db, lot.brand_id)
    return ApiResponse(success=True, data=out)


@router.post("/trims", status_code=201)
async def add_trim(body: TrimCreate, db: DBSession, user: AuthUser):
    user.require("materials.create")
    svc = MaterialsService(db)
    lot = await svc.create_trim(body, user.company_id, user.user_id)
    await db.commit()
    await db.refresh(lot)
    out = LotOut.model_validate(lot)
    out.product_name = await _resolve_product_name(db, lot.product_id)
    out.brand_name = await _resolve_brand_name(db, lot.brand_id)
    return ApiResponse(success=True, data=out)


@router.post("/fabric-runs", status_code=201)
async def create_fabric_run(body: FabricRunCreate, db: DBSession, user: AuthUser):
    user.require("materials.create")
    svc = MaterialsService(db)
    run = await svc.create_fabric_run(body, user.company_id, user.user_id)
    await db.commit()
    await db.refresh(run)
    return ApiResponse(success=True, data=FabricRunOut.model_validate(run))


@router.get("/lots/trim-types")
async def list_trim_types(db: DBSession, user: AuthUser):
    user.require("materials.view")
    svc = MaterialsService(db)
    rows = await svc.list_trim_types(user.company_id)
    return ApiResponse(success=True, data=[{"trim_type": t, "count": c} for t, c in rows])


@router.get("/lots")
async def list_lots(
    db: DBSession, user: AuthUser,
    material_type: str | None = None,
    trim_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    user.require("materials.view")
    svc = MaterialsService(db)
    rows, total = await svc.list_lots(
        user.company_id, material_type=material_type, trim_type=trim_type,
        page=page, page_size=page_size,
    )

    # Compute stock per lot from the ledger
    lot_ids = [r.id for r in rows]
    stock_map: dict[str, float] = {}
    if lot_ids:
        stock_rows = await db.execute(
            select(InventoryTransaction.lot_id, func.sum(InventoryTransaction.quantity).label("qty"))
            .where(InventoryTransaction.lot_id.in_(lot_ids))
            .group_by(InventoryTransaction.lot_id)
        )
        stock_map = {str(row.lot_id): float(row.qty or 0) for row in stock_rows}

    # Resolve linked product names in one batch — same source of truth the
    # Products catalog itself uses, so a lot's category can never silently
    # drift from the product it's linked to.
    product_ids = {r.product_id for r in rows if r.product_id}
    product_name_map: dict[str, str] = {}
    if product_ids:
        product_rows = await db.execute(select(Product.id, Product.name).where(Product.id.in_(product_ids)))
        product_name_map = {str(p.id): p.name for p in product_rows}

    brand_ids = {r.brand_id for r in rows if r.brand_id}
    brand_name_map: dict[str, str] = {}
    if brand_ids:
        brand_rows = await db.execute(select(Brand.id, Brand.name).where(Brand.id.in_(brand_ids)))
        brand_name_map = {str(b.id): b.name for b in brand_rows}

    data = []
    for r in rows:
        out = LotOut.model_validate(r)
        out.stock_qty = stock_map.get(str(r.id))
        out.product_name = product_name_map.get(str(r.product_id)) if r.product_id else None
        out.brand_name = brand_name_map.get(str(r.brand_id)) if r.brand_id else None
        data.append(out)

    return ApiResponse(
        success=True,
        data=data,
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/lots/{lot_id}")
async def get_lot(lot_id: UUID, db: DBSession, user: AuthUser):
    user.require("materials.view")
    from sqlalchemy import select
    from app.models.inventory import InventoryLot
    result = await db.execute(
        select(InventoryLot).where(
            InventoryLot.id == lot_id,
            InventoryLot.company_id == user.company_id,
        )
    )
    lot = result.scalar_one_or_none()
    if not lot:
        from fastapi import HTTPException
        raise HTTPException(404, "Lot not found")
    out = LotOut.model_validate(lot)
    out.product_name = await _resolve_product_name(db, lot.product_id)
    out.brand_name = await _resolve_brand_name(db, lot.brand_id)
    return ApiResponse(success=True, data=out)


@router.get("/fabric-runs")
async def list_fabric_runs(
    db: DBSession, user: AuthUser,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    user.require("materials.view")
    svc = MaterialsService(db)
    rows, total = await svc.list_fabric_runs(user.company_id, status=status, page=page, page_size=page_size)
    return ApiResponse(
        success=True,
        data=[FabricRunOut.model_validate(r) for r in rows],
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )
