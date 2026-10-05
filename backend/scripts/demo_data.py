"""Dummy data for empty modules in the development database.

Every row written here is marked [DEMO] in its name/description or carries a
DEMO- number, so it can be found and removed. Payments and vendor payments
are allocated to the paid amounts already on invoices and purchase entries,
so balances stay consistent and nothing is counted twice.

Run inside the backend container:
    python -m scripts.demo_data            # add
    python -m scripts.demo_data --remove   # remove everything it added
"""
import asyncio
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text

from app.db.session import AsyncSessionLocal

COMPANY_ID = "cfa4e79d-ddd7-4c04-8432-d690a97d1b84"
TODAY = date(2026, 10, 6)
MARK = "[DEMO]"
RNG = random.Random(20261006)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _rows(db, sql: str, **params):
    return (await db.execute(text(sql), params)).mappings().all()


async def _exec(db, sql: str, **params):
    await db.execute(text(sql), params)


async def already_present(db) -> bool:
    row = (await db.execute(text("SELECT COUNT(*) FROM expenses WHERE expense_number LIKE 'DEMO-%'"))).scalar()
    return bool(row)


async def remove(db):
    for sql in [
        "DELETE FROM vendor_payment_allocations WHERE vendor_payment_id IN (SELECT id FROM vendor_payments WHERE payment_number LIKE 'DEMO-%')",
        "DELETE FROM payment_allocations WHERE payment_id IN (SELECT id FROM payments WHERE payment_number LIKE 'DEMO-%')",
        "DELETE FROM vendor_payments WHERE payment_number LIKE 'DEMO-%'",
        "DELETE FROM payments WHERE payment_number LIKE 'DEMO-%'",
        "DELETE FROM credit_notes WHERE credit_note_number LIKE 'DEMO-%'",
        "DELETE FROM debit_notes WHERE debit_note_number LIKE 'DEMO-%'",
        "DELETE FROM expenses WHERE expense_number LIKE 'DEMO-%'",
        "DELETE FROM expense_categories WHERE name LIKE '[DEMO]%'",
        "DELETE FROM customer_addresses WHERE line1 LIKE '[DEMO]%'",
        "DELETE FROM customer_contacts WHERE name LIKE '[DEMO]%'",
        "DELETE FROM vendor_contacts WHERE name LIKE '[DEMO]%'",
        "DELETE FROM vendor_bank_details WHERE bank_name LIKE '[DEMO]%'",
        "DELETE FROM warehouse_locations WHERE name LIKE '[DEMO]%'",
        "DELETE FROM brands WHERE name LIKE '[DEMO]%'",
    ]:
        await db.execute(text(sql))


