"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ChevronRight } from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";

const INDIGO = "#0049A7";
const inputCls =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

const UNIT_OPTIONS = [
  { value: "pcs", label: "Pieces (pcs)" },
  { value: "pairs", label: "Pairs" },
  { value: "sets", label: "Sets" },
  { value: "meters", label: "Meters" },
  { value: "kg", label: "Kilograms (kg)" },
  { value: "box", label: "Box" },
  { value: "dozen", label: "Dozen" },
];

interface ProductForm {
  name: string;
  description: string;
  sku: string;
  price: string;
  currency: string;
  unit: string;
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-muted-foreground mb-1">
        {label}{required && <span className="text-destructive ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

function SectionLabel({ label }: { label: string }) {
  return (
    <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground border-b pb-2 mb-4">
      {label}
    </p>
  );
}

export default function NewProductPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ProductForm>({
    name: "", description: "", sku: "", price: "", currency: "INR", unit: "",
  });
  const [errors, setErrors] = useState<{ name?: string; price?: string }>({});

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post("/crm/products", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-products"] });
      router.push("/crm/products");
    },
  });

  function set<K extends keyof ProductForm>(k: K, v: ProductForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
    if (errors[k as keyof typeof errors]) setErrors((e) => ({ ...e, [k]: undefined }));
  }

  function handleSubmit() {
    const errs: typeof errors = {};
    if (!form.name.trim()) errs.name = "Name is required.";
    if (form.price && isNaN(parseFloat(form.price))) errs.price = "Enter a valid price.";
    if (Object.keys(errs).length) { setErrors(errs); return; }

    mutation.mutate({
      name: form.name.trim(),
      description: form.description || undefined,
      sku: form.sku || undefined,
      price: form.price ? parseFloat(form.price) : undefined,
      currency: form.currency,
      unit: form.unit || undefined,
    });
  }

  return (
    <div>
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.push("/crm/products")}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground leading-none">
              CRM / PRODUCTS
            </p>
            <h1 className="text-base font-semibold leading-tight mt-0.5">New Product</h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => router.push("/crm/products")}
            className="px-4 py-1.5 rounded-md border border-input text-sm hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={mutation.isPending}
            className="px-4 py-1.5 rounded-xl text-sm font-semibold text-white disabled:opacity-60 flex items-center gap-1.5 transition-all hover:opacity-90 active:scale-95"
            style={{ background: INDIGO }}
          >
            {mutation.isPending ? "Saving…" : <><ChevronRight className="h-4 w-4" /> Add Product</>}
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="p-6">
        <div className="max-w-2xl space-y-4">
          <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
            <SectionLabel label="PRODUCT INFO" />

            <Field label="Product Name" required>
              <input
                className={`${inputCls} ${errors.name ? "border-destructive" : ""}`}
                placeholder="e.g. Premium Cotton T-Shirt"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                autoFocus
              />
              {errors.name && <p className="text-[11px] text-destructive mt-1">{errors.name}</p>}
            </Field>

            <Field label="Description">
              <textarea
                className={`${inputCls} resize-none`}
                rows={3}
                placeholder="Brief product description…"
                value={form.description}
                onChange={(e) => set("description", e.target.value)}
              />
            </Field>

            <Field label="SKU">
              <input
                className={inputCls}
                placeholder="e.g. APP-SHIRT-001"
                value={form.sku}
                onChange={(e) => set("sku", e.target.value)}
              />
            </Field>
          </div>

          <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
            <SectionLabel label="PRICING & UNIT" />

            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-2">
                <Field label="Price">
                  <input
                    className={`${inputCls} ${errors.price ? "border-destructive" : ""}`}
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="0.00"
                    value={form.price}
                    onChange={(e) => set("price", e.target.value)}
                  />
                  {errors.price && <p className="text-[11px] text-destructive mt-1">{errors.price}</p>}
                </Field>
              </div>
              <Field label="Currency">
                <input
                  className={inputCls}
                  placeholder="INR"
                  value={form.currency}
                  onChange={(e) => set("currency", e.target.value)}
                />
              </Field>
            </div>

            <Field label="Unit">
              <SearchableSelect
                options={UNIT_OPTIONS}
                value={form.unit}
                onChange={(v) => set("unit", v)}
                placeholder="Select unit…"
                accent={INDIGO}
              />
            </Field>
          </div>
        </div>
      </div>
    </div>
  );
}
