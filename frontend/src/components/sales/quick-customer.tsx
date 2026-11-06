"use client";
import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { usePermissions } from "@/lib/permissions";
import { ModalShell } from "@/components/shared/modal-shell";
import { CREATE_CANCELLED } from "@/components/shared/searchable-select";

const GSTIN_RE = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
const inputCls =
  "mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

function autoCode(name: string): string {
  const prefix = name.trim().toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 4) || "CUST";
  return `${prefix}-${Math.floor(1000 + Math.random() * 9000)}`;
}

interface Pending { name: string; resolve: (id: string) => void; reject: (e: Error) => void }

/**
 * "+ Add" for a customer dropdown on Sales forms: opens a short customer form
 * (name, code, phone, GSTIN, billing address) and selects the new customer.
 * The full customer record can be completed later under Sales / CRM → Customers.
 * Returns `onCreate` for SearchableSelect (undefined without sales.create) and
 * the form to render.
 */
export function useQuickCustomer() {
  const { can } = usePermissions();
  const [pending, setPending] = useState<Pending | null>(null);
  const onCreate = can("sales.create")
    ? (name: string) => new Promise<string>((resolve, reject) => setPending({ name, resolve, reject }))
    : undefined;
  const modal = pending ? (
    <QuickCustomerForm
      key={pending.name}
      initialName={pending.name}
      onSaved={(id) => { pending.resolve(id); setPending(null); }}
      onCancel={() => { pending.reject(new Error(CREATE_CANCELLED)); setPending(null); }}
    />
  ) : null;
  return { onCreate, modal };
}

function QuickCustomerForm({ initialName, onSaved, onCancel }: {
  initialName: string; onSaved: (id: string) => void; onCancel: () => void;
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    legal_name: initialName, code: autoCode(initialName), mobile: "", email: "", gstin: "",
    line1: "", city: "", state: "", pincode: "",
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const codeTouched = useRef(false);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function save(e: React.FormEvent) {
    e.preventDefault();
    e.stopPropagation(); // don't submit the order form underneath
    const gstin = form.gstin.trim().toUpperCase();
    if (gstin && !GSTIN_RE.test(gstin)) {
      setError("Invalid GSTIN format (15 characters, e.g. 22AAAAA0000A1Z5)");
      return;
    }
    const hasAddress = form.line1.trim() || form.city.trim() || form.pincode.trim();
    const billing = {
      address_type: "billing", line1: form.line1.trim(), line2: "", city: form.city.trim(),
      state: form.state.trim(), state_code: gstin ? parseInt(gstin.slice(0, 2), 10) : null, pincode: form.pincode.trim(),
      country: "India", is_default: true,
    };
    setSaving(true);
    setError("");
    try {
      const res = await api.post("/sales/customers", {
        code: form.code.trim(),
        legal_name: form.legal_name.trim(),
        mobile: form.mobile.trim() || null,
        email: form.email.trim() || null,
        gstin: gstin || null,
        addresses: hasAddress ? [billing, { ...billing, address_type: "shipping", is_default: false }] : [],
      });
      await qc.invalidateQueries({ queryKey: ["customers-list"] });
      qc.invalidateQueries({ queryKey: ["customers"] });
      onSaved(res.data.data.id as string);
    } catch (err) {
      setError(parseApiError(err, "Could not save this customer."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell onClose={onCancel}>
      <div className="flex items-center justify-between px-5 py-4 border-b">
        <div>
          <h2 className="font-semibold text-base">New customer</h2>
          <p className="text-xs text-muted-foreground mt-0.5">The rest of the details can be added later under Customers.</p>
        </div>
        <button type="button" onClick={onCancel} className="text-muted-foreground hover:text-foreground" aria-label="Close">
          <X className="h-4 w-4" />
        </button>
      </div>
      <form className="p-5 space-y-3" onSubmit={save}>
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-2">
            <label className="text-xs font-medium text-muted-foreground">Customer name *</label>
            <input required autoFocus value={form.legal_name} className={inputCls}
              onChange={(e) => {
                const legal_name = e.target.value;
                setForm((f) => ({ ...f, legal_name, code: codeTouched.current ? f.code : autoCode(legal_name) }));
              }} />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Code *</label>
            <input required value={form.code} className={inputCls}
              onChange={(e) => { codeTouched.current = true; set("code")(e); }} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Mobile</label>
            <input value={form.mobile} onChange={set("mobile")} className={inputCls} placeholder="98765 43210" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Email</label>
            <input type="email" value={form.email} onChange={set("email")} className={inputCls} />
          </div>
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground">GSTIN</label>
          <input value={form.gstin} onChange={set("gstin")} className={`${inputCls} uppercase`} placeholder="33AAAAA0000A1Z5" />
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground">Billing address</label>
          <input value={form.line1} onChange={set("line1")} className={inputCls} placeholder="Street / building" />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <input value={form.city} onChange={set("city")} className={inputCls} placeholder="City" />
          <input value={form.state} onChange={set("state")} className={inputCls} placeholder="State" />
          <input value={form.pincode} onChange={set("pincode")} className={inputCls} placeholder="Pincode" />
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onCancel} className="px-4 py-1.5 rounded border border-input text-sm hover:bg-muted">Cancel</button>
          <button type="submit" disabled={saving}
            className="px-4 py-1.5 rounded bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-60">
            {saving ? "Saving…" : "Save customer"}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}
