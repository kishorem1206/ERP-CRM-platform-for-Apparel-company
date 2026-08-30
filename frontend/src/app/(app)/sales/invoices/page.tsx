"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { ModalPortal } from "@/components/shared/modal-portal";
import { SearchableSelect } from "@/components/shared/searchable-select";

// ── Palette ───────────────────────────────────────────────────────────────────
const INDIGO = "#5347CE";

// ── StatusDot ─────────────────────────────────────────────────────────────────
const STATUS_HEX: Record<string, string> = {
  draft: "#94A3B8", planned: "#4896FE", approved: "#887CFD",
  in_production: "#16C8C7", qc: "#F59E0B", packing: "#F97316",
  completed: "#10B981", cancelled: "#EF4444",
  pending: "#4896FE", received: "#10B981", partial: "#F59E0B",
  paid: "#10B981", unpaid: "#EF4444", overdue: "#EF4444",
  sent: "#887CFD", confirmed: "#10B981", delivered: "#10B981",
  converted: "#10B981", domestic: "#4896FE", export: "#5347CE",
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
interface Invoice {
  id: string;
  invoice_number: string;
  customer_name: string | null;
  invoice_date: string;
  due_date: string | null;
  status: string;
  total_amount: string;
  paid_amount: string;
  balance_amount: string;
}

const STATUS_FILTERS = [
  { label: "All", value: "" },
  { label: "Unpaid", value: "unpaid" },
  { label: "Partial", value: "partial" },
  { label: "Paid", value: "paid" },
  { label: "Cancelled", value: "cancelled" },
];

const fmt = (v: unknown) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(Number(v));

const columns: Column<Record<string, unknown>>[] = [
  { key: "invoice_number", header: "Invoice #", sortable: true },
  { key: "customer_name", header: "Customer", render: (row) => (row.customer_name as string) || "—" },
  { key: "invoice_date", header: "Date", sortable: true },
  { key: "due_date", header: "Due Date", render: (row) => (row.due_date as string) || "—" },
  { key: "status", header: "Status", render: (row) => <StatusDot status={row.status as string} /> },
  { key: "total_amount", header: "Total", className: "text-right", render: (row) => fmt(row.total_amount) },
  { key: "paid_amount", header: "Paid", className: "text-right", render: (row) => fmt(row.paid_amount) },
  {
    key: "balance_amount",
    header: "Balance",
    className: "text-right font-medium",
    render: (row) => (
      <span className={Number(row.balance_amount) > 0 ? "text-destructive" : "text-green-600"}>
        {fmt(row.balance_amount)}
      </span>
    ),
  },
];

// ── Modal ─────────────────────────────────────────────────────────────────────
function AddInvoiceModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [customerId, setCustomerId] = useState("");
  const [soId, setSoId] = useState("");
  const [deliveryId, setDeliveryId] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(today);
  const [dueDate, setDueDate] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");

  const { data: customers } = useQuery({
    queryKey: ["customers-list"],
    queryFn: async () => (await api.get("/sales/customers?page_size=200")).data.data ?? [],
  });
  const { data: salesOrders } = useQuery({
    queryKey: ["sales-orders-list"],
    queryFn: async () => (await api.get("/sales/orders?page_size=200")).data.data ?? [],
  });
  const { data: deliveries } = useQuery({
    queryKey: ["deliveries-list"],
    queryFn: async () => (await api.get("/sales/deliveries?page_size=200")).data.data ?? [],
  });

  const mut = useMutation({
    mutationFn: () =>
      api.post("/sales/invoices", {
        customer_id: customerId,
        sales_order_id: soId || null,
        delivery_id: deliveryId || null,
        invoice_date: invoiceDate,
        due_date: dueDate || null,
        notes: notes || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["invoices"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Failed to create invoice");
    },
  });

  return (
    <ModalPortal>
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
      <div className="bg-card border rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="font-semibold text-base">New Invoice</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
        </div>
        <form
          className="p-5 space-y-3"
          onSubmit={(e) => { e.preventDefault(); setError(""); mut.mutate(); }}
        >
          <div>
            <label className="text-xs font-medium text-muted-foreground">Customer *</label>
            <SearchableSelect
              value={customerId}
              onChange={(v) => setCustomerId(v)}
              placeholder="Select customer…"
              accent="#5347CE"
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
            <label className="text-xs font-medium text-muted-foreground">Sales Order (optional)</label>
            <SearchableSelect
              value={soId}
              onChange={(v) => setSoId(v)}
              placeholder="None"
              accent="#5347CE"
              options={[
                { value: "", label: "None" },
                ...(salesOrders ?? []).map((s: { id: string; order_number: string }) => ({
                  value: s.id,
                  label: s.order_number,
                })),
              ]}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Delivery Challan (optional)</label>
            <SearchableSelect
              value={deliveryId}
              onChange={(v) => setDeliveryId(v)}
              placeholder="None"
              accent="#5347CE"
              options={[
                { value: "", label: "None" },
                ...(deliveries ?? []).map((d: { id: string; delivery_number: string }) => ({
                  value: d.id,
                  label: d.delivery_number,
                })),
              ]}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Invoice Date *</label>
              <input required type="date" value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Due Date</label>
              <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
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
              {mut.isPending ? "Saving…" : "Create Invoice"}
            </button>
          </div>
        </form>
      </div>
    </div>
    </ModalPortal>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function InvoicesPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [showAdd, setShowAdd] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["invoices", statusFilter, page],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      if (statusFilter) params.set("status", statusFilter);
      const res = await api.get(`/sales/invoices?${params}`);
      return res.data;
    },
  });

  const invoices: Invoice[] = data?.data ?? [];
  const total: number = data?.meta?.total ?? 0;

  return (
    <div className="p-8 space-y-8">
      {showAdd && <AddInvoiceModal onClose={() => setShowAdd(false)} />}

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / INVOICES</p>
          <h1 className="text-2xl font-bold tracking-tight">Invoices</h1>
          <p className="text-sm text-muted-foreground mt-1">GST invoices — track payments and outstanding balances.</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: INDIGO }}
        >
          <Plus className="h-4 w-4" /> New Invoice
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
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">ALL INVOICES</p>
            <p className="text-sm font-medium mt-0.5">{total} record{total !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <div className="p-6">
          <DataTable
            columns={columns}
            data={invoices as unknown as Record<string, unknown>[]}
            loading={isLoading}
            emptyMessage="No invoices found"
          />
        </div>
      </div>
    </div>
  );
}
