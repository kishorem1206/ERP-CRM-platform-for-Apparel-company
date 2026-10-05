"""Pydantic schemas for Product master CRUD."""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


PRODUCT_TYPES = ["finished_good", "yarn", "fabric", "trim", "packing", "raw_material"]


class ProductVariantOut(BaseModel):
    id: UUID
    sku: str
    colour_id: Optional[UUID] = None
    colour_name: Optional[str] = None
    size_id: Optional[UUID] = None
    size_name: Optional[str] = None
    mrp: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    wholesale_price: Optional[Decimal] = None
    is_active: bool

    model_config = {"from_attributes": True}


class ProductOut(BaseModel):
    id: UUID
    code: str
    name: str
    product_type: str
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    unit_id: Optional[UUID] = None
    unit_abbreviation: Optional[str] = None
    hsn_id: Optional[UUID] = None
    hsn_code: Optional[str] = None
    gst_rate: Optional[Decimal] = None
    mrp: Optional[Decimal] = None
    dealer_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    wholesale_price: Optional[Decimal] = None
    description: Optional[str] = None
    fabric_type: Optional[str] = None
    fabric_composition: Optional[str] = None
    gsm: Optional[Decimal] = None
    construction: Optional[str] = None
    fit: Optional[str] = None
    season: Optional[str] = None
    gender: Optional[str] = None
    is_active: bool
    merged_into_id: Optional[UUID] = None
    variants: list[ProductVariantOut] = []

    model_config = {"from_attributes": True}


class ProductMergeRequest(BaseModel):
    target_product_id: UUID
    notes: Optional[str] = None


class ProductMergeLogOut(BaseModel):
    id: UUID
    source_product_id: UUID
    source_code: str
    source_name: str
    target_product_id: UUID
    target_code: str
    target_name: str
    notes: Optional[str] = None
    merged_by: Optional[UUID] = None
    merged_by_name: Optional[str] = None
    merged_at: datetime

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=300)
    product_type: str = Field(..., pattern="^(finished_good|yarn|fabric|trim|packing|raw_material)$")
    category_id: Optional[UUID] = None
    sub_category_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None
    hsn_id: Optional[UUID] = None
    mrp: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    dealer_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    cost_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    wholesale_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    description: Optional[str] = None
    fabric_type: Optional[str] = None
    fabric_composition: Optional[str] = None
    gsm: Optional[Decimal] = Field(None, ge=0)
    construction: Optional[str] = None
    fit: Optional[str] = None
    season: Optional[str] = None
    gender: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=300)
    category_id: Optional[UUID] = None
    sub_category_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None
    hsn_id: Optional[UUID] = None
    mrp: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    dealer_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    cost_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    wholesale_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    description: Optional[str] = None
    fabric_type: Optional[str] = None
    fabric_composition: Optional[str] = None
    gsm: Optional[Decimal] = Field(None, ge=0)
    construction: Optional[str] = None
    fit: Optional[str] = None
    season: Optional[str] = None
    gender: Optional[str] = None
    is_active: Optional[bool] = None


class ProductVariantCreate(BaseModel):
    colour_id: Optional[UUID] = None
    size_id: Optional[UUID] = None
    barcode: Optional[str] = None
    mrp: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    cost_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    wholesale_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)


class CategoryOut(BaseModel):
    id: UUID
    name: str
    model_config = {"from_attributes": True}


class SizeOut(BaseModel):
    id: UUID
    name: str
    sort_order: int
    model_config = {"from_attributes": True}


class ColourOut(BaseModel):
    id: UUID
    name: str
    hex_code: Optional[str] = None
    model_config = {"from_attributes": True}


class ProcessMasterCreate(BaseModel):
    name: str
    default_unit: Optional[str] = None
    default_tolerance_pct: Optional[Decimal] = None
    default_min_rate: Optional[Decimal] = None
    default_max_rate: Optional[Decimal] = None
    default_planned_rate: Optional[Decimal] = None
    sort_order: int = 0


class ProcessMasterUpdate(BaseModel):
    name: Optional[str] = None
    default_unit: Optional[str] = None
    default_tolerance_pct: Optional[Decimal] = None
    default_min_rate: Optional[Decimal] = None
    default_max_rate: Optional[Decimal] = None
    default_planned_rate: Optional[Decimal] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ProcessMasterOut(BaseModel):
    id: UUID
    name: str
    default_unit: Optional[str] = None
    default_tolerance_pct: Optional[Decimal] = None
    default_min_rate: Optional[Decimal] = None
    default_max_rate: Optional[Decimal] = None
    default_planned_rate: Optional[Decimal] = None
    sort_order: int
    is_active: bool
    model_config = {"from_attributes": True}


class UnitOut(BaseModel):
    id: UUID
    name: str
    abbreviation: str
    unit_type: str
    model_config = {"from_attributes": True}


class HsnOut(BaseModel):
    id: UUID
    hsn: str
    description: Optional[str] = None
    gst_rate: Decimal
    cess_rate: Optional[Decimal] = None
    model_config = {"from_attributes": True}


class WarehouseOut(BaseModel):
    id: UUID
    name: str
    code: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    model_config = {"from_attributes": True}