async def add(db):
    now = _now()
    admin = (await _rows(db, "SELECT id FROM users WHERE company_id = :c ORDER BY created_at LIMIT 1", c=COMPANY_ID))[0]["id"]

    # ── Masters ────────────────────────────────────────────────────────────
    for name in ["Alpha", "Bravo", "Cedar", "Delta"]:
        await _exec(db, "INSERT INTO brands (id, company_id, name) VALUES (:id, :c, :n)",
                    id=uuid.uuid4(), c=COMPANY_ID, n=f"{MARK} Brand {name}")

    warehouses = await _rows(db, "SELECT id FROM warehouses WHERE company_id = :c", c=COMPANY_ID)
    for w in warehouses:
        for suffix in ["Rack A", "Rack B"]:
            await _exec(db, "INSERT INTO warehouse_locations (id, warehouse_id, name, code) VALUES (:id, :w, :n, :code)",
                        id=uuid.uuid4(), w=w["id"], n=f"{MARK} {suffix}", code=f"DEMO-{suffix[-1]}")

    customers = await _rows(db, "SELECT id FROM customers WHERE company_id = :c ORDER BY code", c=COMPANY_ID)
    for i, cust in enumerate(customers, start=1):
        await _exec(db, """INSERT INTO customer_addresses (id, customer_id, address_type, line1, city, state, state_code,
                           pincode, country, is_default) VALUES (:id, :cid, 'billing', :l1, 'Demo City', 'Tamil Nadu', 33,
                           '600001', 'India', true)""",
                    id=uuid.uuid4(), cid=cust["id"], l1=f"{MARK} Plot {i}, Industrial Estate")
        await _exec(db, """INSERT INTO customer_contacts (id, customer_id, name, designation, phone, email, is_primary,
                           created_at, updated_at) VALUES (:id, :cid, :n, 'Purchase Manager', :ph, :em, true, :now, :now)""",
                    id=uuid.uuid4(), cid=cust["id"], n=f"{MARK} Contact {i}",
                    ph=f"+91 90000 {i:05d}", em=f"demo-contact-{i}@example.com", now=now)

    vendors = await _rows(db, "SELECT id, name FROM vendors WHERE company_id = :c ORDER BY code", c=COMPANY_ID)
    for i, v in enumerate(vendors, start=1):
        await _exec(db, "INSERT INTO vendor_contacts (id, vendor_id, name, phone, email, is_primary) VALUES (:id, :vid, :n, :ph, :em, true)",
                    id=uuid.uuid4(), vid=v["id"], n=f"{MARK} Contact {i}", ph=f"+91 91000 {i:05d}", em=f"demo-vendor-{i}@example.com")
        await _exec(db, """INSERT INTO vendor_bank_details (id, vendor_id, bank_name, account_number, ifsc, account_name, is_primary)
                           VALUES (:id, :vid, :bank, :acc, 'DEMO0000001', :an, true)""",
                    id=uuid.uuid4(), vid=v["id"], bank=f"{MARK} Demo Bank", acc=f"DEMO-ACC-{i:04d}", an=v["name"])

    # ── Expenses ───────────────────────────────────────────────────────────
    category_ids = []
    for name in ["Travel", "Utilities", "Office supplies", "Repairs & maintenance", "Bank charges", "Courier"]:
        cid = uuid.uuid4()
        category_ids.append(cid)
        await _exec(db, "INSERT INTO expense_categories (id, company_id, name) VALUES (:id, :c, :n)",
                    id=cid, c=COMPANY_ID, n=f"{MARK} {name}")

    descriptions = [
        "Site visit fare", "Electricity bill", "Printer toner", "Machine servicing", "Bank service fee",
        "Courier to buyer", "Client lunch", "Fuel for delivery van", "Water supply", "Stationery order",
    ]
    for n in range(1, 26):
        when = TODAY - timedelta(days=RNG.randint(0, 120))
        amount = Decimal(RNG.randint(400, 80000))
        vendor = RNG.choice(vendors)["id"] if RNG.random() < 0.5 else None
        await _exec(db, """INSERT INTO expenses (id, company_id, expense_number, category_id, vendor_id, expense_date,
                           amount, payment_method, reference, description, created_at, created_by)
                           VALUES (:id, :c, :num, :cat, :vid, :dt, :amt, :pm, :ref, :desc, :now, :uid)""",
                    id=uuid.uuid4(), c=COMPANY_ID, num=f"DEMO-EXP-{n:03d}", cat=RNG.choice(category_ids), vid=vendor,
                    dt=when, amt=amount, pm=RNG.choice(["cash", "upi", "neft"]), ref=f"DEMO-REF-{n:04d}",
                    desc=f"{MARK} {RNG.choice(descriptions)}", now=now, uid=admin)

    # ── Customer receipts: allocated to the paid amounts on invoices ───────
    invoices = await _rows(db, """SELECT id, invoice_number, customer_id, invoice_date, total_amount, paid_amount
                                  FROM invoices WHERE company_id = :c AND paid_amount > 0 ORDER BY invoice_date""", c=COMPANY_ID)
    for n, inv in enumerate(invoices, start=1):
        pay_date = min(inv["invoice_date"] + timedelta(days=RNG.randint(5, 20)), TODAY)
        pid = uuid.uuid4()
        await _exec(db, """INSERT INTO payments (id, company_id, payment_number, customer_id, payment_date, amount,
                           payment_mode, reference, bank_account, notes, status, created_at, created_by)
                           VALUES (:id, :c, :num, :cust, :dt, :amt, :mode, :ref, 'DEMO BANK', :notes, 'completed', :now, :uid)""",
                    id=pid, c=COMPANY_ID, num=f"DEMO-PMT-{n:03d}", cust=inv["customer_id"], dt=pay_date, amt=inv["paid_amount"],
                    mode=RNG.choice(["neft", "rtgs", "upi", "cheque"]), ref=f"DEMO-UTR-{n:05d}",
                    notes=f"{MARK} Receipt against {inv['invoice_number']}", now=now, uid=admin)
        await _exec(db, "INSERT INTO payment_allocations (id, payment_id, invoice_id, allocated_amount) VALUES (:id, :p, :i, :a)",
                    id=uuid.uuid4(), p=pid, i=inv["id"], a=inv["paid_amount"])

    # ── Vendor payments: allocated to paid amounts on purchase entries ─────
    entries = await _rows(db, """SELECT id, entry_number, vendor_id, entry_date, total_amount, paid_amount
                                 FROM purchase_entries WHERE company_id = :c AND paid_amount > 0 ORDER BY entry_date""", c=COMPANY_ID)
    for n, pe in enumerate(entries, start=1):
        pay_date = min(pe["entry_date"] + timedelta(days=RNG.randint(7, 25)), TODAY)
        vid = uuid.uuid4()
        await _exec(db, """INSERT INTO vendor_payments (id, company_id, payment_number, vendor_id, payment_date, amount,
                           payment_mode, reference, bank_account, notes, status, created_at, created_by)
                           VALUES (:id, :c, :num, :vend, :dt, :amt, :mode, :ref, 'DEMO BANK', :notes, 'completed', :now, :uid)""",
                    id=vid, c=COMPANY_ID, num=f"DEMO-VPMT-{n:03d}", vend=pe["vendor_id"], dt=pay_date, amt=pe["paid_amount"],
                    mode=RNG.choice(["neft", "rtgs", "upi", "cheque"]), ref=f"DEMO-VUTR-{n:05d}",
                    notes=f"{MARK} Payment against {pe['entry_number']}", now=now, uid=admin)
        await _exec(db, """INSERT INTO vendor_payment_allocations (id, vendor_payment_id, purchase_entry_id, allocated_amount)
                           VALUES (:id, :v, :e, :a)""", id=uuid.uuid4(), v=vid, e=pe["id"], a=pe["paid_amount"])

    # ── Credit notes (sales returns) and debit notes (purchase returns) ────
    for n, inv in enumerate(invoices[:2], start=1):
        total = (Decimal(inv["total_amount"]) * Decimal("0.05")).quantize(Decimal("0.01"))
        taxable = (total / Decimal("1.18")).quantize(Decimal("0.01"))
        tax_each = ((total - taxable) / 2).quantize(Decimal("0.01"))
        await _exec(db, """INSERT INTO credit_notes (id, company_id, credit_note_number, customer_id, invoice_id,
                           credit_note_date, reason, taxable_amount, cgst_amount, sgst_amount, igst_amount, total_amount,
                           status, notes, created_at, created_by)
                           VALUES (:id, :c, :num, :cust, :inv, :dt, :reason, :tx, :cg, :sg, 0, :tot, 'issued', :notes, :now, :uid)""",
                    id=uuid.uuid4(), c=COMPANY_ID, num=f"DEMO-CN-{n:03d}", cust=inv["customer_id"], inv=inv["id"],
                    dt=min(inv["invoice_date"] + timedelta(days=30), TODAY), reason=f"{MARK} Sample sales return",
                    tx=taxable, cg=tax_each, sg=tax_each, tot=total, notes=f"{MARK} Not adjusted against the invoice balance",
                    now=now, uid=admin)
    for n, pe in enumerate(entries[:2], start=1):
        total = (Decimal(pe["total_amount"]) * Decimal("0.03")).quantize(Decimal("0.01"))
        await _exec(db, """INSERT INTO debit_notes (id, company_id, debit_note_number, vendor_id, purchase_entry_id,
                           debit_note_date, reason, total_amount, status, notes, created_at, created_by)
                           VALUES (:id, :c, :num, :vend, :pe, :dt, :reason, :tot, 'issued', :notes, :now, :uid)""",
                    id=uuid.uuid4(), c=COMPANY_ID, num=f"DEMO-DN-{n:03d}", vend=pe["vendor_id"], pe=pe["id"],
                    dt=min(pe["entry_date"] + timedelta(days=20), TODAY), reason=f"{MARK} Sample purchase return",
                    tot=total, notes=f"{MARK} Not adjusted against the entry balance", now=now, uid=admin)

    print(f"added: {len(invoices)} receipts, {len(entries)} vendor payments, 25 expenses, 2 credit notes, 2 debit notes")


async def main():
    remove_mode = "--remove" in sys.argv
    async with AsyncSessionLocal() as db:
        try:
            if remove_mode:
                await remove(db)
                print("removed demo rows")
            else:
                if await already_present(db):
                    print("demo rows already present; run with --remove first")
                    await db.rollback()
                    return
                await add(db)
            await db.commit()
        except Exception:
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
