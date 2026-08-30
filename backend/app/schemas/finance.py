"""Pydantic schemas for the Finance module."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator


# ── Payment (customer receipt) ─────────────────────────────────────────────────

class PaymentAllocationCreate(BaseModel):
    invoice_id: UUID
    allocated_amount: Decimal


class PaymentAllocationOut(BaseModel):
    id: UUID
    invoice_id: UUID
    allocated_amount: Decimal
    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    customer_id: UUID
    payment_date: date
    amount: Decimal
    payment_mode: str = "neft"
    reference: str | None = None
    bank_account: str | None = None
    notes: str | None = None
    allocations: list[PaymentAllocationCreate] = []

    @field_validator("payment_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        allowed = {"cash", "cheque", "neft", "rtgs", "upi", "other"}
        if v not in allowed:
            raise ValueError(f"payment_mode must be one of {allowed}")
        return v


class PaymentOut(BaseModel):
    id: UUID
    payment_number: str
    customer_id: UUID
    customer_name: str | None = None
    payment_date: date
    amount: Decimal
    payment_mode: str
    reference: str | None
    bank_account: str | None
    notes: str | None
    status: str
    allocations: list[PaymentAllocationOut] = []
    model_config = {"from_attributes": True}


# ── Vendor Payment ────────────────────────────────────────────────────────────

class VendorPaymentAllocationCreate(BaseModel):
    purchase_entry_id: UUID
    allocated_amount: Decimal


class VendorPaymentAllocationOut(BaseModel):
    id: UUID
    purchase_entry_id: UUID
    allocated_amount: Decimal
    model_config = {"from_attributes": True}


class VendorPaymentCreate(BaseModel):
    vendor_id: UUID
    payment_date: date
    amount: Decimal
    payment_mode: str = "neft"
    reference: str | None = None
    bank_account: str | None = None
    notes: str | None = None
    allocations: list[VendorPaymentAllocationCreate] = []

    @field_validator("payment_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        allowed = {"cash", "cheque", "neft", "rtgs", "upi", "other"}
        if v not in allowed:
            raise ValueError(f"payment_mode must be one of {allowed}")
        return v


class VendorPaymentOut(BaseModel):
    id: UUID
    payment_number: str
    vendor_id: UUID
    vendor_name: str | None = None
    payment_date: date
    amount: Decimal
    payment_mode: str
    reference: str | None
    bank_account: str | None
    notes: str | None
    status: str
    allocations: list[VendorPaymentAllocationOut] = []
    model_config = {"from_attributes": True}


# ── Credit Note ───────────────────────────────────────────────────────────────

class CreditNoteCreate(BaseModel):
    customer_id: UUID
    invoice_id: UUID | None = None
    credit_note_date: date
    reason: str | None = None
    taxable_amount: Decimal = Decimal("0")
    cgst_amount: Decimal = Decimal("0")
    sgst_amount: Decimal = Decimal("0")
    igst_amount: Decimal = Decimal("0")
    total_amount: Decimal
    notes: str | None = None


class CreditNoteOut(BaseModel):
    id: UUID
    credit_note_number: str
    customer_id: UUID
    customer_name: str | None = None
    invoice_id: UUID | None
    credit_note_date: date
    reason: str | None
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal
    status: str
    notes: str | None
    model_config = {"from_attributes": True}


# ── Debit Note ────────────────────────────────────────────────────────────────

class DebitNoteCreate(BaseModel):
    vendor_id: UUID
    purchase_entry_id: UUID | None = None
    debit_note_date: date
    reason: str | None = None
    total_amount: Decimal
    notes: str | None = None


class DebitNoteOut(BaseModel):
    id: UUID
    debit_note_number: str
    vendor_id: UUID
    vendor_name: str | None = None
    purchase_entry_id: UUID | None
    debit_note_date: date
    reason: str | None
    total_amount: Decimal
    status: str
    notes: str | None
    model_config = {"from_attributes": True}


# ── Ledger ────────────────────────────────────────────────────────────────────

class LedgerEntry(BaseModel):
    entry_date: date
    doc_type: str
    doc_number: str
    description: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


# ── GST Register ──────────────────────────────────────────────────────────────

class GSTOutputEntry(BaseModel):
    invoice_date: date
    invoice_number: str
    customer_name: str
    gstin: str | None
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal


class GSTInputEntry(BaseModel):
    entry_date: date
    entry_number: str
    vendor_name: str
    gstin: str | None
    invoice_number: str | None
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal
