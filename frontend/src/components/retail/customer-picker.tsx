"use client";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { UserPlus, X } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { usePermissions } from "@/lib/permissions";
import { RETAIL_ACCENT, rupees, type RetailCustomer } from "@/lib/retail";

const inputCls =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

/** Find a retail customer by mobile or name, or register one on the spot. */
export function CustomerPicker({ value, onChange }: { value: RetailCustomer | null; onChange: (c: RetailCustomer | null) => void }) {
  const { can } = usePermissions();
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [registering, setRegistering] = useState(false);
  const [form, setForm] = useState({ name: "", mobile: "", date_of_birth: "", city: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 250);
    return () => clearTimeout(t);
  }, [query]);

  const results = useQuery({
    queryKey: ["retail-customers", "pick", debounced],
    queryFn: async () => (await api.get("/retail/customers", { params: { search: debounced, page_size: 6, sort: "recent" } })).data.data as RetailCustomer[],
    enabled: debounced.length >= 2 && !value,
  });
  const digits = debounced.replace(/\D/g, "");
  const noMatch = results.isSuccess && (results.data ?? []).length === 0;

  async function register(e: React.FormEvent) {
    e.preventDefault();
    e.stopPropagation();
    setSaving(true);
    setError("");
    try {
      const res = await api.post("/retail/customers", {
        name: form.name, mobile: form.mobile, date_of_birth: form.date_of_birth || null, city: form.city || null,
      });
      onChange(res.data.data as RetailCustomer);
      setRegistering(false);
      setQuery("");
    } catch (err) {
      setError(parseApiError(err, "Could not register this customer."));
    } finally {
      setSaving(false);
    }
  }

  if (value) {
    return (
      <div className="flex items-start justify-between gap-3 rounded-xl border border-border bg-muted/30 px-3 py-2.5">
        <div className="min-w-0">
          <p className="text-sm font-semibold truncate">{value.name}</p>
          <p className="text-xs text-muted-foreground">
            {value.mobile}
            {value.purchase_count > 0 && ` · ${value.purchase_count} bill${value.purchase_count === 1 ? "" : "s"} · ${rupees(value.total_spent, 0)} spent`}
          </p>
          {Number(value.outstanding) > 0 && (
            <p className="text-xs font-medium text-amber-700 dark:text-amber-400">Outstanding {rupees(value.outstanding)}</p>
          )}
        </div>
        <button type="button" onClick={() => onChange(null)} className="text-muted-foreground hover:text-foreground" aria-label="Remove customer">
          <X className="h-4 w-4" />
        </button>
      </div>
    );
  }

  if (registering) {
    return (
      <form onSubmit={register} className="space-y-2 rounded-xl border border-border p-3">
        <p className="text-xs font-semibold">Register customer</p>
        <input required autoFocus className={inputCls} placeholder="Name *" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
        <input required className={inputCls} placeholder="Mobile * (10 digits)" inputMode="numeric" value={form.mobile}
          onChange={(e) => setForm((f) => ({ ...f, mobile: e.target.value }))} />
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-[11px] text-muted-foreground">Date of birth</label>
            <input type="date" className={inputCls} value={form.date_of_birth} onChange={(e) => setForm((f) => ({ ...f, date_of_birth: e.target.value }))} />
          </div>
          <div>
            <label className="text-[11px] text-muted-foreground">City</label>
            <input className={inputCls} value={form.city} onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))} />
          </div>
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={() => setRegistering(false)} className="px-3 py-1.5 rounded-lg border border-input text-xs hover:bg-muted">Cancel</button>
          <button type="submit" disabled={saving} className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white disabled:opacity-60" style={{ background: RETAIL_ACCENT }}>
            {saving ? "Saving…" : "Register"}
          </button>
        </div>
      </form>
    );
  }

  return (
    <div className="space-y-1.5">
      <input className={inputCls} placeholder="Customer mobile or name (optional for cash)" value={query}
        onChange={(e) => setQuery(e.target.value)} />
      {(results.data ?? []).map((c) => (
        <button key={c.id} type="button" onClick={() => { onChange(c); setQuery(""); }}
          className="w-full text-left rounded-lg border border-border px-3 py-2 hover:bg-muted/60">
          <span className="text-sm font-medium">{c.name}</span>
          <span className="ml-2 text-xs text-muted-foreground">{c.mobile}{c.city ? ` · ${c.city}` : ""}</span>
        </button>
      ))}
      {can("retail.create") && (noMatch || digits.length >= 10) && (
        <button type="button"
          onClick={() => { setForm({ name: /\d/.test(debounced) ? "" : debounced, mobile: digits, date_of_birth: "", city: "" }); setRegistering(true); }}
          className="inline-flex items-center gap-1.5 text-xs font-semibold" style={{ color: RETAIL_ACCENT }}>
          <UserPlus className="h-3.5 w-3.5" /> Register a new customer
        </button>
      )}
    </div>
  );
}
