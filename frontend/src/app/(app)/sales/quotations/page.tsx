"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, X } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { ModalPortal } from "@/components/shared/modal-portal";
import { SearchableSelect } from "@/components/shared/searchable-select";

// ── Palette ───────────────────────────────────────────────────────────────────
const LAVENDER = "#887CFD";

// ── StatusDot ─────────────────────────────────────────────────────────────────
const STATUS_HEX: Record<string, string> = {
  draft: "#94A3B8", planned: "#4896FE", approved: "#887CFD",
  in_production: "#16C8C7", qc: "#F59E0B", packing: "#F97316",
  completed: "#10B981", cancelled: "#EF4444",
  pending: "#4896FE", received: "#10B981", partial: "#F59E0B",
  paid: "#10B981", unpaid: "#EF4444", overdue: "#EF4444",
  sent: "#887CFD", confirmed: "#10B981", delivered: "#10B981",
  converted: "#10B981", domestic: "#4896FE", export: "#5347CE",
  rejected: "#EF4444",
};

function StatusDot({ status }: { status: string }) {
  const color = STATUS_HEX[status?.toLowerCase()] ?? "#94A3B8";
  const label = status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"
      style={{ background: `${color}18`, color }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {label}
    </span>
  );
}

// ── Types ─────────────────────────────────────────────────────────────────────
interface Quotation {
  id: string;
  quotation_number: string;
  customer_name: string | null;
  quotation_date: string;
  valid_until: string | null;
  status: string;
  total_amount: string;
}

interface QItem {
  product_id: string;
  unit_id: string;
  quantity: string;
  unit_price: string;
  gst_rate: string;
  hsn_code: string;
}

const STATUS_FILTERS = [
  { label: "All", value: "" },
  { label: "Draft", value: "draft" },
  { label: "Sent", value: "sent" },
  { label: "Approved", value: "approved" },
  { label: "Converted", value: "converted" },
  { label: "Rejected", value: "rejected" },
];

const columns: Column<Record<string, unknown>>[] = [
  { key: "quotation_number", header: "Number", sortable: true },
  { key: "customer_name", header: "Customer", render: (row) => (row.customer_name as string) || "—" },
  { key: "quotation_date", header: "Date", sortable: true },
  { key: "valid_until", header: "Valid Until", render: (row) => (row.valid_until as string) || "—" },
  { key: "status", header: "Status", render: (row) => <StatusDot status={row.status as string} /> },
  {
    key: "total_amount",
    header: "Total",
    className: "text-right",
    render: (row) =>
      new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(Number(row.total_amount)),
  },
];

const emptyItem = (): QItem => ({ product_id: "", unit_id: "", quantity: "1", unit_price: "0", gst_rate: "0", hsn_code: "" });

