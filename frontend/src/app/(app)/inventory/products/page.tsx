"use client";
import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Search, X, GitMerge, ChevronDown, ChevronUp } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { StatusBadge } from "@/components/shared/status-badge";
import { ModalPortal } from "@/components/shared/modal-portal";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { Can } from "@/lib/permissions";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

type ProductType = "finished_good" | "yarn" | "fabric" | "trim" | "packing" | "raw_material";

interface Product {
  id: string;
  code: string;
  name: string;
  product_type: ProductType;
  category_name: string | null;
  unit_abbreviation: string | null;
  hsn_code: string | null;
  gst_rate: string | null;
  cost_price: string | null;
  is_active: boolean;
  merged_into_id: string | null;
}

interface MasterItem { id: string; name: string; }
interface HsnItem { id: string; hsn: string; description: string | null; gst_rate: string; }

const TYPE_LABELS: Record<ProductType, string> = {
  finished_good: "Finished Good",
  yarn: "Yarn",
  fabric: "Fabric",
  trim: "Trim",
  packing: "Packing",
  raw_material: "Raw Material",
};

const TYPE_FILTERS = [
  { label: "All", value: "" },
  { label: "Finished Goods", value: "finished_good" },
  { label: "Yarn", value: "yarn" },
  { label: "Fabric", value: "fabric" },
  { label: "Trims", value: "trim" },
  { label: "Packing", value: "packing" },
  { label: "Raw Material", value: "raw_material" },
];

function getColumns(
  onEdit: (id: string) => void,
  onMerge: (id: string) => void,
  mergeTargetNames: Record<string, string>,
): Column<Record<string, unknown>>[] { return [
  { key: "code", header: "Code", sortable: true },
  { key: "name", header: "Name", sortable: true },
  {
    key: "product_type",
    header: "Type",
    render: (row) => (
      <span className="text-xs text-muted-foreground">
        {TYPE_LABELS[(row.product_type as ProductType)] ?? (row.product_type as string)}
      </span>
    ),
  },
  { key: "category_name", header: "Category", sortable: true },
  { key: "unit_abbreviation", header: "Unit" },
  { key: "hsn_code", header: "HSN" },
  {
    key: "gst_rate",
    header: "GST %",
    render: (row) => row.gst_rate ? `${row.gst_rate}%` : "—",
    className: "text-right",
  },
  {
    key: "cost_price",
    header: "Cost",
    render: (row) =>
      row.cost_price
        ? new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(Number(row.cost_price))
        : "—",
    className: "text-right",
  },
  {
    key: "is_active",
    header: "Status",
    render: (row) => {
      const mergedIntoId = row.merged_into_id as string | null;
      if (mergedIntoId) {
        const targetName = mergeTargetNames[mergedIntoId];
        return <StatusBadge status="inactive" label={targetName ? `Merged → ${targetName}` : "Merged"} />;
      }
      return <StatusBadge status={row.is_active ? "active" : "inactive"} />;
    },
  },
  {
    key: "edit",
    header: "",
    className: "w-16",
    render: (row) => (
      <div className="flex items-center gap-1">
        <Can perm="master_data.edit"><button
          onClick={(e) => { e.stopPropagation(); onEdit(row.id as string); }}
          className="p-1 rounded transition-colors hover:bg-muted text-muted-foreground"
          title="Edit product"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button></Can>
        {!row.merged_into_id && (
          <Can perm="master_data.merge"><button
            onClick={(e) => { e.stopPropagation(); onMerge(row.id as string); }}
            className="p-1 rounded transition-colors hover:bg-muted text-muted-foreground"
            title="Merge into another product"
          >
            <GitMerge className="h-3.5 w-3.5" />
          </button></Can>
        )}
      </div>
    ),
  },
]; }

// ── Add Product Modal ─────────────────────────────────────────────────────────

