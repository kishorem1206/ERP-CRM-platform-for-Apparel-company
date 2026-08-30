"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, X } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { StatusBadge } from "@/components/shared/status-badge";
import { ModalPortal } from "@/components/shared/modal-portal";
import { SearchableSelect } from "@/components/shared/searchable-select";

const INDIGO   = "#5347CE";
const LAVENDER = "#887CFD";
const BLUE     = "#4896FE";
const TEAL     = "#16C8C7";

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
  { label: "Styles", value: "finished_good" },
  { label: "Yarn", value: "yarn" },
  { label: "Fabric", value: "fabric" },
  { label: "Trims", value: "trim" },
  { label: "Packing", value: "packing" },
];

const columns: Column<Record<string, unknown>>[] = [
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
    render: (row) => <StatusBadge status={row.is_active ? "active" : "inactive"} />,
  },
];

// ── Add Product Modal ─────────────────────────────────────────────────────────

const EMPTY_FORM = {
  code: "", name: "", product_type: "finished_good" as ProductType,
  category_id: "", unit_id: "", hsn_id: "",
  cost_price: "", mrp: "", dealer_price: "",
  fabric_type: "", fabric_composition: "", gsm: "", construction: "",
  fit: "", season: "", gender: "", description: "",
};

function AddProductModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);

  const { data: categories } = useQuery<MasterItem[]>({
    queryKey: ["master-categories"],
    queryFn: async () => (await api.get("/categories")).data.data,
  });
  const { data: units } = useQuery<MasterItem[]>({
    queryKey: ["master-units"],
    queryFn: async () => (await api.get("/units")).data.data,
  });
  const { data: hsnList } = useQuery<HsnItem[]>({
    queryKey: ["master-hsn"],
    queryFn: async () => (await api.get("/hsn")).data.data,
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
              <label className="text-xs font-medium">Code <span className="text-red-500">*</span></label>
              <input value={form.code} onChange={(e) => set("code", e.target.value)}
                placeholder="e.g. FAB-30VL" required
                className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Name <span className="text-red-500">*</span></label>
              <input value={form.name} onChange={(e) => set("name", e.target.value)}
                placeholder="e.g. 30s VL Single Jersey" required
                className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30" />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-medium">Type <span className="text-red-500">*</span></label>
              <SearchableSelect
                value={form.product_type}
                onChange={(v) => set("product_type", v)}
                placeholder="Select type"
                accent="#887CFD"
                options={Object.entries(TYPE_LABELS).map(([v, l]) => ({ value: v, label: l }))}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Category</label>
              <SearchableSelect
                value={form.category_id}
                onChange={(v) => set("category_id", v)}
                placeholder="— select —"
                accent="#887CFD"
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
                accent="#887CFD"
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
                accent="#887CFD"
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
            <div className="grid grid-cols-3 gap-4">
              {[
                { key: "cost_price" as const, label: "Cost Price" },
                { key: "mrp" as const, label: "MRP" },
                { key: "dealer_price" as const, label: "Dealer Price" },
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
            <p className="text-xs text-red-500 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-xl px-3 py-2">
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

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ProductsPage() {
  const [typeFilter, setTypeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [showAdd, setShowAdd] = useState(false);

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

  return (
    <div className="p-8 space-y-8">
      {showAdd && <AddProductModal onClose={() => setShowAdd(false)} />}

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
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: LAVENDER }}
        >
          <Plus className="h-4 w-4" /> Add Product
        </button>
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
        <p className="text-sm text-red-500">
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
            columns={columns}
            data={(data ?? []) as unknown as Record<string, unknown>[]}
            loading={isLoading}
            emptyMessage="No products found. Click '+ Add Product' to create one."
            rowKey={(row) => row.id as string}
            pageSize={25}
          />
        </div>
      </div>
    </div>
  );
}
