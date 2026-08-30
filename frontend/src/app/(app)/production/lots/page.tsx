"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { ModalPortal } from "@/components/shared/modal-portal";
import { SearchableSelect } from "@/components/shared/searchable-select";

const INDIGO = "#5347CE";

type Lot = Record<string, unknown> & {
  id: string;
  lot_number: string;
  style_name: string | null;
  order_ref: string | null;
  planned_qty: number;
  actual_qty: number;
  delivery_date: string | null;
  season: string | null;
  status: string;
};

const STATUS_TABS = [
  { label: "All", value: "all" },
  { label: "Draft", value: "draft" },
  { label: "Planned", value: "planned" },
  { label: "Approved", value: "approved" },
  { label: "In Production", value: "in_production" },
  { label: "QC", value: "qc" },
  { label: "Packing", value: "packing" },
  { label: "Completed", value: "completed" },
  { label: "Cancelled", value: "cancelled" },
];

const STATUS_HEX: Record<string, string> = {
  draft: "#94A3B8", planned: "#4896FE", approved: "#887CFD",
  in_production: "#16C8C7", qc: "#F59E0B", packing: "#F97316",
  completed: "#10B981", cancelled: "#EF4444",
};

function StatusDot({ status }: { status: string }) {
  const color = STATUS_HEX[status] ?? "#94A3B8";
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

const columns: Column<Lot>[] = [
  { key: "lot_number", header: "Lot No." },
  { key: "style_name", header: "Style" },
  { key: "order_ref", header: "Order Ref" },
  { key: "planned_qty", header: "Planned" },
  { key: "actual_qty", header: "Actual" },
  { key: "delivery_date", header: "Delivery Date" },
  { key: "season", header: "Season" },
  {
    key: "status",
    header: "Status",
    render: (row) => <StatusDot status={row.status} />,
  },
];

function AddLotModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [styleId, setStyleId] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [orderRef, setOrderRef] = useState("");
  const [plannedQty, setPlannedQty] = useState("0");
  const [deliveryDate, setDeliveryDate] = useState("");
  const [season, setSeason] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");

  const { data: styles } = useQuery({
    queryKey: ["styles-list"],
    queryFn: async () => (await api.get("/production/styles")).data.data ?? [],
  });
  const { data: customers } = useQuery({
    queryKey: ["customers-list"],
    queryFn: async () => (await api.get("/sales/customers?page_size=200")).data.data ?? [],
  });

  const mut = useMutation({
    mutationFn: () =>
      api.post("/production/lots", {
        style_id: styleId || null,
        customer_id: customerId || null,
        order_ref: orderRef || null,
        planned_qty: parseInt(plannedQty) || 0,
        delivery_date: deliveryDate || null,
        season: season || null,
        notes: notes || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lots"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Failed to create production lot");
    },
  });

  return (
    <ModalPortal>
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
      <div className="bg-card border rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="font-semibold text-base">New Production Lot</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
        </div>
        <form
          className="p-5 space-y-3"
          onSubmit={(e) => { e.preventDefault(); setError(""); mut.mutate(); }}
        >
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Style</label>
              <div className="mt-1">
                <SearchableSelect
                  value={styleId}
                  onChange={setStyleId}
                  placeholder="None"
                  accent={INDIGO}
                  options={[
                    { value: "", label: "None" },
                    ...(styles ?? []).map((s: { id: string; name: string; code?: string }) => ({
                      value: s.id,
                      label: s.name,
                      meta: s.code,
                    })),
                  ]}
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Customer</label>
              <div className="mt-1">
                <SearchableSelect
                  value={customerId}
                  onChange={setCustomerId}
                  placeholder="None"
                  accent={INDIGO}
                  options={[
                    { value: "", label: "None" },
                    ...(customers ?? []).map((c: { id: string; legal_name: string }) => ({
                      value: c.id,
                      label: c.legal_name,
                    })),
                  ]}
                />
              </div>
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Order Reference</label>
            <input value={orderRef} onChange={(e) => setOrderRef(e.target.value)}
              className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="PO number or order ref" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Planned Qty *</label>
              <input required type="number" min="1" value={plannedQty} onChange={(e) => setPlannedQty(e.target.value)}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Delivery Date</label>
              <input type="date" value={deliveryDate} onChange={(e) => setDeliveryDate(e.target.value)}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Season</label>
            <input value={season} onChange={(e) => setSeason(e.target.value)}
              className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="e.g. SS25, AW26" />
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
              {mut.isPending ? "Saving…" : "Create Lot"}
            </button>
          </div>
        </form>
      </div>
    </div>
    </ModalPortal>
  );
}

export default function ProductionLotsPage() {
  const [activeTab, setActiveTab] = useState("all");
  const [showAdd, setShowAdd] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["production-lots", activeTab],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (activeTab !== "all") params.status = activeTab;
      const res = await api.get("/production/lots", { params });
      return (res.data.data ?? []) as Lot[];
    },
  });

  return (
    <div className="p-8 space-y-8">
      {showAdd && <AddLotModal onClose={() => setShowAdd(false)} />}

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">PRODUCTION / LOTS</p>
          <h1 className="text-2xl font-bold tracking-tight">Production Lots</h1>
          <p className="text-sm text-muted-foreground mt-1">Track every garment batch from planned to delivered.</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all duration-200 hover:opacity-90 active:scale-95"
          style={{ background: INDIGO }}
        >
          <Plus className="h-4 w-4" /> New Lot
        </button>
      </div>

      {/* Filter tab strip */}
      <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit flex-wrap">
        {STATUS_TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setActiveTab(t.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
              activeTab === t.value
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Card-wrapped table */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">ALL LOTS</p>
            <p className="text-sm font-medium mt-0.5">
              {activeTab === "all" ? "All statuses" : STATUS_TABS.find((t) => t.value === activeTab)?.label}
            </p>
          </div>
        </div>
        <DataTable columns={columns} data={data ?? []} loading={isLoading} />
      </div>
    </div>
  );
}
