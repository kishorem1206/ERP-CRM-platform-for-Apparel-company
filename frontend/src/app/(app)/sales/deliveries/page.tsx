"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, X, Printer } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { ModalPortal } from "@/components/shared/modal-portal";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { DatePicker } from "@/components/shared/date-picker";
import { Can } from "@/lib/permissions";

// ── Palette ───────────────────────────────────────────────────────────────────
const TEAL = "#8174F5";

// ── StatusDot ─────────────────────────────────────────────────────────────────
const STATUS_HEX: Record<string, string> = {
  draft: "#94A3B8", planned: "#0049A7", approved: "#0F78FF",
  in_production: "#8174F5", qc: "#A096F7", packing: "#A096F7",
  completed: "#0F78FF", cancelled: "#1D0DB0",
  pending: "#0049A7", received: "#0F78FF", partial: "#A096F7",
  paid: "#0F78FF", unpaid: "#1D0DB0", overdue: "#1D0DB0",
  sent: "#0F78FF", confirmed: "#0F78FF", delivered: "#0F78FF",
  converted: "#0F78FF", domestic: "#0049A7", export: "#0049A7",
  dispatched: "#8174F5",
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
interface Delivery {
  id: string;
  delivery_number: string;
  customer_name: string | null;
  delivery_date: string;
  transporter: string | null;
  lr_number: string | null;
  status: string;
  total_amount: string;
}

interface SOItemOut {
  id: string;
  product_id: string;
  unit_id: string;
  quantity: string;
  unit_price: string;
  product_name?: string;
}

interface StockBalanceRow {
  product_id: string;
  balance: string;
}

const PURPOSE_OPTIONS = [
  { value: "sale", label: "Sale" },
  { value: "sample", label: "Sample" },
  { value: "job_work_return", label: "Job-work return" },
  { value: "branch_transfer", label: "Branch transfer" },
  { value: "other", label: "Other" },
];

const STATUS_FILTERS = [
  { label: "All", value: "" },
  { label: "Draft", value: "draft" },
  { label: "Dispatched", value: "dispatched" },
  { label: "Delivered", value: "delivered" },
  { label: "Cancelled", value: "cancelled" },
];

// Opens the server-generated Packing Slip PDF (ERP Upgrade §4) as a
// download — same blob pattern already used by the Reports Hub PDF export
// (frontend/src/components/reports/report-page.tsx).
async function handlePrintPackingSlip(deliveryId: string, deliveryNumber: string) {
  const res = await api.get(`/sales/deliveries/${deliveryId}/packing-slip`, { responseType: "blob" });
  const blobUrl = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
  const disposition = res.headers["content-disposition"] as string | undefined;
  const match = disposition?.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] ?? `PackingSlip_${deliveryNumber}.pdf`;
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
}

const columns: Column<Record<string, unknown>>[] = [
  { key: "delivery_number", header: "DC Number", sortable: true },
  { key: "customer_name", header: "Customer", render: (row) => (row.customer_name as string) || "—" },
  { key: "delivery_date", header: "Date", sortable: true },
  { key: "transporter", header: "Transporter", render: (row) => (row.transporter as string) || "—" },
  { key: "lr_number", header: "LR #", render: (row) => (row.lr_number as string) || "—" },
  { key: "status", header: "Status", render: (row) => <StatusDot status={row.status as string} /> },
  {
    key: "id", header: "", className: "w-10",
    render: (row) => (
      <button
        onClick={(e) => { e.stopPropagation(); handlePrintPackingSlip(row.id as string, row.delivery_number as string); }}
        className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
        title="Print Packing Slip"
      >
        <Printer className="h-3.5 w-3.5" />
      </button>
    ),
  },
];

