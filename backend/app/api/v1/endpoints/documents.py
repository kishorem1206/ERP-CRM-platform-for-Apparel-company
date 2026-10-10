"""Printable PDFs for the sales and purchase documents shown in the sidebar.

Each route reuses the same GET handler the detail page uses, so the PDF can't
drift from what the screen shows.
"""
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from app.api.v1.deps import AuthUser, DBSession
from app.api.v1.endpoints.purchase import get_purchase_entry, get_purchase_order
from app.api.v1.endpoints.finance import get_credit_note, get_debit_note, get_payment, get_vendor_payment
from app.api.v1.endpoints.sales import get_delivery, get_invoice, get_quotation, get_sales_order, get_sales_return
from app.models.company import Company
from app.models.master import Product, ProductVariant, Unit
from app.models.purchase import PurchaseEntry, PurchaseOrder
from app.models.sales import CustomerAddress, Invoice, SalesOrder
from app.services.business_document import date_text, document_filename, inr, qty, render_business_document_pdf

router = APIRouter(prefix="/documents", tags=["documents"])


async def _company(db, company_id) -> dict:
    c = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if c is None:
        return {"name": "Company"}
    return {
        "name": c.name, "address": c.address, "gstin": c.gstin, "pan": c.pan,
        "phone": c.phone, "email": c.email,
    }


async def _product_names(db, product_ids, variant_ids, unit_ids):
    products = {}
    if product_ids:
        rows = await db.execute(select(Product.id, Product.name).where(Product.id.in_(product_ids)))
        products = {r.id: r.name for r in rows}
    variants = {}
    if variant_ids:
        rows = await db.execute(select(ProductVariant.id, ProductVariant.sku).where(ProductVariant.id.in_(variant_ids)))
        variants = {r.id: r.sku for r in rows}
    units = {}
    if unit_ids:
        rows = await db.execute(select(Unit.id, Unit.name).where(Unit.id.in_(unit_ids)))
        units = {r.id: r.name for r in rows}
    return products, variants, units


def _item_name(item, products, variants) -> tuple[str, str | None]:
    if getattr(item, "description", None):
        return item.description, None
    name = products.get(item.product_id, "Item")
    sku = variants.get(item.variant_id) if getattr(item, "variant_id", None) else None
    return name, (f"SKU {sku}" if sku else None)


def _tax_totals(taxable, cgst, sgst, igst, total) -> list[tuple[str, str]]:
    rows = [("Taxable value", inr(taxable))]
    if cgst:
        rows.append(("CGST", inr(cgst)))
    if sgst:
        rows.append(("SGST", inr(sgst)))
    if igst:
        rows.append(("IGST", inr(igst)))
    return rows


async def _customer_lines(db, customer_id) -> list[str]:
    row = (await db.execute(
        select(CustomerAddress).where(CustomerAddress.customer_id == customer_id, CustomerAddress.is_default.is_(True))
    )).scalar_one_or_none()
    if row is None:
        return []
    parts = [row.line1, row.line2, row.city, row.state, row.pincode]
    return [", ".join(p for p in parts if p)] if any(parts) else []


def _pdf(company: dict, doc: dict, title: str, number: str) -> Response:
    pdf = render_business_document_pdf(company, doc)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{document_filename(title, number)}"'},
    )


