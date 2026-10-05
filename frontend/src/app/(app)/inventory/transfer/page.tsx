"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { DatePicker } from "@/components/shared/date-picker";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

export default function TransferPage() {
  const [form, setForm] = useState({
    product_id: "",
    from_warehouse_id: "",
    to_warehouse_id: "",
    quantity: "",
    unit_id: "",
    unit_cost: "0",
    material_type: "raw_material",
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
      await api.post("/inventory/transfer", {
        ...form,
        quantity: Number(form.quantity),
        unit_cost: Number(form.unit_cost),
      });
      setStatus("success");
      setMessage("Transfer completed successfully.");
      setForm((f) => ({ ...f, quantity: "", notes: "" }));
    } catch (err: unknown) {
      setStatus("error");
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Transfer failed — check available stock.";
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
          <h1 className="text-2xl font-bold tracking-tight">Stock Transfer</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Move stock between warehouse locations.
          </p>
        </div>
      </div>

      {/* Form card */}
      <div className="bg-card border border-border rounded-2xl p-6 max-w-xl space-y-5">
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
              accent="#0049A7"
              options={[
                { value: "", label: "— select product —" },
                ...(masterData?.products ?? []).map((p: Record<string, unknown>) => ({
                  value: p.id as string,
                  label: p.name as string,
                })),
              ]}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>From Warehouse</label>
              <SearchableSelect
                value={form.from_warehouse_id}
                onChange={(v) => set("from_warehouse_id", v)}
                placeholder="— from —"
                accent="#0049A7"
                options={[
                  { value: "", label: "— from —" },
                  ...(masterData?.warehouses ?? []).map((w: Record<string, unknown>) => ({
                    value: w.id as string,
                    label: w.name as string,
                  })),
                ]}
              />
            </div>
            <div>
              <label className={labelClass}>To Warehouse</label>
              <SearchableSelect
                value={form.to_warehouse_id}
                onChange={(v) => set("to_warehouse_id", v)}
                placeholder="— to —"
                accent="#0049A7"
                options={[
                  { value: "", label: "— to —" },
                  ...(masterData?.warehouses ?? []).map((w: Record<string, unknown>) => ({
                    value: w.id as string,
                    label: w.name as string,
                  })),
                ]}
              />
            </div>
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
                accent="#0049A7"
                options={[
                  { value: "", label: "— unit —" },
                  ...(masterData?.units ?? []).map((u: Record<string, unknown>) => ({
                    value: u.id as string,
                    label: `${u.name as string} (${u.abbreviation as string})`,
                  })),
                ]}
              />
            </div>
          </div>

          <div>
            <label className={labelClass}>Date</label>
            <DatePicker value={form.transaction_date} onChange={(v) => set("transaction_date", v)} required />
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
            style={{ background: BLUE }}
          >
            {status === "loading" ? "Transferring…" : "Transfer Stock"}
          </button>
        </form>
      </div>
    </div>
  );
}