const EMPTY_FORM = {
  code: "", name: "", product_type: "finished_good" as ProductType,
  category_id: "", unit_id: "", hsn_id: "",
  cost_price: "", mrp: "", dealer_price: "", wholesale_price: "",
  fabric_type: "", fabric_composition: "", gsm: "", construction: "",
  fit: "", season: "", gender: "", description: "",
};

function AddProductModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);

  const { data: categories } = useQuery<MasterItem[]>({
    queryKey: ["master-categories"],
    queryFn: async () => (await api.get("/master/categories")).data.data,
  });
  const { data: units } = useQuery<MasterItem[]>({
    queryKey: ["master-units"],
    queryFn: async () => (await api.get("/master/units")).data.data,
  });
  const { data: hsnList } = useQuery<HsnItem[]>({
    queryKey: ["master-hsn"],
    queryFn: async () => (await api.get("/master/hsn")).data.data,
  });

  const mutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.post("/products", payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["products"] });
      onClose();
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { error?: unknown } } })?.response?.data?.error;
      setError(
        typeof detail === "string" ? detail :
        typeof detail === "object" && detail !== null ? JSON.stringify(detail) :
        "Failed to create product."
      );
    },
  });

  function set(k: keyof typeof EMPTY_FORM, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!form.code.trim()) { setError("Code is required."); return; }
    if (!form.name.trim()) { setError("Name is required."); return; }

    const payload: Record<string, unknown> = {
      code: form.code.trim(),
      name: form.name.trim(),
      product_type: form.product_type,
    };
    if (form.category_id) payload.category_id = form.category_id;
    if (form.unit_id) payload.unit_id = form.unit_id;
    if (form.hsn_id) payload.hsn_id = form.hsn_id;
    if (form.cost_price) payload.cost_price = Number(form.cost_price);
    if (form.mrp) payload.mrp = Number(form.mrp);
    if (form.dealer_price) payload.dealer_price = Number(form.dealer_price);
    if (form.wholesale_price) payload.wholesale_price = Number(form.wholesale_price);
    if (form.description) payload.description = form.description;
    if (form.fabric_type) payload.fabric_type = form.fabric_type;
    if (form.fabric_composition) payload.fabric_composition = form.fabric_composition;
    if (form.gsm) payload.gsm = Number(form.gsm);
    if (form.construction) payload.construction = form.construction;
    if (form.fit) payload.fit = form.fit;
    if (form.season) payload.season = form.season;
    if (form.gender) payload.gender = form.gender;

    mutation.mutate(payload);
  }

  const isFabric = form.product_type === "fabric";
  const isFinished = form.product_type === "finished_good";

  return (
    <ModalPortal>
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
      <div className="bg-card border rounded-2xl w-full max-w-2xl shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-card z-10">
          <h2 className="text-base font-semibold">Add Product</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-5">
          {/* Core fields */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-medium">Code <span className="text-[#1D0DB0]">*</span></label>
              <input value={form.code} onChange={(e) => set("code", e.target.value)}
                placeholder="e.g. FAB-30VL" required
                className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Name <span className="text-[#1D0DB0]">*</span></label>
              <input value={form.name} onChange={(e) => set("name", e.target.value)}
                placeholder="e.g. 30s VL Single Jersey" required
                className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-medium">Type <span className="text-[#1D0DB0]">*</span></label>
              <SearchableSelect
                value={form.product_type}
                onChange={(v) => set("product_type", v)}
                placeholder="Select type"
                accent="#0F78FF"
                options={Object.entries(TYPE_LABELS).map(([v, l]) => ({ value: v, label: l }))}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Category</label>
              <SearchableSelect
                value={form.category_id}
                onChange={(v) => set("category_id", v)}
                placeholder="— select —"
                accent="#0F78FF"
                options={[
                  { value: "", label: "— select —" },
                  ...(categories ?? []).map((c) => ({ value: c.id, label: c.name })),
                ]}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Unit</label>
              <SearchableSelect
                value={form.unit_id}
                onChange={(v) => set("unit_id", v)}
                placeholder="— select —"
                accent="#0F78FF"
                options={[
                  { value: "", label: "— select —" },
                  ...(units ?? []).map((u) => ({ value: u.id, label: u.name })),
                ]}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-medium">HSN Code</label>
              <SearchableSelect
                value={form.hsn_id}
                onChange={(v) => set("hsn_id", v)}
                placeholder="— select —"
                accent="#0F78FF"
                options={[
                  { value: "", label: "— select —" },
                  ...(hsnList ?? []).map((h) => ({
                    value: h.id,
                    label: `${h.hsn} — ${h.description ?? ""} (${h.gst_rate}% GST)`,
                  })),
                ]}
              />
            </div>
          </div>

          {/* Pricing */}
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Pricing</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { key: "cost_price" as const, label: "Cost Price" },
                { key: "mrp" as const, label: "MRP" },
                { key: "dealer_price" as const, label: "Dealer Price" },
                { key: "wholesale_price" as const, label: "Wholesale Price" },
              ].map(({ key, label }) => (
                <div key={key} className="space-y-1">
                  <label className="text-xs font-medium">{label}</label>
                  <input type="number" min="0" step="0.01" value={form[key]}
                    onChange={(e) => set(key, e.target.value)}
                    placeholder="0.00"
                    className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
              ))}
            </div>
            <p className="text-[11px] text-muted-foreground mt-1.5">
              Wholesale Price is the default price used when creating Sales Orders/Quotations, unless a customer-specific or list price applies.
            </p>
          </div>

          {/* Fabric fields */}
          {isFabric && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Fabric Details</p>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-medium">Fabric Type</label>
                  <input value={form.fabric_type} onChange={(e) => set("fabric_type", e.target.value)}
                    placeholder="e.g. Single Jersey"
                    className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">Composition</label>
                  <input value={form.fabric_composition} onChange={(e) => set("fabric_composition", e.target.value)}
                    placeholder="e.g. 30s Viscose Lycra"
                    className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">GSM</label>
                  <input type="number" min="0" step="0.01" value={form.gsm}
                    onChange={(e) => set("gsm", e.target.value)} placeholder="160"
                    className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">Construction</label>
                  <input value={form.construction} onChange={(e) => set("construction", e.target.value)}
                    placeholder="e.g. S/J - 30&quot; dia"
                    className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
              </div>
            </div>
          )}

          {/* Finished good fields */}
          {isFinished && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Style Details</p>
              <div className="grid grid-cols-3 gap-4">
                {[
                  { key: "fit" as const, label: "Fit", placeholder: "e.g. Regular" },
                  { key: "season" as const, label: "Season", placeholder: "e.g. Summer 2025" },
                  { key: "gender" as const, label: "Gender", placeholder: "e.g. Men / Women / Kids" },
                ].map(({ key, label, placeholder }) => (
                  <div key={key} className="space-y-1">
                    <label className="text-xs font-medium">{label}</label>
                    <input value={form[key]} onChange={(e) => set(key, e.target.value)}
                      placeholder={placeholder}
                      className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Description */}
          <div className="space-y-1">
            <label className="text-xs font-medium">Description</label>
            <textarea value={form.description} onChange={(e) => set("description", e.target.value)}
              rows={2} placeholder="Optional notes..."
              className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30 resize-none" />
          </div>

          {error && (
            <p className="text-xs rounded-xl px-3 py-2" style={{ background: "#1D0DB00D", borderColor: "#1D0DB04D", color: "#1D0DB0", border: "1px solid" }}>
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose}
              className="border rounded-xl px-4 py-2 text-sm font-medium hover:bg-muted transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={mutation.isPending}
              className="text-white rounded-xl px-4 py-2 text-sm font-semibold transition-all hover:opacity-90 active:scale-95 disabled:opacity-60"
              style={{ background: LAVENDER }}>
              {mutation.isPending ? "Saving…" : "Save Product"}
            </button>
          </div>
        </form>
      </div>
    </div>
    </ModalPortal>
  );
}

// ── Edit Product Modal ──────────────────────────────────────────────────────────

interface ProductDetail {
  id: string; code: string; name: string; product_type: ProductType;
  category_id: string | null; unit_id: string | null; hsn_id: string | null;
  mrp: string | null; dealer_price: string | null; cost_price: string | null; wholesale_price: string | null;
  description: string | null; fabric_type: string | null; fabric_composition: string | null;
  gsm: string | null; construction: string | null; fit: string | null; season: string | null;
  gender: string | null; is_active: boolean;
}

function EditProductModal({ productId, onClose }: { productId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<typeof EMPTY_FORM | null>(null);
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { data: product, isLoading } = useQuery<ProductDetail>({
    queryKey: ["product", productId],
    queryFn: async () => (await api.get(`/products/${productId}`)).data.data,
  });

  const { data: categories } = useQuery<MasterItem[]>({
    queryKey: ["master-categories"],
    queryFn: async () => (await api.get("/master/categories")).data.data,
  });
  const { data: units } = useQuery<MasterItem[]>({
    queryKey: ["master-units"],
    queryFn: async () => (await api.get("/master/units")).data.data,
  });
  const { data: hsnList } = useQuery<HsnItem[]>({
    queryKey: ["master-hsn"],
    queryFn: async () => (await api.get("/master/hsn")).data.data,
  });

  useEffect(() => {
    if (!product) return;
    setForm({
      code: product.code, name: product.name, product_type: product.product_type,
      category_id: product.category_id ?? "", unit_id: product.unit_id ?? "", hsn_id: product.hsn_id ?? "",
      cost_price: product.cost_price ?? "", mrp: product.mrp ?? "", dealer_price: product.dealer_price ?? "",
      wholesale_price: product.wholesale_price ?? "",
      fabric_type: product.fabric_type ?? "", fabric_composition: product.fabric_composition ?? "",
      gsm: product.gsm ?? "", construction: product.construction ?? "",
      fit: product.fit ?? "", season: product.season ?? "", gender: product.gender ?? "",
      description: product.description ?? "",
    });
    setIsActive(product.is_active);
  }, [product]);

  const mutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.patch(`/products/${productId}`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["products"] });
      qc.invalidateQueries({ queryKey: ["product", productId] });
      onClose();
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { error?: unknown } } })?.response?.data?.error;
      setError(
        typeof detail === "string" ? detail :
        typeof detail === "object" && detail !== null ? JSON.stringify(detail) :
        "Failed to update product."
      );
    },
  });

  function set(k: keyof typeof EMPTY_FORM, v: string) {
    setForm((f) => (f ? { ...f, [k]: v } : f));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setError(null);
    if (!form.name.trim()) { setError("Name is required."); return; }

    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      category_id: form.category_id || null,
      unit_id: form.unit_id || null,
      hsn_id: form.hsn_id || null,
      mrp: form.mrp ? Number(form.mrp) : null,
      dealer_price: form.dealer_price ? Number(form.dealer_price) : null,
      wholesale_price: form.wholesale_price ? Number(form.wholesale_price) : null,
      cost_price: form.cost_price ? Number(form.cost_price) : null,
      description: form.description || null,
      fabric_type: form.fabric_type || null,
      fabric_composition: form.fabric_composition || null,
      gsm: form.gsm ? Number(form.gsm) : null,
      construction: form.construction || null,
      fit: form.fit || null,
      season: form.season || null,
      gender: form.gender || null,
      is_active: isActive,
    };

    mutation.mutate(payload);
  }

  const isFabric = form?.product_type === "fabric";
  const isFinished = form?.product_type === "finished_good";

  return (
    <ModalPortal>
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
      <div className="bg-card border rounded-2xl w-full max-w-2xl shadow-xl">
        <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-card z-10">
          <h2 className="text-base font-semibold">Edit Product</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        {isLoading || !form ? (
          <div className="px-6 py-10 text-sm text-muted-foreground">Loading…</div>
        ) : (
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-medium">Code</label>
              <input value={form.code} disabled
                className="w-full border rounded-xl px-3 py-2 text-sm bg-muted text-muted-foreground outline-none" />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Name <span className="text-[#1D0DB0]">*</span></label>
              <input value={form.name} onChange={(e) => set("name", e.target.value)}
                required
                className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-medium">Type</label>
              <input value={TYPE_LABELS[form.product_type]} disabled
                className="w-full border rounded-xl px-3 py-2 text-sm bg-muted text-muted-foreground outline-none" />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Category</label>
              <SearchableSelect
                value={form.category_id}
                onChange={(v) => set("category_id", v)}
                placeholder="— select —"
                accent="#0F78FF"
                options={[
                  { value: "", label: "— select —" },
                  ...(categories ?? []).map((c) => ({ value: c.id, label: c.name })),
                ]}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Unit</label>
              <SearchableSelect
                value={form.unit_id}
                onChange={(v) => set("unit_id", v)}
                placeholder="— select —"
                accent="#0F78FF"
                options={[
                  { value: "", label: "— select —" },
                  ...(units ?? []).map((u) => ({ value: u.id, label: u.name })),
                ]}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-medium">HSN Code</label>
              <SearchableSelect
                value={form.hsn_id}
                onChange={(v) => set("hsn_id", v)}
                placeholder="— select —"
                accent="#0F78FF"
                options={[
                  { value: "", label: "— select —" },
                  ...(hsnList ?? []).map((h) => ({
                    value: h.id,
                    label: `${h.hsn} — ${h.description ?? ""} (${h.gst_rate}% GST)`,
                  })),
                ]}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Status</label>
              <div className="flex items-center gap-2 h-[38px]">
                <button
                  type="button"
                  onClick={() => setIsActive((v) => !v)}
                  className="flex items-center gap-2 text-sm font-medium"
                >
                  <span
                    className="w-9 h-5 rounded-full relative transition-colors"
                    style={{ background: isActive ? LAVENDER : "hsl(var(--muted))" }}
                  >
                    <span
                      className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all"
                      style={{ left: isActive ? "18px" : "2px" }}
                    />
                  </span>
                  {isActive ? "Active" : "Inactive"}
                </button>
              </div>
            </div>
          </div>

          {/* Pricing */}
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Pricing</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { key: "cost_price" as const, label: "Cost Price" },
                { key: "mrp" as const, label: "MRP" },
                { key: "dealer_price" as const, label: "Dealer Price" },
                { key: "wholesale_price" as const, label: "Wholesale Price" },
              ].map(({ key, label }) => (
                <div key={key} className="space-y-1">
                  <label className="text-xs font-medium">{label}</label>
                  <input type="number" min="0" step="0.01" value={form[key]}
                    onChange={(e) => set(key, e.target.value)}
                    placeholder="0.00"
                    className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
              ))}
            </div>
            <p className="text-[11px] text-muted-foreground mt-1.5">
              Wholesale Price is the default price used when creating Sales Orders/Quotations, unless a customer-specific or list price applies.
            </p>
          </div>

          {/* Fabric fields */}
          {isFabric && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Fabric Details</p>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-medium">Fabric Type</label>
                  <input value={form.fabric_type} onChange={(e) => set("fabric_type", e.target.value)}
                    placeholder="e.g. Single Jersey"
                    className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">Composition</label>
                  <input value={form.fabric_composition} onChange={(e) => set("fabric_composition", e.target.value)}
                    placeholder="e.g. 30s Viscose Lycra"
                    className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">GSM</label>
                  <input type="number" min="0" step="0.01" value={form.gsm}
                    onChange={(e) => set("gsm", e.target.value)} placeholder="160"
                    className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">Construction</label>
                  <input value={form.construction} onChange={(e) => set("construction", e.target.value)}
                    placeholder="e.g. S/J - 30&quot; dia"
                    className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
              </div>
            </div>
          )}

          {/* Finished good fields */}
          {isFinished && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Style Details</p>
              <div className="grid grid-cols-3 gap-4">
                {[
                  { key: "fit" as const, label: "Fit", placeholder: "e.g. Regular" },
                  { key: "season" as const, label: "Season", placeholder: "e.g. Summer 2025" },
                  { key: "gender" as const, label: "Gender", placeholder: "e.g. Men / Women / Kids" },
                ].map(({ key, label, placeholder }) => (
                  <div key={key} className="space-y-1">
                    <label className="text-xs font-medium">{label}</label>
                    <input value={form[key]} onChange={(e) => set(key, e.target.value)}
                      placeholder={placeholder}
                      className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Description */}
          <div className="space-y-1">
            <label className="text-xs font-medium">Description</label>
            <textarea value={form.description} onChange={(e) => set("description", e.target.value)}
              rows={2} placeholder="Optional notes..."
              className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30 resize-none" />
          </div>

          {error && (
            <p className="text-xs rounded-xl px-3 py-2" style={{ background: "#1D0DB00D", borderColor: "#1D0DB04D", color: "#1D0DB0", border: "1px solid" }}>
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose}
              className="border rounded-xl px-4 py-2 text-sm font-medium hover:bg-muted transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={mutation.isPending}
              className="text-white rounded-xl px-4 py-2 text-sm font-semibold transition-all hover:opacity-90 active:scale-95 disabled:opacity-60"
              style={{ background: LAVENDER }}>
              {mutation.isPending ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </form>
        )}
      </div>
    </div>
    </ModalPortal>
  );
}

// ── Merge Product Modal ───────────────────────────────────────────────────────

function MergeProductModal({ source, allProducts, onClose }: {
  source: Product; allProducts: Product[]; onClose: () => void;
}) {
  const qc = useQueryClient();
  const [targetId, setTargetId] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");

  const targetOptions = allProducts
    .filter((p) => p.id !== source.id && p.is_active && !p.merged_into_id)
    .map((p) => ({ value: p.id, label: p.name, meta: p.code }));

  const mut = useMutation({
    mutationFn: () => api.post(`/products/${source.id}/merge`, { target_product_id: targetId, notes: notes || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["products"] });
      qc.invalidateQueries({ queryKey: ["product-merge-logs"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error;
      setError(typeof msg === "string" ? msg : "Merge failed.");
    },
  });

  return (
    <ModalPortal>
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
      <div className="bg-card border rounded-2xl shadow-2xl w-full max-w-md mx-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="font-semibold text-base">Merge Product</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
        </div>
        <div className="p-5 space-y-4">
          <p className="text-sm">
            Merging <span className="font-semibold">{source.name}</span> ({source.code}) into another product.
          </p>
          <div className="rounded-xl border px-3 py-2.5 text-xs" style={{ background: "#1D0DB00D", borderColor: "#1D0DB04D", color: "#1D0DB0" }}>
            This moves all of {source.name}&rsquo;s history (stock, orders, quotations, purchases) to the target
            and deactivates {source.name}. This cannot be easily undone.
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Merge into *</label>
            <SearchableSelect
              value={targetId}
              onChange={setTargetId}
              placeholder="Select target product…"
              accent={INDIGO}
              options={targetOptions}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Notes</label>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2}
              className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              placeholder="Why these products are being merged" />
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <button onClick={onClose} className="px-4 py-1.5 rounded border border-input text-sm hover:bg-muted">Cancel</button>
            <button
              onClick={() => { setError(""); mut.mutate(); }}
              disabled={!targetId || mut.isPending}
              className="px-4 py-1.5 rounded bg-violet-500 hover:bg-violet-600 text-white text-sm font-semibold disabled:opacity-50"
            >
              {mut.isPending ? "Merging…" : "Merge"}
            </button>
          </div>
        </div>
      </div>
    </div>
    </ModalPortal>
  );
}

// ── Merge History Panel ───────────────────────────────────────────────────────

interface MergeLog {
  id: string;
  source_name: string;
  source_code: string;
  target_name: string;
  target_code: string;
  merged_by_name: string | null;
  merged_at: string;
  notes: string | null;
}

function MergeHistoryPanel() {
  const [open, setOpen] = useState(false);
  const { data } = useQuery({
    queryKey: ["product-merge-logs"],
    queryFn: async () => (await api.get("/products/merge-logs?page_size=50")).data.data as MergeLog[],
    enabled: open,
  });

  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-6 py-4 text-left"
      >
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Merge History</p>
        {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>
      {open && (
        <div className="border-t border-border divide-y divide-border">
          {!data || data.length === 0 ? (
            <p className="px-6 py-6 text-sm text-muted-foreground text-center">No merges recorded yet.</p>
          ) : (
            data.map((log) => (
              <div key={log.id} className="px-6 py-3 text-sm flex items-center justify-between gap-4">
                <div>
                  <span className="font-medium">{log.source_name}</span>
                  <span className="text-muted-foreground"> ({log.source_code}) &rarr; </span>
                  <span className="font-medium">{log.target_name}</span>
                  <span className="text-muted-foreground"> ({log.target_code})</span>
                  {log.notes && <p className="text-xs text-muted-foreground mt-0.5">{log.notes}</p>}
                </div>
                <div className="text-right text-xs text-muted-foreground whitespace-nowrap">
                  <div>{log.merged_by_name ?? "—"}</div>
                  <div>{new Date(log.merged_at).toLocaleString()}</div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ProductsPage() {
  const [typeFilter, setTypeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [editingProductId, setEditingProductId] = useState<string | null>(null);
  const [mergingProductId, setMergingProductId] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["products", typeFilter, search],
    queryFn: async () => {
      const params = new URLSearchParams({ page_size: "200" });
      if (typeFilter) params.set("product_type", typeFilter);
      if (search) params.set("search", search);
      const res = await api.get(`/products?${params}`);
      return res.data?.data as Product[];
    },
  });

  const mergeTargetNames = Object.fromEntries((data ?? []).map((p) => [p.id, p.name]));
  const mergingProduct = (data ?? []).find((p) => p.id === mergingProductId) ?? null;

  return (
    <div className="p-8 space-y-8">
      {showAdd && <AddProductModal onClose={() => setShowAdd(false)} />}
      {editingProductId && <EditProductModal productId={editingProductId} onClose={() => setEditingProductId(null)} />}
      {mergingProduct && (
        <MergeProductModal source={mergingProduct} allProducts={data ?? []} onClose={() => setMergingProductId(null)} />
      )}

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            INVENTORY / PRODUCTS
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Products</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Yarn, fabric, trim and finished goods product master.
          </p>
        </div>
        <Can perm="master_data.create"><button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: LAVENDER }}
        >
          <Plus className="h-4 w-4" /> Add Product
        </button></Can>
      </div>

      {/* Filters row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Type filter tab strip */}
        <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit flex-wrap">
          {TYPE_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setTypeFilter(f.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                typeFilter === f.value
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="flex items-center gap-2 border rounded-xl px-3 py-1.5 bg-background flex-1 max-w-xs">
          <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && setSearch(searchInput)}
            placeholder="Search code or name..."
            className="text-sm bg-transparent outline-none w-full"
          />
        </div>

        {data && (
          <span className="text-xs text-muted-foreground ml-auto">
            {data.length} product{data.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {error && (
        <p className="text-sm text-[#1D0DB0]">
          Failed to load products. Is the backend running?
        </p>
      )}

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              PRODUCT MASTER
            </p>
            <p className="text-sm font-medium mt-0.5">
              Styles, yarns, fabrics, trims and packing materials
            </p>
          </div>
        </div>
        <div className="p-0">
          <DataTable
            columns={getColumns((id) => setEditingProductId(id), (id) => setMergingProductId(id), mergeTargetNames)}
            data={(data ?? []) as unknown as Record<string, unknown>[]}
            loading={isLoading}
            emptyMessage="No products found. Click '+ Add Product' to create one."
            rowKey={(row) => row.id as string}
            onRowClick={(row) => setEditingProductId(row.id as string)}
            pageSize={25}
          />
        </div>
      </div>

      <MergeHistoryPanel />
    </div>
  );
}
