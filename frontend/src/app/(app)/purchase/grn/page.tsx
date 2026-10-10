"use client";
import { useRouter } from "next/navigation";
import { useState, useEffect, Fragment } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, X } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { StatusBadge } from "@/components/shared/status-badge";
import { ModalPortal } from "@/components/shared/modal-portal";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { DatePicker } from "@/components/shared/date-picker";
import { Can } from "@/lib/permissions";

const TEAL = "#8174F5";

interface PurchaseEntry {
  id: string;
  entry_number: string;
  vendor_name: string | null;
  entry_date: string;
  invoice_number: string | null;
  status: string;
  total_amount: string;
  items?: { excess_qty: string | null }[];
}

interface GRNItem {
  po_item_id?: string;
  product_id: string;
  unit_id: string;
  received_qty: string;
  accepted_qty: string;
  unit_price: string;
  ordered_qty?: number;
  received_so_far?: number;
}

const STATUS_FILTERS = [
  { label: "All", value: "" },
  { label: "Draft", value: "draft" },
  { label: "Confirmed", value: "confirmed" },
  { label: "Cancelled", value: "cancelled" },
];

const columns: Column<Record<string, unknown>>[] = [
  { key: "entry_number", header: "GRN Number", sortable: true },
  { key: "vendor_name", header: "Vendor", render: (row) => (row.vendor_name as string) || "—" },
  { key: "entry_date", header: "Date", sortable: true },
  { key: "invoice_number", header: "Invoice #", render: (row) => (row.invoice_number as string) || "—" },
  { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status as string} /> },
  {
    key: "excess",
    header: "",
    render: (row) => {
      const items = (row.items as { excess_qty: string | null }[] | undefined) ?? [];
      const hasExcess = items.some((it) => it.excess_qty != null && Number(it.excess_qty) > 0);
      return hasExcess ? (
        <span className="px-2 py-0.5 rounded text-[11px] font-bold" style={{ background: "#A096F718", color: "#A096F7" }}>
          Excess
        </span>
      ) : null;
    },
  },
  {
    key: "total_amount",
    header: "Total",
    className: "text-right",
    render: (row) =>
      new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(Number(row.total_amount)),
  },
];

const emptyItem = (): GRNItem => ({ product_id: "", unit_id: "", received_qty: "1", accepted_qty: "1", unit_price: "0" });

function AddGRNModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [vendorId, setVendorId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [entryDate, setEntryDate] = useState(today);
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [invoiceDate, setInvoiceDate] = useState("");
  const [notes, setNotes] = useState("");
  const [purchaseOrderId, setPurchaseOrderId] = useState("");
  const [items, setItems] = useState<GRNItem[]>([emptyItem()]);
  const [error, setError] = useState("");

  const { data: vendors } = useQuery({
    queryKey: ["vendors-list"],
    queryFn: async () => (await api.get("/purchase/vendors?page_size=200")).data.data ?? [],
  });
  const { data: vendorPOs } = useQuery({
    queryKey: ["purchase-orders-for-grn", vendorId],
    queryFn: async () => {
      const [approved, partial] = await Promise.all([
        api.get("/purchase/orders", { params: { vendor_id: vendorId, status: "approved", page_size: 100 } }),
        api.get("/purchase/orders", { params: { vendor_id: vendorId, status: "partial", page_size: 100 } }),
      ]);
      return [...(approved.data.data ?? []), ...(partial.data.data ?? [])] as { id: string; po_number: string }[];
    },
    enabled: !!vendorId,
  });
  const { data: selectedPO } = useQuery({
    queryKey: ["purchase-order-detail-for-grn", purchaseOrderId],
    queryFn: async () => (await api.get(`/purchase/orders/${purchaseOrderId}`)).data.data as {
      items: { id: string; product_id: string; unit_id: string; ordered_qty: string; received_qty: string; unit_price: string }[];
    },
    enabled: !!purchaseOrderId,
  });
  const { data: warehouses } = useQuery({
    queryKey: ["warehouses-list"],
    queryFn: async () => (await api.get("/master/warehouses")).data.data ?? [],
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
      api.post("/purchase/entries", {
        purchase_order_id: purchaseOrderId || null,
        vendor_id: vendorId,
        warehouse_id: warehouseId,
        entry_date: entryDate,
        invoice_number: invoiceNumber || null,
        invoice_date: invoiceDate || null,
        notes: notes || null,
        items: items.map((it) => ({
          po_item_id: it.po_item_id || null,
          product_id: it.product_id,
          unit_id: it.unit_id,
          received_qty: parseFloat(it.received_qty),
          accepted_qty: parseFloat(it.accepted_qty),
          unit_price: parseFloat(it.unit_price),
          quality_status: "accepted",
        })),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["purchase-entries"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Failed to create GRN");
    },
  });

  const updateItem = (i: number, k: keyof GRNItem, v: string) =>
    setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, [k]: v } : it)));

  useEffect(() => {
    setPurchaseOrderId("");
  }, [vendorId]);

  useEffect(() => {
    if (!selectedPO) return;
    setItems(selectedPO.items.map((poItem) => {
      const remaining = Number(poItem.ordered_qty) - Number(poItem.received_qty);
      const qty = remaining > 0 ? String(remaining) : "0";
      return {
        po_item_id: poItem.id,
        product_id: poItem.product_id,
        unit_id: poItem.unit_id,
        received_qty: qty,
        accepted_qty: qty,
        unit_price: poItem.unit_price,
        ordered_qty: Number(poItem.ordered_qty),
        received_so_far: Number(poItem.received_qty),
      };
    }));
  }, [selectedPO]);

  return (
    <ModalPortal>
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
      <div className="bg-card border rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto ">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="font-semibold text-base">New Goods Receipt (GRN)</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
        </div>
        <form
          className="overflow-y-auto p-5 space-y-4"
          onSubmit={(e) => { e.preventDefault(); setError(""); mut.mutate(); }}
        >
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Vendor *</label>
              <div className="mt-1">
                <SearchableSelect
                  value={vendorId}
                  onChange={setVendorId}
                  placeholder="Select vendor…"
                  accent={TEAL}
                  options={(vendors ?? []).map((v: { id: string; name: string }) => ({
                    value: v.id,
                    label: v.name,
                  }))}
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Purchase Order (optional)</label>
              <div className="mt-1">
                <SearchableSelect
                  value={purchaseOrderId}
                  onChange={setPurchaseOrderId}
                  placeholder={vendorId ? "— Manual entry —" : "Select a vendor first"}
                  accent={TEAL}
                  options={(vendorPOs ?? []).map((po) => ({ value: po.id, label: po.po_number }))}
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Warehouse *</label>
              <div className="mt-1">
                <SearchableSelect
                  value={warehouseId}
                  onChange={setWarehouseId}
                  placeholder="Select warehouse…"
                  accent={TEAL}
                  options={(warehouses ?? []).map((w: { id: string; name: string }) => ({
                    value: w.id,
                    label: w.name,
                  }))}
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">GRN Date *</label>
              <DatePicker value={entryDate} onChange={(v) => setEntryDate(v)} required />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Vendor Invoice #</label>
              <input value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="INV-123" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Invoice Date</label>
              <DatePicker value={invoiceDate} onChange={(v) => setInvoiceDate(v)} />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground">Items Received *</span>
              <button type="button" onClick={() => setItems((p) => [...p, emptyItem()])}
                className="text-xs text-primary hover:underline">+ Add item</button>
            </div>
            <div className="border rounded overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left px-2 py-1.5 font-medium">Product</th>
                    <th className="text-left px-2 py-1.5 font-medium">Unit</th>
                    <th className="text-right px-2 py-1.5 font-medium">Received</th>
                    <th className="text-right px-2 py-1.5 font-medium">Accepted</th>
                    <th className="text-right px-2 py-1.5 font-medium">Price</th>
                    <th className="w-6"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it, i) => {
                    const projectedTotal = (it.received_so_far ?? 0) + (parseFloat(it.accepted_qty) || 0);
                    const excessPreview = it.ordered_qty != null && projectedTotal > it.ordered_qty
                      ? projectedTotal - it.ordered_qty : 0;
                    return (
                    <Fragment key={i}>
                    <tr className="border-t">
                      <td className="px-2 py-1 min-w-[160px]">
                        {it.po_item_id ? (
                          <div className="px-2 py-1.5 text-xs text-muted-foreground" title="Locked to the Purchase Order's line item">
                            {(products ?? []).find((p: { id: string; name: string }) => p.id === it.product_id)?.name ?? "—"}
                          </div>
                        ) : (
                          <SearchableSelect
                            value={it.product_id}
                            onChange={(v) => updateItem(i, "product_id", v)}
                            placeholder="Select…"
                            accent={TEAL}
                            options={(products ?? []).map((p: { id: string; name: string }) => ({
                              value: p.id,
                              label: p.name,
                            }))}
                          />
                        )}
                      </td>
                      <td className="px-2 py-1 min-w-[100px]">
                        <SearchableSelect
                          value={it.unit_id}
                          onChange={(v) => updateItem(i, "unit_id", v)}
                          placeholder="Unit…"
                          accent={TEAL}
                          options={(units ?? []).map((u: { id: string; abbreviation: string }) => ({
                            value: u.id,
                            label: u.abbreviation,
                          }))}
                        />
                      </td>
                      <td className="px-2 py-1">
                        <input type="number" min="0.01" step="0.01" required value={it.received_qty}
                          onChange={(e) => updateItem(i, "received_qty", e.target.value)}
                          className="w-20 rounded border border-input bg-background px-1.5 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-ring" />
                      </td>
                      <td className="px-2 py-1">
                        <input type="number" min="0" step="0.01" required value={it.accepted_qty}
                          onChange={(e) => updateItem(i, "accepted_qty", e.target.value)}
                          className="w-20 rounded border border-input bg-background px-1.5 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-ring" />
                      </td>
                      <td className="px-2 py-1">
                        <input type="number" min="0" step="0.01" required value={it.unit_price}
                          onChange={(e) => updateItem(i, "unit_price", e.target.value)}
                          className="w-24 rounded border border-input bg-background px-1.5 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-ring" />
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
                    {it.ordered_qty != null && (
                      <tr>
                        <td colSpan={6} className="px-2 pb-1.5 text-[11px] text-muted-foreground">
                          Ordered: {it.ordered_qty} · Received so far: {it.received_so_far ?? 0}
                          {excessPreview > 0 && (
                            <span className="ml-2 font-semibold" style={{ color: "#8174F5" }}>
                              +{excessPreview} excess
                            </span>
                          )}
                        </td>
                      </tr>
                    )}
                    </Fragment>
                    );
                  })}
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
              {mut.isPending ? "Saving…" : "Create GRN"}
            </button>
          </div>
        </form>
      </div>
    </div>
    </ModalPortal>
  );
}

