from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.domain.business_rules import BusinessRulesError
from app.middleware.request_id import RequestIDMiddleware

_SENTRY_DSN = getattr(settings, "SENTRY_DSN", "")
if _SENTRY_DSN:
    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        environment=settings.APP_ENV,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.05,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        send_default_pii=False,
    )


async def _ensure_notifications_table():
    from sqlalchemy import text
    from app.db.session import engine
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notifications (
                id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                company_id  UUID NOT NULL REFERENCES companies(id),
                user_id     UUID REFERENCES users(id),
                notification_type VARCHAR(50) NOT NULL,
                title       VARCHAR(200) NOT NULL,
                body        TEXT NOT NULL,
                data        JSONB,
                is_read     BOOLEAN NOT NULL DEFAULT FALSE,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))


async def _ensure_2fa_columns():
    from sqlalchemy import text
    from app.db.session import engine
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(64)"
        ))
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_count SMALLINT NOT NULL DEFAULT 0"
        ))
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ"
        ))


async def _ensure_refresh_tokens_table():
    from sqlalchemy import text
    from app.db.session import engine
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash  VARCHAR(200) NOT NULL UNIQUE,
                expires_at  TIMESTAMPTZ NOT NULL,
                revoked_at  TIMESTAMPTZ,
                created_at  TIMESTAMPTZ NOT NULL
            )
        """))


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Starting Apparel ERP API", env=settings.APP_ENV)
    await _ensure_notifications_table()
    await _ensure_2fa_columns()
    await _ensure_refresh_tokens_table()
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Apparel Manufacturing ERP",
    version="1.0.0",
    docs_url="/api/v1/docs" if settings.is_development else None,
    redoc_url="/api/v1/redoc" if settings.is_development else None,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# Middleware (order matters — outermost first)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router)


# ── Exception handlers (most specific first) ──────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return ORJSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail},
    )


@app.exception_handler(BusinessRulesError)
async def business_rules_exception_handler(request: Request, exc: BusinessRulesError):
    return ORJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback as _tb
    logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
    msg = f"{type(exc).__name__}: {exc}" if settings.APP_DEBUG else "An unexpected error occurred."
    if settings.APP_DEBUG:
        logger.error(_tb.format_exc())
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {"code": "INTERNAL_ERROR", "message": msg},
        },
    )
