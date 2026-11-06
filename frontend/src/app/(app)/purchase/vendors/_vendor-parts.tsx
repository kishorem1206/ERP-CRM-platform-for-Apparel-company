"use client";
import { Plus, Trash2 } from "lucide-react";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { useCreateVendorType, useVendorTypes } from "@/lib/vendor-types";

const inputCls =
  "w-full rounded border border-input bg-background px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

export interface ContactRow { key: string; name: string; designation: string; phone: string; email: string; notes: string; is_primary: boolean }
export interface BankRow { key: string; bank_name: string; account_name: string; account_number: string; ifsc: string; branch: string; notes: string; is_primary: boolean }

const newKey = () => Math.random().toString(36).slice(2);
export const emptyContact = (primary = false): ContactRow =>
  ({ key: newKey(), name: "", designation: "", phone: "", email: "", notes: "", is_primary: primary });
export const emptyBank = (primary = false): BankRow =>
  ({ key: newKey(), bank_name: "", account_name: "", account_number: "", ifsc: "", branch: "", notes: "", is_primary: primary });

export interface VendorContactApi { name: string; phone: string | null; email: string | null; designation: string | null; notes: string | null; is_primary: boolean }
export interface VendorBankApi { bank_name: string | null; account_name: string | null; account_number: string | null; ifsc: string | null; branch: string | null; notes: string | null; is_primary: boolean }

export const contactRowsFrom = (rows: VendorContactApi[]): ContactRow[] =>
  rows.map((c) => ({
    key: newKey(), name: c.name ?? "", designation: c.designation ?? "", phone: c.phone ?? "",
    email: c.email ?? "", notes: c.notes ?? "", is_primary: c.is_primary,
  }));
export const bankRowsFrom = (rows: VendorBankApi[]): BankRow[] =>
  rows.map((b) => ({
    key: newKey(), bank_name: b.bank_name ?? "", account_name: b.account_name ?? "", account_number: b.account_number ?? "",
    ifsc: b.ifsc ?? "", branch: b.branch ?? "", notes: b.notes ?? "", is_primary: b.is_primary,
  }));

/** A reason the rows can't be saved yet, or "" — so nothing typed is silently dropped. */
export function contactsAndBanksError(contacts: ContactRow[], banks: BankRow[]): string {
  if (contacts.some((c) => !c.name.trim() && (c.designation || c.phone || c.email || c.notes).trim()))
    return "Each contact needs a name.";
  if (banks.some((b) => !b.bank_name.trim() && !b.account_number.trim() && (b.account_name || b.ifsc || b.branch || b.notes).trim()))
    return "Each bank account needs a bank name or account number.";
  if (banks.some((b) => b.ifsc.trim() && !/^[A-Za-z]{4}0[A-Za-z0-9]{6}$/.test(b.ifsc.trim())))
    return "IFSC should be 11 characters, e.g. SBIN0001234.";
  return "";
}

/** What the API takes; blank rows are dropped by the server. */
export const contactsPayload = (rows: ContactRow[]) =>
  rows.map(({ key: _key, ...c }) => ({ ...c, name: c.name.trim() }));
export const banksPayload = (rows: BankRow[]) => rows.map(({ key: _key, ...b }) => b);

export function VendorTypeSelect({ value, onChange, accent }: { value: string; onChange: (v: string) => void; accent: string }) {
  const types = useVendorTypes();
  const createType = useCreateVendorType();
  return (
    <SearchableSelect
      value={value}
      onChange={onChange}
      accent={accent}
      placeholder="Select type"
      onCreate={createType}
      createNoun="vendor type"
      options={(types.data ?? []).map((t) => ({ value: t.code, label: t.name }))}
    />
  );
}

function Field({ label, children, className = "" }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={className}>
      <label className="text-[11px] font-medium text-muted-foreground">{label}</label>
      <div className="mt-0.5">{children}</div>
    </div>
  );
}

function SectionHead({ title, hint, onAdd, addLabel }: { title: string; hint: string; onAdd: () => void; addLabel: string }) {
  return (
    <div className="flex items-end justify-between gap-3">
      <div>
        <p className="text-sm font-semibold">{title}</p>
        <p className="text-[11px] text-muted-foreground">{hint}</p>
      </div>
      <button type="button" onClick={onAdd} className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline shrink-0">
        <Plus className="h-3.5 w-3.5" /> {addLabel}
      </button>
    </div>
  );
}

