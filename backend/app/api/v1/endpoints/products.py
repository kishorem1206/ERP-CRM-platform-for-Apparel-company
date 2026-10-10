"""Product master CRUD endpoints."""
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.v1.deps import AuthUser, DBSession
from app.models.master import Product, ProductVariant, Category, Unit, HsnCode
from app.models.product_merge import ProductMergeLog
from app.models.user import User
from app.schemas.base import ApiResponse, PaginatedMeta
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductOut, ProductVariantCreate, ProductVariantOut,
    ProductMergeRequest, ProductMergeLogOut,
)
from app.services.product_merge import MergeService, ProductMergeError
from app.services.sku import build_variant_sku

router = APIRouter(prefix="/products", tags=["products"])


def _to_product_out(p: Product) -> ProductOut:
    return ProductOut(
        id=p.id,
        code=p.code,
        name=p.name,
        product_type=p.product_type,
        category_id=p.category_id,
        category_name=p.category.name if p.category else None,
        brand_id=p.brand_id,
        brand_name=p.brand.name if p.brand else None,
        unit_id=p.unit_id,
        unit_abbreviation=p.unit.abbreviation if p.unit else None,
        hsn_id=p.hsn_id,
        hsn_code=p.hsn.hsn if p.hsn else None,
        gst_rate=p.hsn.gst_rate if p.hsn else None,
        mrp=p.mrp,
        dealer_price=p.dealer_price,
        cost_price=p.cost_price,
        wholesale_price=p.wholesale_price,
        description=p.description,
        fabric_type=p.fabric_type,
        fabric_composition=p.fabric_composition,
        gsm=p.gsm,
        construction=p.construction,
        fit=p.fit,
        season=p.season,
        gender=p.gender,
        is_active=p.is_active,
        merged_into_id=p.merged_into_id,
        variants=[
            ProductVariantOut(
                id=v.id,
                sku=v.sku,
                colour_id=v.colour_id,
                colour_name=v.colour.name if v.colour else None,
                size_id=v.size_id,
                size_name=v.size.name if v.size else None,
                mrp=v.mrp,
                cost_price=v.cost_price,
                wholesale_price=v.wholesale_price,
                is_active=v.is_active,
            )
            for v in p.variants
        ],
    )


