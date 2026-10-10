"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, X } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { ModalPortal } from "@/components/shared/modal-portal";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { DatePicker } from "@/components/shared/date-picker";
import { Can } from "@/lib/permissions";

// ── Palette ───────────────────────────────────────────────────────────────────
const BLUE = "#0049A7";

// ── StatusDot ─────────────────────────────────────────────────────────────────
const STATUS_HEX: Record<string, string> = {
  draft: "#94A3B8", planned: "#0049A7", approved: "#0F78FF",
  in_production: "#8174F5", qc: "#A096F7", packing: "#A096F7",
  completed: "#0F78FF", cancelled: "#1D0DB0",
  pending: "#0049A7", received: "#0F78FF", partial: "#A096F7",
  paid: "#0F78FF", unpaid: "#1D0DB0", overdue: "#1D0DB0",
  sent: "#0F78FF", confirmed: "#0F78FF", delivered: "#0F78FF",
  converted: "#0F78FF", domestic: "#0049A7", export: "#0049A7",
  processing: "#A096F7",
};

function StatusDot({ status }: { status: string }) {
  const color = STATUS_HEX[status?.toLowerCase()] ?? "#94A3B8";
  const label = status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap"
      style={{ background: `${color}18`, color }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {label}
    </span>
  );
}

// ── Types ─────────────────────────────────────────────────────────────────────
interface SalesOrder {
  id: string;
  order_number: string;
  customer_name: string | null;
  order_date: string;
  expected_delivery: string | null;
  status: string;
  total_amount: string;
}

// This app's error envelope is {"error": "..."} or {"error": {"message": "..."}}
// (see backend/app/main.py's exception handlers) - not FastAPI's default
// {"detail": ...}, which only basic Pydantic validation errors still use.
// Reading only `.detail` (as this modal previously did) silently swallows
// every business-rule error, e.g. the PO quantity tolerance message below.
function parseApiError(e: unknown, fallback: string): string {
  const data = (e as { response?: { data?: Record<string, unknown> } })?.response?.data;
  if (!data) return fallback;
  const err = data.error;
  if (typeof err === "string") return err;
  if (err && typeof (err as { message?: string }).message === "string")
    return (err as { message: string }).message;
  const detail = data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0)
    return (detail as Array<{ msg: string }>)[0]?.msg ?? fallback;
  return fallback;
}

interface StockCheck {
  ordered_quantity: string;
  available_stock: string;
  committed_quantity: string;
  remaining_quantity: string;
  can_fulfill: boolean;
}

interface SOItem {
  product_id: string;
  unit_id: string;
  quantity: string;
  unit_price: string;
  gst_rate: string;
  hsn_code: string;
  price_source: string;
  stock_check: StockCheck | null;
}

const STATUS_FILTERS = [
  { label: "All", value: "" },
  { label: "Confirmed", value: "confirmed" },
  { label: "Processing", value: "processing" },
  { label: "Partial", value: "partial" },
  { label: "Completed", value: "completed" },
  { label: "Cancelled", value: "cancelled" },
];

const columns: Column<Record<string, unknown>>[] = [
  { key: "order_number", header: "Order #", sortable: true },
  { key: "customer_name", header: "Customer", render: (row) => (row.customer_name as string) || "—" },
  { key: "order_date", header: "Order Date", sortable: true },
  { key: "expected_delivery", header: "Expected", render: (row) => (row.expected_delivery as string) || "—" },
  { key: "status", header: "Status", render: (row) => <StatusDot status={row.status as string} /> },
  {
    key: "total_amount",
    header: "Total",
    className: "text-right",
    render: (row) =>
      new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(Number(row.total_amount)),
  },
];

const emptyItem = (): SOItem => ({ product_id: "", unit_id: "", quantity: "1", unit_price: "0", gst_rate: "0", hsn_code: "", price_source: "", stock_check: null });

