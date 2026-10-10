"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { ModalPortal } from "@/components/shared/modal-portal";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { DatePicker } from "@/components/shared/date-picker";
import { Can } from "@/lib/permissions";

const INDIGO = "#0049A7";

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
  { label: "Cutting", value: "cutting" },
  { label: "Checking", value: "checking" },
  { label: "Packing", value: "packing" },
  { label: "Completed", value: "completed" },
  { label: "Cancelled", value: "cancelled" },
];

const STATUS_HEX: Record<string, string> = {
  cutting: "#8174F5", checking: "#A096F7", packing: "#0F78FF",
  completed: "#0F78FF", cancelled: "#1D0DB0",
};

function StatusDot({ status }: { status: string }) {
  const color = STATUS_HEX[status] ?? "#94A3B8";
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
  const [colourId, setColourId] = useState("");
  const [plannedWeightKg, setPlannedWeightKg] = useState("");
  const [deliveryDate, setDeliveryDate] = useState("");
  const [season, setSeason] = useState("");
  const [notes, setNotes] = useState("");
  const [piecesPerBox, setPiecesPerBox] = useState("");
  const [costs, setCosts] = useState<{ key: number; cost_type: "additional" | "agent_commission"; description: string; planned_amount: string; party_vendor_id: string }[]>([]);
  const [lotSizes, setLotSizes] = useState<Record<string, string>>({});
  const [error, setError] = useState("");

  const { data: styles } = useQuery({
    queryKey: ["styles-list"],
    queryFn: async () => (await api.get("/production/styles")).data.data ?? [],
  });
  const { data: agentVendors } = useQuery({
    queryKey: ["vendors", "agent"],
    queryFn: async () => (await api.get("/purchase/vendors", { params: { vendor_type: "agent", page_size: 200 } })).data.data as { id: string; name: string }[],
  });
  const { data: styleDetail } = useQuery({
    queryKey: ["style-detail-for-lot", styleId],
    queryFn: async () => (await api.get(`/production/styles/${styleId}`)).data.data as {
      sizes: { size_id: string; quantity: number | null }[];
    },
    enabled: !!styleId,
  });
  const { data: sizesMaster } = useQuery({
    queryKey: ["master-sizes"],
    queryFn: async () => (await api.get("/master/sizes")).data.data as { id: string; name: string }[],
  });

  useEffect(() => {
    if (!styleDetail) { setLotSizes({}); return; }
    setLotSizes(Object.fromEntries(
      styleDetail.sizes.filter((s) => s.quantity != null).map((s) => [s.size_id, String(s.quantity)])
    ));
  }, [styleDetail]);
  const { data: customers } = useQuery({
    queryKey: ["customers-list"],
    queryFn: async () => (await api.get("/sales/customers?page_size=200")).data.data ?? [],
  });
  const { data: colours } = useQuery({
    queryKey: ["master-colours"],
    queryFn: async () => (await api.get("/master/colours")).data.data as { id: string; name: string; hex_code: string | null }[],
  });

  const mut = useMutation({
    mutationFn: () =>
      api.post("/production/lots", {
        style_id: styleId || null,
        customer_id: customerId || null,
        order_ref: orderRef || null,
        planned_qty: parseInt(plannedQty) || 0,
        colour_id: colourId,
        planned_weight_kg: plannedWeightKg ? Number(plannedWeightKg) : undefined,
        delivery_date: deliveryDate || null,
        season: season || null,
        notes: notes || null,
        pieces_per_box: piecesPerBox ? parseInt(piecesPerBox) : undefined,
        sizes: Object.entries(lotSizes).filter(([, v]) => v).map(([size_id, planned_qty]) => ({
          size_id, planned_qty: parseInt(planned_qty) || 0,
        })),
        additional_costs: costs.filter((c) => c.description.trim()).map((c) => ({
          cost_type: c.cost_type, description: c.description.trim(),
          planned_amount: c.planned_amount ? Number(c.planned_amount) : undefined,
          party_vendor_id: c.cost_type === "agent_commission" && c.party_vendor_id ? c.party_vendor_id : undefined,
        })),
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
                  onChange={(v) => {
                    setStyleId(v);
                    const st = (styles ?? []).find((x: { id: string; pieces_per_box?: number | null }) => x.id === v);
                    if (st?.pieces_per_box) setPiecesPerBox(String(st.pieces_per_box));
                  }}
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
              <DatePicker value={deliveryDate} onChange={(v) => setDeliveryDate(v)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Colour *</label>
              <div className="mt-1">
                <SearchableSelect
                  value={colourId}
                  onChange={setColourId}
                  placeholder="Select colour"
                  accent={INDIGO}
                  options={(colours ?? []).map((c) => ({ value: c.id, label: c.name }))}
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Planned Weight (kg, optional)</label>
              <input type="number" step="0.001" value={plannedWeightKg} onChange={(e) => setPlannedWeightKg(e.target.value)}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="e.g. 500" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Pieces per Box (optional)</label>
            <input type="number" min="1" value={piecesPerBox} onChange={(e) => setPiecesPerBox(e.target.value)}
              className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="e.g. 12 — defaults from the Style" />
          </div>
          {styleDetail && styleDetail.sizes.length > 0 && (
            <div>
              <label className="text-xs font-medium text-muted-foreground">Planned Qty per Size</label>
              <p className="text-[11px] text-muted-foreground mt-0.5 mb-1.5">Pre-filled from the Style's size quantities — edit any value below.</p>
              <div className="space-y-1.5">
                {styleDetail.sizes.map((s) => (
                  <div key={s.size_id} className="flex items-center gap-2">
                    <span className="text-xs font-medium w-20 flex-shrink-0">
                      {(sizesMaster ?? []).find((m) => m.id === s.size_id)?.name ?? "—"}
                    </span>
                    <input
                      type="number" min="0"
                      value={lotSizes[s.size_id] ?? ""}
                      onChange={(e) => setLotSizes((prev) => ({ ...prev, [s.size_id]: e.target.value }))}
                      className="w-28 rounded border border-input bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      placeholder="Qty"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
          <div>
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-muted-foreground">Additional Costs & Agent Commission (optional)</label>
              <button type="button" onClick={() => setCosts((c) => [...c, { key: Date.now(), cost_type: "additional", description: "", planned_amount: "", party_vendor_id: "" }])}
                className="text-xs font-semibold" style={{ color: INDIGO }}>+ Add</button>
            </div>
            {costs.map((c) => (
              <div key={c.key} className="flex gap-2 mt-1.5 flex-wrap">
                <div className="w-40 flex-shrink-0">
                  <SearchableSelect
                    value={c.cost_type}
                    onChange={(v) => setCosts((r) => r.map((x) => x.key === c.key ? { ...x, cost_type: v as "additional" | "agent_commission" } : x))}
                    placeholder="Type"
                    accent={INDIGO}
                    options={[{ value: "additional", label: "Additional" }, { value: "agent_commission", label: "Agent Commission" }]}
                  />
                </div>
                <input value={c.description} onChange={(e) => setCosts((r) => r.map((x) => x.key === c.key ? { ...x, description: e.target.value } : x))}
                  placeholder="Description" className="flex-1 rounded border border-input bg-background px-2 py-1.5 text-xs" />
                <input type="number" step="0.01" value={c.planned_amount} onChange={(e) => setCosts((r) => r.map((x) => x.key === c.key ? { ...x, planned_amount: e.target.value } : x))}
                  placeholder="₹ planned" className="w-24 rounded border border-input bg-background px-2 py-1.5 text-xs" />
                <button type="button" onClick={() => setCosts((r) => r.filter((x) => x.key !== c.key))} className="text-muted-foreground px-1">×</button>
                {c.cost_type === "agent_commission" && (
                  <div className="w-full">
                    <SearchableSelect
                      value={c.party_vendor_id}
                      onChange={(v) => setCosts((r) => r.map((x) => x.key === c.key ? { ...x, party_vendor_id: v } : x))}
                      placeholder="Select Agent"
                      accent={INDIGO}
                      options={(agentVendors ?? []).map((v) => ({ value: v.id, label: v.name }))}
                    />
                  </div>
                )}
              </div>
            ))}
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
            <button type="submit" disabled={mut.isPending || !colourId}
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
  const router = useRouter();
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
        <Can perm="production.create"><button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all duration-200 hover:opacity-90 active:scale-95"
          style={{ background: INDIGO }}
        >
          <Plus className="h-4 w-4" /> New Lot
        </button></Can>
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
        <DataTable
          columns={columns}
          data={data ?? []}
          loading={isLoading}
          onRowClick={(row) => router.push(`/production/lots/${row.id}`)}
        />
      </div>
    </div>
  );
}
