import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import AuthUser, DBSession
from app.core.config import settings
from app.core.security import (
    check_rate_limit,
    consume_pending_2fa,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp,
    generate_totp_secret,
    get_totp_provisioning_uri,
    hash_password,
    store_otp,
    store_pending_2fa,
    verify_and_consume_otp,
    verify_password,
    verify_totp,
)
from app.models.user import RefreshToken, User
from app.schemas.base import ApiResponse

router = APIRouter()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


# ─── Request / Response models ────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Verify2FARequest(BaseModel):
    session_id: str
    code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


class Enable2FARequest(BaseModel):
    code: str


class Disable2FARequest(BaseModel):
    password: str


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_user_permissions(db: AsyncSession, user_id) -> list[str]:
    from app.models.user import UserRole, RolePermission, Permission
    result = await db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
        .distinct()
    )
    return [row[0] for row in result.all()]


async def _issue_tokens(db: AsyncSession, user: User, response: Response) -> str:
    """Issue access + refresh tokens. Stores refresh token hash. Returns access token."""
    permissions = await _get_user_permissions(db, user.id)
    access_token = create_access_token({
        "sub": str(user.id),
        "company_id": str(user.company_id),
        "email": user.email,
        "permissions": permissions,
    })
    refresh_token_str = create_refresh_token(user.id)
    token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(days=30),
        created_at=now,
    ))
    response.set_cookie(
        key="refresh_token",
        value=refresh_token_str,
        httponly=True,
        secure=not settings.is_development,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
    return access_token


async def _revoke_refresh_token(db: AsyncSession, request: Request) -> None:
    """Revoke the current refresh token from DB."""
    raw = request.cookies.get("refresh_token")
    if not raw:
        return
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()
    if stored:
        stored.revoked_at = datetime.now(timezone.utc)


# ─── Login ────────────────────────────────────────────────────────────────────

@router.post("/auth/login")
async def login(body: LoginRequest, request: Request, response: Response, db: DBSession):
    ip = request.client.host if request.client else "anon"
    if not await check_rate_limit(f"login:{ip}", limit=10, window=60):
        raise HTTPException(status_code=429, detail="Too many login attempts. Wait 1 minute.")

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Invalid credentials"})

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail={"code": "ACCOUNT_LOCKED", "message": "Account temporarily locked."})

    if not verify_password(body.password, user.hashed_password):
        new_count = (user.failed_login_count or 0) + 1
        updates: dict = {"failed_login_count": new_count}
        if new_count >= MAX_FAILED_ATTEMPTS:
            updates["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        await db.execute(update(User).where(User.id == user.id).values(**updates))
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Invalid credentials"})

    await db.execute(
        update(User).where(User.id == user.id).values(
            failed_login_count=0, locked_until=None, last_login_at=datetime.now(timezone.utc)
        )
    )

    # 2FA check
    if getattr(user, "totp_enabled", False) and user.totp_secret:
        session_id = str(uuid.uuid4())
        await store_pending_2fa(session_id, str(user.id))
        await db.commit()
        return ApiResponse(success=True, data={"requires_2fa": True, "session_id": session_id})

    access_token = await _issue_tokens(db, user, response)
    await db.commit()
    return ApiResponse(success=True, data=TokenResponse(access_token=access_token))


@router.post("/auth/login/verify-2fa")
async def verify_2fa_login(body: Verify2FARequest, response: Response, db: DBSession):
    user_id = await consume_pending_2fa(body.session_id)
    if not user_id:
        raise HTTPException(status_code=401, detail="2FA session expired or invalid.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.totp_secret:
        raise HTTPException(status_code=401, detail="User not found.")

    if not verify_totp(user.totp_secret, body.code):
        raise HTTPException(status_code=401, detail="Invalid 2FA code.")

    access_token = await _issue_tokens(db, user, response)
    await db.commit()
    return ApiResponse(success=True, data=TokenResponse(access_token=access_token))


# ─── Refresh (token rotation) ────────────────────────────────────────────────

@router.post("/auth/refresh")
async def refresh(request: Request, response: Response, db: DBSession):
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "No refresh token"})

    payload = decode_token(raw)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Invalid refresh token"})

    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.expires_at > datetime.now(timezone.utc),
            RefreshToken.revoked_at.is_(None),
        )
    )
    stored = result.scalar_one_or_none()
    if not stored:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Refresh token expired or revoked"})

    # Revoke old token (rotation)
    stored.revoked_at = datetime.now(timezone.utc)

    user_result = await db.execute(select(User).where(User.id == stored.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "User not found or inactive"})

    access_token = await _issue_tokens(db, user, response)
    await db.commit()
    return ApiResponse(success=True, data={"access_token": access_token, "token_type": "bearer"})