function PrimaryAndRemove({ name, checked, onPrimary, onRemove }: { name: string; checked: boolean; onPrimary: () => void; onRemove: () => void }) {
  return (
    <div className="flex items-center justify-between">
      <label className="inline-flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer">
        <input type="radio" name={name} checked={checked} onChange={onPrimary} /> Primary
      </label>
      <button type="button" onClick={onRemove} className="text-muted-foreground hover:text-destructive" aria-label="Remove">
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

export function ContactsEditor({ rows, onChange }: { rows: ContactRow[]; onChange: (rows: ContactRow[]) => void }) {
  const set = (key: string, patch: Partial<ContactRow>) => onChange(rows.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  const remove = (key: string) => {
    const left = rows.filter((r) => r.key !== key);
    if (left.length && !left.some((r) => r.is_primary)) left[0] = { ...left[0], is_primary: true };
    onChange(left);
  };
  return (
    <div className="space-y-2">
      <SectionHead title="Contacts" hint="People at this vendor — add as many as you need."
        addLabel="Add contact" onAdd={() => onChange([...rows, emptyContact(rows.length === 0)])} />
      {rows.length === 0 && <p className="text-xs text-muted-foreground">No contacts yet.</p>}
      {rows.map((c) => (
        <div key={c.key} className="rounded-xl border border-border bg-muted/20 p-3 space-y-2">
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            <Field label="Name *"><input className={inputCls} value={c.name} onChange={(e) => set(c.key, { name: e.target.value })} placeholder="Contact name" /></Field>
            <Field label="Designation"><input className={inputCls} value={c.designation} onChange={(e) => set(c.key, { designation: e.target.value })} placeholder="e.g. Owner, Accounts" /></Field>
            <Field label="Phone"><input className={inputCls} value={c.phone} onChange={(e) => set(c.key, { phone: e.target.value })} placeholder="98765 43210" /></Field>
            <Field label="Email"><input type="email" className={inputCls} value={c.email} onChange={(e) => set(c.key, { email: e.target.value })} /></Field>
          </div>
          <Field label="Notes"><input className={inputCls} value={c.notes} onChange={(e) => set(c.key, { notes: e.target.value })} placeholder="e.g. Call after 6 pm" /></Field>
          <PrimaryAndRemove name="primary-contact" checked={c.is_primary}
            onPrimary={() => onChange(rows.map((r) => ({ ...r, is_primary: r.key === c.key })))} onRemove={() => remove(c.key)} />
        </div>
      ))}
    </div>
  );
}

export function BanksEditor({ rows, onChange }: { rows: BankRow[]; onChange: (rows: BankRow[]) => void }) {
  const set = (key: string, patch: Partial<BankRow>) => onChange(rows.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  const remove = (key: string) => {
    const left = rows.filter((r) => r.key !== key);
    if (left.length && !left.some((r) => r.is_primary)) left[0] = { ...left[0], is_primary: true };
    onChange(left);
  };
  return (
    <div className="space-y-2">
      <SectionHead title="Bank accounts" hint="Add every account you pay this vendor into; mark the usual one as primary."
        addLabel="Add bank account" onAdd={() => onChange([...rows, emptyBank(rows.length === 0)])} />
      {rows.length === 0 && <p className="text-xs text-muted-foreground">No bank accounts yet.</p>}
      {rows.map((b) => (
        <div key={b.key} className="rounded-xl border border-border bg-muted/20 p-3 space-y-2">
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
            <Field label="Bank name"><input className={inputCls} value={b.bank_name} onChange={(e) => set(b.key, { bank_name: e.target.value })} placeholder="e.g. SBI" /></Field>
            <Field label="Account holder name"><input className={inputCls} value={b.account_name} onChange={(e) => set(b.key, { account_name: e.target.value })} /></Field>
            <Field label="Account number"><input className={inputCls} value={b.account_number} maxLength={30} onChange={(e) => set(b.key, { account_number: e.target.value })} /></Field>
            <Field label="IFSC"><input className={`${inputCls} uppercase`} value={b.ifsc} maxLength={11} onChange={(e) => set(b.key, { ifsc: e.target.value })} placeholder="SBIN0001234" /></Field>
            <Field label="Branch"><input className={inputCls} value={b.branch} onChange={(e) => set(b.key, { branch: e.target.value })} /></Field>
            <Field label="Notes"><input className={inputCls} value={b.notes} onChange={(e) => set(b.key, { notes: e.target.value })} placeholder="e.g. Only for job-work bills" /></Field>
          </div>
          <PrimaryAndRemove name="primary-bank" checked={b.is_primary}
            onPrimary={() => onChange(rows.map((r) => ({ ...r, is_primary: r.key === b.key })))} onRemove={() => remove(b.key)} />
        </div>
      ))}
    </div>
  );
}
