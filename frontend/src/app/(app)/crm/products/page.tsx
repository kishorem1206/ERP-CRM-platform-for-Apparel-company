"use client";
import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, X, Pencil, ToggleLeft, ToggleRight } from "lucide-react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { ModalShell } from "@/components/shared/modal-shell";
import { Can } from "@/lib/permissions";

// ── Palette ───────────────────────────────────────────────────────────────────
const INDIGO = "#0049A7";

const fmt = (v: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(v);

const inputCls =
  "w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

const UNIT_OPTIONS = [
  { value: "Pcs", label: "Pcs" },
  { value: "Meters", label: "Meters" },
  { value: "Kg", label: "Kg" },
  { value: "Set", label: "Set" },
  { value: "Pair", label: "Pair" },
];

// ── Types ─────────────────────────────────────────────────────────────────────
interface Product {
  id: string;
  name: string;
  description: string | null;
  sku: string | null;
  price: number | null;
  currency: string;
  unit: string | null;
  is_active: boolean;
}

interface ProductForm {
  name: string;
  description: string;
  sku: string;
  price: string;
  currency: string;
  unit: string;
}

const emptyForm = (): ProductForm => ({
  name: "",
  description: "",
  sku: "",
  price: "",
  currency: "INR",
  unit: "Pcs",
});

function productToForm(p: Product): ProductForm {
  return {
    name: p.name,
    description: p.description ?? "",
    sku: p.sku ?? "",
    price: p.price != null ? String(p.price) : "",
    currency: p.currency ?? "INR",
    unit: p.unit ?? "Pcs",
  };
}

// ── Status Badge ──────────────────────────────────────────────────────────────
function ActiveBadge({ active }: { active: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap ${
        active
          ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
          : "bg-muted text-muted-foreground"
      }`}
    >
      <span
        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
        style={{ background: active ? "#0F78FF" : "currentColor" }}
      />
      {active ? "Active" : "Inactive"}
    </span>
  );
}

// ── Product Modal ─────────────────────────────────────────────────────────────
function ProductModal({
  product,
  onClose,
}: {
  product?: Product;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const isEdit = !!product;
  const [form, setForm] = useState<ProductForm>(
    product ? productToForm(product) : emptyForm()
  );
  const [errors, setErrors] = useState<Partial<Record<keyof ProductForm, string>>>({});

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      isEdit
        ? api.patch(`/crm/products/${product!.id}`, data)
        : api.post("/crm/products", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-products"] });
      onClose();
    },
  });

  function set<K extends keyof ProductForm>(k: K, v: ProductForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
    if (errors[k]) setErrors((e) => ({ ...e, [k]: undefined }));
  }

  function validate(): boolean {
    const newErrors: Partial<Record<keyof ProductForm, string>> = {};
    if (!form.name.trim()) newErrors.name = "Name is required";
    if (form.price && parseFloat(form.price) < 0) newErrors.price = "Price must be ≥ 0";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  function handleSubmit() {
    if (!validate()) return;
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
    <ModalShell maxWidth="max-w-lg" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold">{isEdit ? "Edit Product" : "New Product"}</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          {/* Name */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Name <span className="text-destructive">*</span>
            </label>
            <input
              className={`${inputCls} ${errors.name ? "border-destructive" : ""}`}
              placeholder="Product name…"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
            />
            {errors.name && (
              <p className="text-[11px] text-destructive mt-1">{errors.name}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Description</label>
            <textarea
              className={`${inputCls} resize-none`}
              rows={2}
              placeholder="Product description…"
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
            />
          </div>

          {/* SKU */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">SKU</label>
            <input
              className={inputCls}
              placeholder="e.g. APP-SHIRT-001"
              value={form.sku}
              onChange={(e) => set("sku", e.target.value)}
            />
          </div>

          {/* Price + Currency */}
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-muted-foreground mb-1">Price</label>
              <input
                className={`${inputCls} ${errors.price ? "border-destructive" : ""}`}
                type="number"
                min="0"
                step="0.01"
                placeholder="0.00"
                value={form.price}
                onChange={(e) => set("price", e.target.value)}
              />
              {errors.price && (
                <p className="text-[11px] text-destructive mt-1">{errors.price}</p>
              )}
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Currency</label>
              <input
                className={inputCls}
                placeholder="INR"
                value={form.currency}
                onChange={(e) => set("currency", e.target.value)}
              />
            </div>
          </div>

          {/* Unit */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Unit</label>
            <SearchableSelect
              options={UNIT_OPTIONS}
              value={form.unit}
              onChange={(v) => set("unit", v)}
              placeholder="Select unit…"
              accent={INDIGO}
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={mutation.isPending}
            className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
            style={{ background: INDIGO }}
          >
            {mutation.isPending ? "Saving…" : isEdit ? "Save Changes" : "Add Product"}
          </button>
        </div>
    </ModalShell>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function ProductsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [modalProduct, setModalProduct] = useState<Product | undefined>(undefined);
  const [showModal, setShowModal] = useState(false);

  const { data: productsData, isLoading } = useQuery({
    queryKey: ["crm-products"],
    queryFn: async () => {
      const res = await api.get("/crm/products");
      return res.data;
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.patch(`/crm/products/${id}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["crm-products"] }),
  });

  const products: Product[] = productsData?.data ?? [];

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    if (!q) return products;
    return products.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.sku ?? "").toLowerCase().includes(q)
    );
  }, [products, search]);

  function openEdit(p: Product) {
    setModalProduct(p);
    setShowModal(true);
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            CRM / PRODUCTS
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Products</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Service and product catalog for quoting.
          </p>
        </div>
        <Can perm="crm.create"><button
          onClick={() => router.push("/crm/products/new")}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: INDIGO }}
        >
          <Plus className="h-4 w-4" /> New Product
        </button></Can>
      </div>

      {/* Search */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            className="rounded-xl border border-input bg-background pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Search by name or SKU…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              ALL PRODUCTS
            </p>
            <p className="text-sm font-medium mt-0.5">
              {filtered.length} record{filtered.length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
            Loading…
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-sm text-muted-foreground gap-2">
            {search ? "No products match your search." : "No products yet — click New Product to add one."}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Name
                  </th>
                  <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    SKU
                  </th>
                  <th className="text-right px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Price
                  </th>
                  <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Unit
                  </th>
                  <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Status
                  </th>
                  <th className="px-6 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map((p) => (
                  <tr key={p.id} className="hover:bg-muted/20 transition-colors">
                    <td className="px-6 py-3">
                      <p className="font-medium">{p.name}</p>
                      {p.description && (
                        <p className="text-[11px] text-muted-foreground mt-0.5 truncate max-w-xs">
                          {p.description}
                        </p>
                      )}
                    </td>
                    <td className="px-6 py-3 text-muted-foreground font-mono text-xs">
                      {p.sku ?? "—"}
                    </td>
                    <td className="px-6 py-3 text-right font-medium tabular-nums">
                      {p.price != null ? fmt(p.price) : "—"}
                    </td>
                    <td className="px-6 py-3 text-muted-foreground">{p.unit ?? "—"}</td>
                    <td className="px-6 py-3">
                      <ActiveBadge active={p.is_active} />
                    </td>
                    <td className="px-6 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <Can perm="crm.edit"><button
                          onClick={() => openEdit(p)}
                          className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                          title="Edit"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button></Can>
                        <Can perm="crm.edit"><button
                          onClick={() =>
                            toggleMutation.mutate({ id: p.id, is_active: !p.is_active })
                          }
                          disabled={toggleMutation.isPending}
                          className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground disabled:opacity-40"
                          title={p.is_active ? "Deactivate" : "Activate"}
                        >
                          {p.is_active ? (
                            <ToggleRight className="h-4 w-4 text-blue-500" />
                          ) : (
                            <ToggleLeft className="h-4 w-4" />
                          )}
                        </button></Can>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <ProductModal
          product={modalProduct}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}
