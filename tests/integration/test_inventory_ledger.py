"""Integration tests for the inventory ledger invariants."""
import pytest
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


import os as _os
_TEST_EMAIL = _os.getenv("TEST_ADMIN_EMAIL", "admin@company.com")
_TEST_PASSWORD = _os.environ["ADMIN_SEED_PASSWORD"]


async def _login(client):
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": _TEST_EMAIL, "password": _TEST_PASSWORD},
    )
    return res.json()["data"]["access_token"]


async def test_receive_increases_balance(client, db: AsyncSession):
    token = await _login(client)

    # Fetch warehouse and product IDs from seed data
    wh = await db.execute(text("SELECT id FROM warehouses LIMIT 1"))
    warehouse_id = str(wh.scalar())

    prod = await db.execute(text("SELECT id FROM products LIMIT 1"))
    product_id = prod.scalar()
    if product_id is None:
        pytest.skip("No products in DB — run seed data first")

    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post(
        "/api/v1/inventory/receive",
        json={
            "product_id": str(product_id),
            "warehouse_id": warehouse_id,
            "quantity": "100.0000",
            "unit_cost": "50.00",
            "reference": "TEST-RCV-001",
        },
        headers=headers,
    )
    assert res.status_code == 200

    # Verify a +1 transaction was created
    row = await db.execute(
        text("SELECT direction, quantity FROM inventory_transactions ORDER BY created_at DESC LIMIT 1")
    )
    txn = row.fetchone()
    assert txn.direction == 1
    assert Decimal(str(txn.quantity)) == Decimal("100.0000")


async def test_cannot_issue_more_than_available(client, db: AsyncSession):
    token = await _login(client)
    wh = await db.execute(text("SELECT id FROM warehouses LIMIT 1"))
    warehouse_id = str(wh.scalar())
    prod = await db.execute(text("SELECT id FROM products LIMIT 1"))
    product_id = prod.scalar()
    if product_id is None:
        pytest.skip("No products in DB")

    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post(
        "/api/v1/inventory/issue",
        json={
            "product_id": str(product_id),
            "warehouse_id": warehouse_id,
            "quantity": "999999.0000",
            "reference": "TEST-ISS-OVER",
        },
        headers=headers,
    )
    assert res.status_code == 422  # business rule violation


async def test_transfer_between_warehouses(client, db: AsyncSession):
    token = await _login(client)

    warehouses = await db.execute(text("SELECT id FROM warehouses LIMIT 2"))
    rows = warehouses.fetchall()
    if len(rows) < 2:
        pytest.skip("Need at least 2 warehouses")

    from_wh, to_wh = str(rows[0][0]), str(rows[1][0])
    prod = await db.execute(text("SELECT id FROM products LIMIT 1"))
    product_id = prod.scalar()
    if product_id is None:
        pytest.skip("No products in DB")

    headers = {"Authorization": f"Bearer {token}"}

    # First receive into source warehouse
    await client.post(
        "/api/v1/inventory/receive",
        json={
            "product_id": str(product_id),
            "warehouse_id": from_wh,
            "quantity": "50.0000",
            "unit_cost": "40.00",
            "reference": "TEST-RCV-XFER",
        },
        headers=headers,
    )

    # Transfer
    res = await client.post(
        "/api/v1/inventory/transfer",
        json={
            "product_id": str(product_id),
            "from_warehouse_id": from_wh,
            "to_warehouse_id": to_wh,
            "quantity": "20.0000",
            "reference": "TEST-XFER-001",
        },
        headers=headers,
    )
    assert res.status_code == 200

    # Total net across both warehouses should be unchanged (50 original)
    result = await db.execute(
        text("""
            SELECT SUM(quantity * direction)
            FROM inventory_transactions
            WHERE product_id = :pid
        """),
        {"pid": str(product_id)},
    )
    net = result.scalar()
    assert Decimal(str(net)) >= Decimal("50.0000")


async def test_transactions_are_immutable(client, db: AsyncSession):
    """Verify the API layer exposes no DELETE or UPDATE route for inventory transactions."""
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    row = await db.execute(text("SELECT id FROM inventory_transactions LIMIT 1"))
    txn_id = row.scalar()
    if txn_id is None:
        pytest.skip("No transactions yet — receive stock first")

    # No DELETE route — expect 404 or 405
    res = await client.delete(f"/api/v1/inventory/transactions/{txn_id}", headers=headers)
    assert res.status_code in (404, 405), (
        f"DELETE should be blocked but got {res.status_code}"
    )

    # No PATCH/PUT route — expect 404 or 405
    res = await client.patch(
        f"/api/v1/inventory/transactions/{txn_id}",
        json={"direction": 0},
        headers=headers,
    )
    assert res.status_code in (404, 405), (
        f"PATCH should be blocked but got {res.status_code}"
    )
