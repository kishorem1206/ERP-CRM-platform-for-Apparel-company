"""Vendors: user-added types, and contacts / bank accounts set on create and
replaced on edit. Runs in a rolled-back transaction.
Run from the backend container: python -m pytest tests/test_vendors.py
"""
import asyncio
from uuid import uuid4

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.domain.business_rules import BusinessRulesError
from app.models.user import User
from app.schemas.purchase import VendorBankDetailCreate, VendorContactCreate, VendorCreate, VendorUpdate
from app.services.purchase import PurchaseService


async def _run_vendor_scenario():
    async with AsyncSessionLocal() as db:
        try:
            user_id, company_id = (await db.execute(select(User.id, User.company_id).limit(1))).one()
            svc = PurchaseService(db)
            r = {}

            async def code_of(coro):
                try:
                    await coro
                except BusinessRulesError as e:
                    return e.code

            name = f"Embroiderer {uuid4().hex[:4]}"
            created = await svc.create_vendor_type(name, company_id)
            r["type_code"] = created["code"]
            r["dup_type"] = await code_of(svc.create_vendor_type(name.upper(), company_id))
            r["dup_builtin"] = await code_of(svc.create_vendor_type("agent", company_id))
            r["types"] = [t["code"] for t in await svc.list_vendor_types(company_id)]

            vendor = await svc.create_vendor(VendorCreate(
                code=f"T-{uuid4().hex[:6]}", name="Test Vendor", vendor_type=created["code"],
                contacts=[
                    VendorContactCreate(name="Ravi", phone="98400 00001", designation="Owner", notes="Calls after 6pm"),
                    VendorContactCreate(name="Meena", designation="Accounts", is_primary=True),
                    VendorContactCreate(name="  "),   # blank row is skipped
                ],
                bank_details=[
                    VendorBankDetailCreate(bank_name="SBI", account_number="1234", ifsc="sbin0001234", branch="Tiruppur"),
                    VendorBankDetailCreate(bank_name="HDFC", account_number="5678"),
                ],
            ), company_id, user_id)
            r["contacts"] = sorted((c.name, c.designation, c.is_primary) for c in vendor.contacts)
            r["banks"] = sorted((b.bank_name, b.ifsc, b.branch, b.is_primary) for b in vendor.bank_details)
            r["bad_type"] = await code_of(svc.create_vendor(VendorCreate(
                code=f"T-{uuid4().hex[:6]}", name="X", vendor_type="no_such_type"), company_id, user_id))

            vendor_id = vendor.id
            updated = await svc.update_vendor(vendor_id, VendorUpdate(
                vendor_type="job_worker", contacts=[VendorContactCreate(name="Kumar", designation="Manager")],
            ), company_id)
            r["after_edit"] = (
                updated.vendor_type,
                [(c.name, c.designation, c.is_primary) for c in updated.contacts],
                len(updated.bank_details),   # not sent, so kept
            )
            return r
        finally:
            await db.rollback()


def test_vendor_types_contacts_and_banks():
    r = asyncio.run(_run_vendor_scenario())
    assert r["type_code"].startswith("embroiderer_")
    assert r["dup_type"] == "DUPLICATE_NAME"
    assert r["dup_builtin"] == "DUPLICATE_NAME"
    assert r["types"][:4] == ["supplier", "job_worker", "transporter", "agent"] and r["type_code"] in r["types"]
    assert r["contacts"] == [("Meena", "Accounts", True), ("Ravi", "Owner", False)]
    assert r["banks"] == [("HDFC", None, None, False), ("SBI", "SBIN0001234", "Tiruppur", True)]
    assert r["bad_type"] == "UNKNOWN_VENDOR_TYPE"
    assert r["after_edit"] == ("job_worker", [("Kumar", "Manager", True)], 2)
