from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    phone: str | None
    is_active: bool
    is_owner: bool
    last_login_at: datetime | None
    roles: list[str] = []

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str | None = None
    phone: str | None = None
    password: str
    role_ids: list[UUID] = []


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    is_active: bool | None = None


class AssignRoleBody(BaseModel):
    role_ids: list[UUID]


class PermissionOut(BaseModel):
    id: UUID
    code: str
    description: str | None

    model_config = {"from_attributes": True}


class RoleOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_system: bool
    permission_count: int = 0

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class SetPermissionsBody(BaseModel):
    permission_ids: list[UUID]


class CompanyUpdate(BaseModel):
    name: str | None = None
    gstin: str | None = None
    pan: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    state_code: int | None = None
    pincode: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    fabric_variance_pct: float | None = None
    negative_stock_allowed: bool | None = None


class CompanyOut(BaseModel):
    id: UUID
    name: str
    gstin: str | None
    pan: str | None
    address: str | None
    city: str | None
    state: str | None
    state_code: int | None
    pincode: str | None
    phone: str | None
    email: str | None
    website: str | None
    currency: str
    fabric_variance_pct: float | None
    negative_stock_allowed: bool

    model_config = {"from_attributes": True}
