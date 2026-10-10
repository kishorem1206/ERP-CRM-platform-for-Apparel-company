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

const TEAL = "#8174F5";

const DISPOSITION_OPTIONS = [
  { value: "usable_stock", label: "Usable stock (back to sellable inventory)" },
  { value: "resale_stock", label: "Resale stock (back to inventory, secondary)" },
  { value: "scrap", label: "Scrap (no inventory value)" },
  { value: "wastage", label: "Wastage (no inventory value)" },
];

interface SalesReturn {
  id: string;
  return_number: string;
  customer_name: string | null;
  return_date: string;
  status: string;
  reason: string | null;
}
interface DeliveryItemLite {
  id: string;
  product_id: string;
  product_name: string | null;
  variant_id: string | null;
  unit_id: string;
  quantity: string;
  returnable: boolean;
  returned_qty: string;
}

async function handlePrintReturn(returnId: string, returnNumber: string) {
  const res = await api.get(`/documents/returns/${returnId}/pdf`, { responseType: "blob" });
  const blobUrl = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = `SalesReturn_${returnNumber}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
}

const columns: Column<Record<string, unknown>>[] = [
  { key: "return_number", header: "Return #", sortable: true },
  { key: "customer_name", header: "Customer", render: (row) => (row.customer_name as string) || "—" },
  { key: "return_date", header: "Date", sortable: true },
  { key: "reason", header: "Reason", render: (row) => (row.reason as string) || "—" },
  { key: "status", header: "Status" },
  {
    key: "id", header: "", className: "w-10",
    render: (row) => (
      <button
        onClick={(e) => { e.stopPropagation(); handlePrintReturn(row.id as string, row.return_number as string); }}
        className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
        title="Print"
      >
        <Printer className="h-3.5 w-3.5" />
      </button>
    ),
  },
];

function AddReturnModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [deliveryId, setDeliveryId] = useState("");
  const [returnDate, setReturnDate] = useState(today);
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [itemQtys, setItemQtys] = useState<Record<string, string>>({});
  const [itemDisposition, setItemDisposition] = useState<Record<string, string>>({});
  const [error, setError] = useState("");

  const { data: deliveries } = useQuery({
    queryKey: ["deliveries-list-for-return"],
    queryFn: async () => (await api.get("/sales/deliveries?page_size=200")).data.data ?? [],
  });
  const { data: deliveryDetail, isLoading: delLoading } = useQuery({
    queryKey: ["delivery-detail-for-return", deliveryId],
    queryFn: async () => {
      if (!deliveryId) return null;
      const res = await api.get(`/sales/deliveries/${deliveryId}`);
      return res.data.data;
    },
    enabled: !!deliveryId,
  });

  const items: DeliveryItemLite[] = deliveryDetail?.items ?? [];
  const customerId: string | null = deliveryDetail?.customer_id ?? null;

  const mut = useMutation({
    mutationFn: () =>
      api.post("/sales/returns", {
        delivery_id: deliveryId,
        customer_id: customerId,
        return_date: returnDate,
        reason: reason || null,
        notes: notes || null,
        items: items
          .filter((it) => Number(itemQtys[it.id] ?? "0") > 0)
          .map((it) => ({
            delivery_item_id: it.id,
            product_id: it.product_id,
            quantity: parseFloat(itemQtys[it.id]),
            unit_id: it.unit_id,
            disposition: itemDisposition[it.id] ?? "usable_stock",
          })),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sales-returns"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string; error?: { message?: string } } } })?.response?.data;
      setError(msg?.detail || msg?.error?.message || "Failed to create return");
    },
  });

  return (
    <ModalPortal>
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
      <div className="bg-card border rounded-lg shadow-xl w-full max-w-2xl mx-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="font-semibold text-base">New Sales Return</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
        </div>
        <form
          className="overflow-y-auto p-5 space-y-4"
          onSubmit={(e) => { e.preventDefault(); setError(""); mut.mutate(); }}
        >
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-xs font-medium text-muted-foreground">Delivery Challan *</label>
              <SearchableSelect
                value={deliveryId}
                onChange={(v) => { setDeliveryId(v); setItemQtys({}); setItemDisposition({}); }}
                placeholder="Select delivery challan…"
                accent={TEAL}
                options={[
                  { value: "", label: "Select delivery challan…" },
                  ...(deliveries ?? []).map((d: { id: string; delivery_number: string; customer_name?: string }) => ({
                    value: d.id,
                    label: d.customer_name ? `${d.delivery_number} — ${d.customer_name}` : d.delivery_number,
                  })),
                ]}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Return Date *</label>
              <DatePicker value={returnDate} onChange={(v) => setReturnDate(v)} required />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Reason</label>
              <input value={reason} onChange={(e) => setReason(e.target.value)}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="e.g. Size mismatch, damaged in transit" />
            </div>
          </div>

          {deliveryId && (
            <div>
              <span className="text-xs font-medium text-muted-foreground">Items from Delivery Challan</span>
              {delLoading ? (
                <p className="text-xs text-muted-foreground mt-2">Loading items…</p>
              ) : items.length === 0 ? (
                <p className="text-xs text-muted-foreground mt-2">No items found on this delivery.</p>
              ) : (
                <div className="border rounded mt-2 overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="text-left px-2 py-1.5 font-medium">Product</th>
                        <th className="text-right px-2 py-1.5 font-medium">Delivered</th>
                        <th className="text-right px-2 py-1.5 font-medium">Already Returned</th>
                        <th className="text-right px-2 py-1.5 font-medium">Return Qty</th>
                        <th className="text-left px-2 py-1.5 font-medium">Disposition</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((it) => {
                        const remaining = Number(it.quantity) - Number(it.returned_qty || "0");
                        return (
                          <tr key={it.id} className={`border-t ${!it.returnable ? "opacity-40" : ""}`}>
                            <td className="px-2 py-1">{it.product_name ?? it.product_id.slice(0, 8)}</td>
                            <td className="px-2 py-1 text-right text-muted-foreground">{it.quantity}</td>
                            <td className="px-2 py-1 text-right text-muted-foreground">{it.returned_qty || "0"}</td>
                            <td className="px-2 py-1">
                              <input
                                type="number" min="0" max={remaining} step="0.01"
                                disabled={!it.returnable || remaining <= 0}
                                value={itemQtys[it.id] ?? ""}
                                onChange={(e) => setItemQtys((q) => ({ ...q, [it.id]: e.target.value }))}
                                className="w-20 rounded border border-input bg-background px-1.5 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-ring float-right disabled:opacity-50"
                              />
                            </td>
                            <td className="px-2 py-1">
                              <select
                                disabled={!it.returnable}
                                value={itemDisposition[it.id] ?? "usable_stock"}
                                onChange={(e) => setItemDisposition((d) => ({ ...d, [it.id]: e.target.value }))}
                                className="w-full rounded border border-input bg-background px-1.5 py-1 text-xs disabled:opacity-50"
                              >
                                {DISPOSITION_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                              </select>
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
            <button
              type="submit"
              disabled={mut.isPending || !deliveryId || !Object.values(itemQtys).some((v) => Number(v) > 0)}
              className="px-4 py-1.5 rounded bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-60"
            >
              {mut.isPending ? "Saving…" : "Create Return"}
            </button>
          </div>
        </form>
      </div>
    </div>
    </ModalPortal>
  );
}

export default function SalesReturnsPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [showAdd, setShowAdd] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["sales-returns", page],
    queryFn: async () => {
      const res = await api.get(`/sales/returns?page=${page}&page_size=50`);
      return res.data;
    },
  });

  const returns: SalesReturn[] = data?.data ?? [];
  const total: number = data?.meta?.total ?? 0;

  return (
    <div className="p-8 space-y-8">
      {showAdd && <AddReturnModal onClose={() => setShowAdd(false)} />}

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / RETURNS</p>
          <h1 className="text-2xl font-bold tracking-tight">Sales Returns</h1>
          <p className="text-sm text-muted-foreground mt-1">Customer returns of finished goods, classified as usable stock, resale stock, scrap, or wastage.</p>
        </div>
        <Can perm="sales.create"><button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: TEAL }}
        >
          <Plus className="h-4 w-4" /> New Return
        </button></Can>
      </div>

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">ALL RETURNS</p>
            <p className="text-sm font-medium mt-0.5">{total} record{total !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <div className="p-6">
          <DataTable
            columns={columns}
            data={returns as unknown as Record<string, unknown>[]}
            loading={isLoading}
            onRowClick={(row) => router.push(`/sales/returns/${row.id as string}`)}
            emptyMessage="No sales returns found"
          />
        </div>
      </div>
    </div>
  );
}
