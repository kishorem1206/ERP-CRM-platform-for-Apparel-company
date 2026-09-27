"use client";
import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, X, Trash2 } from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { ModalShell } from "@/components/shared/modal-shell";

// ── Palette ───────────────────────────────────────────────────────────────────
export const INDIGO = "#0049A7";

export const STATUS_COLORS: Record<string, string> = {
  draft: "bg-muted text-muted-foreground",
  sent: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  accepted: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  declined: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
  expired: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
};

export const fmt = (v: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(v);

const inputCls =
  "w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

// ── Types ─────────────────────────────────────────────────────────────────────
export interface QuoteSummary {
  id: string;
  quote_number: string;
  title: string;
  status: string;
  lead_title: string | null;
  person_name: string | null;
  org_name: string | null;
  total_amount: number | null;
  valid_until: string | null;
  created_at: string;
}

export interface QuoteLineItem {
  id?: string;
  product_id: string | null;
  name: string;
  quantity: number;
  unit_price: number;
  discount_percent: number;
}

export interface QuoteFull extends QuoteSummary {
  lead_id: string | null;
  person_id: string | null;
  organization_id: string | null;
  discount_percent: number;
  notes: string | null;
  terms: string | null;
  assigned_to_name: string | null;
  items: QuoteLineItem[];
}

interface DropdownOption {
  id: string;
  title?: string;
  name?: string;
  full_name?: string;
}

interface Product {
  id: string;
  name: string;
  price: number | null;
  unit: string | null;
}

interface QuoteFormData {
  title: string;
  lead_id: string;
  person_id: string;
  organization_id: string;
  valid_until: string;
  discount_percent: string;
  notes: string;
  terms: string;
  items: QuoteLineItemForm[];
}

interface QuoteLineItemForm {
  _key: string;
  product_id: string;
  name: string;
  quantity: string;
  unit_price: string;
  discount_percent: string;
}

let _keyCounter = 0;
function newKey() {
  return `item-${++_keyCounter}`;
}

function emptyItem(): QuoteLineItemForm {
  return {
    _key: newKey(),
    product_id: "",
    name: "",
    quantity: "1",
    unit_price: "0",
    discount_percent: "0",
  };
}

const emptyForm = (): QuoteFormData => ({
  title: "",
  lead_id: "",
  person_id: "",
  organization_id: "",
  valid_until: "",
  discount_percent: "0",
  notes: "",
  terms: "",
  items: [emptyItem()],
});

function quoteToForm(q: QuoteFull): QuoteFormData {
  return {
    title: q.title,
    lead_id: q.lead_id ?? "",
    person_id: q.person_id ?? "",
    organization_id: q.organization_id ?? "",
    valid_until: q.valid_until ?? "",
    discount_percent: String(q.discount_percent ?? 0),
    notes: q.notes ?? "",
    terms: q.terms ?? "",
    items:
      q.items.length > 0
        ? q.items.map((it) => ({
            _key: newKey(),
            product_id: it.product_id ?? "",
            name: it.name,
            quantity: String(it.quantity),
            unit_price: String(it.unit_price),
            discount_percent: String(it.discount_percent),
          }))
        : [emptyItem()],
  };
}

// ── Computations ──────────────────────────────────────────────────────────────
function itemTotal(row: QuoteLineItemForm): number {
  const qty = parseFloat(row.quantity) || 0;
  const up = parseFloat(row.unit_price) || 0;
  const disc = parseFloat(row.discount_percent) || 0;
  return qty * up * (1 - disc / 100);
}

function computeTotals(items: QuoteLineItemForm[], discountPercent: string) {
  const subtotal = items.reduce((s, r) => s + itemTotal(r), 0);
  const discPct = parseFloat(discountPercent) || 0;
  const discountAmount = subtotal * (discPct / 100);
  const total = subtotal - discountAmount;
  return { subtotal, discountAmount, total };
}

// ── Status Badge ──────────────────────────────────────────────────────────────
export function QuoteStatusBadge({ status }: { status: string }) {
  const cls = STATUS_COLORS[status] ?? "bg-muted text-muted-foreground";
  const label = status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap ${cls}`}>
      {label}
    </span>
  );
}

// ── Quote Form Modal ───────────────────────────────────────────────────────────
export function QuoteFormModal({
  quote,
  onClose,
}: {
  quote?: QuoteFull;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const isEdit = !!quote;
  const [form, setForm] = useState<QuoteFormData>(
    quote ? quoteToForm(quote) : emptyForm()
  );
  const [titleError, setTitleError] = useState("");

  const { data: leadsData } = useQuery({
    queryKey: ["crm-leads-dropdown"],
    queryFn: async () => {
      const res = await api.get("/crm/leads?page_size=200");
      return res.data;
    },
  });

  const { data: personsData } = useQuery({
    queryKey: ["crm-persons-dropdown"],
    queryFn: async () => {
      const res = await api.get("/crm/persons?page_size=200");
      return res.data;
    },
  });

  const { data: orgsData } = useQuery({
    queryKey: ["crm-orgs-dropdown"],
    queryFn: async () => {
      const res = await api.get("/crm/organizations?page_size=200");
      return res.data;
    },
  });

  const { data: productsData } = useQuery({
    queryKey: ["crm-products-dropdown"],
    queryFn: async () => {
      const res = await api.get("/crm/products?is_active=true");
      return res.data;
    },
  });

  const leads: DropdownOption[] = leadsData?.data ?? [];
  const persons: DropdownOption[] = personsData?.data ?? [];
  const orgs: DropdownOption[] = orgsData?.data ?? [];
  const products: Product[] = productsData?.data ?? [];

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      isEdit
        ? api.patch(`/crm/quotes/${quote!.id}`, data)
        : api.post("/crm/quotes", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-quotes"] });
      if (isEdit) queryClient.invalidateQueries({ queryKey: ["crm-quote", quote!.id] });
      onClose();
    },
  });

  function setField<K extends keyof QuoteFormData>(k: K, v: QuoteFormData[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function setItemField(key: string, field: keyof QuoteLineItemForm, value: string) {
    setForm((f) => ({
      ...f,
      items: f.items.map((it) =>
        it._key === key ? { ...it, [field]: value } : it
      ),
    }));
  }

  const handleProductSelect = useCallback(
    (key: string, productId: string) => {
      const product = products.find((p) => p.id === productId);
      setForm((f) => ({
        ...f,
        items: f.items.map((it) =>
          it._key === key
            ? {
                ...it,
                product_id: productId,
                name: product?.name ?? it.name,
                unit_price: product?.price != null ? String(product.price) : it.unit_price,
              }
            : it
        ),
      }));
    },
    [products]
  );

  function addItem() {
    setForm((f) => ({ ...f, items: [...f.items, emptyItem()] }));
  }

  function removeItem(key: string) {
    setForm((f) => ({
      ...f,
      items: f.items.filter((it) => it._key !== key),
    }));
  }

  const { subtotal, discountAmount, total } = computeTotals(form.items, form.discount_percent);

  function handleSubmit() {
    if (!form.title.trim()) {
      setTitleError("Title is required");
      return;
    }
    setTitleError("");
    mutation.mutate({
      title: form.title.trim(),
      lead_id: form.lead_id || undefined,
      person_id: form.person_id || undefined,
      organization_id: form.organization_id || undefined,
      valid_until: form.valid_until || undefined,
      discount_percent: parseFloat(form.discount_percent) || 0,
      notes: form.notes || undefined,
      terms: form.terms || undefined,
      items: form.items
        .filter((it) => it.name.trim())
        .map((it) => ({
          product_id: it.product_id || undefined,
          name: it.name,
          quantity: parseFloat(it.quantity) || 1,
          unit_price: parseFloat(it.unit_price) || 0,
          discount_percent: parseFloat(it.discount_percent) || 0,
        })),
    });
  }

  return (
    <ModalShell maxWidth="max-w-3xl" onClose={onClose}>
      <div className="flex flex-col max-h-[85vh]">
      {/* Header */}
        <div className="flex items-center justify-between p-6 border-b flex-shrink-0">
          <h2 className="text-lg font-semibold">{isEdit ? "Edit Quote" : "New Quote"}</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-6 space-y-5 overflow-y-auto flex-1">
          {/* Title */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Title <span className="text-destructive">*</span>
            </label>
            <input
              className={`${inputCls} ${titleError ? "border-destructive" : ""}`}
              placeholder="Quote title…"
              value={form.title}
              onChange={(e) => {
                setField("title", e.target.value);
                if (titleError) setTitleError("");
              }}
            />
            {titleError && <p className="text-[11px] text-destructive mt-1">{titleError}</p>}
          </div>

          {/* Lead / Person / Org */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Lead</label>
              <SearchableSelect
                options={leads.map((l) => ({ value: l.id, label: l.title ?? l.id }))}
                value={form.lead_id}
                onChange={(v) => setField("lead_id", v)}
                placeholder="Select lead…"
                accent={INDIGO}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Person</label>
              <SearchableSelect
                options={persons.map((p) => ({ value: p.id, label: p.full_name ?? p.name ?? p.id }))}
                value={form.person_id}
                onChange={(v) => setField("person_id", v)}
                placeholder="Select person…"
                accent={INDIGO}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Organization</label>
              <SearchableSelect
                options={orgs.map((o) => ({ value: o.id, label: o.name ?? o.id }))}
                value={form.organization_id}
                onChange={(v) => setField("organization_id", v)}
                placeholder="Select org…"
                accent={INDIGO}
              />
            </div>
          </div>

          {/* Valid Until + Discount */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Valid Until</label>
              <input
                className={inputCls}
                type="date"
                value={form.valid_until}
                onChange={(e) => setField("valid_until", e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">
                Quote Discount %
              </label>
              <input
                className={inputCls}
                type="number"
                min="0"
                max="100"
                step="0.01"
                placeholder="0"
                value={form.discount_percent}
                onChange={(e) => setField("discount_percent", e.target.value)}
              />
            </div>
          </div>

          {/* Notes + Terms */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
              <textarea
                className={`${inputCls} resize-none`}
                rows={3}
                placeholder="Internal notes…"
                value={form.notes}
                onChange={(e) => setField("notes", e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Terms</label>
              <textarea
                className={`${inputCls} resize-none`}
                rows={3}
                placeholder="Payment and delivery terms…"
                value={form.terms}
                onChange={(e) => setField("terms", e.target.value)}
              />
            </div>
          </div>

          {/* Line Items */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                Line Items
              </p>
            </div>

            <div className="border border-border rounded-xl overflow-hidden">
              <div className="divide-y divide-border">
                <div className="grid gap-2 px-3 py-2 bg-muted/30 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
                  style={{ gridTemplateColumns: "minmax(0,2fr) minmax(0,2fr) minmax(0,1fr) minmax(0,1.5fr) minmax(0,1fr) minmax(0,1.5fr) auto" }}>
                  <span>Product</span>
                  <span>Name</span>
                  <span>Qty</span>
                  <span>Unit Price</span>
                  <span>Disc %</span>
                  <span className="text-right">Total</span>
                  <span />
                </div>

                {form.items.map((item) => (
                  <div
                    key={item._key}
                    className="grid gap-2 px-3 py-2 items-center"
                    style={{ gridTemplateColumns: "minmax(0,2fr) minmax(0,2fr) minmax(0,1fr) minmax(0,1.5fr) minmax(0,1fr) minmax(0,1.5fr) auto" }}
                  >
                    <SearchableSelect
                      options={products.map((p) => ({ value: p.id, label: p.name }))}
                      value={item.product_id}
                      onChange={(v) => handleProductSelect(item._key, v)}
                      placeholder="Product…"
                      accent={INDIGO}
                    />
                    <input
                      className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      placeholder="Item name…"
                      value={item.name}
                      onChange={(e) => setItemField(item._key, "name", e.target.value)}
                    />
                    <input
                      className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring tabular-nums"
                      type="number"
                      min="0"
                      step="1"
                      value={item.quantity}
                      onChange={(e) => setItemField(item._key, "quantity", e.target.value)}
                    />
                    <input
                      className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring tabular-nums"
                      type="number"
                      min="0"
                      step="0.01"
                      value={item.unit_price}
                      onChange={(e) => setItemField(item._key, "unit_price", e.target.value)}
                    />
                    <input
                      className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring tabular-nums"
                      type="number"
                      min="0"
                      max="100"
                      step="0.01"
                      value={item.discount_percent}
                      onChange={(e) => setItemField(item._key, "discount_percent", e.target.value)}
                    />
                    <p className="text-sm font-medium text-right tabular-nums">
                      {fmt(itemTotal(item))}
                    </p>
                    <button
                      type="button"
                      onClick={() => removeItem(item._key)}
                      disabled={form.items.length === 1}
                      className="p-1 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-destructive disabled:opacity-30"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>

              <div className="border-t border-border px-3 py-2">
                <button
                  type="button"
                  onClick={addItem}
                  className="flex items-center gap-1.5 text-xs font-semibold transition-colors hover:opacity-80"
                  style={{ color: INDIGO }}
                >
                  <Plus className="h-3.5 w-3.5" /> Add Item
                </button>
              </div>

              <div className="border-t border-border bg-muted/20 px-4 py-3 space-y-1">
                <div className="flex justify-between text-sm text-muted-foreground">
                  <span>Subtotal</span>
                  <span className="tabular-nums">{fmt(subtotal)}</span>
                </div>
                <div className="flex justify-between text-sm text-muted-foreground">
                  <span>
                    Discount{" "}
                    {parseFloat(form.discount_percent) > 0
                      ? `(${parseFloat(form.discount_percent)}%)`
                      : ""}
                  </span>
                  <span className="tabular-nums text-[#8174F5]">
                    -{fmt(discountAmount)}
                  </span>
                </div>
                <div className="flex justify-between text-base font-semibold pt-1 border-t border-border">
                  <span>Total</span>
                  <span className="tabular-nums" style={{ color: INDIGO }}>
                    {fmt(total)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t flex-shrink-0">
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
            {mutation.isPending ? "Saving…" : isEdit ? "Save Changes" : "Create Quote"}
          </button>
        </div>
      </div>
    </ModalShell>
  );
}
