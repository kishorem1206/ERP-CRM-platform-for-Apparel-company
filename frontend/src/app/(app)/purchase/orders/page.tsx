"use client";
import { useRouter } from "next/navigation";
import { Fragment, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Plus, Trash2, X } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { StatusBadge } from "@/components/shared/status-badge";
import { ModalPortal } from "@/components/shared/modal-portal";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { DatePicker } from "@/components/shared/date-picker";
import { Can, usePermissions } from "@/lib/permissions";
import { parseApiError } from "@/lib/api-error";
import { fetchLastRate, lastRateNote } from "@/lib/last-rate";
import { PO_STATUS_LABEL, rangeText } from "@/lib/po-tolerance";

const BLUE = "#0049A7";

interface PurchaseOrder {
  id: string;
  po_number: string;
  vendor_name: string | null;
  order_date: string;
  expected_date: string | null;
  status: string;
  total_amount: string;
}

interface LineItem {
  product_id: string;
  unit_id: string;
  ordered_qty: string;
  unit_price: string;
  gst_rate: string;
  tolerance_pct: string;
  rate_note?: string;
}

const STATUS_FILTERS = [
  { label: "All", value: "" },
  { label: "Draft", value: "draft" },
  { label: "Approved", value: "approved" },
  { label: "Partial", value: "partial" },
  { label: "Received", value: "received" },
  { label: "Awaiting close approval", value: "close_requested" },
  { label: "Closed", value: "closed" },
  { label: "Cancelled", value: "cancelled" },
];

const baseColumns: Column<Record<string, unknown>>[] = [
  { key: "po_number", header: "PO Number", sortable: true },
  { key: "vendor_name", header: "Vendor", sortable: true, render: (row) => (row.vendor_name as string) || "—" },
  { key: "order_date", header: "Order Date", sortable: true },
  { key: "expected_date", header: "Expected", render: (row) => (row.expected_date as string) || "—" },
  { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status as string} label={PO_STATUS_LABEL[row.status as string]} /> },
  {
    key: "total_amount",
    header: "Total",
    className: "text-right",
    render: (row) =>
      new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(Number(row.total_amount)),
  },
];

const emptyLine = (): LineItem => ({ product_id: "", unit_id: "", ordered_qty: "1", unit_price: "0", gst_rate: "0", tolerance_pct: "" });

