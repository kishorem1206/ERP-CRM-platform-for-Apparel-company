"""Master data reference endpoints — categories, sizes, colours, units, warehouses, HSN."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.v1.deps import AuthUser, DBSession
from app.models.master import Category, SubCategory, Colour, Size, Unit, HsnCode, Warehouse
from app.models.production import ProcessMaster
from app.schemas.base import ApiResponse
from app.schemas.product import (
    CategoryOut, SizeOut, ColourOut, UnitOut, HsnOut, WarehouseOut,
    ProcessMasterCreate, ProcessMasterUpdate, ProcessMasterOut,
)

router = APIRouter(prefix="/master", tags=["master"])


def _conflict(exc: IntegrityError, on_duplicate: str, on_reference: str) -> HTTPException:
    detail = str(exc.orig) if exc.orig else str(exc)
    if "unique" in detail.lower() or "duplicate" in detail.lower():
        return HTTPException(409, on_duplicate)
    return HTTPException(409, on_reference)


# ── Categories ──────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str


class CategoryUpdate(BaseModel):
    name: str | None = None


@router.get("/categories")
async def list_categories(db: DBSession, user: AuthUser):
    user.require("master_data.view")
    result = await db.execute(
        select(Category).where(Category.company_id == user.company_id).order_by(Category.name)
    )
    cats = result.scalars().all()
    return ApiResponse(success=True, data=[CategoryOut.model_validate(c) for c in cats])


@router.post("/categories", status_code=201)
async def create_category(body: CategoryCreate, db: DBSession, user: AuthUser):
    user.require("master_data.create")
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Category name is required")
    cat = Category(company_id=user.company_id, name=name)
    db.add(cat)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "A category with this name already exists", "Cannot create category")
    await db.refresh(cat)
    return ApiResponse(success=True, data=CategoryOut.model_validate(cat), message="Category created")


@router.patch("/categories/{category_id}")
async def update_category(category_id: UUID, body: CategoryUpdate, db: DBSession, user: AuthUser):
    user.require("master_data.edit")
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.company_id == user.company_id)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "Category not found")
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(400, "Category name is required")
        cat.name = name
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "A category with this name already exists", "Cannot update category")
    await db.refresh(cat)
    return ApiResponse(success=True, data=CategoryOut.model_validate(cat), message="Category updated")


@router.delete("/categories/{category_id}")
async def delete_category(category_id: UUID, db: DBSession, user: AuthUser):
    user.require("master_data.delete")
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.company_id == user.company_id)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "Category not found")
    await db.delete(cat)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Cannot delete — this category is used by existing products or sub-categories")
    return ApiResponse(success=True, message="Category deleted")


# ── Sizes ───────────────────────────────────────────────────────────────────

class SizeCreate(BaseModel):
    name: str
    sort_order: int = 0


class SizeUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None


@router.get("/sizes")
async def list_sizes(db: DBSession, user: AuthUser):
    user.require("master_data.view")
    result = await db.execute(
        select(Size).where(Size.company_id == user.company_id).order_by(Size.sort_order, Size.name)
    )
    sizes = result.scalars().all()
    return ApiResponse(success=True, data=[SizeOut.model_validate(s) for s in sizes])


@router.post("/sizes", status_code=201)
async def create_size(body: SizeCreate, db: DBSession, user: AuthUser):
    user.require("master_data.create")
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Size name is required")
    existing = await db.execute(
        select(Size).where(Size.company_id == user.company_id, Size.name == name)
    )
    found = existing.scalar_one_or_none()
    if found:
        return ApiResponse(success=True, data=SizeOut.model_validate(found))
    size = Size(company_id=user.company_id, name=name, sort_order=body.sort_order)
    db.add(size)
    await db.commit()
    await db.refresh(size)
    return ApiResponse(success=True, data=SizeOut.model_validate(size), message="Size created")


@router.patch("/sizes/{size_id}")
async def update_size(size_id: UUID, body: SizeUpdate, db: DBSession, user: AuthUser):
    user.require("master_data.edit")
    result = await db.execute(
        select(Size).where(Size.id == size_id, Size.company_id == user.company_id)
    )
    size = result.scalar_one_or_none()
    if not size:
        raise HTTPException(404, "Size not found")
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(400, "Size name is required")
        size.name = name
    if body.sort_order is not None:
        size.sort_order = body.sort_order
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "A size with this name already exists", "Cannot update size")
    await db.refresh(size)
    return ApiResponse(success=True, data=SizeOut.model_validate(size), message="Size updated")


@router.delete("/sizes/{size_id}")
async def delete_size(size_id: UUID, db: DBSession, user: AuthUser):
    user.require("master_data.delete")
    result = await db.execute(
        select(Size).where(Size.id == size_id, Size.company_id == user.company_id)
    )
    size = result.scalar_one_or_none()
    if not size:
        raise HTTPException(404, "Size not found")
    await db.delete(size)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Cannot delete — this size is used by existing products, styles, or lots")
    return ApiResponse(success=True, message="Size deleted")


# ── Colours ─────────────────────────────────────────────────────────────────

class ColourCreate(BaseModel):
    name: str
    hex_code: str | None = None


class ColourUpdate(BaseModel):
    name: str | None = None
    hex_code: str | None = None


@router.get("/colours")
async def list_colours(db: DBSession, user: AuthUser):
    user.require("master_data.view")
    result = await db.execute(
        select(Colour).where(Colour.company_id == user.company_id).order_by(Colour.name)
    )
    colours = result.scalars().all()
    return ApiResponse(success=True, data=[ColourOut.model_validate(c) for c in colours])


@router.post("/colours", status_code=201)
async def create_colour(body: ColourCreate, db: DBSession, user: AuthUser):
    user.require("master_data.create")
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Colour name is required")
    colour = Colour(company_id=user.company_id, name=name, hex_code=body.hex_code or None)
    db.add(colour)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "A colour with this name already exists", "Cannot create colour")
    await db.refresh(colour)
    return ApiResponse(success=True, data=ColourOut.model_validate(colour), message="Colour created")


@router.patch("/colours/{colour_id}")
async def update_colour(colour_id: UUID, body: ColourUpdate, db: DBSession, user: AuthUser):
    user.require("master_data.edit")
    result = await db.execute(
        select(Colour).where(Colour.id == colour_id, Colour.company_id == user.company_id)
    )
    colour = result.scalar_one_or_none()
    if not colour:
        raise HTTPException(404, "Colour not found")
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(400, "Colour name is required")
        colour.name = name
    if body.hex_code is not None:
        colour.hex_code = body.hex_code or None
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "A colour with this name already exists", "Cannot update colour")
    await db.refresh(colour)
    return ApiResponse(success=True, data=ColourOut.model_validate(colour), message="Colour updated")


@router.delete("/colours/{colour_id}")
async def delete_colour(colour_id: UUID, db: DBSession, user: AuthUser):
    user.require("master_data.delete")
    result = await db.execute(
        select(Colour).where(Colour.id == colour_id, Colour.company_id == user.company_id)
    )
    colour = result.scalar_one_or_none()
    if not colour:
        raise HTTPException(404, "Colour not found")
    await db.delete(colour)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Cannot delete — this colour is used by existing products, styles, or lots")
    return ApiResponse(success=True, message="Colour deleted")


# ── Process Master ──────────────────────────────────────────────────────────

@router.get("/processes")
async def list_processes(db: DBSession, user: AuthUser):
    user.require("master_data.view")
    result = await db.execute(
        select(ProcessMaster).where(ProcessMaster.company_id == user.company_id, ProcessMaster.is_active.is_(True))
        .order_by(ProcessMaster.sort_order, ProcessMaster.name)
    )
    processes = result.scalars().all()
    return ApiResponse(success=True, data=[ProcessMasterOut.model_validate(p) for p in processes])


@router.post("/processes", status_code=201)
async def create_process(body: ProcessMasterCreate, db: DBSession, user: AuthUser):
    user.require("master_data.create")
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Process name is required")
    process = ProcessMaster(
        company_id=user.company_id, name=name, default_unit=body.default_unit,
        default_tolerance_pct=body.default_tolerance_pct, default_min_rate=body.default_min_rate,
        default_max_rate=body.default_max_rate, default_planned_rate=body.default_planned_rate,
        sort_order=body.sort_order, created_at=datetime.now(timezone.utc),
    )
    db.add(process)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "A process with this name already exists", "Cannot create process")
    await db.refresh(process)
    return ApiResponse(success=True, data=ProcessMasterOut.model_validate(process), message="Process created")


@router.patch("/processes/{process_id}")
async def update_process(process_id: UUID, body: ProcessMasterUpdate, db: DBSession, user: AuthUser):
    user.require("master_data.edit")
    result = await db.execute(
        select(ProcessMaster).where(ProcessMaster.id == process_id, ProcessMaster.company_id == user.company_id)
    )
    process = result.scalar_one_or_none()
    if not process:
        raise HTTPException(404, "Process not found")
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(400, "Process name is required")
        process.name = name
    if body.default_unit is not None:
        process.default_unit = body.default_unit
    if body.default_tolerance_pct is not None:
        process.default_tolerance_pct = body.default_tolerance_pct
    if body.default_min_rate is not None:
        process.default_min_rate = body.default_min_rate
    if body.default_max_rate is not None:
        process.default_max_rate = body.default_max_rate
    if body.default_planned_rate is not None:
        process.default_planned_rate = body.default_planned_rate
    if body.sort_order is not None:
        process.sort_order = body.sort_order
    if body.is_active is not None:
        process.is_active = body.is_active
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "A process with this name already exists", "Cannot update process")
    await db.refresh(process)
    return ApiResponse(success=True, data=ProcessMasterOut.model_validate(process), message="Process updated")


@router.delete("/processes/{process_id}")
async def delete_process(process_id: UUID, db: DBSession, user: AuthUser):
    user.require("master_data.delete")
    result = await db.execute(
        select(ProcessMaster).where(ProcessMaster.id == process_id, ProcessMaster.company_id == user.company_id)
    )
    process = result.scalar_one_or_none()
    if not process:
        raise HTTPException(404, "Process not found")
    await db.delete(process)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Cannot delete — this process is used by existing styles")
    return ApiResponse(success=True, message="Process deleted")


# ── Units ───────────────────────────────────────────────────────────────────

class UnitCreate(BaseModel):
    name: str
    abbreviation: str
    unit_type: str = "piece"


class UnitUpdate(BaseModel):
    name: str | None = None
    abbreviation: str | None = None
    unit_type: str | None = None


@router.get("/units")
async def list_units(db: DBSession, user: AuthUser):
    user.require("master_data.view")
    result = await db.execute(
        select(Unit).where(Unit.company_id == user.company_id).order_by(Unit.name)
    )
    units = result.scalars().all()
    return ApiResponse(success=True, data=[UnitOut.model_validate(u) for u in units])


@router.post("/units", status_code=201)
async def create_unit(body: UnitCreate, db: DBSession, user: AuthUser):
    user.require("master_data.create")
    name = body.name.strip()
    abbr = body.abbreviation.strip()
    if not name or not abbr:
        raise HTTPException(400, "Unit name and abbreviation are required")
    unit = Unit(company_id=user.company_id, name=name, abbreviation=abbr, unit_type=body.unit_type)
    db.add(unit)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "A unit with this abbreviation already exists", "Cannot create unit")
    await db.refresh(unit)
    return ApiResponse(success=True, data=UnitOut.model_validate(unit), message="Unit created")


@router.patch("/units/{unit_id}")
async def update_unit(unit_id: UUID, body: UnitUpdate, db: DBSession, user: AuthUser):
    user.require("master_data.edit")
    result = await db.execute(
        select(Unit).where(Unit.id == unit_id, Unit.company_id == user.company_id)
    )
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(404, "Unit not found")
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(400, "Unit name is required")
        unit.name = name
    if body.abbreviation is not None:
        abbr = body.abbreviation.strip()
        if not abbr:
            raise HTTPException(400, "Unit abbreviation is required")
        unit.abbreviation = abbr
    if body.unit_type is not None:
        unit.unit_type = body.unit_type
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "A unit with this abbreviation already exists", "Cannot update unit")
    await db.refresh(unit)
    return ApiResponse(success=True, data=UnitOut.model_validate(unit), message="Unit updated")


@router.delete("/units/{unit_id}")
async def delete_unit(unit_id: UUID, db: DBSession, user: AuthUser):
    user.require("master_data.delete")
    result = await db.execute(
        select(Unit).where(Unit.id == unit_id, Unit.company_id == user.company_id)
    )
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(404, "Unit not found")
    await db.delete(unit)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Cannot delete — this unit is used by existing products or transactions")
    return ApiResponse(success=True, message="Unit deleted")


# ── Warehouses ──────────────────────────────────────────────────────────────
# No hard delete: warehouses are referenced throughout the inventory ledger,
# so "removing" one means deactivating it (is_active=False) via PATCH, matching
# the is_active filter already used by list_warehouses.

class WarehouseCreate(BaseModel):
    name: str
    code: str | None = None
    address: str | None = None


class WarehouseUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    address: str | None = None
    is_active: bool | None = None


@router.get("/warehouses")
async def list_warehouses(db: DBSession, user: AuthUser, include_inactive: bool = False):
    user.require("master_data.view")
    stmt = select(Warehouse).where(Warehouse.company_id == user.company_id)
    if not include_inactive:
        stmt = stmt.where(Warehouse.is_active.is_(True))
    result = await db.execute(stmt.order_by(Warehouse.name))
    whs = result.scalars().all()
    return ApiResponse(success=True, data=[WarehouseOut.model_validate(w) for w in whs])


@router.post("/warehouses", status_code=201)
async def create_warehouse(body: WarehouseCreate, db: DBSession, user: AuthUser):
    user.require("master_data.create")
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Warehouse name is required")
    wh = Warehouse(company_id=user.company_id, name=name, code=body.code or None, address=body.address or None)
    db.add(wh)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "A warehouse with this code already exists", "Cannot create warehouse")
    await db.refresh(wh)
    return ApiResponse(success=True, data=WarehouseOut.model_validate(wh), message="Warehouse created")


@router.patch("/warehouses/{warehouse_id}")
async def update_warehouse(warehouse_id: UUID, body: WarehouseUpdate, db: DBSession, user: AuthUser):
    user.require("master_data.edit")
    result = await db.execute(
        select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.company_id == user.company_id)
    )
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(404, "Warehouse not found")
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(400, "Warehouse name is required")
        wh.name = name
    if body.code is not None:
        wh.code = body.code or None
    if body.address is not None:
        wh.address = body.address or None
    if body.is_active is not None:
        wh.is_active = body.is_active
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "A warehouse with this code already exists", "Cannot update warehouse")
    await db.refresh(wh)
    return ApiResponse(success=True, data=WarehouseOut.model_validate(wh), message="Warehouse updated")


# ── HSN Codes ───────────────────────────────────────────────────────────────
# HSN codes have no company_id — they're a shared national tax classification,
# not scoped per company.

class HsnCreate(BaseModel):
    hsn: str
    description: str | None = None
    gst_rate: Decimal = Decimal("5")
    cess_rate: Decimal = Decimal("0")


class HsnUpdate(BaseModel):
    hsn: str | None = None
    description: str | None = None
    gst_rate: Decimal | None = None
    cess_rate: Decimal | None = None


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


@router.post("/hsn", status_code=201)
async def create_hsn(body: HsnCreate, db: DBSession, user: AuthUser):
    user.require("master_data.create")
    hsn = body.hsn.strip()
    if not hsn:
        raise HTTPException(400, "HSN code is required")
    code = HsnCode(hsn=hsn, description=body.description or None, gst_rate=body.gst_rate, cess_rate=body.cess_rate)
    db.add(code)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "This HSN code already exists", "Cannot create HSN code")
    await db.refresh(code)
    return ApiResponse(success=True, data=HsnOut.model_validate(code), message="HSN code created")


@router.patch("/hsn/{hsn_id}")
async def update_hsn(hsn_id: UUID, body: HsnUpdate, db: DBSession, user: AuthUser):
    user.require("master_data.edit")
    result = await db.execute(select(HsnCode).where(HsnCode.id == hsn_id))
    code = result.scalar_one_or_none()
    if not code:
        raise HTTPException(404, "HSN code not found")
    if body.hsn is not None:
        hsn = body.hsn.strip()
        if not hsn:
            raise HTTPException(400, "HSN code is required")
        code.hsn = hsn
    if body.description is not None:
        code.description = body.description or None
    if body.gst_rate is not None:
        code.gst_rate = body.gst_rate
    if body.cess_rate is not None:
        code.cess_rate = body.cess_rate
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(exc, "This HSN code already exists", "Cannot update HSN code")
    await db.refresh(code)
    return ApiResponse(success=True, data=HsnOut.model_validate(code), message="HSN code updated")


@router.delete("/hsn/{hsn_id}")
async def delete_hsn(hsn_id: UUID, db: DBSession, user: AuthUser):
    user.require("master_data.delete")
    result = await db.execute(select(HsnCode).where(HsnCode.id == hsn_id))
    code = result.scalar_one_or_none()
    if not code:
        raise HTTPException(404, "HSN code not found")
    await db.delete(code)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Cannot delete — this HSN code is used by existing products")
    return ApiResponse(success=True, message="HSN code deleted")
