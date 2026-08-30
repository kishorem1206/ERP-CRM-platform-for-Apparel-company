import random
import string
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pyotp
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

OTP_TTL = 600        # 10 minutes
TOTP_ISSUER = "Apparel ERP"


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(payload: dict) -> str:
    data = payload.copy()
    data["exp"] = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    data["type"] = "access"
    return jwt.encode(data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    data = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        ),
    }
    return jwt.encode(data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None


# ─── TOTP (2FA) ───────────────────────────────────────────────────────────────

def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_provisioning_uri(secret: str, email: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=TOTP_ISSUER)


def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


# ─── Password-reset OTP (Redis-backed) ───────────────────────────────────────

def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


async def store_otp(email: str, otp: str) -> None:
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await r.setex(f"erp:otp:{email.lower()}", OTP_TTL, otp)
    finally:
        await r.aclose()


async def verify_and_consume_otp(email: str, code: str) -> bool:
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        stored = await r.get(f"erp:otp:{email.lower()}")
        if stored and stored == code:
            await r.delete(f"erp:otp:{email.lower()}")
            return True
        return False
    finally:
        await r.aclose()


# ─── Rate-limit helper (Redis sliding-window) ────────────────────────────────

async def check_rate_limit(key: str, limit: int, window: int) -> bool:
    """Returns True if the request is allowed, False if rate-limited."""
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        count = await r.incr(f"erp:rl:{key}")
        if count == 1:
            await r.expire(f"erp:rl:{key}", window)
        return count <= limit
    finally:
        await r.aclose()


# ─── 2FA pending-session (Redis) ─────────────────────────────────────────────

async def store_pending_2fa(session_id: str, user_id: str) -> None:
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await r.setex(f"erp:2fa:{session_id}", 300, user_id)  # 5 min
    finally:
        await r.aclose()


async def consume_pending_2fa(session_id: str) -> str | None:
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        user_id = await r.get(f"erp:2fa:{session_id}")
        if user_id:
            await r.delete(f"erp:2fa:{session_id}")
        return user_id
    finally:
        await r.aclose()
