"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";

const TEAL = "#16C8C7";

export default function StockOutPage() {
  const [form, setForm] = useState({
    product_id: "",
    warehouse_id: "",
    quantity: "",
    unit_id: "",
    reference: "",
    transaction_date: new Date().toISOString().slice(0, 10),
    notes: "",
  });
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const { data: masterData } = useQuery({
    queryKey: ["master-for-inventory"],
    queryFn: async () => {
      const [products, warehouses, units] = await Promise.all([
        api.get("/products?page_size=200"),
        api.get("/master/warehouses"),
        api.get("/master/units"),
      ]);
      return {
        products: products.data.data ?? [],
        warehouses: warehouses.data.data ?? [],
        units: units.data.data ?? [],
      };
    },
  });

  const set = (field: string, value: string) => setForm((f) => ({ ...f, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    try {
      await api.post("/inventory/stock-out", {
        ...form,
        quantity: Number(form.quantity),
        reference: form.reference || null,
      });
      setStatus("success");
      setMessage("Stock issued successfully.");
      setForm((f) => ({ ...f, quantity: "", reference: "", notes: "" }));
    } catch (err: unknown) {
      setStatus("error");
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to issue stock.";
      setMessage(msg);
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
          <h1 className="text-2xl font-bold tracking-tight">Stock Out</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Record outgoing goods from warehouse.
          </p>
        </div>
      </div>

      {/* Form card */}
      <div className="bg-card border border-border rounded-2xl p-6 max-w-xl space-y-5">
        {status === "success" && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 dark:bg-emerald-950/30 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-400">
            {message}
          </div>
        )}
        {status === "error" && (
          <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/30 px-4 py-3 text-sm text-red-700">
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
              accent={TEAL}
              options={(masterData?.products ?? []).map((p: Record<string, unknown>) => ({
                value: p.id as string,
                label: p.name as string,
              }))}
            />
          </div>

          <div>
            <label className={labelClass}>Warehouse</label>
            <SearchableSelect
              value={form.warehouse_id}
              onChange={(v) => set("warehouse_id", v)}
              placeholder="— select warehouse —"
              accent={TEAL}
              options={(masterData?.warehouses ?? []).map((w: Record<string, unknown>) => ({
                value: w.id as string,
                label: w.name as string,
              }))}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Quantity</label>
              <input type="number" min="0.0001" step="0.0001" className={inputClass} value={form.quantity}
                onChange={(e) => set("quantity", e.target.value)} required />
            </div>
            <div>
              <label className={labelClass}>Unit</label>
              <SearchableSelect
                value={form.unit_id}
                onChange={(v) => set("unit_id", v)}
                placeholder="— unit —"
                accent={TEAL}
                options={(masterData?.units ?? []).map((u: Record<string, unknown>) => ({
                  value: u.id as string,
                  label: `${u.name as string} (${(u.symbol ?? u.abbreviation) as string})`,
                }))}
              />
            </div>
          </div>

          <div>
            <label className={labelClass}>Reference / Reason</label>
            <input className={inputClass} value={form.reference} placeholder="e.g. MIS-001 or sample issue"
              onChange={(e) => set("reference", e.target.value)} />
          </div>

          <div>
            <label className={labelClass}>Date</label>
            <input type="date" className={inputClass} value={form.transaction_date}
              onChange={(e) => set("transaction_date", e.target.value)} required />
          </div>

          <div>
            <label className={labelClass}>Notes</label>
            <textarea className={inputClass} rows={2} value={form.notes}
              onChange={(e) => set("notes", e.target.value)} />
          </div>

          <button
            type="submit"
            disabled={status === "loading"}
            className="w-full rounded-xl px-4 py-2.5 text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
            style={{ background: ORANGE }}
          >
            {status === "loading" ? "Issuing…" : "Issue Stock"}
          </button>
        </form>
      </div>
    </div>
  );
}
