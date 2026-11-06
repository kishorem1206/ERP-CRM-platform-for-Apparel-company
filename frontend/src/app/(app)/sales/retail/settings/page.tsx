"use client";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { Can } from "@/lib/permissions";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { RETAIL_ACCENT, type RetailSettings } from "@/lib/retail";

const inputCls = "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
const FIELD_LABELS: Record<string, string> = {
  min_discount_pct: "Minimum discount %", max_discount_pct: "Maximum discount %", default_discount_pct: "Default discount %",
  allow_approved_override: "Managers may approve above maximum", warehouse_id: "Stock warehouse",
  credit_days: "Credit days", estimate_validity_days: "Estimate validity days",
};

export default function RetailSettingsPage() {
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ["retail-settings"], queryFn: async () => (await api.get("/retail/settings")).data.data as RetailSettings });
  const warehouses = useQuery({ queryKey: ["warehouses-list"], queryFn: async () => (await api.get("/master/warehouses")).data.data as { id: string; name: string }[] });
  const audit = useQuery({
    queryKey: ["retail-settings-audit"],
    queryFn: async () => (await api.get("/retail/settings/audit")).data.data as { field: string; old_value: string | null; new_value: string | null; changed_by_name: string | null; changed_at: string }[],
  });
  const [f, setF] = useState({ min: "", max: "", def: "", override: true, warehouse: "", credit: "", validity: "" });
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    const s = settings.data;
    if (s) setF({
      min: String(Number(s.min_discount_pct)), max: String(Number(s.max_discount_pct)), def: String(Number(s.default_discount_pct)),
      override: s.allow_approved_override, warehouse: s.warehouse_id ?? "", credit: String(s.credit_days), validity: String(s.estimate_validity_days),
    });
  }, [settings.data]);
  const save = useMutation({
    mutationFn: () => api.patch("/retail/settings", {
      min_discount_pct: Number(f.min) || 0, max_discount_pct: Number(f.max) || 0, default_discount_pct: Number(f.def) || 0,
      allow_approved_override: f.override, warehouse_id: f.warehouse || null,
      credit_days: Number(f.credit) || 0, estimate_validity_days: Number(f.validity) || 7,
    }),
    onSuccess: () => {
      setError(""); setMsg("Saved.");
      qc.invalidateQueries({ queryKey: ["retail-settings"] });
      qc.invalidateQueries({ queryKey: ["retail-settings-audit"] });
    },
    onError: (e: unknown) => { setMsg(""); setError(parseApiError(e, "Could not save the settings.")); },
  });
  const whName = (v: string | null) => (warehouses.data ?? []).find((w) => w.id === v)?.name ?? v;

  return (
    <div className="p-8 space-y-6 max-w-4xl">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / RETAIL</p>
        <h1 className="text-2xl font-bold tracking-tight">Retail Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Discount limits are checked on the server for every bill and estimate.</p>
      </div>
      <Can perm="retail.manage">
        <div className="rounded-2xl border border-border bg-card p-5 space-y-4">
          <p className="text-sm font-semibold">Discounts</p>
          <div className="grid gap-3 md:grid-cols-3">
            <div><label className="text-xs text-muted-foreground">Minimum discount %</label><input type="number" min="0" max="100" step="0.5" className={inputCls} value={f.min} onChange={(e) => setF((x) => ({ ...x, min: e.target.value }))} /></div>
            <div><label className="text-xs text-muted-foreground">Maximum discount %</label><input type="number" min="0" max="100" step="0.5" className={inputCls} value={f.max} onChange={(e) => setF((x) => ({ ...x, max: e.target.value }))} /></div>
            <div><label className="text-xs text-muted-foreground">Default bill discount %</label><input type="number" min="0" max="100" step="0.5" className={inputCls} value={f.def} onChange={(e) => setF((x) => ({ ...x, def: e.target.value }))} /></div>
          </div>
          <p className="text-[11px] text-muted-foreground">A discount must be 0, or between the minimum and maximum — per item, for the bill, and both together.</p>
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-0.5" checked={f.override} onChange={(e) => setF((x) => ({ ...x, override: e.target.checked }))} />
            <span>Users with <b>Retail discount approval</b> may bill above the maximum (recorded on the bill). Untick to make the maximum a hard stop for everyone.</span>
          </label>
          <p className="text-sm font-semibold pt-2">Billing</p>
          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <label className="text-xs text-muted-foreground">Stock comes from</label>
              <SearchableSelect value={f.warehouse} onChange={(v) => setF((x) => ({ ...x, warehouse: v }))} accent={RETAIL_ACCENT} placeholder="Select warehouse"
                options={(warehouses.data ?? []).map((w) => ({ value: w.id, label: w.name }))} />
            </div>
            <div><label className="text-xs text-muted-foreground">Credit bills due after (days)</label><input type="number" min="0" className={inputCls} value={f.credit} onChange={(e) => setF((x) => ({ ...x, credit: e.target.value }))} /></div>
            <div><label className="text-xs text-muted-foreground">Estimates valid for (days)</label><input type="number" min="1" className={inputCls} value={f.validity} onChange={(e) => setF((x) => ({ ...x, validity: e.target.value }))} /></div>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
          <div className="flex justify-end">
            <button onClick={() => { setMsg(""); save.mutate(); }} disabled={save.isPending}
              className="px-4 py-2 rounded-xl text-sm font-semibold text-white disabled:opacity-50" style={{ background: RETAIL_ACCENT }}>
              {save.isPending ? "Saving…" : "Save settings"}
            </button>
          </div>
        </div>
        <div className="rounded-2xl border border-border bg-card p-5">
          <p className="text-sm font-semibold mb-3">Change history</p>
          {(audit.data ?? []).length === 0 ? <p className="text-sm text-muted-foreground">No changes yet.</p> : (
            <table className="w-full text-sm">
              <tbody>
                {(audit.data ?? []).map((a, i) => (
                  <tr key={i} className="border-t border-border first:border-0">
                    <td className="py-1.5 pr-3 text-xs text-muted-foreground whitespace-nowrap">{new Date(a.changed_at).toLocaleString("en-IN")}</td>
                    <td className="py-1.5 pr-3">{FIELD_LABELS[a.field] ?? a.field}</td>
                    <td className="py-1.5 pr-3">
                      {a.field === "warehouse_id" ? `${whName(a.old_value) ?? "—"} → ${whName(a.new_value) ?? "—"}` : `${a.old_value ?? "—"} → ${a.new_value ?? "—"}`}
                    </td>
                    <td className="py-1.5 text-xs text-muted-foreground">{a.changed_by_name ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Can>
    </div>
  );
}
