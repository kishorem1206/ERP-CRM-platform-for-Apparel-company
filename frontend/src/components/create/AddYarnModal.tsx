"use client";
import { useState, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { ModalShell, Field, Input, Textarea, SegControl, ModalActions, SearchableSelect } from "./ModalShell";
import api from "@/lib/api";

interface Comp { fibre_name: string; percentage: string }

interface Props {
  open: boolean;
  onClose: () => void;
}

const SPINNING = ["Ring", "Open-end", "Vortex"];
const TREATMENT = ["None", "Compact", "Gassed", "Mercerised"];
const PLY_OPTIONS = ["Single", "2 Ply", "3 Ply", "4 Ply"];

export function AddYarnModal({ open, onClose }: Props) {
  const qc = useQueryClient();

  const [form, setForm] = useState({
    supplier_id: "",
    invoice_number: "",
    invoice_date: "",
    yarn_count: "",
    ply: "Single",
    mill: "",
    spinning_type: "Ring",
    treatment: "None",
    colour: "Greige",
    bags: "",
    kg_per_bag: "",
    unit_cost: "",
    notes: "",
    blendMode: "single" as "single" | "blend",
    singleFibre: "Cotton",
    compositions: [] as Comp[],
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
    queryKey: ["products-yarn"],
    queryFn: async () => {
      const r = await api.get("/products", { params: { page_size: 200, product_type: "yarn" } });
      return (r.data.data ?? []) as { id: string; name: string }[];
    },
    enabled: open,
  });

  function set(k: string, v: string) { setForm((f) => ({ ...f, [k]: v })); setErr(null); }
  function addComp() { setForm((f) => ({ ...f, compositions: [...f.compositions, { fibre_name: "", percentage: "" }] })); }
  function rmComp(i: number) { setForm((f) => ({ ...f, compositions: f.compositions.filter((_, j) => j !== i) })); }
  function setComp(i: number, k: keyof Comp, v: string) {
    setForm((f) => {
      const c = [...f.compositions];
      c[i] = { ...c[i], [k]: v };
      return { ...f, compositions: c };
    });
  }

  const totalKg = useMemo(() => {
    const b = Number(form.bags), kpb = Number(form.kg_per_bag);
    return b && kpb ? (b * kpb).toFixed(3) : "";
  }, [form.bags, form.kg_per_bag]);

  const totalValue = useMemo(() => {
    const kg = Number(totalKg), rate = Number(form.unit_cost);
    return kg && rate ? (kg * rate).toFixed(2) : "";
  }, [totalKg, form.unit_cost]);

  const pctTotal = useMemo(
    () => form.compositions.reduce((s, c) => s + (Number(c.percentage) || 0), 0),
    [form.compositions],
  );

  const mut = useMutation({
    mutationFn: async () => {
      const compositions = form.blendMode === "single"
        ? [{ fibre_name: form.singleFibre, percentage: "100" }]
        : form.compositions.map((c) => ({ fibre_name: c.fibre_name, percentage: Number(c.percentage) }));

      return api.post("/materials/yarn", {
        supplier_id: form.supplier_id || undefined,
        invoice_number: form.invoice_number || undefined,
        invoice_date: form.invoice_date || undefined,
        yarn_count: form.yarn_count || undefined,
        ply: form.ply,
        mill: form.mill || undefined,
        spinning_type: form.spinning_type === "None" ? undefined : form.spinning_type,
        treatment: form.treatment === "None" ? undefined : form.treatment,
        colour: form.colour || undefined,
        bags: form.bags ? Number(form.bags) : undefined,
        kg_per_bag: form.kg_per_bag ? Number(form.kg_per_bag) : undefined,
        unit_cost: form.unit_cost ? Number(form.unit_cost) : undefined,
        notes: form.notes || undefined,
        compositions,
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
      setErr(msg ?? "Failed to save yarn lot");
    },
  });

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="Add Yarn"
      subtitle="Receive a new yarn lot into inventory."
      footer={
        <form onSubmit={(e) => { e.preventDefault(); mut.mutate(); }}>
          <ModalActions onClose={onClose} loading={mut.isPending} label="Save Lot" />
        </form>
      }
    >
      <form onSubmit={(e) => { e.preventDefault(); mut.mutate(); }} className="space-y-4">
        {/* Supplier + Invoice */}
        <Field label="Supplier">
          <SearchableSelect
            value={form.supplier_id}
            onChange={(v) => set("supplier_id", v)}
            placeholder="— Select supplier —"
            accent="#D97706"
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

        {/* Yarn specs */}
        <div className="grid grid-cols-2 gap-3">
          <Field label="Yarn Count">
            <Input placeholder="30s / 40s / 2/60s" value={form.yarn_count} onChange={(e) => set("yarn_count", e.target.value)} />
          </Field>
          <Field label="Mill">
            <Input placeholder="Mill name" value={form.mill} onChange={(e) => set("mill", e.target.value)} />
          </Field>
        </div>

        <Field label="Ply">
          <SegControl options={PLY_OPTIONS} value={form.ply} onChange={(v) => set("ply", v)} />
        </Field>

        <Field label="Spinning Type">
          <SegControl options={SPINNING} value={form.spinning_type} onChange={(v) => set("spinning_type", v)} />
        </Field>

        <Field label="Treatment">
          <SegControl options={TREATMENT} value={form.treatment} onChange={(v) => set("treatment", v)} />
        </Field>

        <div className="h-px bg-border" />

        {/* Composition */}
        <Field label="Composition">
          <div className="flex gap-2 mb-2">
            <SegControl
              options={["Single fibre", "Blend"]}
              value={form.blendMode === "single" ? "Single fibre" : "Blend"}
              onChange={(v) => set("blendMode", v === "Single fibre" ? "single" : "blend")}
            />
          </div>
          {form.blendMode === "single" ? (
            <Input
              placeholder="Cotton / Polyester / Viscose…"
              value={form.singleFibre}
              onChange={(e) => set("singleFibre", e.target.value)}
            />
          ) : (
            <div className="space-y-2">
              {form.compositions.map((c, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <Input
                    placeholder="Fibre name"
                    value={c.fibre_name}
                    onChange={(e) => setComp(i, "fibre_name", e.target.value)}
                    className="flex-1"
                  />
                  <Input
                    type="number"
                    placeholder="%"
                    value={c.percentage}
                    onChange={(e) => setComp(i, "percentage", e.target.value)}
                    className="w-20"
                    min={0.1}
                    max={100}
                    step={0.01}
                  />
                  <button type="button" onClick={() => rmComp(i)} className="text-muted-foreground hover:text-red-500">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={addComp}
                className="flex items-center gap-1 text-xs text-primary hover:underline"
              >
                <Plus className="h-3 w-3" /> Add fibre
              </button>
              {form.compositions.length > 0 && pctTotal !== 100 && (
                <p className="text-xs text-amber-600">Total: {pctTotal}% (must equal 100%)</p>
              )}
            </div>
          )}
        </Field>

        <div className="h-px bg-border" />

        {/* Colour */}
        <Field label="State">
          <SegControl
            options={["Greige", "Dyed"]}
            value={form.colour === "Greige" ? "Greige" : "Dyed"}
            onChange={(v) => {
              if (v === "Greige") set("colour", "Greige");
              else set("colour", "");
            }}
          />
          {form.colour !== "Greige" && (
            <Input
              className="mt-2"
              placeholder="Colour name / shade"
              value={form.colour === "Greige" ? "" : form.colour}
              onChange={(e) => set("colour", e.target.value)}
            />
          )}
        </Field>

        <div className="h-px bg-border" />

        {/* Quantity */}
        <div className="grid grid-cols-3 gap-3">
          <Field label="Bags">
            <Input type="number" step="1" placeholder="0" value={form.bags} onChange={(e) => set("bags", e.target.value)} />
          </Field>
          <Field label="Kg / Bag">
            <Input type="number" step="0.001" placeholder="0.000" value={form.kg_per_bag} onChange={(e) => set("kg_per_bag", e.target.value)} />
          </Field>
          <Field label="Total Kg">
            <Input value={totalKg} readOnly className="bg-muted cursor-default" tabIndex={-1} />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Rate / Kg (₹)">
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
            Book to Inventory <span className="normal-case font-normal">(optional — auto-posts a stock-in transaction)</span>
          </p>
          <Field label="Warehouse">
            <SearchableSelect
              value={form.warehouse_id}
              onChange={(v) => set("warehouse_id", v)}
              placeholder="— Skip —"
              accent="#D97706"
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
                placeholder="— Select product —"
                accent="#D97706"
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
                accent="#D97706"
                options={(units.data ?? []).map((u) => ({
                  value: u.id,
                  label: `${u.name} (${u.abbreviation})`,
                }))}
              />
            </Field>
          </div>
          {totalKg && form.warehouse_id && form.product_id && form.unit_id && (
            <p className="text-xs text-emerald-600">Will book {totalKg} kg into inventory on save.</p>
          )}
        </div>

        {err && <p className="text-xs text-red-500">{err}</p>}
      </form>
    </ModalShell>
  );
}
