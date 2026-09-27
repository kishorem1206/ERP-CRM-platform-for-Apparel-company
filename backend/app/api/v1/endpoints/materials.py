"""Materials endpoints: yarn, fabric, trims, fabric runs, lots."""
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.v1.deps import AuthUser, DBSession
from app.models.inventory import InventoryTransaction
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.materials import (
    FabricCreate, FabricRunCreate, FabricRunOut,
    LotOut, TrimCreate, YarnCreate,
)
from app.services.materials import MaterialsService

router = APIRouter(prefix="/materials", tags=["materials"])


@router.post("/yarn", status_code=201)
async def add_yarn(body: YarnCreate, db: DBSession, user: AuthUser):
    user.require("materials.create")
    svc = MaterialsService(db)
    lot = await svc.create_yarn(body, user.company_id, user.user_id)
    await db.commit()
    await db.refresh(lot)
    return ApiResponse(success=True, data=LotOut.model_validate(lot))


@router.post("/fabric", status_code=201)
async def add_fabric(body: FabricCreate, db: DBSession, user: AuthUser):
    user.require("materials.create")
    svc = MaterialsService(db)
    lot = await svc.create_fabric(body, user.company_id, user.user_id)
    await db.commit()
    await db.refresh(lot)
    return ApiResponse(success=True, data=LotOut.model_validate(lot))


@router.post("/trims", status_code=201)
async def add_trim(body: TrimCreate, db: DBSession, user: AuthUser):
    user.require("materials.create")
    svc = MaterialsService(db)
    lot = await svc.create_trim(body, user.company_id, user.user_id)
    await db.commit()
    await db.refresh(lot)
    return ApiResponse(success=True, data=LotOut.model_validate(lot))


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

    data = []
    for r in rows:
        out = LotOut.model_validate(r)
        out.stock_qty = stock_map.get(str(r.id))
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
    return ApiResponse(success=True, data=LotOut.model_validate(lot))


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
