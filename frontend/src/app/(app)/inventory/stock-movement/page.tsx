"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { DatePicker } from "@/components/shared/date-picker";
import { useProductOptions, useWarehouseOptions, useUnitOptions } from "@/components/reports/filter-sources";
import { parseApiError } from "@/lib/api-error";

const TEAL = "#8174F5";
const ORANGE = "#A096F7";
const BLUE = "#0049A7";
const LAVENDER = "#0F78FF";

type MovementType = "in" | "out" | "transfer" | "adjust";

const MOVEMENT_TYPES: { value: MovementType; label: string }[] = [
  { value: "in", label: "Stock In" },
  { value: "out", label: "Stock Out" },
  { value: "transfer", label: "Transfer" },
  { value: "adjust", label: "Adjustment" },
];

const MOVEMENT_META: Record<MovementType, { description: string; endpoint: string; cta: string; savingCta: string; accent: string; successMessage: string }> = {
  in: {
    description: "Record incoming goods into a warehouse.",
    endpoint: "/inventory/stock-in",
    cta: "Receive Stock",
    savingCta: "Saving…",
    accent: TEAL,
    successMessage: "Stock received successfully.",
  },
  out: {
    description: "Record outgoing goods from a warehouse.",
    endpoint: "/inventory/stock-out",
    cta: "Issue Stock",
    savingCta: "Issuing…",
    accent: ORANGE,
    successMessage: "Stock issued successfully.",
  },
  transfer: {
    description: "Move stock between warehouse locations.",
    endpoint: "/inventory/transfer",
    cta: "Transfer Stock",
    savingCta: "Transferring…",
    accent: BLUE,
    successMessage: "Transfer completed successfully.",
  },
  adjust: {
    description: "Add, reduce, or replace stock in one unified workflow.",
    endpoint: "/inventory/adjust",
    cta: "Post Adjustment",
    savingCta: "Saving…",
    accent: LAVENDER,
    successMessage: "Adjustment recorded successfully.",
  },
};

const MATERIAL_TYPE_OPTIONS = [
  { value: "raw_material", label: "Raw Material" },
  { value: "fabric", label: "Fabric" },
  { value: "trim", label: "Trim" },
  { value: "packing", label: "Packing" },
  { value: "finished_good", label: "Finished Good" },
];

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

function isMovementType(v: string | null): v is MovementType {
  return v === "in" || v === "out" || v === "transfer" || v === "adjust";
}

function StockMovementForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialType = searchParams.get("type");

  const [movementType, setMovementType] = useState<MovementType>(isMovementType(initialType) ? initialType : "in");
  const [adjustmentType, setAdjustmentType] = useState<AdjustmentType>("replace");
  const [form, setForm] = useState({
    product_id: "",
    warehouse_id: "",
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

  const productOptions = useProductOptions();
  const warehouseOptions = useWarehouseOptions();
  const unitOptions = useUnitOptions();

  const selectType = (type: MovementType) => {
    setMovementType(type);
    setStatus("idle");
    router.replace(`/inventory/stock-movement?type=${type}`, { scroll: false });
  };

  // Current balance for the selected product+warehouse — shown for every
  // type, not just Adjust: knowing what's on hand before you issue or
  // move it prevents a failed submit from being the first warning.
  const balanceWarehouseId = movementType === "transfer" ? form.from_warehouse_id : form.warehouse_id;
  const { data: balanceRows } = useQuery({
    queryKey: ["current-balance-for-movement", form.product_id, balanceWarehouseId],
    queryFn: async () => {
      const res = await api.get("/inventory/balance", {
        params: { product_id: form.product_id, warehouse_id: balanceWarehouseId, status: "all" },
      });
      return (res.data.data ?? []) as { balance: string }[];
    },
    enabled: Boolean(form.product_id && balanceWarehouseId),
  });
  const currentBalance = (balanceRows ?? []).reduce((sum, r) => sum + Number(r.balance), 0);
  const hasCurrentBalance = Boolean(form.product_id && balanceWarehouseId);

  const previewBalance = (() => {
    const qty = Number(form.quantity) || 0;
    if (movementType === "out" || movementType === "transfer") return currentBalance - qty;
    if (movementType === "adjust") {
      if (adjustmentType === "add") return currentBalance + qty;
      if (adjustmentType === "reduce") return currentBalance - qty;
      return qty;
    }
    return currentBalance + qty; // in
  })();

  const set = (field: string, value: string) => setForm((f) => ({ ...f, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    try {
      const base = {
        product_id: form.product_id,
        quantity: Number(form.quantity),
        unit_id: form.unit_id,
        material_type: form.material_type,
        transaction_date: form.transaction_date,
      };
      let payload: Record<string, unknown>;
      if (movementType === "transfer") {
        payload = {
          ...base,
          from_warehouse_id: form.from_warehouse_id,
          to_warehouse_id: form.to_warehouse_id,
          unit_cost: Number(form.unit_cost),
          notes: form.notes,
        };
      } else if (movementType === "adjust") {
        payload = {
          ...base,
          warehouse_id: form.warehouse_id,
          adjustment_type: adjustmentType,
          reason: form.notes,
        };
      } else if (movementType === "in") {
        payload = {
          ...base,
          warehouse_id: form.warehouse_id,
          unit_cost: Number(form.unit_cost),
          notes: form.notes,
        };
      } else {
        payload = {
          ...base,
          warehouse_id: form.warehouse_id,
          notes: form.notes,
        };
      }

      const res = await api.post(MOVEMENT_META[movementType].endpoint, payload);
      setStatus("success");
      setMessage((res.data?.message as string | undefined) ?? MOVEMENT_META[movementType].successMessage);
      setForm((f) => ({ ...f, quantity: "", notes: "" }));
    } catch (err: unknown) {
      setStatus("error");
      setMessage(parseApiError(err, "The movement could not be saved."));
    }
  };

  const labelClass = "block text-xs font-semibold mb-1.5 text-muted-foreground";
  const inputClass = "w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 transition-all";
  const accent = MOVEMENT_META[movementType].accent;
  const quantityLabel = movementType === "adjust" ? QUANTITY_LABELS[adjustmentType] : "Quantity";

  return (
    <div className="p-8 space-y-8">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          INVENTORY / OPERATIONS
        </p>
        <h1 className="text-2xl font-bold tracking-tight">Stock Movement</h1>
        <p className="text-sm text-muted-foreground mt-1">{MOVEMENT_META[movementType].description}</p>
      </div>

      <div className="bg-card border border-border rounded-2xl p-6 max-w-xl space-y-5">
        <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit flex-wrap">
          {MOVEMENT_TYPES.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => selectType(t.value)}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                movementType === t.value ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {movementType === "adjust" && (
          <div className="flex items-center gap-1 p-1 bg-muted/30 rounded-xl w-fit">
            {ADJUSTMENT_TYPES.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setAdjustmentType(t.value)}
                className={`px-3 py-1 rounded-lg text-[11px] font-semibold transition-all duration-150 ${
                  adjustmentType === t.value ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}

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

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className={labelClass}>Product</label>
            <SearchableSelect
              value={form.product_id}
              onChange={(v) => set("product_id", v)}
              placeholder="— select product —"
              accent={accent}
              options={productOptions}
            />
          </div>

          {movementType === "transfer" ? (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>From Warehouse</label>
                <SearchableSelect
                  value={form.from_warehouse_id}
                  onChange={(v) => set("from_warehouse_id", v)}
                  placeholder="— from —"
                  accent={accent}
                  options={warehouseOptions}
                />
              </div>
              <div>
                <label className={labelClass}>To Warehouse</label>
                <SearchableSelect
                  value={form.to_warehouse_id}
                  onChange={(v) => set("to_warehouse_id", v)}
                  placeholder="— to —"
                  accent={accent}
                  options={warehouseOptions}
                />
              </div>
            </div>
          ) : (
            <div>
              <label className={labelClass}>Warehouse</label>
              <SearchableSelect
                value={form.warehouse_id}
                onChange={(v) => set("warehouse_id", v)}
                placeholder="— select warehouse —"
                accent={accent}
                options={warehouseOptions}
              />
            </div>
          )}

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
              <label className={labelClass}>{quantityLabel}</label>
              <input
                type="number" min="0.0001" step="0.0001"
                className={inputClass}
                value={form.quantity}
                onChange={(e) => set("quantity", e.target.value)}
                required
              />
            </div>
            <div>
              <label className={labelClass}>Unit</label>
              <SearchableSelect
                value={form.unit_id}
                onChange={(v) => set("unit_id", v)}
                placeholder="— unit —"
                accent={accent}
                options={unitOptions}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {(movementType === "in" || movementType === "transfer") && (
              <div>
                <label className={labelClass}>Unit Cost (₹)</label>
                <input
                  type="number" min="0" step="0.01"
                  className={inputClass}
                  value={form.unit_cost}
                  onChange={(e) => set("unit_cost", e.target.value)}
                />
              </div>
            )}
            <div>
              <label className={labelClass}>Material Type</label>
              <SearchableSelect
                value={form.material_type}
                onChange={(v) => set("material_type", v)}
                placeholder="Material type"
                accent={accent}
                options={MATERIAL_TYPE_OPTIONS}
              />
            </div>
          </div>

          <div>
            <label className={labelClass}>Date</label>
            <DatePicker value={form.transaction_date} onChange={(v) => set("transaction_date", v)} required />
          </div>

          <div>
            <label className={labelClass}>{movementType === "adjust" ? "Reason / Remarks" : "Notes"}</label>
            <textarea
              className={inputClass + " resize-none"}
              rows={2}
              value={form.notes}
              onChange={(e) => set("notes", e.target.value)}
              required={movementType === "adjust"}
              placeholder={movementType === "adjust" ? "e.g. Physical stock count, write-off, damage" : undefined}
            />
          </div>

          <button
            type="submit"
            disabled={status === "loading"}
            className="w-full rounded-xl px-4 py-2.5 text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
            style={{ background: accent }}
          >
            {status === "loading" ? MOVEMENT_META[movementType].savingCta : MOVEMENT_META[movementType].cta}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function StockMovementPage() {
  return (
    <Suspense fallback={null}>
      <StockMovementForm />
    </Suspense>
  );
}
