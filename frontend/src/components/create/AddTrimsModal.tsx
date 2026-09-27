"use client";
import { useState, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ModalShell, Field, Input, Textarea, SegControl, ModalActions, SearchableSelect } from "./ModalShell";
import api from "@/lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
}

const TRIM_TYPES = ["Button", "Label", "Tag", "Zipper", "Thread", "Elastic", "Interlining", "Tape", "Other"];
const TRIM_UNITS = ["Pieces", "Gross", "Dozen", "Metre", "Kilogram", "Yard"];

export function AddTrimsModal({ open, onClose }: Props) {
  const qc = useQueryClient();

  const [form, setForm] = useState({
    supplier_id: "",
    invoice_number: "",
    invoice_date: "",
    trim_type: "Button",
    trim_unit: "Pieces",
    colour: "",
    split_by_colour: false,
    brand: "",
    description: "",
    quantity: "",
    unit_cost: "",
    notes: "",
    // Inventory booking
    warehouse_id: "",
    product_id: "",
    unit_id: "",
  });
  const [err, setErr] = useState<string | null>(null);

  const vendors = useQuery({
    queryKey: ["vendors-list"],
    queryFn: async () => {
      const r = await api.get("/purchase/vendors", { params: { page_size: 200 } });
      return (r.data.data ?? []) as { id: string; name: string }[];
    },
    enabled: open,
  });

  const warehouses = useQuery({
    queryKey: ["warehouses"],
    queryFn: async () => {
      const r = await api.get("/master/warehouses");
      return (r.data.data ?? []) as { id: string; name: string }[];
    },
    enabled: open,
  });

  const units = useQuery({
    queryKey: ["units"],
    queryFn: async () => {
      const r = await api.get("/master/units");
      return (r.data.data ?? []) as { id: string; name: string; abbreviation: string }[];
    },
    enabled: open,
  });

  const products = useQuery({
    queryKey: ["products-trims"],
    queryFn: async () => {
      const r = await api.get("/products", { params: { page_size: 200, product_type: "trim" } });
      return (r.data.data ?? []) as { id: string; name: string }[];
    },
    enabled: open,
  });

  function set(k: string, v: unknown) { setForm((f) => ({ ...f, [k]: v })); setErr(null); }

  const totalValue = useMemo(() => {
    const qty = Number(form.quantity), cost = Number(form.unit_cost);
    return qty && cost ? (qty * cost).toFixed(2) : "";
  }, [form.quantity, form.unit_cost]);

  const mut = useMutation({
    mutationFn: async () => {
      return api.post("/materials/trims", {
        supplier_id: form.supplier_id || undefined,
        invoice_number: form.invoice_number || undefined,
        invoice_date: form.invoice_date || undefined,
        trim_type: form.trim_type,
        trim_unit: form.trim_unit,
        colour: form.colour || undefined,
        split_by_colour: form.split_by_colour,
        unit_cost: form.unit_cost ? Number(form.unit_cost) : undefined,
        quantity: form.quantity ? Number(form.quantity) : undefined,
        notes: [form.brand ? `Brand: ${form.brand}` : "", form.description, form.notes].filter(Boolean).join(" | ") || undefined,
        // Inventory booking
        warehouse_id: form.warehouse_id || undefined,
        product_id: form.product_id || undefined,
        unit_id: form.unit_id || undefined,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["material-lots"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message;
      setErr(msg ?? "Failed to save trims lot");
    },
  });

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="Add Trims"
      subtitle="Receive buttons, labels, or other trim items."
      footer={
        <form onSubmit={(e) => { e.preventDefault(); mut.mutate(); }}>
          <ModalActions onClose={onClose} loading={mut.isPending} label="Save Lot" />
        </form>
      }
    >
      <form onSubmit={(e) => { e.preventDefault(); mut.mutate(); }} className="space-y-4">
        {/* Supplier */}
        <Field label="Supplier">
          <SearchableSelect
            value={form.supplier_id}
            onChange={(v) => set("supplier_id", v)}
            placeholder="— Select supplier —"
            accent="#0F78FF"
            options={(vendors.data ?? []).map((v) => ({
              value: v.id,
              label: v.name,
            }))}
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Invoice No.">
            <Input placeholder="INV-001" value={form.invoice_number} onChange={(e) => set("invoice_number", e.target.value)} />
          </Field>
          <Field label="Invoice Date">
            <Input type="date" value={form.invoice_date} onChange={(e) => set("invoice_date", e.target.value)} />
          </Field>
        </div>

        <div className="h-px bg-border" />

        {/* Trim type */}
        <Field label="Trim Type">
          <div className="flex gap-1 flex-wrap">
            {TRIM_TYPES.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => set("trim_type", t)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                  form.trim_type === t
                    ? "bg-primary/10 text-primary border-primary/40"
                    : "bg-background border-border text-muted-foreground hover:border-foreground/30"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </Field>

        <Field label="Unit">
          <SegControl options={TRIM_UNITS} value={form.trim_unit} onChange={(v) => set("trim_unit", v)} />
        </Field>

        <div className="h-px bg-border" />

        <div className="grid grid-cols-2 gap-3">
          <Field label="Brand">
            <Input placeholder="Brand name" value={form.brand} onChange={(e) => set("brand", e.target.value)} />
          </Field>
          <Field label="Colour">
            <Input placeholder="Colour / shade" value={form.colour} onChange={(e) => set("colour", e.target.value)} />
          </Field>
        </div>

        <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
          <input
            type="checkbox"
            checked={form.split_by_colour}
            onChange={(e) => set("split_by_colour", e.target.checked)}
            className="h-4 w-4 rounded border-border accent-primary"
          />
          Split by Colour
        </label>

        <Field label="Description">
          <Textarea
            placeholder="Additional details…"
            value={form.description}
            onChange={(e) => set("description", e.target.value)}
          />
        </Field>

        <div className="h-px bg-border" />

        <div className="grid grid-cols-3 gap-3">
          <Field label={`Qty (${form.trim_unit})`}>
            <Input type="number" step="1" placeholder="0" value={form.quantity} onChange={(e) => set("quantity", e.target.value)} />
          </Field>
          <Field label="Cost / Unit (₹)">
            <Input type="number" step="0.01" placeholder="0.00" value={form.unit_cost} onChange={(e) => set("unit_cost", e.target.value)} />
          </Field>
          <Field label="Total Value (₹)">
            <Input value={totalValue} readOnly className="bg-muted cursor-default" tabIndex={-1} />
          </Field>
        </div>

        <Field label="Notes">
          <Textarea value={form.notes} onChange={(e) => set("notes", e.target.value)} />
        </Field>

        <div className="h-px bg-border" />

        {/* Inventory booking */}
        <div className="space-y-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Book to Inventory <span className="normal-case font-normal">(optional)</span>
          </p>
          <Field label="Warehouse">
            <SearchableSelect
              value={form.warehouse_id}
              onChange={(v) => set("warehouse_id", v)}
              placeholder="— Skip —"
              accent="#0F78FF"
              options={[
                { value: "", label: "— Skip —" },
                ...(warehouses.data ?? []).map((w) => ({
                  value: w.id,
                  label: w.name,
                })),
              ]}
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Product">
              <SearchableSelect
                value={form.product_id}
                onChange={(v) => set("product_id", v)}
                placeholder="— Select —"
                accent="#0F78FF"
                options={(products.data ?? []).map((p) => ({
                  value: p.id,
                  label: p.name,
                }))}
              />
            </Field>
            <Field label="Unit">
              <SearchableSelect
                value={form.unit_id}
                onChange={(v) => set("unit_id", v)}
                placeholder="— Unit —"
                accent="#0F78FF"
                options={(units.data ?? []).map((u) => ({
                  value: u.id,
                  label: `${u.name} (${u.abbreviation})`,
                }))}
              />
            </Field>
          </div>
          {form.quantity && form.warehouse_id && form.product_id && form.unit_id && (
            <p className="text-xs text-blue-600">Will book {form.quantity} {form.trim_unit} into inventory on save.</p>
          )}
          {form.quantity && !(form.warehouse_id && form.product_id && form.unit_id) && (
            <p className="text-xs text-violet-600 bg-violet-50 border border-violet-200 rounded-lg px-3 py-2">
              Quantity entered but Warehouse, Product, and Unit are all required to book stock. Without them the quantity will not be tracked in inventory.
            </p>
          )}
        </div>

        {err && <p className="text-xs text-violet-500">{err}</p>}
      </form>
    </ModalShell>
  );
}