// ── Modal ─────────────────────────────────────────────────────────────────────
function AddDeliveryModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [soId, setSoId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [deliveryDate, setDeliveryDate] = useState(today);
  const [purpose, setPurpose] = useState("sale");
  const [transporter, setTransporter] = useState("");
  const [lrNumber, setLrNumber] = useState("");
  const [vehicleNumber, setVehicleNumber] = useState("");
  const [cartonCount, setCartonCount] = useState("");
  const [packageCount, setPackageCount] = useState("");
  const [grossWeight, setGrossWeight] = useState("");
  const [netWeight, setNetWeight] = useState("");
  const [packingMarks, setPackingMarks] = useState("");
  const [notes, setNotes] = useState("");
  const [itemQtys, setItemQtys] = useState<Record<string, string>>({});
  const [itemReturnable, setItemReturnable] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");

  const { data: salesOrders } = useQuery({
    queryKey: ["sales-orders-list"],
    queryFn: async () => (await api.get("/sales/orders?page_size=200&status=confirmed")).data.data ?? [],
  });
  const { data: warehouses } = useQuery({
    queryKey: ["warehouses-list"],
    queryFn: async () => (await api.get("/master/warehouses")).data.data ?? [],
  });
  const { data: soDetail, isLoading: soLoading } = useQuery({
    queryKey: ["so-detail", soId],
    queryFn: async () => {
      if (!soId) return null;
      const res = await api.get(`/sales/orders/${soId}`);
      return res.data.data ?? res.data;
    },
    enabled: !!soId,
  });
  const { data: balances } = useQuery({
    queryKey: ["stock-balance-for-delivery", warehouseId],
    queryFn: async () => (await api.get(`/inventory/balance?warehouse_id=${warehouseId}`)).data.data ?? [],
    enabled: !!warehouseId,
  });

  const soItems: SOItemOut[] = soDetail?.items ?? [];
  const balanceByProduct = new Map<string, number>(
    (balances ?? []).map((b: StockBalanceRow) => [b.product_id, Number(b.balance)]),
  );

  const mut = useMutation({
    mutationFn: () =>
      api.post("/sales/deliveries", {
        sales_order_id: soId,
        warehouse_id: warehouseId,
        delivery_date: deliveryDate,
        purpose,
        transporter: transporter || null,
        lr_number: lrNumber || null,
        vehicle_number: vehicleNumber || null,
        carton_count: cartonCount ? Number(cartonCount) : null,
        package_count: packageCount ? Number(packageCount) : null,
        gross_weight: grossWeight ? Number(grossWeight) : null,
        net_weight: netWeight ? Number(netWeight) : null,
        packing_marks: packingMarks || null,
        notes: notes || null,
        items: soItems.map((it) => ({
          so_item_id: it.id,
          product_id: it.product_id,
          unit_id: it.unit_id,
          quantity: parseFloat(itemQtys[it.id] ?? it.quantity),
          unit_price: parseFloat(String(it.unit_price)),
          returnable: itemReturnable[it.id] ?? true,
        })),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["deliveries"] });
      onClose();
    },
    onError: (e: unknown) => {
      const err = (e as {
        response?: { data?: { error?: string | { message?: string; available?: string; shortage?: string } } };
      })?.response?.data?.error;
      if (typeof err === "string") {
        setError(err);
      } else if (err?.message) {
        const extra = err.shortage && Number(err.shortage) > 0
          ? ` (available: ${err.available}, short by: ${err.shortage})` : "";
        setError(`${err.message}${extra}`);
      } else {
        setError("Failed to create delivery");
      }
    },
  });

  return (
    <ModalPortal>
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
      <div className="bg-card border rounded-lg shadow-xl w-full max-w-2xl mx-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="font-semibold text-base">New Delivery Challan</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
        </div>
        <form
          className="overflow-y-auto p-5 space-y-4"
          onSubmit={(e) => { e.preventDefault(); setError(""); mut.mutate(); }}
        >
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-xs font-medium text-muted-foreground">Sales Order *</label>
              <SearchableSelect
                value={soId}
                onChange={(v) => { setSoId(v); setItemQtys({}); }}
                placeholder="Select confirmed sales order…"
                accent="#8174F5"
                options={[
                  { value: "", label: "Select confirmed sales order…" },
                  ...(salesOrders ?? []).map((s: { id: string; order_number: string; customer_name?: string }) => ({
                    value: s.id,
                    label: s.customer_name ? `${s.order_number} — ${s.customer_name}` : s.order_number,
                  })),
                ]}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Warehouse *</label>
              <SearchableSelect
                value={warehouseId}
                onChange={(v) => setWarehouseId(v)}
                placeholder="Select warehouse…"
                accent="#8174F5"
                options={[
                  { value: "", label: "Select warehouse…" },
                  ...(warehouses ?? []).map((w: { id: string; name: string }) => ({
                    value: w.id,
                    label: w.name,
                  })),
                ]}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Delivery Date *</label>
              <DatePicker value={deliveryDate} onChange={(v) => setDeliveryDate(v)} required />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Purpose</label>
              <SearchableSelect
                value={purpose}
                onChange={(v) => setPurpose(v)}
                placeholder="Purpose of movement…"
                accent="#8174F5"
                options={PURPOSE_OPTIONS}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Transporter</label>
              <input value={transporter} onChange={(e) => setTransporter(e.target.value)}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Transport company name" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">LR Number</label>
              <input value={lrNumber} onChange={(e) => setLrNumber(e.target.value)}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Lorry receipt number" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Vehicle Number</label>
              <input value={vehicleNumber} onChange={(e) => setVehicleNumber(e.target.value)}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="MH12AB1234" />
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Packing Details</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <label className="text-xs font-medium text-muted-foreground">Cartons</label>
                <input type="number" min="0" value={cartonCount} onChange={(e) => setCartonCount(e.target.value)}
                  className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Packages</label>
                <input type="number" min="0" value={packageCount} onChange={(e) => setPackageCount(e.target.value)}
                  className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Gross Weight (kg)</label>
                <input type="number" min="0" step="0.001" value={grossWeight} onChange={(e) => setGrossWeight(e.target.value)}
                  className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Net Weight (kg)</label>
                <input type="number" min="0" step="0.001" value={netWeight} onChange={(e) => setNetWeight(e.target.value)}
                  className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
            </div>
            <div className="mt-3">
              <label className="text-xs font-medium text-muted-foreground">Packing Marks</label>
              <input value={packingMarks} onChange={(e) => setPackingMarks(e.target.value)}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="e.g. Handle with care, This side up" />
            </div>
          </div>

          {soId && (
            <div>
              <span className="text-xs font-medium text-muted-foreground">Items from Sales Order</span>
              {soLoading ? (
                <p className="text-xs text-muted-foreground mt-2">Loading items…</p>
              ) : soItems.length === 0 ? (
                <p className="text-xs text-muted-foreground mt-2">No items found in this order.</p>
              ) : (
                <div className="border rounded mt-2 overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="text-left px-2 py-1.5 font-medium">Product</th>
                        <th className="text-right px-2 py-1.5 font-medium">Ordered</th>
                        <th className="text-right px-2 py-1.5 font-medium">Available</th>
                        <th className="text-right px-2 py-1.5 font-medium">Deliver Qty</th>
                        <th className="text-center px-2 py-1.5 font-medium">Returnable</th>
                      </tr>
                    </thead>
                    <tbody>
                      {soItems.map((it) => {
                        const requested = Number(itemQtys[it.id] ?? it.quantity);
                        const available = warehouseId ? balanceByProduct.get(it.product_id) ?? 0 : null;
                        const short = available !== null && requested > available;
                        return (
                          <tr key={it.id} className="border-t">
                            <td className="px-2 py-1">{it.product_name ?? it.product_id.slice(0, 8)}</td>
                            <td className="px-2 py-1 text-right text-muted-foreground">{it.quantity}</td>
                            <td className="px-2 py-1 text-right" style={short ? { color: "#1D0DB0", fontWeight: 600 } : undefined}>
                              {available === null ? "—" : available}
                              {short && <span className="block text-[10px]">short {(requested - available!).toFixed(2)}</span>}
                            </td>
                            <td className="px-2 py-1">
                              <input
                                type="number" min="0.01" step="0.01"
                                value={itemQtys[it.id] ?? it.quantity}
                                onChange={(e) => setItemQtys((q) => ({ ...q, [it.id]: e.target.value }))}
                                className="w-24 rounded border border-input bg-background px-1.5 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-ring float-right"
                              />
                            </td>
                            <td className="px-2 py-1 text-center">
                              <input
                                type="checkbox"
                                checked={itemReturnable[it.id] ?? true}
                                onChange={(e) => setItemReturnable((r) => ({ ...r, [it.id]: e.target.checked }))}
                              />
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          <div>
            <label className="text-xs font-medium text-muted-foreground">Notes</label>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2}
              className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none" />
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose}
              className="px-4 py-1.5 rounded border border-input text-sm hover:bg-muted">Cancel</button>
            <button type="submit" disabled={mut.isPending || !soId || soItems.length === 0}
              className="px-4 py-1.5 rounded bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-60">
              {mut.isPending ? "Saving…" : "Create Delivery"}
            </button>
          </div>
        </form>
      </div>
    </div>
    </ModalPortal>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function DeliveriesPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [showAdd, setShowAdd] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["deliveries", statusFilter, page],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      if (statusFilter) params.set("status", statusFilter);
      const res = await api.get(`/sales/deliveries?${params}`);
      return res.data;
    },
  });

  const deliveries: Delivery[] = data?.data ?? [];
  const total: number = data?.meta?.total ?? 0;

  return (
    <div className="p-8 space-y-8">
      {showAdd && <AddDeliveryModal onClose={() => setShowAdd(false)} />}

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / DELIVERIES</p>
          <h1 className="text-2xl font-bold tracking-tight">Delivery Challans</h1>
          <p className="text-sm text-muted-foreground mt-1">Dispatch records and outbound inventory movements.</p>
        </div>
        <Can perm="sales.create"><button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: TEAL }}
        >
          <Plus className="h-4 w-4" /> New Delivery
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
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">ALL DELIVERY CHALLANS</p>
            <p className="text-sm font-medium mt-0.5">{total} record{total !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <div className="p-6">
          <DataTable
            columns={columns}
            data={deliveries as unknown as Record<string, unknown>[]}
            loading={isLoading}
            onRowClick={(row) => router.push(`/sales/deliveries/${row.id as string}`)}
            emptyMessage="No delivery challans found"
          />
        </div>
      </div>
    </div>
  );
}
