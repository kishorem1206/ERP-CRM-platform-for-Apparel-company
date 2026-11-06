"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { X } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { ModalShell } from "@/components/shared/modal-shell";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { RETAIL_ACCENT } from "@/lib/retail";

const inputCls = "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

/** Register a retail customer, or edit one (pass `initial` with its id). */
export function CustomerFormModal({ initial, onClose, onSaved }: {
  initial?: Record<string, string | null> & { id?: string }; onClose: () => void; onSaved: (id: string) => void;
}) {
  const [f, setF] = useState({
    name: initial?.name ?? "", mobile: initial?.mobile ?? "", email: initial?.email ?? "",
    date_of_birth: initial?.date_of_birth ?? "", gender: initial?.gender ?? "",
    billing_address: initial?.billing_address ?? "", shipping_address: initial?.shipping_address ?? "",
    city: initial?.city ?? "", state: initial?.state ?? "", pincode: initial?.pincode ?? "", notes: initial?.notes ?? "",
  });
  const [error, setError] = useState("");
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF((x) => ({ ...x, [k]: e.target.value }));
  const save = useMutation({
    mutationFn: async () => {
      const body = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v === "" ? null : v]));
      return initial?.id
        ? (await api.patch(`/retail/customers/${initial.id}`, body)).data.data
        : (await api.post("/retail/customers", body)).data.data;
    },
    onSuccess: (c: { id: string }) => onSaved(c.id),
    onError: (e: unknown) => setError(parseApiError(e, "Could not save this customer.")),
  });
  return (
    <ModalShell maxWidth="max-w-xl" onClose={onClose}>
      <div className="flex items-center justify-between px-5 py-4 border-b">
        <h2 className="font-semibold">{initial?.id ? "Edit customer" : "Register retail customer"}</h2>
        <button onClick={onClose} aria-label="Close"><X className="h-4 w-4" /></button>
      </div>
      <form className="p-5 space-y-3" onSubmit={(e) => { e.preventDefault(); setError(""); save.mutate(); }}>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="text-xs text-muted-foreground">Name *</label><input required className={inputCls} value={f.name} onChange={set("name")} /></div>
          <div><label className="text-xs text-muted-foreground">Mobile *</label><input required inputMode="numeric" className={inputCls} value={f.mobile} onChange={set("mobile")} /></div>
          <div><label className="text-xs text-muted-foreground">Email</label><input type="email" className={inputCls} value={f.email} onChange={set("email")} /></div>
          <div className="grid grid-cols-2 gap-2">
            <div><label className="text-xs text-muted-foreground">Date of birth</label><input type="date" className={inputCls} value={f.date_of_birth} onChange={set("date_of_birth")} /></div>
            <div>
              <label className="text-xs text-muted-foreground">Gender</label>
              <SearchableSelect clearable value={f.gender} onChange={(v) => setF((x) => ({ ...x, gender: v }))} accent={RETAIL_ACCENT} placeholder="—"
                options={[{ value: "female", label: "Female" }, { value: "male", label: "Male" }, { value: "other", label: "Other" }]} />
            </div>
          </div>
        </div>
        <div><label className="text-xs text-muted-foreground">Billing address</label><textarea rows={2} className={`${inputCls} resize-none`} value={f.billing_address} onChange={set("billing_address")} /></div>
        <div><label className="text-xs text-muted-foreground">Shipping address (if different)</label><textarea rows={2} className={`${inputCls} resize-none`} value={f.shipping_address} onChange={set("shipping_address")} /></div>
        <div className="grid grid-cols-3 gap-3">
          <div><label className="text-xs text-muted-foreground">City</label><input className={inputCls} value={f.city} onChange={set("city")} /></div>
          <div><label className="text-xs text-muted-foreground">State</label><input className={inputCls} value={f.state} onChange={set("state")} /></div>
          <div><label className="text-xs text-muted-foreground">Pincode</label><input className={inputCls} value={f.pincode} onChange={set("pincode")} /></div>
        </div>
        <div><label className="text-xs text-muted-foreground">Notes</label><input className={inputCls} value={f.notes} onChange={set("notes")} /></div>
        {error && <p className="text-xs text-destructive">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-xl border text-sm">Cancel</button>
          <button type="submit" disabled={save.isPending} className="px-4 py-2 rounded-xl text-sm font-semibold text-white disabled:opacity-50" style={{ background: RETAIL_ACCENT }}>
            {save.isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}