export default function GRNPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [showAdd, setShowAdd] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["purchase-entries", statusFilter, page],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      if (statusFilter) params.set("status", statusFilter);
      const res = await api.get(`/purchase/entries?${params}`);
      return res.data;
    },
  });

  const entries: PurchaseEntry[] = data?.data ?? [];
  const total: number = data?.meta?.total ?? 0;

  return (
    <div className="p-8 space-y-8">
      {showAdd && <AddGRNModal onClose={() => setShowAdd(false)} />}

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">PURCHASE / GRN</p>
          <h1 className="text-2xl font-bold tracking-tight">Goods Receipt</h1>
          <p className="text-sm text-muted-foreground mt-1">Record incoming materials against purchase orders.</p>
        </div>
        <Can perm="purchase.create"><button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all duration-200 hover:opacity-90 active:scale-95"
          style={{ background: TEAL }}
        >
          <Plus className="h-4 w-4" /> New GRN
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
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">GOODS RECEIPT NOTES</p>
            <p className="text-sm font-medium mt-0.5">{total} receipts total</p>
          </div>
        </div>
        <DataTable
          columns={columns}
          data={entries as unknown as Record<string, unknown>[]}
          loading={isLoading}
          onRowClick={(row) => router.push(`/purchase/grn/${row.id as string}`)}
          emptyMessage="No GRNs found"
        />
      </div>
    </div>
  );
}