// ── Modal ─────────────────────────────────────────────────────────────────────
function AddSOModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [customerId, setCustomerId] = useState("");
  const [orderDate, setOrderDate] = useState(today);
  const [expectedDelivery, setExpectedDelivery] = useState("");
  const [notes, setNotes] = useState("");
  const [intrastate, setIntrastate] = useState(true);
  const [customerPoNumber, setCustomerPoNumber] = useState("");
  const [customerPoQuantity, setCustomerPoQuantity] = useState("");
  const [poTolerancePct, setPoTolerancePct] = useState("5");
  const [items, setItems] = useState<SOItem[]>([emptyItem()]);
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
      api.post("/sales/orders", {
        customer_id: customerId,
        order_date: orderDate,
        expected_delivery: expectedDelivery || null,
        notes: notes || null,
        intrastate,
        customer_po_number: customerPoNumber || null,
        customer_po_quantity: customerPoQuantity ? Number(customerPoQuantity) : null,
        po_tolerance_pct: poTolerancePct ? Number(poTolerancePct) : 5,
        items: items.map((it) => ({
          product_id: it.product_id,
          unit_id: it.unit_id,
          quantity: parseFloat(it.quantity),
          unit_price: parseFloat(it.unit_price),
          gst_rate: parseFloat(it.gst_rate),
          hsn_code: it.hsn_code || null,
        })),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sales-orders"] });
      onClose();
    },
    onError: (e: unknown) => setError(parseApiError(e, "Failed to create sales order")),
  });

  const updateItem = (i: number, k: keyof SOItem, v: string) =>
    setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, [k]: v } : it)));

  // Selecting a product suggests its default price (customer-specific list ->
  // generic list -> Wholesale Price -> MRP fallback) via the shared pricing
  // resolver. Never forces the value — only fills it while still at the "0"
  // default, so a price the user already edited is never clobbered.
  const handleProductChange = (i: number, productId: string) => {
    const unit = (products ?? []).find((p: { id: string; unit_id?: string | null }) => p.id === productId)?.unit_id;
    setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, product_id: productId, unit_id: unit || it.unit_id, price_source: "", stock_check: null } : it)));
    if (!productId) return;
    api
      .get("/sales/price-lists/resolve", {
        params: {
          product_id: productId,
          customer_id: customerId || undefined,
          quantity: 1,
          on_date: new Date().toISOString().slice(0, 10),
        },
      })
      .then((res) => {
        const result = res.data?.data;
        if (!result || result.source === "not_found") return;
        setItems((prev) =>
          prev.map((it, idx) =>
            idx === i && it.unit_price === "0"
              ? { ...it, unit_price: String(result.unit_price), price_source: result.source }
              : it
          )
        );
      })
      .catch(() => undefined);
    runStockCheck(i, productId, items[i]?.quantity ?? "1");
  };

  // Informational only (ERP Upgrade §2) — shows Ordered/Available/Committed/
  // Remaining so the user can judge fulfillability before confirming; never
  // blocks the order. Re-run on product change and on quantity blur (not
  // every keystroke, to avoid a network call per digit typed).
  const runStockCheck = (i: number, productId: string, quantity: string) => {
    if (!productId || !quantity || Number(quantity) <= 0) return;
    api
      .get("/sales/orders/stock-check", { params: { product_id: productId, quantity } })
      .then((res) => {
        const result = res.data?.data as StockCheck | undefined;
        if (!result) return;
        setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, stock_check: result } : it)));
      })
      .catch(() => undefined);
  };

  return (
    <ModalPortal>
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
      <div className="bg-card border rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto ">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="font-semibold text-base">New Sales Order</h2>
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
                accent="#0049A7"
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
              <label className="text-xs font-medium text-muted-foreground">Order Date *</label>
              <DatePicker value={orderDate} onChange={(v) => setOrderDate(v)} required />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Expected Delivery</label>
              <DatePicker value={expectedDelivery} onChange={(v) => setExpectedDelivery(v)} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="intrastate-so" checked={intrastate} onChange={(e) => setIntrastate(e.target.checked)}
              className="rounded border-input" />
            <label htmlFor="intrastate-so" className="text-sm">Intrastate (CGST+SGST)</label>
          </div>

          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Customer PO Reference (optional)</p>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs font-medium text-muted-foreground">PO Number</label>
                <input value={customerPoNumber} onChange={(e) => setCustomerPoNumber(e.target.value)}
                  className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">PO Quantity</label>
                <input type="number" min="0" step="0.01" value={customerPoQuantity} onChange={(e) => setCustomerPoQuantity(e.target.value)}
                  className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Tolerance %</label>
                <input type="number" min="0" step="0.1" value={poTolerancePct} onChange={(e) => setPoTolerancePct(e.target.value)}
                  className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
            </div>
            {customerPoQuantity && (
              <p className="text-[11px] text-muted-foreground mt-1.5">
                Order quantity must stay within ±{poTolerancePct || 5}% of {customerPoQuantity} to be accepted.
              </p>
            )}
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
                          onChange={(v) => handleProductChange(i, v)}
                          placeholder="Select…"
                          accent="#0049A7"
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
                          accent="#0049A7"
                          options={[
                            { value: "", label: "Unit…" },
                            ...(units ?? []).map((u: { id: string; abbreviation: string }) => ({
                              value: u.id,
                              label: u.abbreviation,
                            })),
                          ]}
                        />
                      </td>
                      <td className="px-2 py-1">
                        <input type="number" min="0.01" step="0.01" required value={it.quantity}
                          onChange={(e) => updateItem(i, "quantity", e.target.value)}
                          onBlur={(e) => runStockCheck(i, it.product_id, e.target.value)}
                          className="w-20 rounded border border-input bg-background px-1.5 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-ring" />
                        {it.stock_check && (
                          <p className={`text-[10px] mt-0.5 whitespace-nowrap ${it.stock_check.can_fulfill ? "text-muted-foreground" : "text-amber-600"}`}>
                            {Number(it.stock_check.available_stock).toLocaleString("en-IN")} avail ·{" "}
                            {Number(it.stock_check.committed_quantity).toLocaleString("en-IN")} committed ·{" "}
                            {Number(it.stock_check.remaining_quantity).toLocaleString("en-IN")} remaining
                          </p>
                        )}
                      </td>
                      <td className="px-2 py-1">
                        <input type="number" min="0" step="0.01" required value={it.unit_price}
                          onChange={(e) => setItems((prev) => prev.map((row, idx) => (idx === i ? { ...row, unit_price: e.target.value, price_source: "" } : row)))}
                          className="w-24 rounded border border-input bg-background px-1.5 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-ring" />
                        {it.price_source && (
                          <p className="text-[10px] text-muted-foreground mt-0.5 whitespace-nowrap">
                            Suggested from {it.price_source.replace(/_/g, " ")}
                          </p>
                        )}
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
              {mut.isPending ? "Saving…" : "Create Order"}
            </button>
          </div>
        </form>
      </div>
    </div>
    </ModalPortal>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function SalesOrdersPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [showAdd, setShowAdd] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["sales-orders", statusFilter, page],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      if (statusFilter) params.set("status", statusFilter);
      const res = await api.get(`/sales/orders?${params}`);
      return res.data;
    },
  });

  const orders: SalesOrder[] = data?.data ?? [];
  const total: number = data?.meta?.total ?? 0;

  return (
    <div className="p-8 space-y-8">
      {showAdd && <AddSOModal onClose={() => setShowAdd(false)} />}

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / ORDERS</p>
          <h1 className="text-2xl font-bold tracking-tight">Sales Orders</h1>
          <p className="text-sm text-muted-foreground mt-1">Confirmed orders from buyers — track delivery and status.</p>
        </div>
        <Can perm="sales.create"><button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: BLUE }}
        >
          <Plus className="h-4 w-4" /> New Order
        </button></Can>
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
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">ALL ORDERS</p>
            <p className="text-sm font-medium mt-0.5">{total} record{total !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <div className="p-6">
          <DataTable
            columns={columns}
            data={orders as unknown as Record<string, unknown>[]}
            loading={isLoading}
            onRowClick={(row) => router.push(`/sales/orders/${row.id as string}`)}
            emptyMessage="No sales orders found"
          />
        </div>
      </div>
    </div>
  );
}