// ── Modal ─────────────────────────────────────────────────────────────────────
function AddQuotationModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [customerId, setCustomerId] = useState("");
  const [quotationDate, setQuotationDate] = useState(today);
  const [validUntil, setValidUntil] = useState("");
  const [notes, setNotes] = useState("");
  const [intrastate, setIntrastate] = useState(true);
  const [items, setItems] = useState<QItem[]>([emptyItem()]);
  const [error, setError] = useState("");

  const { data: customers } = useQuery({
    queryKey: ["customers-list"],
    queryFn: async () => (await api.get("/sales/customers?page_size=200")).data.data ?? [],
  });
  const { data: products } = useQuery({
    queryKey: ["products-list"],
    queryFn: async () => (await api.get("/products?page_size=200")).data.data ?? [],
  });
  const { data: units } = useQuery({
    queryKey: ["units-list"],
    queryFn: async () => (await api.get("/master/units")).data.data ?? [],
  });

  const mut = useMutation({
    mutationFn: () =>
      api.post("/sales/quotations", {
        customer_id: customerId,
        quotation_date: quotationDate,
        valid_until: validUntil || null,
        notes: notes || null,
        intrastate,
        items: items.map((it) => ({
          product_id: it.product_id,
          unit_id: it.unit_id,
          quantity: parseFloat(it.quantity),
          unit_price: parseFloat(it.unit_price),
          gst_rate: parseFloat(it.gst_rate),
          hsn_code: it.hsn_code || null,
          sort_order: 0,
        })),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["quotations"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Failed to create quotation");
    },
  });

  const updateItem = (i: number, k: keyof QItem, v: string) =>
    setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, [k]: v } : it)));

  return (
    <ModalPortal>
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
      <div className="bg-card border rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto ">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="font-semibold text-base">New Quotation</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
        </div>
        <form
          className="overflow-y-auto p-5 space-y-4"
          onSubmit={(e) => { e.preventDefault(); setError(""); mut.mutate(); }}
        >
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-xs font-medium text-muted-foreground">Customer *</label>
              <SearchableSelect
                value={customerId}
                onChange={(v) => setCustomerId(v)}
                placeholder="Select customer…"
                accent="#887CFD"
                options={[
                  { value: "", label: "Select customer…" },
                  ...(customers ?? []).map((c: { id: string; legal_name: string }) => ({
                    value: c.id,
                    label: c.legal_name,
                  })),
                ]}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Date *</label>
              <input required type="date" value={quotationDate} onChange={(e) => setQuotationDate(e.target.value)}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Valid Until</label>
              <input type="date" value={validUntil} onChange={(e) => setValidUntil(e.target.value)}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="intrastate-qt" checked={intrastate} onChange={(e) => setIntrastate(e.target.checked)}
              className="rounded border-input" />
            <label htmlFor="intrastate-qt" className="text-sm">Intrastate (CGST+SGST)</label>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground">Items *</span>
              <button type="button" onClick={() => setItems((p) => [...p, emptyItem()])}
                className="text-xs text-primary hover:underline">+ Add item</button>
            </div>
            <div className="border rounded overflow-auto">
              <table className="w-full text-xs min-w-[600px]">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left px-2 py-1.5 font-medium">Product</th>
                    <th className="text-left px-2 py-1.5 font-medium">Unit</th>
                    <th className="text-right px-2 py-1.5 font-medium">Qty</th>
                    <th className="text-right px-2 py-1.5 font-medium">Price</th>
                    <th className="text-right px-2 py-1.5 font-medium">GST%</th>
                    <th className="text-left px-2 py-1.5 font-medium">HSN</th>
                    <th className="w-6"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it, i) => (
                    <tr key={i} className="border-t">
                      <td className="px-2 py-1">
                        <SearchableSelect
                          value={it.product_id}
                          onChange={(v) => updateItem(i, "product_id", v)}
                          placeholder="Select…"
                          accent="#887CFD"
                          options={[
                            { value: "", label: "Select…" },
                            ...(products ?? []).map((p: { id: string; name: string }) => ({
                              value: p.id,
                              label: p.name,
                            })),
                          ]}
                        />
                      </td>
                      <td className="px-2 py-1">
                        <SearchableSelect
                          value={it.unit_id}
                          onChange={(v) => updateItem(i, "unit_id", v)}
                          placeholder="Unit…"
                          accent="#887CFD"
                          options={[
                            { value: "", label: "Unit…" },
                            ...(units ?? []).map((u: { id: string; symbol: string }) => ({
                              value: u.id,
                              label: u.symbol,
                            })),
                          ]}
                        />
                      </td>
                      <td className="px-2 py-1">
                        <input type="number" min="0.01" step="0.01" required value={it.quantity}
                          onChange={(e) => updateItem(i, "quantity", e.target.value)}
                          className="w-20 rounded border border-input bg-background px-1.5 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-ring" />
                      </td>
                      <td className="px-2 py-1">
                        <input type="number" min="0" step="0.01" required value={it.unit_price}
                          onChange={(e) => updateItem(i, "unit_price", e.target.value)}
                          className="w-24 rounded border border-input bg-background px-1.5 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-ring" />
                      </td>
                      <td className="px-2 py-1">
                        <input type="number" min="0" max="28" step="0.1" value={it.gst_rate}
                          onChange={(e) => updateItem(i, "gst_rate", e.target.value)}
                          className="w-16 rounded border border-input bg-background px-1.5 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-ring" />
                      </td>
                      <td className="px-2 py-1">
                        <input value={it.hsn_code} onChange={(e) => updateItem(i, "hsn_code", e.target.value)}
                          className="w-20 rounded border border-input bg-background px-1.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                          placeholder="6111" />
                      </td>
                      <td className="px-1 py-1">
                        {items.length > 1 && (
                          <button type="button" onClick={() => setItems((p) => p.filter((_, idx) => idx !== i))}
                            className="text-muted-foreground hover:text-destructive">
                            <Trash2 className="h-3 w-3" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground">Notes</label>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2}
              className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none" />
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose}
              className="px-4 py-1.5 rounded border border-input text-sm hover:bg-muted">Cancel</button>
            <button type="submit" disabled={mut.isPending}
              className="px-4 py-1.5 rounded bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-60">
              {mut.isPending ? "Saving…" : "Create Quotation"}
            </button>
          </div>
        </form>
      </div>
    </div>
    </ModalPortal>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function QuotationsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [showAdd, setShowAdd] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["quotations", statusFilter, page],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      if (statusFilter) params.set("status", statusFilter);
      const res = await api.get(`/sales/quotations?${params}`);
      return res.data;
    },
  });

  const quotations: Quotation[] = data?.data ?? [];
  const total: number = data?.meta?.total ?? 0;

  return (
    <div className="p-8 space-y-8">
      {showAdd && <AddQuotationModal onClose={() => setShowAdd(false)} />}

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / QUOTATIONS</p>
          <h1 className="text-2xl font-bold tracking-tight">Quotations</h1>
          <p className="text-sm text-muted-foreground mt-1">Price quotes sent to buyers — track status and conversions.</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: LAVENDER }}
        >
          <Plus className="h-4 w-4" /> New Quotation
        </button>
      </div>

      {/* Filter tab strip */}
      <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit flex-wrap">
        {STATUS_FILTERS.map((t) => (
          <button
            key={t.value}
            onClick={() => { setStatusFilter(t.value); setPage(1); }}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
              statusFilter === t.value
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">ALL QUOTATIONS</p>
            <p className="text-sm font-medium mt-0.5">{total} record{total !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <div className="p-6">
          <DataTable
            columns={columns}
            data={quotations as unknown as Record<string, unknown>[]}
            loading={isLoading}
            emptyMessage="No quotations found"
          />
        </div>
      </div>
    </div>
  );
}
