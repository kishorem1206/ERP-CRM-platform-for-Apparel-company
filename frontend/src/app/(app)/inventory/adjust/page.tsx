"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { useProductOptions, useWarehouseOptions } from "@/components/reports/filter-sources";
import { DatePicker } from "@/components/shared/date-picker";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";

// This app's real error envelope is {"error": "..."} or {"error": {"message": "..."}}
// (see backend/app/main.py's exception handlers), not FastAPI's default
// {"detail": ...} — reading only `.detail` (as this page previously did)
// silently swallows every business-rule error, e.g. the negative-balance
// rejection this phase wires in. Same fix already applied on the Sales
// Order page (Phase 4).
function parseApiError(e: unknown, fallback: string): string {
  const data = (e as { response?: { data?: Record<string, unknown> } })?.response?.data;
  if (!data) return fallback;
  const err = data.error;
  if (typeof err === "string") return err;
  if (err && typeof (err as { message?: string }).message === "string")
    return (err as { message: string }).message;
  const detail = data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0)
    return (detail as Array<{ msg: string }>)[0]?.msg ?? fallback;
  return fallback;
}

const ADJUSTMENT_TYPES = [
  { label: "Add", value: "add" },
  { label: "Reduce", value: "reduce" },
  { label: "Replace", value: "replace" },
] as const;
type AdjustmentType = (typeof ADJUSTMENT_TYPES)[number]["value"];

const QUANTITY_LABELS: Record<AdjustmentType, string> = {
  add: "Quantity to Add",
  reduce: "Quantity to Reduce",
  replace: "New Quantity (physical count)",
};

export default function AdjustPage() {
  const [adjustmentType, setAdjustmentType] = useState<AdjustmentType>("replace");
  const [form, setForm] = useState({
    product_id: "",
    warehouse_id: "",
    quantity: "",
    unit_id: "",
    unit_cost: "0",
    material_type: "raw_material",
    transaction_date: new Date().toISOString().slice(0, 10),
    reason: "",
  });
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const productOptions = useProductOptions();
  const warehouseOptions = useWarehouseOptions();

  const { data: masterData } = useQuery({
    queryKey: ["units-for-inventory"],
    queryFn: async () => (await api.get("/master/units")).data.data ?? [],
  });

  // Current balance for the selected product+warehouse — reuses the
  // Phase 5 filterable Stock Balance endpoint rather than a new lookup.
  const { data: balanceRows } = useQuery({
    queryKey: ["current-balance-for-adjust", form.product_id, form.warehouse_id],
    queryFn: async () => {
      const res = await api.get("/inventory/balance", {
        params: { product_id: form.product_id, warehouse_id: form.warehouse_id, status: "all" },
      });
      return (res.data.data ?? []) as { balance: string; unit_symbol: string }[];
    },
    enabled: Boolean(form.product_id && form.warehouse_id),
  });
  const currentBalance = (balanceRows ?? []).reduce((sum, r) => sum + Number(r.balance), 0);
  const hasCurrentBalance = Boolean(form.product_id && form.warehouse_id);

  const previewBalance = (() => {
    const qty = Number(form.quantity) || 0;
    if (adjustmentType === "add") return currentBalance + qty;
    if (adjustmentType === "reduce") return currentBalance - qty;
    return qty;
  })();

  const set = (field: string, value: string) => setForm((f) => ({ ...f, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    try {
      const res = await api.post("/inventory/adjust", {
        ...form,
        adjustment_type: adjustmentType,
        quantity: Number(form.quantity),
        unit_cost: Number(form.unit_cost),
      });
      setStatus("success");
      setMessage(res.data.message ?? "Adjustment recorded successfully.");
    } catch (err: unknown) {
      setStatus("error");
      setMessage(parseApiError(err, "Adjustment failed."));
    }
  };

  const labelClass = "block text-xs font-medium mb-1 text-muted-foreground";
  const inputClass = "w-full rounded-xl border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40";

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            INVENTORY / OPERATIONS
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Stock Adjustment</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Add, reduce, or replace stock in one unified workflow.
          </p>
        </div>
      </div>

      {/* Form card */}
      <div className="bg-card border border-border rounded-2xl p-6 max-w-xl space-y-5">
        {/* Adjustment type tabs */}
        <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit">
          {ADJUSTMENT_TYPES.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => setAdjustmentType(t.value)}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                adjustmentType === t.value ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {status === "success" && (
          <div className="rounded-xl border px-4 py-3 text-sm" style={{ background: "#0F78FF0D", borderColor: "#0F78FF4D", color: "#0049A7" }}>
            {message}
          </div>
        )}
        {status === "error" && (
          <div className="rounded-xl border px-4 py-3 text-sm" style={{ background: "#1D0DB00D", borderColor: "#1D0DB04D", color: "#1D0DB0" }}>
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={labelClass}>Product</label>
            <SearchableSelect
              value={form.product_id}
              onChange={(v) => set("product_id", v)}
              placeholder="— select product —"
              accent={INDIGO}
              options={productOptions}
            />
          </div>

          <div>
            <label className={labelClass}>Warehouse</label>
            <SearchableSelect
              value={form.warehouse_id}
              onChange={(v) => set("warehouse_id", v)}
              placeholder="— select warehouse —"
              accent={INDIGO}
              options={warehouseOptions}
            />
          </div>

          {hasCurrentBalance && (
            <div className="rounded-xl bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
              Current balance: <span className="font-semibold text-foreground">{currentBalance.toFixed(4)}</span>
              {form.quantity && (
                <> &rarr; resulting balance: <span className="font-semibold text-foreground">{previewBalance.toFixed(4)}</span></>
              )}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>{QUANTITY_LABELS[adjustmentType]}</label>
              <input type="number" min="0" step="0.0001" className={inputClass} value={form.quantity}
                onChange={(e) => set("quantity", e.target.value)} required />
            </div>
            <div>
              <label className={labelClass}>Unit</label>
              <SearchableSelect
                value={form.unit_id}
                onChange={(v) => set("unit_id", v)}
                placeholder="— unit —"
                accent={INDIGO}
                options={(masterData ?? []).map((u: Record<string, unknown>) => ({
                  value: u.id as string,
                  label: `${u.name as string} (${u.abbreviation as string})`,
                }))}
              />
            </div>
          </div>

          <div>
            <label className={labelClass}>Date</label>
            <DatePicker value={form.transaction_date} onChange={(v) => set("transaction_date", v)} required />
          </div>

          <div>
            <label className={labelClass}>Reason / Remarks</label>
            <textarea className={inputClass} rows={2} value={form.reason} required
              onChange={(e) => set("reason", e.target.value)}
              placeholder="e.g. Physical stock count, write-off, damage" />
          </div>

          <button
            type="submit"
            disabled={status === "loading"}
            className="w-full rounded-xl px-4 py-2.5 text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
            style={{ background: LAVENDER }}
          >
            {status === "loading" ? "Saving…" : "Post Adjustment"}
          </button>
        </form>
      </div>
    </div>
  );
}
