"""Master data reference endpoints — categories, sizes, colours, units, warehouses, HSN."""
from fastapi import APIRouter
from sqlalchemy import select

from app.api.v1.deps import AuthUser, DBSession
from app.models.master import Category, SubCategory, Colour, Size, Unit, HsnCode, Warehouse
from app.schemas.base import ApiResponse
from app.schemas.product import CategoryOut, SizeOut, ColourOut, UnitOut, HsnOut, WarehouseOut

router = APIRouter(prefix="/master", tags=["master"])


@router.get("/categories")
async def list_categories(db: DBSession, user: AuthUser):
    user.require("master_data.view")
    result = await db.execute(
        select(Category).where(Category.company_id == user.company_id).order_by(Category.name)
    )
    cats = result.scalars().all()
    return ApiResponse(success=True, data=[CategoryOut.model_validate(c) for c in cats])


@router.get("/sizes")
async def list_sizes(db: DBSession, user: AuthUser):
    user.require("master_data.view")
    result = await db.execute(
        select(Size).where(Size.company_id == user.company_id).order_by(Size.sort_order, Size.name)
    )
    sizes = result.scalars().all()
    return ApiResponse(success=True, data=[SizeOut.model_validate(s) for s in sizes])


@router.get("/colours")
async def list_colours(db: DBSession, user: AuthUser):
    user.require("master_data.view")
    result = await db.execute(
        select(Colour).where(Colour.company_id == user.company_id).order_by(Colour.name)
    )
    colours = result.scalars().all()
    return ApiResponse(success=True, data=[ColourOut.model_validate(c) for c in colours])


@router.get("/units")
async def list_units(db: DBSession, user: AuthUser):
    user.require("master_data.view")
    result = await db.execute(
        select(Unit).where(Unit.company_id == user.company_id).order_by(Unit.name)
    )
    units = result.scalars().all()
    return ApiResponse(success=True, data=[UnitOut.model_validate(u) for u in units])


@router.get("/warehouses")
async def list_warehouses(db: DBSession, user: AuthUser):
    user.require("master_data.view")
    result = await db.execute(
        select(Warehouse)
        .where(Warehouse.company_id == user.company_id, Warehouse.is_active.is_(True))
        .order_by(Warehouse.name)
    )
    whs = result.scalars().all()
    return ApiResponse(success=True, data=[WarehouseOut.model_validate(w) for w in whs])


@router.get("/hsn")
async def search_hsn(db: DBSession, user: AuthUser, q: str = ""):
    user.require("master_data.view")
    stmt = select(HsnCode).order_by(HsnCode.hsn)
    if q:
        stmt = stmt.where(HsnCode.hsn.ilike(f"%{q}%") | HsnCode.description.ilike(f"%{q}%"))
    stmt = stmt.limit(50)
    result = await db.execute(stmt)
    codes = result.scalars().all()
    return ApiResponse(success=True, data=[HsnOut.model_validate(c) for c in codes])
