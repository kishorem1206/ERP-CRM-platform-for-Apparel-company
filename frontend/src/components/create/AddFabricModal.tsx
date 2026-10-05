"use client";
import { useState, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { ModalShell, Field, Input, Textarea, SegControl, ModalActions, SearchableSelect } from "./ModalShell";
import api from "@/lib/api";
import { DatePicker } from "@/components/shared/date-picker";

interface Comp { fibre_name: string; percentage: string }

interface Props {
  open: boolean;
  onClose: () => void;
}

const KNIT_TYPES = ["Single Jersey", "Double Jersey", "Rib", "Interlock", "Pique", "Fleece", "Waffle"];
const FINISH_OPTIONS = ["Bio-wash", "Anti-pilling", "Softener", "Mercerised", "Brushed", "Sanforized"];

export function AddFabricModal({ open, onClose }: Props) {
  const qc = useQueryClient();

  const [form, setForm] = useState({
    supplier_id: "",
    invoice_number: "",
    invoice_date: "",
    constructionType: "Knit" as "Knit" | "Woven",
    knit_type: "Single Jersey",
    gsm: "",
    diameter_inches: "",
    colour: "",
    finish: [] as string[],
    blendMode: "single" as "single" | "blend",
    singleFibre: "Cotton",
    compositions: [] as Comp[],
    split_by_colour: false,
    split_by_dia: false,
    unit_cost: "",
    notes: "",
    // Inventory booking
    warehouse_id: "",
    product_id: "",
    unit_id: "",
    quantity: "",
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
    queryKey: ["products-fabric"],
    queryFn: async () => {
      const r = await api.get("/products", { params: { page_size: 200, product_type: "fabric" } });
      return (r.data.data ?? []) as { id: string; name: string }[];
    },
    enabled: open,
  });

  function set(k: string, v: unknown) { setForm((f) => ({ ...f, [k]: v })); setErr(null); }
  function toggleFinish(f: string) {
    setForm((prev) => ({
      ...prev,
      finish: prev.finish.includes(f) ? prev.finish.filter((x) => x !== f) : [...prev.finish, f],
    }));
  }
  function addComp() { setForm((f) => ({ ...f, compositions: [...f.compositions, { fibre_name: "", percentage: "" }] })); }
  function rmComp(i: number) { setForm((f) => ({ ...f, compositions: f.compositions.filter((_, j) => j !== i) })); }
  function setComp(i: number, k: keyof Comp, v: string) {
    setForm((f) => { const c = [...f.compositions]; c[i] = { ...c[i], [k]: v }; return { ...f, compositions: c }; });
  }

  const pctTotal = useMemo(
    () => form.compositions.reduce((s, c) => s + (Number(c.percentage) || 0), 0),
    [form.compositions],
  );

  const construction = form.constructionType === "Knit" ? `${form.knit_type}` : "Woven";

  const mut = useMutation({
    mutationFn: async () => {
      const compositions = form.blendMode === "single"
        ? [{ fibre_name: form.singleFibre, percentage: 100 }]
        : form.compositions.map((c) => ({ fibre_name: c.fibre_name, percentage: Number(c.percentage) }));

      return api.post("/materials/fabric", {
        supplier_id: form.supplier_id || undefined,
        invoice_number: form.invoice_number || undefined,
        invoice_date: form.invoice_date || undefined,
        construction,
        gsm: form.gsm ? Number(form.gsm) : undefined,
        diameter_inches: form.diameter_inches ? Number(form.diameter_inches) : undefined,
        colour: form.colour || undefined,
        finish: form.finish.join(", ") || undefined,
        compositions,
        split_by_colour: form.split_by_colour,
        split_by_dia: form.split_by_dia,
        unit_cost: form.unit_cost ? Number(form.unit_cost) : undefined,
        notes: form.notes || undefined,
        // Inventory booking
        warehouse_id: form.warehouse_id || undefined,
        product_id: form.product_id || undefined,
        unit_id: form.unit_id || undefined,
        quantity: form.quantity ? Number(form.quantity) : undefined,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["material-lots"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message;
      setErr(msg ?? "Failed to save fabric lot");
    },
  });

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="Add Fabric"
      subtitle="Receive a new fabric lot."
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
            accent="#0049A7"
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
            <DatePicker value={form.invoice_date} onChange={(v) => set("invoice_date", v)} />
          </Field>
        </div>

        <div className="h-px bg-border" />

        {/* Construction */}
        <Field label="Construction">
          <SegControl
            options={["Knit", "Woven"]}
            value={form.constructionType}
            onChange={(v) => set("constructionType", v)}
          />
        </Field>

        {form.constructionType === "Knit" && (
          <Field label="Knit Type">
            <div className="flex gap-1 flex-wrap">
              {KNIT_TYPES.map((kt) => (
                <button
                  key={kt}
                  type="button"
                  onClick={() => set("knit_type", kt)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                    form.knit_type === kt
                      ? "bg-primary/10 text-primary border-primary/40"
                      : "bg-background border-border text-muted-foreground hover:border-foreground/30"
                  }`}
                >
                  {kt}
                </button>
              ))}
            </div>
          </Field>
        )}

        <div className="grid grid-cols-2 gap-3">
          <Field label="GSM">
            <Input type="number" step="0.01" placeholder="180" value={form.gsm} onChange={(e) => set("gsm", e.target.value)} />
          </Field>
          <Field label="Dia (inches)">
            <Input type="number" step="0.1" placeholder="72" value={form.diameter_inches} onChange={(e) => set("diameter_inches", e.target.value)} />
          </Field>
        </div>

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
              placeholder="Cotton / Polyester…"
              value={form.singleFibre}
              onChange={(e) => set("singleFibre", e.target.value)}
            />
          ) : (
            <div className="space-y-2">
              {form.compositions.map((c, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <Input placeholder="Fibre" value={c.fibre_name} onChange={(e) => setComp(i, "fibre_name", e.target.value)} className="flex-1" />
                  <Input type="number" placeholder="%" value={c.percentage} onChange={(e) => setComp(i, "percentage", e.target.value)} className="w-20" min={0.1} max={100} step={0.01} />
                  <button type="button" onClick={() => rmComp(i)} className="text-muted-foreground hover:text-violet-500"><X className="h-4 w-4" /></button>
                </div>
              ))}
              <button type="button" onClick={addComp} className="flex items-center gap-1 text-xs text-primary hover:underline">
                <Plus className="h-3 w-3" /> Add fibre
              </button>
              {form.compositions.length > 0 && pctTotal !== 100 && (
                <p className="text-xs text-violet-600">Total: {pctTotal}% (must equal 100%)</p>
              )}
            </div>
          )}
        </Field>

        <div className="h-px bg-border" />

        {/* Colour + finish */}
        <Field label="Colour">
          <Input placeholder="Colour / shade" value={form.colour} onChange={(e) => set("colour", e.target.value)} />
        </Field>

        <Field label="Finish">
          <div className="flex gap-1 flex-wrap">
            {FINISH_OPTIONS.map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => toggleFinish(f)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                  form.finish.includes(f)
                    ? "bg-primary/10 text-primary border-primary/40"
                    : "bg-background border-border text-muted-foreground hover:border-foreground/30"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </Field>

        {/* Split toggles */}
        <div className="flex gap-4">
          {[
            { key: "split_by_colour", label: "Split by Colour" },
            { key: "split_by_dia", label: "Split by Dia" },
          ].map(({ key, label }) => (
            <label key={key} className="flex items-center gap-2 text-sm cursor-pointer select-none">
              <input
                type="checkbox"
                checked={(form as Record<string, unknown>)[key] as boolean}
                onChange={(e) => set(key, e.target.checked)}
                className="h-4 w-4 rounded border-border accent-primary"
              />
              {label}
            </label>
          ))}
        </div>

        <div className="h-px bg-border" />

        <Field label="Rate / Meter (₹)">
          <Input type="number" step="0.01" placeholder="0.00" value={form.unit_cost} onChange={(e) => set("unit_cost", e.target.value)} />
        </Field>

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
              accent="#0049A7"
              options={[
                { value: "", label: "— Skip —" },
                ...(warehouses.data ?? []).map((w) => ({
                  value: w.id,
                  label: w.name,
                })),
              ]}
            />
          </Field>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Product">
              <SearchableSelect
                value={form.product_id}
                onChange={(v) => set("product_id", v)}
                placeholder="— Select —"
                accent="#0049A7"
                options={(products.data ?? []).map((p) => ({
                  value: p.id,
                  label: p.name,
                }))}
              />
            </Field>
            <Field label="Qty (m / kg)">
              <Input
                type="number"
                step="0.001"
                placeholder="0.000"
                value={form.quantity}
                onChange={(e) => set("quantity", e.target.value)}
              />
            </Field>
            <Field label="Unit">
              <SearchableSelect
                value={form.unit_id}
                onChange={(v) => set("unit_id", v)}
                placeholder="— Unit —"
                accent="#0049A7"
                options={(units.data ?? []).map((u) => ({
                  value: u.id,
                  label: u.abbreviation,
                }))}
              />
            </Field>
          </div>
          {form.quantity && form.warehouse_id && form.product_id && form.unit_id && (
            <p className="text-xs text-blue-600">Will book {form.quantity} units into inventory on save.</p>
          )}
        </div>

        {err && <p className="text-xs text-violet-500">{err}</p>}
      </form>
    </ModalShell>
  );
}