const inr = (v: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(v);
const lineAmount = (it: LineItem) =>
  (parseFloat(it.ordered_qty) || 0) * (parseFloat(it.unit_price) || 0) * (1 + (parseFloat(it.gst_rate) || 0) / 100);

function AddPOModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [vendorId, setVendorId] = useState("");
  const [orderDate, setOrderDate] = useState(today);
  const [expectedDate, setExpectedDate] = useState("");
  const [notes, setNotes] = useState("");
  const [intrastate, setIntrastate] = useState(true);
  const [items, setItems] = useState<LineItem[]>([emptyLine()]);
  const [error, setError] = useState("");
  const [tolFocus, setTolFocus] = useState<number | null>(null);
  const { can } = usePermissions();
  const canApprove = can("purchase.approve");

  const { data: vendors } = useQuery({
    queryKey: ["vendors-list"],
    queryFn: async () => (await api.get("/purchase/vendors?page_size=200")).data.data as { id: string; name: string; supplies_product_types: string[] | null }[],
  });
  const { data: products } = useQuery({
    queryKey: ["products-list"],
    queryFn: async () => (await api.get("/products?page_size=200")).data.data as { id: string; name: string; product_type: string; unit_id: string | null; gst_rate?: number | string | null }[],
  });
  const selectedVendor = (vendors ?? []).find((v) => v.id === vendorId);
  const availableProducts = selectedVendor?.supplies_product_types?.length
    ? (products ?? []).filter((p) => selectedVendor.supplies_product_types!.includes(p.product_type))
    : (products ?? []);
  const { data: units } = useQuery({
    queryKey: ["units-list"],
    queryFn: async () => (await api.get("/master/units")).data.data ?? [],
  });

  // A PO starts as a draft; GRNs can only be booked against an approved one,
  // so "Create & Approve" saves the extra trip to the PO page.
  const mut = useMutation({
    mutationFn: async (approve: boolean) => {
      const res = await api.post("/purchase/orders", {
        vendor_id: vendorId,
        order_date: orderDate,
        expected_date: expectedDate || null,
        notes: notes || null,
        intrastate,
        items: items.map((it) => ({
          product_id: it.product_id,
          unit_id: it.unit_id,
          ordered_qty: parseFloat(it.ordered_qty),
          unit_price: parseFloat(it.unit_price),
          gst_rate: parseFloat(it.gst_rate),
          tolerance_pct: it.tolerance_pct === "" ? null : parseFloat(it.tolerance_pct),
        })),
      });
      if (approve) await api.post(`/purchase/orders/${res.data.data.id}/approve`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["purchase-orders"] });
      onClose();
    },
    onError: (e: unknown) => {
      qc.invalidateQueries({ queryKey: ["purchase-orders"] });
      setError(parseApiError(e, "Failed to create purchase order"));
    },
  });
  const orderTotal = items.reduce((sum, it) => sum + lineAmount(it), 0);
  const unitAbbr = (unitId: string) =>
    (units ?? []).find((u: { id: string; abbreviation: string }) => u.id === unitId)?.abbreviation as string | undefined;

  const updateItem = (i: number, k: keyof LineItem, v: string) =>
    setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, [k]: v } : it)));

  // Picking a product fills its unit, GST and the latest rate paid for it.
  const pickProduct = async (i: number, productId: string) => {
    const product = (products ?? []).find((p) => p.id === productId);
    setItems((prev) => prev.map((it, idx) => (idx === i ? {
      ...it, product_id: productId, unit_id: product?.unit_id ?? it.unit_id, rate_note: undefined,
      gst_rate: product?.gst_rate != null ? String(Number(product.gst_rate)) : it.gst_rate,
    } : it)));
    if (!productId) return;
    const rate = await fetchLastRate(productId, vendorId);
    if (!rate) return;
    setItems((prev) => prev.map((it, idx) =>
      idx === i && it.product_id === productId
        ? { ...it, unit_price: String(Number(rate.unit_price)), rate_note: lastRateNote(rate) }
        : it));
  };

  return (
    <ModalPortal>
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
      <div className="bg-card border rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="font-semibold text-base">New Purchase Order</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
        </div>
        <form
          className="overflow-y-auto p-5 space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            setError("");
            const submitter = (e.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
            mut.mutate(submitter?.value === "approve");
          }}
        >
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-xs font-medium text-muted-foreground">Vendor *</label>
              <div className="mt-1">
                <SearchableSelect
                  value={vendorId}
                  onChange={setVendorId}
                  placeholder="Select vendor…"
                  accent={BLUE}
                  options={(vendors ?? []).map((v: { id: string; name: string }) => ({
                    value: v.id,
                    label: v.name,
                  }))}
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Order Date *</label>
              <DatePicker value={orderDate} onChange={(v) => setOrderDate(v)} required />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Expected Date</label>
              <DatePicker value={expectedDate} onChange={(v) => setExpectedDate(v)} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="intrastate-po" checked={intrastate} onChange={(e) => setIntrastate(e.target.checked)}
              className="rounded border-input" />
            <label htmlFor="intrastate-po" className="text-sm">Intrastate (CGST+SGST)</label>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground">Line Items *</span>
              <button type="button" onClick={() => setItems((p) => [...p, emptyLine()])}
                className="text-xs text-primary hover:underline">+ Add item</button>
            </div>
            <div className="border rounded overflow-x-auto">
              <table className="w-full min-w-[840px] text-xs">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left px-2 py-1.5 font-medium">Product</th>
                    <th className="text-left px-2 py-1.5 font-medium">Unit</th>
                    <th className="text-right px-2 py-1.5 font-medium">Qty</th>
                    <th className="text-right px-2 py-1.5 font-medium">Price</th>
                    <th className="text-right px-2 py-1.5 font-medium">GST%</th>
                    <th className="text-right px-2 py-1.5 font-medium" title="How far the received quantity may be from the ordered quantity, either way, before closing the PO needs admin approval. Internal only — not printed on the PO.">Tolerance ±%</th>
                    <th className="text-right px-2 py-1.5 font-medium">Amount</th>
                    <th className="w-6"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it, i) => (
                    <Fragment key={i}>
                    <tr className="border-t">
                      <td className="px-2 py-1 min-w-[220px]">
                        <SearchableSelect
                          value={it.product_id}
                          onChange={(v) => pickProduct(i, v)}
                          placeholder="Select…"
                          accent={BLUE}
                          options={availableProducts.map((p) => ({
                            value: p.id,
                            label: p.name,
                          }))}
                        />
                      </td>
                      <td className="px-2 py-1 min-w-[100px]">
                        <SearchableSelect
                          value={it.unit_id}
                          onChange={(v) => updateItem(i, "unit_id", v)}
                          placeholder="Unit…"
                          accent={BLUE}
                          options={(units ?? []).map((u: { id: string; abbreviation: string }) => ({
                            value: u.id,
                            label: u.abbreviation,
                          }))}
                        />
                      </td>
                      <td className="px-2 py-1">
                        <input type="number" min="0.01" step="0.01" required value={it.ordered_qty}
                          onChange={(e) => updateItem(i, "ordered_qty", e.target.value)}
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
                        <input type="number" min="0" max="100" step="0.1" value={it.tolerance_pct} placeholder="0"
                          onChange={(e) => updateItem(i, "tolerance_pct", e.target.value)}
                          onFocus={() => setTolFocus(i)} onBlur={() => setTolFocus((f) => (f === i ? null : f))}
                          className="w-16 rounded border border-input bg-background px-1.5 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-ring" />
                      </td>
                      <td className="px-2 py-1 text-right tabular-nums whitespace-nowrap">{inr(lineAmount(it))}</td>
                      <td className="px-1 py-1">
                        {items.length > 1 && (
                          <button type="button" onClick={() => setItems((p) => p.filter((_, idx) => idx !== i))}
                            className="text-muted-foreground hover:text-destructive">
                            <Trash2 className="h-3 w-3" />
                          </button>
                        )}
                      </td>
                    </tr>
                    {it.rate_note && (
                      <tr>
                        <td colSpan={8} className="px-2 pb-1.5 text-[11px] text-muted-foreground">{it.rate_note}</td>
                      </tr>
                    )}
                    {(tolFocus === i || (parseFloat(it.tolerance_pct) || 0) > 0) && (parseFloat(it.ordered_qty) || 0) > 0 && (
                      <tr>
                        <td colSpan={8} className="px-2 pb-2">
                          <span className="inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px]"
                            style={{ borderColor: `${BLUE}40`, background: `${BLUE}0D`, color: BLUE }}>
                            {(parseFloat(it.tolerance_pct) || 0) > 0 ? (
                              <>Allowed on receipt: <b>{rangeText(parseFloat(it.ordered_qty), it.tolerance_pct, unitAbbr(it.unit_id))}</b> (±{it.tolerance_pct}%) — outside this, closing the PO needs admin approval</>
                            ) : (
                              <>No tolerance: only <b>{rangeText(parseFloat(it.ordered_qty), 0, unitAbbr(it.unit_id)).replace("exactly ", "")}</b> closes without admin approval. Enter a % to allow some variation.</>
                            )}
                          </span>
                        </td>
                      </tr>
                    )}
                    </Fragment>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t bg-muted/30">
                    <td colSpan={6} className="px-2 py-1.5 text-right font-medium">Total (incl. GST)</td>
                    <td className="px-2 py-1.5 text-right font-semibold tabular-nums whitespace-nowrap">{inr(orderTotal)}</td>
                    <td></td>
                  </tr>
                </tfoot>
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
            <button type="submit" value="draft" disabled={mut.isPending}
              className={canApprove
                ? "px-4 py-1.5 rounded border border-input text-sm hover:bg-muted disabled:opacity-60"
                : "px-4 py-1.5 rounded bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-60"}>
              {mut.isPending ? "Saving…" : canApprove ? "Save as Draft" : "Create PO"}
            </button>
            {canApprove && (
              <button type="submit" value="approve" disabled={mut.isPending}
                className="px-4 py-1.5 rounded bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-60">
                {mut.isPending ? "Saving…" : "Create & Approve"}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
    </ModalPortal>
  );
}

export default function PurchaseOrdersPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [showAdd, setShowAdd] = useState(false);
  const [approveError, setApproveError] = useState("");
  const qc = useQueryClient();
  const { can } = usePermissions();

  const approve = useMutation({
    mutationFn: (id: string) => api.post(`/purchase/orders/${id}/approve`),
    onSuccess: () => {
      setApproveError("");
      qc.invalidateQueries({ queryKey: ["purchase-orders"] });
    },
    onError: (e: unknown) => setApproveError(parseApiError(e, "Could not approve this PO.")),
  });

  const columns: Column<Record<string, unknown>>[] = can("purchase.approve")
    ? [
        ...baseColumns,
        {
          key: "actions",
          header: "",
          className: "text-right",
          render: (row) =>
            row.status === "draft" ? (
              <button
                onClick={(e) => { e.stopPropagation(); approve.mutate(row.id as string); }}
                disabled={approve.isPending}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border border-border hover:bg-muted disabled:opacity-50"
                style={{ color: BLUE }}
              >
                <CheckCircle2 className="h-3.5 w-3.5" /> Approve
              </button>
            ) : null,
        },
      ]
    : baseColumns;

  const { data, isLoading } = useQuery({
    queryKey: ["purchase-orders", statusFilter, page],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      if (statusFilter) params.set("status", statusFilter);
      const res = await api.get(`/purchase/orders?${params}`);
      return res.data;
    },
  });

  const orders: PurchaseOrder[] = data?.data ?? [];
  const total: number = data?.meta?.total ?? 0;

  return (
    <div className="p-8 space-y-8">
      {showAdd && <AddPOModal onClose={() => setShowAdd(false)} />}

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">PURCHASE / ORDERS</p>
          <h1 className="text-2xl font-bold tracking-tight">Purchase Orders</h1>
          <p className="text-sm text-muted-foreground mt-1">Raise and track orders to your vendors.</p>
        </div>
        <Can perm="purchase.create"><button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all duration-200 hover:opacity-90 active:scale-95"
          style={{ background: BLUE }}
        >
          <Plus className="h-4 w-4" /> New PO
        </button></Can>
      </div>

      {/* Filter tab strip */}
      <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit flex-wrap">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => { setStatusFilter(f.value); setPage(1); }}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
              statusFilter === f.value
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Card-wrapped table */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">PURCHASE ORDERS</p>
            <p className="text-sm font-medium mt-0.5">{total} orders total</p>
          </div>
        </div>
        {approveError && <p className="px-6 py-2 text-xs text-destructive border-b border-border">{approveError}</p>}
        <DataTable
          columns={columns}
          data={orders as unknown as Record<string, unknown>[]}
          loading={isLoading}
          onRowClick={(row) => router.push(`/purchase/orders/${row.id as string}`)}
          emptyMessage="No purchase orders found"
        />
      </div>
    </div>
  );
}
