"""Integration tests for auth endpoints."""
import os
import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@company.com")
_PASSWORD = os.environ["ADMIN_SEED_PASSWORD"]


async def test_login_success(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": _EMAIL, "password": _PASSWORD},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert body["data"]["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": _EMAIL, "password": "wrong_password"},
    )
    assert res.status_code == 401


async def test_login_unknown_email(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@company.com", "password": _PASSWORD},
    )
    assert res.status_code == 401


async def test_protected_route_without_token(client: AsyncClient):
    res = await client.get("/api/v1/health")
    assert res.status_code == 200  # health is public

    res = await client.post("/api/v1/agents/chat", json={"message": "hello"})
    assert res.status_code == 401


async def test_refresh_token_flow(client: AsyncClient):
    # Login to get refresh cookie
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": _EMAIL, "password": _PASSWORD},
    )
    assert login_res.status_code == 200
    body = login_res.json()
    assert body["success"] is True

    # Refresh should return new access token (cookie is forwarded automatically by httpx)
    refresh_res = await client.post("/api/v1/auth/refresh")
    assert refresh_res.status_code == 200
    refresh_body = refresh_res.json()
    assert refresh_body["success"] is True
    assert "access_token" in refresh_body["data"]


async def test_account_lockout_after_five_failures(client: AsyncClient):
    for _ in range(5):
        await client.post(
            "/api/v1/auth/login",
            json={"email": _EMAIL, "password": "bad_pass"},
        )

    res = await client.post(
        "/api/v1/auth/login",
        json={"email": _EMAIL, "password": _PASSWORD},
    )
    # Account should be locked — 423 or 401 with lockout message
    assert res.status_code in (401, 423)
    body = res.json()
    error = body.get("error", {})
    error_code = error.get("code", "") if isinstance(error, dict) else str(error)
    assert "lock" in error_code.lower() or res.status_code == 423