# ─── Logout ───────────────────────────────────────────────────────────────────

@router.post("/auth/logout")
async def logout(request: Request, response: Response, user: AuthUser, db: DBSession):
    await _revoke_refresh_token(db, request)
    await db.commit()
    response.delete_cookie("refresh_token")
    return ApiResponse(success=True, message="Logged out")


# ─── Me ───────────────────────────────────────────────────────────────────────

@router.get("/auth/me")
async def me(user: AuthUser, db: DBSession):
    result = await db.execute(select(User).where(User.id == user.user_id))
    u = result.scalar_one_or_none()
    return ApiResponse(success=True, data={
        "user_id": str(user.user_id),
        "company_id": str(user.company_id),
        "email": user.email if hasattr(user, "email") else None,
        "permissions": user.permissions,
        "totp_enabled": bool(u and getattr(u, "totp_enabled", False)),
    })


# ─── Change Password ─────────────────────────────────────────────────────────

@router.post("/auth/change-password")
async def change_password(body: ChangePasswordRequest, user: AuthUser, db: DBSession):
    result = await db.execute(select(User).where(User.id == user.user_id))
    u = result.scalar_one_or_none()
    if not u or not verify_password(body.current_password, u.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    u.hashed_password = hash_password(body.new_password)
    u.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return ApiResponse(success=True, message="Password updated.")


# ─── Password Reset ───────────────────────────────────────────────────────────

@router.post("/auth/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request, db: DBSession):
    ip = request.client.host if request.client else "anon"
    if not await check_rate_limit(f"forgot:{ip}", limit=5, window=300):
        raise HTTPException(status_code=429, detail="Too many requests.")

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    # Always return success to prevent email enumeration
    if not user or not user.is_active:
        return ApiResponse(success=True, message="If that email exists, an OTP has been sent.")

    otp = generate_otp()
    await store_otp(body.email, otp)

    from app.core.config import settings
    if settings.is_development:
        return ApiResponse(success=True, data={"otp": otp}, message="OTP generated (dev mode — not emailed).")
    # In production: send email via SMTP (not yet configured)
    return ApiResponse(success=True, message="OTP sent to your email.")


@router.post("/auth/reset-password")
async def reset_password(body: ResetPasswordRequest, db: DBSession):
    if not await verify_and_consume_otp(body.email, body.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.hashed_password = hash_password(body.new_password)
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return ApiResponse(success=True, message="Password reset successfully. Please log in.")


# ─── 2FA Setup ────────────────────────────────────────────────────────────────

@router.post("/auth/2fa/setup")
async def setup_2fa(user: AuthUser, db: DBSession):
    result = await db.execute(select(User).where(User.id == user.user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found.")
    if getattr(u, "totp_enabled", False):
        raise HTTPException(status_code=400, detail="2FA is already enabled.")
    secret = generate_totp_secret()
    u.totp_secret = secret
    await db.commit()
    uri = get_totp_provisioning_uri(secret, u.email)
    return ApiResponse(success=True, data={"secret": secret, "uri": uri})


@router.post("/auth/2fa/enable")
async def enable_2fa(body: Enable2FARequest, user: AuthUser, db: DBSession):
    result = await db.execute(select(User).where(User.id == user.user_id))
    u = result.scalar_one_or_none()
    if not u or not u.totp_secret:
        raise HTTPException(status_code=400, detail="Run /auth/2fa/setup first.")
    if not verify_totp(u.totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid code.")
    u.totp_enabled = True
    await db.commit()
    return ApiResponse(success=True, message="2FA enabled.")


@router.post("/auth/2fa/disable")
async def disable_2fa(body: Disable2FARequest, user: AuthUser, db: DBSession):
    result = await db.execute(select(User).where(User.id == user.user_id))
    u = result.scalar_one_or_none()
    if not u or not verify_password(body.password, u.hashed_password):
        raise HTTPException(status_code=400, detail="Password incorrect.")
    u.totp_enabled = False
    u.totp_secret = None
    await db.commit()
    return ApiResponse(success=True, message="2FA disabled.")