@router.get("")
async def list_products(
    db: DBSession,
    user: AuthUser,
    product_type: str | None = None,
    category_id: UUID | None = None,
    active_only: bool = True,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    user.require("master_data.view")

    q = (
        select(Product)
        .where(Product.company_id == user.company_id, Product.deleted_at.is_(None))
        .options(
            selectinload(Product.category),
            selectinload(Product.unit),
            selectinload(Product.hsn),
            selectinload(Product.brand),
            selectinload(Product.variants).selectinload(ProductVariant.colour),
            selectinload(Product.variants).selectinload(ProductVariant.size),
        )
    )

    if product_type:
        q = q.where(Product.product_type == product_type)
    if category_id:
        q = q.where(Product.category_id == category_id)
    if active_only:
        q = q.where(Product.is_active.is_(True))
    if search:
        q = q.where(
            Product.name.ilike(f"%{search}%") | Product.code.ilike(f"%{search}%")
        )

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.order_by(Product.code).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    products = result.scalars().all()

    return ApiResponse(
        success=True,
        data=[_to_product_out(p) for p in products],
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


@router.post("", status_code=201)
async def create_product(
    body: ProductCreate,
    db: DBSession,
    user: AuthUser,
):
    user.require("master_data.create")

    # Check code uniqueness within company
    existing = await db.execute(
        select(Product).where(Product.company_id == user.company_id, Product.code == body.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Product code '{body.code}' already exists")

    product = Product(
        company_id=user.company_id,
        created_by=user.user_id,
        **body.model_dump(),
    )
    db.add(product)
    await db.flush()  # get the generated id; session commits at request teardown

    # Fetch with relationships for the response
    result = await db.execute(
        select(Product)
        .where(Product.id == product.id)
        .options(
            selectinload(Product.category),
            selectinload(Product.unit),
            selectinload(Product.hsn),
            selectinload(Product.brand),
            selectinload(Product.variants),
        )
    )
    p = result.scalar_one()
    return ApiResponse(success=True, data=_to_product_out(p))


@router.get("/merge-logs")
async def list_merge_logs(db: DBSession, user: AuthUser, page: int = 1, page_size: int = 50):
    """Audit trail for Product Merge (ERP Upgrade §10) - must stay
    registered before GET /{product_id}, otherwise FastAPI tries to parse
    "merge-logs" as a product_id UUID and 422s before this ever matches."""
    user.require("master_data.view")
    merged_by = User.__table__.alias("merged_by_user")
    result = await db.execute(
        select(ProductMergeLog, merged_by.c.full_name)
        .outerjoin(merged_by, merged_by.c.id == ProductMergeLog.merged_by)
        .where(ProductMergeLog.company_id == user.company_id)
        .order_by(ProductMergeLog.merged_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    rows = result.all()
    total = (await db.execute(
        select(func.count()).select_from(ProductMergeLog).where(ProductMergeLog.company_id == user.company_id)
    )).scalar() or 0
    data = []
    for log, merged_by_name in rows:
        out = ProductMergeLogOut.model_validate(log)
        out.merged_by_name = merged_by_name
        data.append(out)
    return ApiResponse(success=True, data=data, meta=PaginatedMeta(page=page, page_size=page_size, total=total))


@router.post("/{source_product_id}/merge", status_code=201)
async def merge_product(source_product_id: UUID, body: ProductMergeRequest, db: DBSession, user: AuthUser):
    """Merge a duplicate product into a master product (ERP Upgrade §10).
    Controlled, auditable, atomic - see MergeService for the full
    repoint-everything-then-deactivate-source sequence."""
    user.require("master_data.merge")
    svc = MergeService(db)
    try:
        target, log = await svc.merge_products(
            user.company_id, source_product_id, body.target_product_id, user.user_id, body.notes,
        )
    except ProductMergeError as e:
        raise HTTPException(400, e.message)

    result = await db.execute(
        select(Product)
        .where(Product.id == target.id)
        .options(
            selectinload(Product.category),
            selectinload(Product.unit),
            selectinload(Product.hsn),
            selectinload(Product.brand),
            selectinload(Product.variants).selectinload(ProductVariant.colour),
            selectinload(Product.variants).selectinload(ProductVariant.size),
        )
    )
    refreshed_target = result.scalar_one()
    merger = (await db.execute(select(User.full_name).where(User.id == log.merged_by))).scalar_one_or_none()
    log_out = ProductMergeLogOut.model_validate(log)
    log_out.merged_by_name = merger
    return ApiResponse(success=True, data={
        "target": _to_product_out(refreshed_target),
        "merge_log": log_out,
    }, message=f"'{log.source_name}' merged into '{log.target_name}'")


@router.get("/{product_id}")
async def get_product(product_id: UUID, db: DBSession, user: AuthUser):
    user.require("master_data.view")

    result = await db.execute(
        select(Product)
        .where(Product.id == product_id, Product.company_id == user.company_id)
        .options(
            selectinload(Product.category),
            selectinload(Product.unit),
            selectinload(Product.hsn),
            selectinload(Product.brand),
            selectinload(Product.variants).selectinload(ProductVariant.colour),
            selectinload(Product.variants).selectinload(ProductVariant.size),
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Product not found")
    return ApiResponse(success=True, data=_to_product_out(p))


@router.patch("/{product_id}")
async def update_product(product_id: UUID, body: ProductUpdate, db: DBSession, user: AuthUser):
    user.require("master_data.edit")

    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.company_id == user.company_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Product not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(p, field, value)

    await db.flush()

    # Re-fetch with relationships so _to_product_out can access category/unit/hsn/variants
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(
            selectinload(Product.category),
            selectinload(Product.unit),
            selectinload(Product.hsn),
            selectinload(Product.brand),
            selectinload(Product.variants).selectinload(ProductVariant.colour),
            selectinload(Product.variants).selectinload(ProductVariant.size),
        )
    )
    p = result.scalar_one()
    return ApiResponse(success=True, data=_to_product_out(p))


@router.delete("/{product_id}", status_code=204)
async def deactivate_product(product_id: UUID, db: DBSession, user: AuthUser):
    user.require("master_data.delete")

    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.company_id == user.company_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Product not found")

    p.is_active = False
    await db.commit()


@router.post("/{product_id}/variants", status_code=201)
async def add_variant(product_id: UUID, body: ProductVariantCreate, db: DBSession, user: AuthUser):
    user.require("master_data.create")

    prod_result = await db.execute(
        select(Product).where(Product.id == product_id, Product.company_id == user.company_id)
    )
    product = prod_result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")

    sku = await build_variant_sku(db, product.code, body.size_id, body.colour_id)

    variant = ProductVariant(
        product_id=product_id,
        sku=sku,
        **body.model_dump(),
    )
    db.add(variant)
    await db.flush()
    await db.refresh(variant)
    return ApiResponse(success=True, data=ProductVariantOut.model_validate(variant))
