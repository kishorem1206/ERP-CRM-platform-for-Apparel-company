from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select

from app.api.v1.deps import AuthUser, DBSession
from app.core.security import hash_password
from app.models.company import Company
from app.models.user import Permission, Role, RolePermission, User, UserRole
from app.schemas.admin import (
    AssignRoleBody,
    CompanyOut,
    CompanyUpdate,
    PermissionOut,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    SetPermissionsBody,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.schemas.base import ApiResponse

router = APIRouter()


# ─── helpers ─────────────────────────────────────────────────────────────────

async def _user_out(db, user: User) -> UserOut:
    result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    roles = [r[0] for r in result.all()]
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        is_active=user.is_active,
        is_owner=user.is_owner,
        last_login_at=user.last_login_at,
        roles=roles,
    )


async def _role_out(db, role: Role) -> RoleOut:
    result = await db.execute(
        select(RolePermission).where(RolePermission.role_id == role.id)
    )
    count = len(result.all())
    return RoleOut(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permission_count=count,
    )


# ─── users ───────────────────────────────────────────────────────────────────

@router.get("/admin/users", response_model=ApiResponse)
async def list_users(user: AuthUser, db: DBSession):
    user.require("admin.users")
    result = await db.execute(
        select(User)
        .where(User.company_id == user.company_id)
        .order_by(User.full_name)
    )
    users = result.scalars().all()
    data = [await _user_out(db, u) for u in users]
    return ApiResponse(success=True, data=[d.model_dump() for d in data])


@router.post("/admin/users", response_model=ApiResponse, status_code=201)
async def create_user(body: UserCreate, user: AuthUser, db: DBSession):
    user.require("admin.users")
    exists = await db.execute(select(User).where(User.email == body.email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already in use")
    now = datetime.now(timezone.utc)
    new_user = User(
        company_id=user.company_id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        phone=body.phone,
        is_active=True,
        is_owner=False,
        created_at=now,
        updated_at=now,
    )
    db.add(new_user)
    await db.flush()
    for rid in body.role_ids:
        db.add(UserRole(user_id=new_user.id, role_id=rid))
    await db.commit()
    await db.refresh(new_user)
    return ApiResponse(success=True, data=(await _user_out(db, new_user)).model_dump(), message="User created")


@router.patch("/admin/users/{user_id}", response_model=ApiResponse)
async def update_user(user_id: UUID, body: UserUpdate, user: AuthUser, db: DBSession):
    user.require("admin.users")
    result = await db.execute(
        select(User).where(User.id == user_id, User.company_id == user.company_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.is_owner:
        raise HTTPException(status_code=403, detail="Cannot modify owner account")
    if body.full_name is not None:
        target.full_name = body.full_name
    if body.phone is not None:
        target.phone = body.phone
    if body.is_active is not None:
        target.is_active = body.is_active
    target.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return ApiResponse(success=True, data=(await _user_out(db, target)).model_dump())


@router.post("/admin/users/{user_id}/roles", response_model=ApiResponse)
async def assign_roles(user_id: UUID, body: AssignRoleBody, user: AuthUser, db: DBSession):
    user.require("admin.users")
    result = await db.execute(
        select(User).where(User.id == user_id, User.company_id == user.company_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await db.execute(delete(UserRole).where(UserRole.user_id == user_id))
    for rid in body.role_ids:
        db.add(UserRole(user_id=user_id, role_id=rid))
    await db.commit()
    return ApiResponse(success=True, message="Roles updated")


# ─── roles ───────────────────────────────────────────────────────────────────

@router.get("/admin/roles", response_model=ApiResponse)
async def list_roles(user: AuthUser, db: DBSession):
    user.require("admin.roles")
    result = await db.execute(
        select(Role)
        .where(Role.company_id == user.company_id)
        .order_by(Role.name)
    )
    roles = result.scalars().all()
    data = [await _role_out(db, r) for r in roles]
    return ApiResponse(success=True, data=[d.model_dump() for d in data])


@router.post("/admin/roles", response_model=ApiResponse, status_code=201)
async def create_role(body: RoleCreate, user: AuthUser, db: DBSession):
    user.require("admin.roles")
    now = datetime.now(timezone.utc)
    role = Role(
        company_id=user.company_id,
        name=body.name,
        description=body.description,
        is_system=False,
        created_at=now,
        updated_at=now,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return ApiResponse(success=True, data=(await _role_out(db, role)).model_dump(), message="Role created")


@router.patch("/admin/roles/{role_id}", response_model=ApiResponse)
async def update_role(role_id: UUID, body: RoleUpdate, user: AuthUser, db: DBSession):
    user.require("admin.roles")
    result = await db.execute(
        select(Role).where(Role.id == role_id, Role.company_id == user.company_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=403, detail="Cannot modify system roles")
    if body.name is not None:
        role.name = body.name
    if body.description is not None:
        role.description = body.description
    role.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return ApiResponse(success=True, data=(await _role_out(db, role)).model_dump())


@router.delete("/admin/roles/{role_id}", response_model=ApiResponse)
async def delete_role(role_id: UUID, user: AuthUser, db: DBSession):
    user.require("admin.roles")
    result = await db.execute(
        select(Role).where(Role.id == role_id, Role.company_id == user.company_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=403, detail="Cannot delete system roles")
    await db.delete(role)
    await db.commit()
    return ApiResponse(success=True, message="Role deleted")


@router.get("/admin/roles/{role_id}/permissions", response_model=ApiResponse)
async def get_role_permissions(role_id: UUID, user: AuthUser, db: DBSession):
    user.require("admin.roles")
    result = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
        .order_by(Permission.code)
    )
    perms = result.scalars().all()
    return ApiResponse(success=True, data=[PermissionOut.model_validate(p).model_dump() for p in perms])


@router.put("/admin/roles/{role_id}/permissions", response_model=ApiResponse)
async def set_role_permissions(role_id: UUID, body: SetPermissionsBody, user: AuthUser, db: DBSession):
    user.require("admin.roles")
    result = await db.execute(
        select(Role).where(Role.id == role_id, Role.company_id == user.company_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=403, detail="Cannot modify system role permissions")
    await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    for pid in body.permission_ids:
        db.add(RolePermission(role_id=role_id, permission_id=pid))
    await db.commit()
    return ApiResponse(success=True, message="Permissions updated")


# ─── permissions ─────────────────────────────────────────────────────────────

@router.get("/admin/permissions", response_model=ApiResponse)
async def list_permissions(user: AuthUser, db: DBSession):
    user.require("admin.roles")
    result = await db.execute(select(Permission).order_by(Permission.code))
    perms = result.scalars().all()
    return ApiResponse(success=True, data=[PermissionOut.model_validate(p).model_dump() for p in perms])


# ─── company ─────────────────────────────────────────────────────────────────

@router.get("/admin/company", response_model=ApiResponse)
async def get_company(user: AuthUser, db: DBSession):
    user.require("admin.settings")
    result = await db.execute(select(Company).where(Company.id == user.company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return ApiResponse(success=True, data=CompanyOut.model_validate(company).model_dump())


@router.put("/admin/company", response_model=ApiResponse)
async def update_company(body: CompanyUpdate, user: AuthUser, db: DBSession):
    user.require("admin.settings")
    result = await db.execute(select(Company).where(Company.id == user.company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(company, field, val)
    company.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(company)
    return ApiResponse(success=True, data=CompanyOut.model_validate(company).model_dump(), message="Settings saved")