@router.get("/quotations/{quotation_id}/pdf")
async def quotation_pdf(quotation_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.view")
    q = (await get_quotation(quotation_id, db, user)).data
    products, variants, units = await _product_names(
        db, {i.product_id for i in q.items}, {i.variant_id for i in q.items if i.variant_id},
        {i.unit_id for i in q.items},
    )
    items = [
        {
            "description": _item_name(i, products, variants)[0], "sub": _item_name(i, products, variants)[1],
            "hsn": i.hsn_code, "qty": qty(i.quantity), "unit": units.get(i.unit_id),
            "rate": inr(i.unit_price), "discount": qty(i.discount_pct) if i.discount_pct else None,
            "amount": inr(i.taxable_amount),
        }
        for i in q.items
    ]
    doc = {
        "title": "Quotation", "number": q.quotation_number, "date": date_text(q.quotation_date), "status": q.status,
        "meta": [("Valid until", date_text(q.valid_until))],
        "parties": [{"label": "Quotation to", "name": q.customer_name,
                     "lines": await _customer_lines(db, q.customer_id)}],
        "lines": items,
        "totals": _tax_totals(q.taxable_amount, q.cgst_amount, q.sgst_amount, q.igst_amount, q.total_amount)
        + ([("Discount", inr(q.discount_amount))] if q.discount_amount else []),
        "grand_total": inr(q.total_amount), "notes": q.notes, "terms": q.terms,
    }
    return _pdf(await _company(db, user.company_id), doc, "Quotation", q.quotation_number)


@router.get("/sales-orders/{so_id}/pdf")
async def sales_order_pdf(so_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.view")
    so = (await get_sales_order(so_id, db, user)).data
    products, variants, units = await _product_names(
        db, {i.product_id for i in so.items}, {i.variant_id for i in so.items if i.variant_id},
        {i.unit_id for i in so.items},
    )
    items = [
        {
            "description": _item_name(i, products, variants)[0], "sub": _item_name(i, products, variants)[1],
            "hsn": i.hsn_code, "qty": qty(i.quantity), "unit": units.get(i.unit_id),
            "rate": inr(i.unit_price), "discount": qty(i.discount_pct) if i.discount_pct else None,
            "amount": inr(i.taxable_amount),
        }
        for i in so.items
    ]
    meta = [("Order date", date_text(so.order_date)), ("Expected delivery", date_text(so.expected_delivery))]
    if so.customer_po_number:
        meta.append(("Customer PO", so.customer_po_number))
    doc = {
        "title": "Sales order", "number": so.order_number, "date": date_text(so.order_date), "status": so.status,
        "meta": meta,
        "parties": [{"label": "Customer", "name": so.customer_name, "lines": await _customer_lines(db, so.customer_id)}],
        "lines": items,
        "totals": _tax_totals(so.taxable_amount, so.cgst_amount, so.sgst_amount, so.igst_amount, so.total_amount)
        + ([("Discount", inr(so.discount_amount))] if so.discount_amount else []),
        "grand_total": inr(so.total_amount), "notes": so.notes,
    }
    return _pdf(await _company(db, user.company_id), doc, "SalesOrder", so.order_number)


@router.get("/deliveries/{delivery_id}/pdf")
async def delivery_challan_pdf(delivery_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.view")
    d = (await get_delivery(delivery_id, db, user)).data
    products, variants, units = await _product_names(
        db, {i.product_id for i in d.items}, {i.variant_id for i in d.items if i.variant_id},
        {i.unit_id for i in d.items},
    )
    so_number = None
    if d.sales_order_id:
        so_number = (await db.execute(select(SalesOrder.order_number).where(SalesOrder.id == d.sales_order_id))).scalar()
    items = [
        {
            "description": _item_name(i, products, variants)[0], "sub": _item_name(i, products, variants)[1],
            "hsn": None, "qty": qty(i.quantity), "unit": units.get(i.unit_id),
            "rate": None, "discount": None, "amount": None,
        }
        for i in d.items
    ]
    meta = [("Sales order", so_number or "—"), ("Dispatch date", date_text(d.delivery_date))]
    for label, value in [("Transporter", d.transporter), ("LR number", d.lr_number), ("Vehicle", d.vehicle_number),
                         ("Cartons", d.carton_count), ("Packages", d.package_count),
                         ("Gross weight", qty(d.gross_weight) + " kg" if d.gross_weight else None),
                         ("Net weight", qty(d.net_weight) + " kg" if d.net_weight else None)]:
        if value not in (None, ""):
            meta.append((label, str(value)))
    doc = {
        "title": "Delivery challan", "number": d.delivery_number, "date": date_text(d.delivery_date),
        "status": d.status, "meta": meta,
        "parties": [{"label": "Deliver to", "name": d.customer_name, "lines": await _customer_lines(db, d.customer_id)}],
        "lines": items, "totals": [], "grand_total": None, "notes": d.notes,
    }
    return _pdf(await _company(db, user.company_id), doc, "DeliveryChallan", d.delivery_number)


@router.get("/returns/{return_id}/pdf")
async def sales_return_pdf(return_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.view")
    r = (await get_sales_return(return_id, db, user)).data
    products, variants, units = await _product_names(
        db, {i.product_id for i in r.items}, {i.variant_id for i in r.items if i.variant_id},
        {i.unit_id for i in r.items},
    )
    items = [
        {
            "description": _item_name(i, products, variants)[0], "sub": _item_name(i, products, variants)[1],
            "hsn": None, "qty": qty(i.quantity), "unit": units.get(i.unit_id),
            "rate": inr(i.unit_cost) if i.unit_cost else None, "discount": None,
            "amount": inr(i.total_cost) if i.total_cost else None,
        }
        for i in r.items
    ]
    meta = [("Disposition", ", ".join(sorted({i.disposition for i in r.items})))]
    doc = {
        "title": "Sales return", "number": r.return_number, "date": date_text(r.return_date),
        "status": r.status, "meta": meta,
        "parties": [{"label": "Customer", "name": r.customer_name, "lines": await _customer_lines(db, r.customer_id)}],
        "lines": items, "totals": [], "grand_total": None, "notes": r.reason,
    }
    return _pdf(await _company(db, user.company_id), doc, "SalesReturn", r.return_number)


@router.get("/invoices/{invoice_id}/pdf")
async def invoice_pdf(invoice_id: UUID, db: DBSession, user: AuthUser):
    user.require("sales.view")
    inv = (await get_invoice(invoice_id, db, user)).data
    items: list[dict] = []
    if inv.delivery_id:
        d = (await get_delivery(inv.delivery_id, db, user)).data
        products, variants, units = await _product_names(
            db, {i.product_id for i in d.items}, {i.variant_id for i in d.items if i.variant_id},
            {i.unit_id for i in d.items},
        )
        items = [
            {
                "description": _item_name(i, products, variants)[0], "sub": _item_name(i, products, variants)[1],
                "hsn": None, "qty": qty(i.quantity), "unit": units.get(i.unit_id),
                "rate": inr(i.unit_price), "discount": None, "amount": inr(i.total_amount),
            }
            for i in d.items
        ]
    elif inv.sales_order_id:
        so = (await get_sales_order(inv.sales_order_id, db, user)).data
        products, variants, units = await _product_names(
            db, {i.product_id for i in so.items}, {i.variant_id for i in so.items if i.variant_id},
            {i.unit_id for i in so.items},
        )
        items = [
            {
                "description": _item_name(i, products, variants)[0], "sub": _item_name(i, products, variants)[1],
                "hsn": i.hsn_code, "qty": qty(i.quantity), "unit": units.get(i.unit_id),
                "rate": inr(i.unit_price), "discount": qty(i.discount_pct) if i.discount_pct else None,
                "amount": inr(i.taxable_amount),
            }
            for i in so.items
        ]
    doc = {
        "title": "Tax invoice", "number": inv.invoice_number, "date": date_text(inv.invoice_date),
        "status": inv.status,
        "meta": [("Due date", date_text(inv.due_date))],
        "parties": [{"label": "Bill to", "name": inv.customer_name, "lines": await _customer_lines(db, inv.customer_id)}],
        "lines": items,
        "totals": _tax_totals(inv.taxable_amount, inv.cgst_amount, inv.sgst_amount, inv.igst_amount, inv.total_amount)
        + [("Paid", inr(inv.paid_amount)), ("Balance due", inr(inv.balance_amount))],
        "grand_total": inr(inv.total_amount), "notes": inv.notes,
    }
    return _pdf(await _company(db, user.company_id), doc, "Invoice", inv.invoice_number)


@router.get("/purchase-orders/{po_id}/pdf")
async def purchase_order_pdf(po_id: UUID, db: DBSession, user: AuthUser):
    user.require("purchase.view")
    po = (await get_purchase_order(po_id, db, user)).data
    products, variants, units = await _product_names(
        db, {i.product_id for i in po.items}, {i.variant_id for i in po.items if i.variant_id},
        {i.unit_id for i in po.items},
    )
    items = [
        {
            "description": _item_name(i, products, variants)[0], "sub": _item_name(i, products, variants)[1],
            "hsn": None, "qty": qty(i.ordered_qty), "unit": units.get(i.unit_id),
            "rate": inr(i.unit_price), "discount": qty(i.discount_pct) if i.discount_pct else None,
            "amount": inr(i.taxable_amount),
        }
        for i in po.items
    ]
    doc = {
        "title": "Purchase order", "number": po.po_number, "date": date_text(po.order_date), "status": po.status,
        "meta": [("Expected date", date_text(po.expected_date))],
        "parties": [{"label": "Vendor", "name": po.vendor_name, "lines": []}],
        "lines": items,
        "totals": _tax_totals(po.taxable_amount, po.cgst_amount, po.sgst_amount, po.igst_amount, po.total_amount),
        "grand_total": inr(po.total_amount), "notes": po.notes, "terms": po.terms,
    }
    return _pdf(await _company(db, user.company_id), doc, "PurchaseOrder", po.po_number)


@router.get("/goods-receipts/{entry_id}/pdf")
async def goods_receipt_pdf(entry_id: UUID, db: DBSession, user: AuthUser):
    user.require("purchase.view")
    e = (await get_purchase_entry(entry_id, db, user)).data
    products, variants, units = await _product_names(
        db, {i.product_id for i in e.items}, {i.variant_id for i in e.items if i.variant_id},
        {i.unit_id for i in e.items},
    )
    po_number = None
    if e.purchase_order_id:
        po_number = (await db.execute(select(PurchaseOrder.po_number).where(PurchaseOrder.id == e.purchase_order_id))).scalar()
    items = [
        {
            "description": _item_name(i, products, variants)[0], "sub": _item_name(i, products, variants)[1],
            "hsn": None,
            "qty": f"{qty(i.accepted_qty)} / {qty(i.received_qty)}",
            "unit": units.get(i.unit_id),
            "rate": inr(i.unit_price), "discount": None, "amount": inr(i.total_amount),
        }
        for i in e.items
    ]
    meta = [("Purchase order", po_number or "—")]
    if e.invoice_number:
        meta.append(("Vendor invoice", e.invoice_number))
    if e.invoice_date:
        meta.append(("Invoice date", date_text(e.invoice_date)))
    doc = {
        "title": "Goods receipt", "number": e.entry_number, "date": date_text(e.entry_date), "status": e.status,
        "meta": meta,
        "parties": [{"label": "Received from", "name": e.vendor_name, "lines": []}],
        "lines": items,
        "totals": [("Taxable value", inr(e.taxable_amount))],
        "grand_total": inr(e.total_amount), "notes": e.notes,
    }
    return _pdf(await _company(db, user.company_id), doc, "GoodsReceipt", e.entry_number)


def _allocation_lines(allocations, labels: dict, prefix: str) -> list[dict]:
    return [
        {
            "description": f"{prefix} {labels.get(a.get('ref_id'), '—')}" if labels.get(a.get("ref_id")) else f"{prefix} —",
            "sub": None, "hsn": None, "qty": "", "unit": None, "rate": "", "discount": None,
            "amount": inr(a["allocated_amount"]),
        }
        for a in allocations
    ]


@router.get("/payments/{payment_id}/pdf")
async def payment_receipt_pdf(payment_id: UUID, db: DBSession, user: AuthUser):
    user.require("finance.view")
    p = (await get_payment(payment_id, db, user)).data
    invoice_ids = [a.invoice_id for a in p.allocations]
    numbers = {}
    if invoice_ids:
        rows = await db.execute(select(Invoice.id, Invoice.invoice_number).where(Invoice.id.in_(invoice_ids)))
        numbers = {r.id: r.invoice_number for r in rows}
    lines = _allocation_lines(
        [{"ref_id": a.invoice_id, "allocated_amount": a.allocated_amount} for a in p.allocations],
        numbers, "Against invoice",
    )
    meta = [("Payment mode", str(p.payment_mode).upper())]
    if p.reference:
        meta.append(("Reference", p.reference))
    if p.bank_account:
        meta.append(("Bank account", p.bank_account))
    doc = {
        "title": "Payment receipt", "number": p.payment_number, "date": date_text(p.payment_date), "status": p.status,
        "meta": meta,
        "parties": [{"label": "Received from", "name": p.customer_name, "lines": await _customer_lines(db, p.customer_id)}],
        "lines": lines,
        "totals": [("Amount received", inr(p.amount))],
        "grand_total": inr(p.amount), "notes": p.notes,
    }
    return _pdf(await _company(db, user.company_id), doc, "PaymentReceipt", p.payment_number)


@router.get("/vendor-payments/{payment_id}/pdf")
async def vendor_payment_voucher_pdf(payment_id: UUID, db: DBSession, user: AuthUser):
    user.require("finance.view")
    p = (await get_vendor_payment(payment_id, db, user)).data
    entry_ids = [a.purchase_entry_id for a in p.allocations]
    numbers = {}
    if entry_ids:
        rows = await db.execute(select(PurchaseEntry.id, PurchaseEntry.entry_number).where(PurchaseEntry.id.in_(entry_ids)))
        numbers = {r.id: r.entry_number for r in rows}
    lines = _allocation_lines(
        [{"ref_id": a.purchase_entry_id, "allocated_amount": a.allocated_amount} for a in p.allocations],
        numbers, "Against goods receipt",
    )
    meta = [("Payment mode", str(p.payment_mode).upper())]
    if p.reference:
        meta.append(("Reference", p.reference))
    if p.bank_account:
        meta.append(("Bank account", p.bank_account))
    doc = {
        "title": "Payment voucher", "number": p.payment_number, "date": date_text(p.payment_date), "status": p.status,
        "meta": meta,
        "parties": [{"label": "Paid to", "name": p.vendor_name, "lines": []}],
        "lines": lines,
        "totals": [("Amount paid", inr(p.amount))],
        "grand_total": inr(p.amount), "notes": p.notes,
    }
    return _pdf(await _company(db, user.company_id), doc, "PaymentVoucher", p.payment_number)


@router.get("/credit-notes/{cn_id}/pdf")
async def credit_note_pdf(cn_id: UUID, db: DBSession, user: AuthUser):
    user.require("finance.view")
    cn = (await get_credit_note(cn_id, db, user)).data
    invoice_number = None
    if cn.invoice_id:
        invoice_number = (await db.execute(select(Invoice.invoice_number).where(Invoice.id == cn.invoice_id))).scalar()
    doc = {
        "title": "Credit note", "number": cn.credit_note_number, "date": date_text(cn.credit_note_date),
        "status": cn.status,
        "meta": [("Against invoice", invoice_number or "—")],
        "parties": [{"label": "Customer", "name": cn.customer_name, "lines": await _customer_lines(db, cn.customer_id)}],
        "lines": [{"description": cn.reason or "Sales return / adjustment", "sub": None, "hsn": None, "qty": "",
                   "unit": None, "rate": "", "discount": None, "amount": inr(cn.taxable_amount)}],
        "totals": _tax_totals(cn.taxable_amount, cn.cgst_amount, cn.sgst_amount, cn.igst_amount, cn.total_amount),
        "grand_total": inr(cn.total_amount), "notes": cn.notes,
    }
    return _pdf(await _company(db, user.company_id), doc, "CreditNote", cn.credit_note_number)


@router.get("/debit-notes/{dn_id}/pdf")
async def debit_note_pdf(dn_id: UUID, db: DBSession, user: AuthUser):
    user.require("finance.view")
    dn = (await get_debit_note(dn_id, db, user)).data
    entry_number = None
    if dn.purchase_entry_id:
        entry_number = (await db.execute(select(PurchaseEntry.entry_number).where(PurchaseEntry.id == dn.purchase_entry_id))).scalar()
    doc = {
        "title": "Debit note", "number": dn.debit_note_number, "date": date_text(dn.debit_note_date),
        "status": dn.status,
        "meta": [("Against goods receipt", entry_number or "—")],
        "parties": [{"label": "Vendor", "name": dn.vendor_name, "lines": []}],
        "lines": [{"description": dn.reason or "Purchase return / adjustment", "sub": None, "hsn": None, "qty": "",
                   "unit": None, "rate": "", "discount": None, "amount": inr(dn.total_amount)}],
        "totals": [],
        "grand_total": inr(dn.total_amount), "notes": dn.notes,
    }
    return _pdf(await _company(db, user.company_id), doc, "DebitNote", dn.debit_note_number)
