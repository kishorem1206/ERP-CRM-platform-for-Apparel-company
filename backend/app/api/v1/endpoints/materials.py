"""Materials endpoints: yarn, fabric, trims, fabric runs, lots."""
from uuid import UUID

from fastapi import APIRouter

from app.api.v1.deps import AuthUser, DBSession
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


@router.get("/lots")
async def list_lots(
    db: DBSession, user: AuthUser,
    material_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    user.require("materials.view")
    svc = MaterialsService(db)
    rows, total = await svc.list_lots(user.company_id, material_type=material_type, page=page, page_size=page_size)
    return ApiResponse(
        success=True,
        data=[LotOut.model_validate(r) for r in rows],
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
