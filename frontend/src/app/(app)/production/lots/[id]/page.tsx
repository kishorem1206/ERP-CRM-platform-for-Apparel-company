"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, Pencil, Plus, X, ChevronRight, Truck, Trash2, RotateCcw, Inbox, Download, FileText,
  Flame, Printer, Shirt, CircleDot, Sparkles, Droplets, CheckCircle2, Wind, Package, MoreHorizontal,
} from "lucide-react";
import api from "@/lib/api";
import { ModalShell } from "@/components/shared/modal-shell";
import { SearchableSelect } from "@/components/shared/searchable-select";

const INDIGO = "#0049A7";
const inputCls =
  "w-full rounded-xl border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

const STATUS_HEX: Record<string, string> = {
  draft: "#94A3B8", planned: "#0049A7", approved: "#0F78FF",
  in_production: "#8174F5", qc: "#A096F7", packing: "#A096F7",
  ready_to_dispatch: "#0F78FF", completed: "#0F78FF", cancelled: "#1D0DB0",
};
const STATUS_FLOW: Record<string, string> = {
  draft: "planned", planned: "approved", approved: "in_production",
  in_production: "qc", qc: "packing", packing: "ready_to_dispatch",
  ready_to_dispatch: "completed",
};
const STAGE_STATUS_HEX: Record<string, string> = {
  pending: "#94A3B8", in_progress: "#0049A7", completed: "#0F78FF",
};

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_HEX[status] ?? "#94A3B8";
  const label = status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-bold whitespace-nowrap"
      style={{ background: `${color}18`, color }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {label}
    </span>
  );
}

const boxesLabel = (qty: number, perBox: number | null) => {
  if (!perBox || perBox <= 0 || qty <= 0) return null;
  const full = Math.floor(qty / perBox);
  const rem = qty % perBox;
  return rem
    ? `${full + 1} boxes (${full} × ${perBox} + ${rem})`
    : `${full} boxes (${full} × ${perBox})`;
};

const INR = (v: number) => `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

interface Size { id: string; name: string }
interface LotSize { id: string; size_id: string; planned_qty: number; cut_qty: number; sewn_qty: number; finished_qty: number }
interface StageEntry {
  id: string; entry_date: string; pieces_in: number; pieces_out: number; rejected: number;
  operator: string | null; machine: string | null; notes: string | null;
}
interface StageChallan {
  id: string; challan_number: string; vendor_id: string | null; worker_id: string | null;
  out_date: string; out_qty: number;
  in_date: string | null; in_qty: number | null; rejected_qty: number | null; pending_qty: number;
  expected_return_days: number | null;
  status: string; bill_amount: number | null; bill_received: boolean;
  bill_received_date: string | null; notes: string | null;
}
interface Stage {
  id: string; stage_type: string; stage_name: string; planned_qty: number | null;
  input_qty: number; output_qty: number; sent_qty: number; received_qty: number; accepted_qty: number;
  rejected_qty: number; rework_qty: number; status: string;
  assignment_type: string | null; vendor_id: string | null; worker_id: string | null;
  rate_per_pc: number | null; bill_amount: number | null; notes: string | null;
  tolerance_pct: number | null; input_unit: string | null; output_unit: string | null; conversion_rule: string | null;
  min_rate: number | null; max_rate: number | null; planned_rate: number | null;
  entries: StageEntry[]; challans: StageChallan[];
}
interface Worker { id: string; name: string; role_title: string | null }
interface LotAdditionalCost {
  id: string; cost_type: string; description: string;
  planned_amount: number | null; actual_amount: number | null;
  basis: string | null; party_vendor_id: string | null; notes: string | null;
}
interface FabricProcessing {
  id: string; process_type: string; vendor_id: string | null;
  in_date: string; input_kg: number; out_date: string | null; output_kg: number | null;
  gain_loss_kg: number | null; rate_per_kg: number | null; bill_amount: number | null;
  status: string; notes: string | null;
}
interface LotCostComponent {
  name: string; planned_amount: number | null; actual_amount: number | null;
  variance_amount: number | null; variance_pct: number | null; note: string | null;
}
interface LotCostSummary {
  components: LotCostComponent[]; total_planned: number | null; total_actual: number;
  first_quality_qty: number; rejected_qty: number; total_output_qty: number; yield_pct: number | null;
  cost_per_first_quality_piece: number | null; target_price: number | null;
  target_revenue: number | null; expected_margin_pct: number | null;
  actual_selling_price_per_piece: number | null; selling_price_source: string | null;
  actual_revenue: number | null; profit_per_piece: number | null; actual_profit: number | null;
  gross_margin_pct: number | null; is_final: boolean; missing_rate_warnings: string[];
}
interface LotDetail {
  id: string; lot_number: string; style_id: string | null; style_name: string | null;
  customer_id: string | null; order_ref: string | null; planned_qty: number; actual_qty: number;
  colour_id: string | null; planned_weight_kg: number | null; actual_weight_kg: number | null;
  delivery_date: string | null; season: string | null; target_sp: number | null;
  actual_selling_price: number | null; pieces_per_box: number | null; status: string;
  notes: string | null; final_output_unit: string | null; style_version: number | null;
  closed_at: string | null; sizes: LotSize[]; stages: Stage[]; additional_costs: LotAdditionalCost[];
  fabric_processing: FabricProcessing[]; cost_summary: LotCostSummary;
}
interface MISRow { id: string; issue_number: string; issue_date: string; status: string; items: { total_cost: number; excess_qty: number | null }[] }
interface OutputRow { id: string; output_number: string; output_date: string; quantity: number; rejected_qty: number | null; unit_cost: number; total_cost: number }

function Card({ title, subtitle, action, children }: { title: string; subtitle?: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="bg-card border border-border rounded-2xl overflow-hidden">
      <div className="px-6 py-4 border-b border-border flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">{title}</h2>
          {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="p-6">{children}</div>
    </section>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="text-sm text-muted-foreground">{text}</p>;
}

// ── Edit Lot Modal ────────────────────────────────────────────────────────────
function EditLotModal({ lot, onClose }: { lot: LotDetail; onClose: () => void }) {
  const qc = useQueryClient();
  const [deliveryDate, setDeliveryDate] = useState(lot.delivery_date ?? "");
  const [season, setSeason] = useState(lot.season ?? "");
  const [targetSp, setTargetSp] = useState(lot.target_sp != null ? String(lot.target_sp) : "");
  const [notes, setNotes] = useState(lot.notes ?? "");
  const [piecesPerBox, setPiecesPerBox] = useState(lot.pieces_per_box != null ? String(lot.pieces_per_box) : "");

  const mut = useMutation({
    mutationFn: () =>
      api.patch(`/production/lots/${lot.id}`, {
        pieces_per_box: piecesPerBox ? Number(piecesPerBox) : null,
        delivery_date: deliveryDate || null,
        season: season || null,
        target_sp: targetSp ? Number(targetSp) : null,
        notes: notes || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lot", lot.id] });
      qc.invalidateQueries({ queryKey: ["production-lots"] });
      onClose();
    },
  });

  return (
    <ModalShell maxWidth="max-w-md" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Edit Lot</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Delivery Date</label>
            <input type="date" className={inputCls} value={deliveryDate} onChange={(e) => setDeliveryDate(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Season</label>
            <input className={inputCls} placeholder="e.g. SS26" value={season} onChange={(e) => setSeason(e.target.value)} />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Target Selling Price (₹)</label>
          <input type="number" step="0.01" className={inputCls} value={targetSp} onChange={(e) => setTargetSp(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Pieces per Box</label>
          <input type="number" min="1" className={inputCls} value={piecesPerBox} onChange={(e) => setPiecesPerBox(e.target.value)} placeholder="e.g. 12" />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
          <textarea className={`${inputCls} resize-none`} rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mut.isPending ? "Saving…" : "Save Changes"}
        </button>
      </div>
    </ModalShell>
  );
}

// ── Edit Stage Modal ───────────────────────────────────────────────────────────
function EditStageModal({ stage, lotId, onClose }: { stage: Stage; lotId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [ratePerPc, setRatePerPc] = useState(stage.rate_per_pc != null ? String(stage.rate_per_pc) : "");
  const [sentQty, setSentQty] = useState(String(stage.sent_qty));
  const [receivedQty, setReceivedQty] = useState(String(stage.received_qty));
  const [rejectedQty, setRejectedQty] = useState(String(stage.rejected_qty));
  const [notes, setNotes] = useState(stage.notes ?? "");
  const [err, setErr] = useState<string | null>(null);
  const isAssigned = !!stage.assignment_type;

  const mut = useMutation({
    mutationFn: () =>
      api.patch(`/production/stages/${stage.id}`, {
        rate_per_pc: ratePerPc ? Number(ratePerPc) : null,
        ...(isAssigned
          ? { sent_qty: Number(sentQty) || 0, received_qty: Number(receivedQty) || 0, rejected_qty: Number(rejectedQty) || 0 }
          : {}),
        notes: notes || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lot", lotId] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error;
      setErr(typeof msg === "string" ? msg : "Failed to save");
    },
  });

  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Edit — {stage.stage_name}</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Rate per Piece (₹)</label>
          <input type="number" step="0.01" className={inputCls} value={ratePerPc} onChange={(e) => setRatePerPc(e.target.value)} />
          {stage.planned_rate != null && (
            <p className="text-[11px] text-muted-foreground mt-1">Style's planned rate: {INR(stage.planned_rate)}</p>
          )}
        </div>
        {isAssigned && (
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Sent OUT</label>
              <input type="number" className={inputCls} value={sentQty} onChange={(e) => setSentQty(e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">First Quality</label>
              <input type="number" className={inputCls} value={receivedQty} onChange={(e) => setReceivedQty(e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Rejected</label>
              <input type="number" className={inputCls} value={rejectedQty} onChange={(e) => setRejectedQty(e.target.value)} />
            </div>
          </div>
        )}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
          <textarea className={`${inputCls} resize-none`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
        {err && <p className="text-xs text-[#1D0DB0]">{err}</p>}
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => { setErr(null); mut.mutate(); }}
          disabled={mut.isPending}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mut.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </ModalShell>
  );
}

// ── Record Actual Additional Cost Modal ───────────────────────────────────────
// ── Edit Selling Price Modal ───────────────────────────────────────────────────
function EditSellingPriceModal({ lot, onClose }: { lot: LotDetail; onClose: () => void }) {
  const qc = useQueryClient();
  const [price, setPrice] = useState(lot.actual_selling_price != null ? String(lot.actual_selling_price) : "");

  const mut = useMutation({
    mutationFn: (value: number | null) =>
      api.patch(`/production/lots/${lot.id}`, { actual_selling_price: value }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lot", lot.id] });
      onClose();
    },
  });

  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Selling Price / Piece</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Actual Selling Price (₹ / piece)</label>
          <input type="number" step="0.01" className={inputCls} value={price} onChange={(e) => setPrice(e.target.value)} autoFocus />
          <p className="text-[11px] text-muted-foreground mt-1">
            Once set, this is used as the actual selling price for this lot (ahead of any sales order or product MRP),
            and is applied to the produced product&apos;s MRP in Inventory.
          </p>
        </div>
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        {lot.actual_selling_price != null && (
          <button
            onClick={() => mut.mutate(null)}
            disabled={mut.isPending}
            className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors mr-auto"
          >
            Clear
          </button>
        )}
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => mut.mutate(price ? Number(price) : null)}
          disabled={mut.isPending || !price}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mut.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </ModalShell>
  );
}

// ── Add Additional Cost / Agent Commission Modal ──────────────────────────────
function AddLotCostModal({ lotId, onClose }: { lotId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [costType, setCostType] = useState<"additional" | "agent_commission">("additional");
  const [description, setDescription] = useState("");
  const [planned, setPlanned] = useState("");
  const [actual, setActual] = useState("");
  const mut = useMutation({
    mutationFn: () => api.post(`/production/lots/${lotId}/additional-costs`, {
      cost_type: costType, description: description.trim(),
      planned_amount: planned ? Number(planned) : undefined,
      actual_amount: actual ? Number(actual) : undefined,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["production-lot", lotId] }); onClose(); },
  });
  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Add Cost</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors"><X className="h-4 w-4" /></button>
      </div>
      <div className="p-6 space-y-4">
        <div className="flex gap-2">
          {(["additional", "agent_commission"] as const).map((t) => (
            <button key={t} type="button" onClick={() => setCostType(t)}
              className="flex-1 px-3 py-2 rounded-full border text-sm font-medium"
              style={costType === t ? { borderColor: INDIGO, background: `${INDIGO}12`, color: INDIGO } : { borderColor: "hsl(var(--border))" }}>
              {t === "additional" ? "Additional Cost" : "Agent Commission"}
            </button>
          ))}
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Description</label>
          <input className={inputCls} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. Freight" autoFocus />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Planned (₹)</label>
            <input type="number" step="0.01" className={inputCls} value={planned} onChange={(e) => setPlanned(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Actual (₹)</label>
            <input type="number" step="0.01" className={inputCls} value={actual} onChange={(e) => setActual(e.target.value)} />
          </div>
        </div>
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">Cancel</button>
        <button onClick={() => mut.mutate()} disabled={mut.isPending || !description.trim()}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold disabled:opacity-50" style={{ background: INDIGO }}>
          {mut.isPending ? "Saving…" : "Add"}
        </button>
      </div>
    </ModalShell>
  );
}

function RecordActualCostModal({ cost, lotId, onClose }: { cost: LotAdditionalCost; lotId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [actualAmount, setActualAmount] = useState(cost.actual_amount != null ? String(cost.actual_amount) : "");
  const [notes, setNotes] = useState(cost.notes ?? "");

  const mut = useMutation({
    mutationFn: () =>
      api.patch(`/production/lots/additional-costs/${cost.id}`, {
        actual_amount: actualAmount ? Number(actualAmount) : null,
        notes: notes || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lot", lotId] });
      onClose();
    },
  });

  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Record Actual — {cost.description}</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Actual Amount (₹)</label>
          <input type="number" step="0.01" className={inputCls} value={actualAmount} onChange={(e) => setActualAmount(e.target.value)} />
          {cost.planned_amount != null && (
            <p className="text-[11px] text-muted-foreground mt-1">Planned amount: {INR(cost.planned_amount)}</p>
          )}
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
          <textarea className={`${inputCls} resize-none`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mut.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </ModalShell>
  );
}

// ── Add Stage Entry Modal ─────────────────────────────────────────────────────
function AddEntryModal({ stage, lotId, onClose }: { stage: Stage; lotId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [entryDate, setEntryDate] = useState(today);
  const [piecesIn, setPiecesIn] = useState("0");
  const [piecesOut, setPiecesOut] = useState("0");
  const [rejected, setRejected] = useState("0");
  const [operator, setOperator] = useState("");
  const [machine, setMachine] = useState("");

  const mut = useMutation({
    mutationFn: () =>
      api.post(`/production/stages/${stage.id}/entries`, {
        entry_date: entryDate,
        pieces_in: Number(piecesIn) || 0,
        pieces_out: Number(piecesOut) || 0,
        rejected: Number(rejected) || 0,
        operator: operator || undefined,
        machine: machine || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lot", lotId] });
      onClose();
    },
  });

  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Log Entry — {stage.stage_name}</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Date</label>
          <input type="date" className={inputCls} value={entryDate} onChange={(e) => setEntryDate(e.target.value)} />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Pieces In</label>
            <input type="number" className={inputCls} value={piecesIn} onChange={(e) => setPiecesIn(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Pieces Out</label>
            <input type="number" className={inputCls} value={piecesOut} onChange={(e) => setPiecesOut(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Rejected</label>
            <input type="number" className={inputCls} value={rejected} onChange={(e) => setRejected(e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Operator</label>
            <input className={inputCls} value={operator} onChange={(e) => setOperator(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Machine</label>
            <input className={inputCls} value={machine} onChange={(e) => setMachine(e.target.value)} />
          </div>
        </div>
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mut.isPending ? "Saving…" : "Log Entry"}
        </button>
      </div>
    </ModalShell>
  );
}

// ── Send to Vendor Modal (create Job Work Challan) ────────────────────────────
function AssignmentTypeToggle({ value, onChange, allowNone }: {
  value: "vendor" | "internal_worker" | null; onChange: (v: "vendor" | "internal_worker" | null) => void; allowNone?: boolean;
}) {
  const ALL_OPTIONS: { value: "vendor" | "internal_worker" | null; label: string }[] = [
    { value: null, label: "Unassigned" },
    { value: "vendor", label: "Vendor" },
    { value: "internal_worker", label: "Internal Worker" },
  ];
  const OPTIONS = allowNone ? ALL_OPTIONS : ALL_OPTIONS.slice(1);
  return (
    <div className="flex items-center gap-2 mb-1">
      {OPTIONS.map((o) => {
        const isActive = value === o.value;
        return (
          <button
            key={o.label}
            type="button"
            onClick={() => onChange(o.value)}
            className="flex-1 px-3.5 py-2 rounded-full border text-sm font-medium transition-colors"
            style={isActive ? { borderColor: INDIGO, background: `${INDIGO}12`, color: INDIGO } : { borderColor: "hsl(var(--border))" }}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function SendToVendorModal({ stage, lotId, onClose }: { stage: Stage; lotId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [assignmentType, setAssignmentType] = useState<"vendor" | "internal_worker">(
    stage.assignment_type === "internal_worker" ? "internal_worker" : "vendor"
  );
  const [vendorId, setVendorId] = useState(stage.vendor_id ?? "");
  const [workerId, setWorkerId] = useState(stage.worker_id ?? "");
  const [outDate, setOutDate] = useState(today);
  const [outQty, setOutQty] = useState(String(stage.planned_qty ?? ""));
  const [expectedReturnDays, setExpectedReturnDays] = useState("3");
  const [notes, setNotes] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const vendors = useQuery({
    queryKey: ["vendors", "ref"],
    queryFn: async () => (await api.get("/purchase/vendors", { params: { page_size: 200 } })).data.data as { id: string; name: string; vendor_type: string }[],
    enabled: assignmentType === "vendor",
  });
  const workers = useQuery({
    queryKey: ["production-workers"],
    queryFn: async () => (await api.get("/production/workers")).data.data as Worker[],
    enabled: assignmentType === "internal_worker",
  });

  const mut = useMutation({
    mutationFn: () =>
      api.post(`/production/stages/${stage.id}/challans`, {
        vendor_id: assignmentType === "vendor" ? vendorId : undefined,
        worker_id: assignmentType === "internal_worker" ? workerId : undefined,
        out_date: outDate,
        out_qty: Number(outQty) || 0,
        expected_return_days: expectedReturnDays ? Number(expectedReturnDays) : undefined,
        notes: notes || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lot", lotId] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error;
      setErr(typeof msg === "string" ? msg : "Failed to send");
    },
  });

  const assigneeId = assignmentType === "vendor" ? vendorId : workerId;

  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Assign & Send — {stage.stage_name}</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-2">Assignment Type</label>
          <AssignmentTypeToggle value={assignmentType} onChange={(v) => setAssignmentType(v ?? "vendor")} />
        </div>
        {assignmentType === "vendor" ? (
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Vendor</label>
            <SearchableSelect
              value={vendorId}
              onChange={setVendorId}
              placeholder="Select job-work vendor"
              accent={INDIGO}
              options={(vendors.data ?? []).map((v) => ({ value: v.id, label: v.name, meta: v.vendor_type }))}
            />
          </div>
        ) : (
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Internal Worker</label>
            <SearchableSelect
              value={workerId}
              onChange={setWorkerId}
              placeholder="Select internal worker"
              accent={INDIGO}
              options={(workers.data ?? []).map((w) => ({ value: w.id, label: w.name, meta: w.role_title ?? undefined }))}
            />
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Out Date</label>
            <input type="date" className={inputCls} value={outDate} onChange={(e) => setOutDate(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Out Qty</label>
            <input type="number" className={inputCls} value={outQty} onChange={(e) => setOutQty(e.target.value)} />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Expected Return (days)</label>
          <input type="number" className={inputCls} value={expectedReturnDays} onChange={(e) => setExpectedReturnDays(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
          <textarea className={`${inputCls} resize-none`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
        {err && <p className="text-xs text-[#1D0DB0]">{err}</p>}
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => { setErr(null); mut.mutate(); }}
          disabled={mut.isPending || !assigneeId || !outQty}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mut.isPending ? "Sending…" : "Send"}
        </button>
      </div>
    </ModalShell>
  );
}

// ── Add Stage Modal ─────────────────────────────────────────────────────────────

const STAGE_CHIPS: { name: string; stage_type: string; icon: typeof Flame }[] = [
  { name: "Fusing", stage_type: "making", icon: Flame },
  { name: "Printing", stage_type: "making", icon: Printer },
  { name: "Stitching", stage_type: "making", icon: Shirt },
  { name: "Button", stage_type: "making", icon: CircleDot },
  { name: "Embroidery", stage_type: "making", icon: Sparkles },
  { name: "Washing", stage_type: "making", icon: Droplets },
  { name: "Checking", stage_type: "qc", icon: CheckCircle2 },
  { name: "Ironing", stage_type: "finishing", icon: Wind },
  { name: "Packing", stage_type: "packing", icon: Package },
];

function AddStageModal({ lotId, onClose }: { lotId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);
  const [customName, setCustomName] = useState("");
  const [assignmentType, setAssignmentType] = useState<"vendor" | "internal_worker" | null>(null);
  const [vendorId, setVendorId] = useState("");
  const [workerId, setWorkerId] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");

  const vendors = useQuery({
    queryKey: ["vendors", "ref"],
    queryFn: async () => (await api.get("/purchase/vendors", { params: { page_size: 200 } })).data.data as { id: string; name: string; vendor_type: string }[],
    enabled: assignmentType === "vendor",
  });
  const workers = useQuery({
    queryKey: ["production-workers"],
    queryFn: async () => (await api.get("/production/workers")).data.data as Worker[],
    enabled: assignmentType === "internal_worker",
  });

  const isOther = selected === "Other";
  const stageName = isOther ? customName.trim() : (selected ?? "");
  const stageType = STAGE_CHIPS.find((c) => c.name === selected)?.stage_type ?? "making";

  const mut = useMutation({
    mutationFn: () =>
      api.post(`/production/lots/${lotId}/stages`, {
        stage_type: stageType,
        stage_name: stageName,
        assignment_type: assignmentType || undefined,
        vendor_id: assignmentType === "vendor" ? (vendorId || undefined) : undefined,
        worker_id: assignmentType === "internal_worker" ? (workerId || undefined) : undefined,
        notes: notes || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lot", lotId] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message;
      setError(msg ?? "Failed to add stage");
    },
  });

  return (
    <ModalShell maxWidth="max-w-lg" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Add Stage</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-2">Stage</label>
          <div className="flex flex-wrap gap-2">
            {STAGE_CHIPS.map((c) => {
              const isActive = selected === c.name;
              return (
                <button
                  key={c.name}
                  type="button"
                  onClick={() => setSelected(c.name)}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-full border text-sm font-medium transition-colors"
                  style={isActive ? { borderColor: INDIGO, background: `${INDIGO}12`, color: INDIGO } : { borderColor: "hsl(var(--border))" }}
                >
                  <c.icon className="h-3.5 w-3.5" />
                  {c.name}
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => setSelected("Other")}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-full border border-dashed text-sm font-medium transition-colors"
              style={isOther ? { borderColor: INDIGO, background: `${INDIGO}12`, color: INDIGO } : { borderColor: "hsl(var(--border))" }}
            >
              <MoreHorizontal className="h-3.5 w-3.5" />
              Other
            </button>
          </div>
          {isOther && (
            <input
              className={`${inputCls} mt-2`}
              placeholder="Custom stage name"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              autoFocus
            />
          )}
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-2">Assignment (optional)</label>
          <AssignmentTypeToggle value={assignmentType} onChange={setAssignmentType} allowNone />
          {assignmentType === "vendor" && (
            <SearchableSelect
              value={vendorId}
              onChange={setVendorId}
              placeholder="Start typing a vendor"
              accent={INDIGO}
              options={(vendors.data ?? []).map((v) => ({ value: v.id, label: v.name, meta: v.vendor_type }))}
            />
          )}
          {assignmentType === "internal_worker" && (
            <SearchableSelect
              value={workerId}
              onChange={setWorkerId}
              placeholder="Start typing a worker"
              accent={INDIGO}
              options={(workers.data ?? []).map((w) => ({ value: w.id, label: w.name, meta: w.role_title ?? undefined }))}
            />
          )}
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
          <textarea className={`${inputCls} resize-none`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => { setError(""); mut.mutate(); }}
          disabled={mut.isPending || !stageName}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mut.isPending ? "Adding…" : "Add stage"}
        </button>
      </div>
    </ModalShell>
  );
}

// ── Receive Challan Modal ──────────────────────────────────────────────────────
function ReceiveChallanModal({ challan, lotId, onClose }: { challan: StageChallan; lotId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [inDate, setInDate] = useState(today);
  const [inQty, setInQty] = useState(String(challan.out_qty));
  const [rejectedQty, setRejectedQty] = useState("0");
  const [billAmount, setBillAmount] = useState("");
  const [notes, setNotes] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const pending = challan.out_qty - (Number(inQty) || 0) - (Number(rejectedQty) || 0);

  const mut = useMutation({
    mutationFn: () =>
      api.patch(`/production/stages/challans/${challan.id}/receive`, {
        in_date: inDate,
        in_qty: Number(inQty) || 0,
        rejected_qty: Number(rejectedQty) || 0,
        bill_amount: billAmount ? Number(billAmount) : undefined,
        notes: notes || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lot", lotId] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error;
      setErr(typeof msg === "string" ? msg : "Failed to receive challan");
    },
  });

  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Receive — {challan.challan_number}</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <p className="text-xs text-muted-foreground">Sent OUT: {challan.out_qty} pcs on {challan.out_date}</p>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">In Date</label>
          <input type="date" className={inputCls} value={inDate} onChange={(e) => setInDate(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">First Quality</label>
            <input type="number" className={inputCls} value={inQty} onChange={(e) => setInQty(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Rejected</label>
            <input type="number" className={inputCls} value={rejectedQty} onChange={(e) => setRejectedQty(e.target.value)} />
          </div>
        </div>
        <p className="text-[11px] text-muted-foreground -mt-2">
          Pending / still with {challan.worker_id ? "worker" : "vendor"}: <span className="font-semibold" style={{ color: pending === 0 ? INDIGO : "#A096F7" }}>{pending}</span>
          {" "}({challan.out_qty} sent = {inQty || 0} received + {rejectedQty || 0} rejected + {pending} pending)
        </p>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Bill Amount / Cost (₹)</label>
          <input type="number" step="0.01" className={inputCls} value={billAmount} onChange={(e) => setBillAmount(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
          <textarea className={`${inputCls} resize-none`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
        {err && <p className="text-xs text-[#1D0DB0]">{err}</p>}
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => { setErr(null); mut.mutate(); }}
          disabled={mut.isPending}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mut.isPending ? "Saving…" : "Receive"}
        </button>
      </div>
    </ModalShell>
  );
}

// ── Start Fabric Processing Modal ─────────────────────────────────────────────
function StartFabricProcessingModal({ lotId, onClose }: { lotId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [processType, setProcessType] = useState<"dyeing" | "printing" | "other">("dyeing");
  const [vendorId, setVendorId] = useState("");
  const [inDate, setInDate] = useState(today);
  const [inputKg, setInputKg] = useState("");
  const [ratePerKg, setRatePerKg] = useState("");
  const [notes, setNotes] = useState("");

  const vendors = useQuery({
    queryKey: ["vendors", "ref"],
    queryFn: async () => (await api.get("/purchase/vendors", { params: { page_size: 200 } })).data.data as { id: string; name: string; vendor_type: string }[],
  });

  const mut = useMutation({
    mutationFn: () =>
      api.post(`/production/lots/${lotId}/fabric-processing`, {
        process_type: processType,
        vendor_id: vendorId || undefined,
        in_date: inDate,
        input_kg: Number(inputKg) || 0,
        rate_per_kg: ratePerKg ? Number(ratePerKg) : undefined,
        notes: notes || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lot", lotId] });
      onClose();
    },
  });

  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Start Fabric Processing</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Process Type</label>
          <SearchableSelect
            value={processType}
            onChange={(v) => setProcessType(v as typeof processType)}
            placeholder="Select type"
            accent={INDIGO}
            options={[{ value: "dyeing", label: "Dyeing" }, { value: "printing", label: "Printing" }, { value: "other", label: "Other" }]}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Vendor (optional)</label>
          <SearchableSelect
            value={vendorId}
            onChange={setVendorId}
            placeholder="In-house / select vendor"
            accent={INDIGO}
            options={(vendors.data ?? []).map((v) => ({ value: v.id, label: v.name, meta: v.vendor_type }))}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">In Date</label>
            <input type="date" className={inputCls} value={inDate} onChange={(e) => setInDate(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Input (kg)</label>
            <input type="number" step="0.001" className={inputCls} value={inputKg} onChange={(e) => setInputKg(e.target.value)} />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Rate per Kg (₹)</label>
          <input type="number" step="0.01" className={inputCls} value={ratePerKg} onChange={(e) => setRatePerKg(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
          <textarea className={`${inputCls} resize-none`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => mut.mutate()}
          disabled={mut.isPending || !inputKg}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mut.isPending ? "Starting…" : "Start"}
        </button>
      </div>
    </ModalShell>
  );
}

// ── Complete Fabric Processing Modal ──────────────────────────────────────────
function CompleteFabricProcessingModal({ entry, lotId, onClose }: { entry: FabricProcessing; lotId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [outDate, setOutDate] = useState(today);
  const [outputKg, setOutputKg] = useState(String(entry.input_kg));
  const [billAmount, setBillAmount] = useState("");
  const [notes, setNotes] = useState("");

  const mut = useMutation({
    mutationFn: () =>
      api.patch(`/production/fabric-processing/${entry.id}/complete`, {
        out_date: outDate,
        output_kg: Number(outputKg) || 0,
        bill_amount: billAmount ? Number(billAmount) : undefined,
        notes: notes || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lot", lotId] });
      onClose();
    },
  });

  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Complete Processing</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <p className="text-xs text-muted-foreground">Input: {entry.input_kg} kg on {entry.in_date}</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Out Date</label>
            <input type="date" className={inputCls} value={outDate} onChange={(e) => setOutDate(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Output (kg)</label>
            <input type="number" step="0.001" className={inputCls} value={outputKg} onChange={(e) => setOutputKg(e.target.value)} />
          </div>
        </div>
        <p className="text-[11px] text-muted-foreground">
          A weight increase or decrease is both valid here — dyeing/printing can gain weight from absorbed dye/moisture.
        </p>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Bill Amount (₹)</label>
          <input type="number" step="0.01" className={inputCls} value={billAmount} onChange={(e) => setBillAmount(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
          <textarea className={`${inputCls} resize-none`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mut.isPending ? "Saving…" : "Complete"}
        </button>
      </div>
    </ModalShell>
  );
}

// ── Edit Fabric Processing Modal ──────────────────────────────────────────────
function EditFabricProcessingModal({ entry, lotId, onClose }: { entry: FabricProcessing; lotId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [vendorId, setVendorId] = useState(entry.vendor_id ?? "");
  const [inDate, setInDate] = useState(entry.in_date);
  const [inputKg, setInputKg] = useState(String(entry.input_kg));
  const [ratePerKg, setRatePerKg] = useState(entry.rate_per_kg != null ? String(entry.rate_per_kg) : "");
  const [outDate, setOutDate] = useState(entry.out_date ?? "");
  const [outputKg, setOutputKg] = useState(entry.output_kg != null ? String(entry.output_kg) : "");
  const [billAmount, setBillAmount] = useState(entry.bill_amount != null ? String(entry.bill_amount) : "");
  const [notes, setNotes] = useState(entry.notes ?? "");

  const vendors = useQuery({
    queryKey: ["vendors", "ref"],
    queryFn: async () => (await api.get("/purchase/vendors", { params: { page_size: 200 } })).data.data as { id: string; name: string; vendor_type: string }[],
  });

  const mut = useMutation({
    mutationFn: () =>
      api.patch(`/production/fabric-processing/${entry.id}`, {
        vendor_id: vendorId || null,
        in_date: inDate,
        input_kg: Number(inputKg) || 0,
        rate_per_kg: ratePerKg ? Number(ratePerKg) : null,
        out_date: entry.status === "completed" ? (outDate || null) : undefined,
        output_kg: entry.status === "completed" ? (outputKg ? Number(outputKg) : null) : undefined,
        bill_amount: entry.status === "completed" ? (billAmount ? Number(billAmount) : null) : undefined,
        notes: notes || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lot", lotId] });
      onClose();
    },
  });

  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Edit Fabric Processing</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Vendor (optional)</label>
          <SearchableSelect
            value={vendorId}
            onChange={setVendorId}
            placeholder="In-house / select vendor"
            accent={INDIGO}
            options={(vendors.data ?? []).map((v) => ({ value: v.id, label: v.name, meta: v.vendor_type }))}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">In Date</label>
            <input type="date" className={inputCls} value={inDate} onChange={(e) => setInDate(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Input (kg)</label>
            <input type="number" step="0.001" className={inputCls} value={inputKg} onChange={(e) => setInputKg(e.target.value)} />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Rate per Kg (₹)</label>
          <input type="number" step="0.01" className={inputCls} value={ratePerKg} onChange={(e) => setRatePerKg(e.target.value)} />
        </div>
        {entry.status === "completed" && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Out Date</label>
                <input type="date" className={inputCls} value={outDate} onChange={(e) => setOutDate(e.target.value)} />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Output (kg)</label>
                <input type="number" step="0.001" className={inputCls} value={outputKg} onChange={(e) => setOutputKg(e.target.value)} />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Bill Amount (₹)</label>
              <input type="number" step="0.01" className={inputCls} value={billAmount} onChange={(e) => setBillAmount(e.target.value)} />
            </div>
          </>
        )}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
          <textarea className={`${inputCls} resize-none`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mut.isPending ? "Saving…" : "Save Changes"}
        </button>
      </div>
    </ModalShell>
  );
}

// ── Issue Material Modal (MIS create — one or more line items) ────────────────
interface MISItemRow { key: string; productId: string; quantity: string; unitId: string; unitCost: string }
let misRowSeq = 0;
function newMisRowId() {
  misRowSeq += 1;
  return `mis-row-${Date.now()}-${misRowSeq}`;
}

function IssueMaterialModal({ lotId, onClose }: { lotId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [warehouseId, setWarehouseId] = useState("");
  const [issueDate, setIssueDate] = useState(today);
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<MISItemRow[]>([
    { key: newMisRowId(), productId: "", quantity: "", unitId: "", unitCost: "0" },
  ]);
  const [error, setError] = useState("");

  const products = useQuery({
    queryKey: ["products", "all-ref"],
    queryFn: async () => (await api.get("/products", { params: { page_size: 500 } })).data.data as { id: string; name: string; code: string; product_type: string }[],
  });
  const warehouses = useQuery({
    queryKey: ["master-warehouses"],
    queryFn: async () => (await api.get("/master/warehouses")).data.data as { id: string; name: string }[],
  });
  const units = useQuery({
    queryKey: ["master-units"],
    queryFn: async () => (await api.get("/master/units")).data.data as { id: string; name: string; abbreviation: string }[],
  });

  function addItem() {
    setItems((r) => [...r, { key: newMisRowId(), productId: "", quantity: "", unitId: "", unitCost: "0" }]);
  }
  function updateItem(key: string, patch: Partial<MISItemRow>) {
    setItems((r) => r.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }
  function removeItem(key: string) {
    setItems((r) => (r.length > 1 ? r.filter((row) => row.key !== key) : r));
  }

  const validItems = items.filter((it) => it.productId && it.quantity && it.unitId);

  const mut = useMutation({
    mutationFn: () =>
      api.post("/production/mis", {
        production_lot_id: lotId,
        warehouse_id: warehouseId,
        issue_date: issueDate,
        notes: notes || undefined,
        items: validItems.map((it) => ({
          product_id: it.productId,
          issued_qty: Number(it.quantity) || 0,
          unit_id: it.unitId,
          unit_cost: Number(it.unitCost) || 0,
        })),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-mis", "lot", lotId] });
      qc.invalidateQueries({ queryKey: ["production-lot", lotId] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: { message?: string }; detail?: string } } })
        ?.response?.data?.error?.message
        ?? (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Failed to issue material");
    },
  });

  return (
    <ModalShell maxWidth="max-w-2xl" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Issue Material</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Warehouse</label>
            <SearchableSelect
              value={warehouseId}
              onChange={setWarehouseId}
              placeholder="Select warehouse"
              accent={INDIGO}
              options={(warehouses.data ?? []).map((w) => ({ value: w.id, label: w.name }))}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Issue Date</label>
            <input type="date" className={inputCls} value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
          </div>
        </div>

        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2">Items</p>
          <div className="space-y-2">
            {items.map((it) => (
              <div key={it.key} className="p-3 rounded-xl border border-border bg-background">
                <div className="grid grid-cols-12 gap-2 items-start">
                  <div className="col-span-5">
                    <SearchableSelect
                      value={it.productId}
                      onChange={(v) => updateItem(it.key, { productId: v })}
                      placeholder="Select material"
                      accent={INDIGO}
                      options={(products.data ?? [])
                        .filter((p) => p.product_type !== "finished_good")
                        .map((p) => ({ value: p.id, label: p.name, meta: `${p.product_type} · ${p.code}` }))}
                    />
                  </div>
                  <div className="col-span-2">
                    <input type="number" step="0.0001" className={inputCls} placeholder="Qty" value={it.quantity} onChange={(e) => updateItem(it.key, { quantity: e.target.value })} />
                  </div>
                  <div className="col-span-2">
                    <SearchableSelect
                      value={it.unitId}
                      onChange={(v) => updateItem(it.key, { unitId: v })}
                      placeholder="Unit"
                      accent={INDIGO}
                      options={(units.data ?? []).map((u) => ({ value: u.id, label: u.abbreviation || u.name }))}
                    />
                  </div>
                  <div className="col-span-2">
                    <input type="number" step="0.01" className={inputCls} placeholder="Rate (₹)" value={it.unitCost} onChange={(e) => updateItem(it.key, { unitCost: e.target.value })} />
                  </div>
                  <div className="col-span-1 flex justify-end">
                    <button type="button" onClick={() => removeItem(it.key)} className="p-1.5 rounded-md text-muted-foreground hover:text-[#1D0DB0] hover:bg-[#1D0DB0]/10 transition-colors">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={addItem}
            className="mt-2 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border border-dashed border-border text-muted-foreground hover:text-foreground hover:border-foreground/40 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" /> Add Item
          </button>
        </div>

        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
          <textarea className={`${inputCls} resize-none`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => { setError(""); mut.mutate(); }}
          disabled={mut.isPending || !warehouseId || validItems.length === 0}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mut.isPending ? "Issuing…" : "Issue Material"}
        </button>
      </div>
    </ModalShell>
  );
}

// ── Record Output Modal (FG receive with quality split) ───────────────────────
function RecordOutputModal({ lotId, onClose }: { lotId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [productId, setProductId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [unitId, setUnitId] = useState("");
  const [outputDate, setOutputDate] = useState(today);
  const [quantity, setQuantity] = useState("");
  const [rejectedQty, setRejectedQty] = useState("0");
  const [unitCost, setUnitCost] = useState("0");

  const products = useQuery({
    queryKey: ["products", "finished_good"],
    queryFn: async () => (await api.get("/products", { params: { product_type: "finished_good", page_size: 200 } })).data.data as { id: string; name: string; code: string }[],
  });
  const warehouses = useQuery({
    queryKey: ["master-warehouses"],
    queryFn: async () => (await api.get("/master/warehouses")).data.data as { id: string; name: string }[],
  });
  const units = useQuery({
    queryKey: ["master-units"],
    queryFn: async () => (await api.get("/master/units")).data.data as { id: string; name: string; abbreviation: string }[],
  });

  const mut = useMutation({
    mutationFn: () =>
      api.post("/production/outputs", {
        production_lot_id: lotId,
        warehouse_id: warehouseId,
        output_date: outputDate,
        product_id: productId,
        quantity: Number(quantity) || 0,
        rejected_qty: rejectedQty ? Number(rejectedQty) : undefined,
        unit_id: unitId,
        unit_cost: Number(unitCost) || 0,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lot", lotId] });
      qc.invalidateQueries({ queryKey: ["production-outputs", "lot", lotId] });
      onClose();
    },
  });

  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Record Output</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Product</label>
          <SearchableSelect
            value={productId}
            onChange={setProductId}
            placeholder="Select finished good"
            accent={INDIGO}
            options={(products.data ?? []).map((p) => ({ value: p.id, label: p.name, meta: p.code }))}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Warehouse</label>
            <SearchableSelect
              value={warehouseId}
              onChange={setWarehouseId}
              placeholder="Select warehouse"
              accent={INDIGO}
              options={(warehouses.data ?? []).map((w) => ({ value: w.id, label: w.name }))}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Unit</label>
            <SearchableSelect
              value={unitId}
              onChange={setUnitId}
              placeholder="Select unit"
              accent={INDIGO}
              options={(units.data ?? []).map((u) => ({ value: u.id, label: u.abbreviation || u.name }))}
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Output Date</label>
          <input type="date" className={inputCls} value={outputDate} onChange={(e) => setOutputDate(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">First Quality Qty</label>
            <input type="number" className={inputCls} value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Rejected Qty</label>
            <input type="number" className={inputCls} value={rejectedQty} onChange={(e) => setRejectedQty(e.target.value)} />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Unit Cost (₹)</label>
          <input type="number" step="0.01" className={inputCls} value={unitCost} onChange={(e) => setUnitCost(e.target.value)} />
        </div>
        <p className="text-[11px] text-muted-foreground">
          Only First Quality Qty is received into sellable inventory. Rejected Qty is recorded for visibility only.
        </p>
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => mut.mutate()}
          disabled={mut.isPending || !productId || !warehouseId || !unitId || !quantity}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mut.isPending ? "Saving…" : "Record"}
        </button>
      </div>
    </ModalShell>
  );
}

// ── Job Work Challan Row ────────────────────────────────────────────────────────
function ChallanRow({ challan, lotId, assigneeName, onReceive }: { challan: StageChallan; lotId: string; assigneeName: string; onReceive: () => void }) {
  const qc = useQueryClient();
  const isWorker = !!challan.worker_id;
  const billMut = useMutation({
    mutationFn: () =>
      api.patch(`/production/stages/challans/${challan.id}/bill`, {
        bill_received: true,
        bill_received_date: new Date().toISOString().slice(0, 10),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["production-lot", lotId] }),
  });

  return (
    <div className="flex items-center justify-between text-xs px-3 py-2 rounded-lg bg-muted/30 flex-wrap gap-2">
      <div className="flex items-center gap-2">
        <span className="font-mono">{challan.challan_number}</span>
        <span className="text-muted-foreground">{assigneeName}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground">OUT {challan.out_qty} · {challan.out_date}</span>
        {challan.status === "out" ? (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold" style={{ background: "#A096F718", color: "#A096F7" }}>
            Out at {isWorker ? "Worker" : "Vendor"}
          </span>
        ) : (
          <span className="text-muted-foreground">
            IN {challan.in_qty} · {challan.in_date}
            {(challan.rejected_qty ?? 0) > 0 && <> · Rej {challan.rejected_qty}</>}
            {challan.pending_qty > 0 && <> · Pending {challan.pending_qty}</>}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        {challan.bill_amount != null && <span className="text-muted-foreground">{isWorker ? "Cost" : "Bill"} {INR(Number(challan.bill_amount))}</span>}
        {!isWorker && challan.status !== "out" && (
          challan.bill_received ? (
            <span className="px-2 py-0.5 rounded text-[11px] font-bold" style={{ background: "#0F78FF18", color: "#0F78FF" }}>
              Bill Received
            </span>
          ) : (
            <button
              onClick={() => billMut.mutate()}
              disabled={billMut.isPending}
              className="text-[11px] font-semibold hover:opacity-80 transition-opacity disabled:opacity-50"
              style={{ color: INDIGO }}
            >
              {billMut.isPending ? "Saving…" : "Mark Bill Received"}
            </button>
          )
        )}
        {(challan.status === "out" || challan.status === "partial") && (
          <button onClick={onReceive} className="text-[11px] font-semibold hover:opacity-80 transition-opacity" style={{ color: INDIGO }}>
            Receive
          </button>
        )}
      </div>
    </div>
  );
}

// ── Stage Card ────────────────────────────────────────────────────────────────
function StageCard({
  stage, idx, lotId, vendorById, workerById, onEditRate, onAddEntry, onSendToVendor, onReceiveChallan,
}: {
  stage: Stage; idx: number; lotId: string; vendorById: Map<string, string>; workerById: Map<string, string>;
  onEditRate: () => void; onAddEntry: () => void; onSendToVendor: () => void;
  onReceiveChallan: (challan: StageChallan) => void;
}) {
  const sortedEntries = [...stage.entries].sort((a, b) => a.entry_date.localeCompare(b.entry_date));
  const sortedChallans = [...stage.challans].sort((a, b) => a.out_date.localeCompare(b.out_date));
  const isAssigned = !!stage.assignment_type;
  const showChallans = isAssigned || sortedChallans.length > 0;
  const pending = stage.sent_qty - stage.received_qty - stage.rejected_qty;
  const pendingChallan = [...sortedChallans].reverse().find((c) => c.status === "out" || c.status === "partial");
  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-2.5 bg-muted/30 border-b border-border">
        <span className="text-xs font-mono text-muted-foreground">{idx + 1}</span>
        <span className="text-sm font-semibold flex-1">{stage.stage_name}</span>
        <StatusBadge status={stage.status} />
      </div>
      <div className="px-4 py-3 grid grid-cols-4 gap-3 text-xs border-b border-border">
        <div><p className="text-muted-foreground">Tolerance</p><p className="font-medium mt-0.5">{stage.tolerance_pct != null ? `${Number(stage.tolerance_pct)}%` : "—"}</p></div>
        <div><p className="text-muted-foreground">Input / Output Unit</p><p className="font-medium mt-0.5">{stage.input_unit ?? "—"} / {stage.output_unit ?? "—"}</p></div>
        <div><p className="text-muted-foreground">Planned Rate</p><p className="font-medium mt-0.5">{stage.planned_rate != null ? INR(Number(stage.planned_rate)) : "—"}</p></div>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-muted-foreground">Rate / Pc</p>
            <p className="font-medium mt-0.5">{stage.rate_per_pc != null ? INR(Number(stage.rate_per_pc)) : "—"}</p>
          </div>
          <button onClick={onEditRate} className="p-1 rounded hover:bg-muted text-muted-foreground transition-colors" title="Edit rate">
            <Pencil className="h-3 w-3" />
          </button>
        </div>
      </div>
      <div className="px-4 py-3 grid grid-cols-5 gap-3 text-xs border-b border-border bg-muted/10">
        <div>
          <p className="text-muted-foreground">Planned Qty</p>
          <p className="font-medium mt-0.5">{stage.planned_qty ?? "—"}</p>
        </div>
        {isAssigned ? (
          <>
            <div><p className="text-muted-foreground">Sent OUT</p><p className="font-medium mt-0.5">{stage.sent_qty}</p></div>
            <div>
              <p className="text-muted-foreground">First Quality</p>
              <p className="font-medium mt-0.5">
                {stage.received_qty}
                {pending > 0 && <span className="ml-1.5 text-[11px]" style={{ color: "#A096F7" }}>({pending} pending)</span>}
              </p>
            </div>
          </>
        ) : (
          <>
            <div><p className="text-muted-foreground">Input</p><p className="font-medium mt-0.5">{stage.input_qty}</p></div>
            <div><p className="text-muted-foreground">Output</p><p className="font-medium mt-0.5">{stage.output_qty}</p></div>
          </>
        )}
        <div><p className="text-muted-foreground">Rejected</p><p className="font-medium mt-0.5 text-[#1D0DB0]">{stage.rejected_qty}</p></div>
        <div><p className="text-muted-foreground">Bill Amount</p><p className="font-semibold mt-0.5" style={{ color: INDIGO }}>{stage.bill_amount != null ? INR(Number(stage.bill_amount)) : "—"}</p></div>
      </div>
      <div className="px-4 py-3 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Entries</p>
          <div className="flex items-center gap-3">
            {pendingChallan ? (
              <button onClick={() => onReceiveChallan(pendingChallan)} className="flex items-center gap-1 text-[11px] font-semibold hover:opacity-80 transition-opacity" style={{ color: INDIGO }}>
                <Inbox className="h-3 w-3" /> Receive
              </button>
            ) : (
              <button onClick={onSendToVendor} className="flex items-center gap-1 text-[11px] font-semibold hover:opacity-80 transition-opacity" style={{ color: INDIGO }}>
                <Truck className="h-3 w-3" /> Send
              </button>
            )}
            <button onClick={onAddEntry} className="flex items-center gap-1 text-[11px] font-semibold hover:opacity-80 transition-opacity" style={{ color: INDIGO }}>
              <Plus className="h-3 w-3" /> Log Entry
            </button>
          </div>
        </div>
        {sortedEntries.length === 0 ? (
          <p className="text-xs text-muted-foreground">No entries logged yet.</p>
        ) : (
          <div className="space-y-1.5">
            {sortedEntries.map((e) => (
              <div key={e.id} className="flex items-center justify-between text-xs px-3 py-1.5 rounded-lg bg-muted/30">
                <span className="text-muted-foreground">{e.entry_date}</span>
                <span>In {e.pieces_in} · Out {e.pieces_out} · Rej {e.rejected}</span>
                <span className="text-muted-foreground">{[e.operator, e.machine].filter(Boolean).join(" · ") || "—"}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      {showChallans && (
        <div className="px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">Job Work / Assignments</p>
          {sortedChallans.length === 0 ? (
            <p className="text-xs text-muted-foreground">No assignments sent yet.</p>
          ) : (
            <div className="space-y-1.5">
              {sortedChallans.map((c) => (
                <ChallanRow
                  key={c.id} challan={c} lotId={lotId}
                  assigneeName={(c.worker_id ? workerById.get(c.worker_id) : c.vendor_id ? vendorById.get(c.vendor_id) : null) ?? "—"}
                  onReceive={() => onReceiveChallan(c)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function LotDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const [showEdit, setShowEdit] = useState(false);
  const [rateStage, setRateStage] = useState<Stage | null>(null);
  const [entryStage, setEntryStage] = useState<Stage | null>(null);
  const [actualCost, setActualCost] = useState<LotAdditionalCost | null>(null);
  const [showAddCost, setShowAddCost] = useState(false);
  const [vendorStage, setVendorStage] = useState<Stage | null>(null);
  const [receiveChallan, setReceiveChallan] = useState<StageChallan | null>(null);
  const [showAddStage, setShowAddStage] = useState(false);
  const [showIssueMaterial, setShowIssueMaterial] = useState(false);
  const [showStartFabric, setShowStartFabric] = useState(false);
  const [completeFabricEntry, setCompleteFabricEntry] = useState<FabricProcessing | null>(null);
  const [editFabricEntry, setEditFabricEntry] = useState<FabricProcessing | null>(null);
  const [showRecordOutput, setShowRecordOutput] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [showEditPrice, setShowEditPrice] = useState(false);
  const [deleteErr, setDeleteErr] = useState<string | null>(null);
  const [reportBusy, setReportBusy] = useState<"download" | "preview" | null>(null);
  const [reportErr, setReportErr] = useState<string | null>(null);

  const { data: lot, isLoading } = useQuery({
    queryKey: ["production-lot", id],
    queryFn: async () => (await api.get(`/production/lots/${id}`)).data.data as LotDetail,
    enabled: !!id,
  });

  const sizes = useQuery({
    queryKey: ["master-sizes"],
    queryFn: async () => (await api.get("/master/sizes")).data.data as Size[],
  });

  const colours = useQuery({
    queryKey: ["master-colours"],
    queryFn: async () => (await api.get("/master/colours")).data.data as { id: string; name: string; hex_code: string | null }[],
  });

  const vendors = useQuery({
    queryKey: ["vendors", "ref"],
    queryFn: async () => (await api.get("/purchase/vendors", { params: { page_size: 200 } })).data.data as { id: string; name: string }[],
  });

  const workers = useQuery({
    queryKey: ["production-workers"],
    queryFn: async () => (await api.get("/production/workers")).data.data as Worker[],
  });

  const misQuery = useQuery({
    queryKey: ["production-mis", "lot", id],
    queryFn: async () => (await api.get("/production/mis", { params: { lot_id: id } })).data.data as MISRow[],
    enabled: !!id,
  });

  const outputsQuery = useQuery({
    queryKey: ["production-outputs", "lot", id],
    queryFn: async () => (await api.get("/production/outputs", { params: { lot_id: id } })).data.data as OutputRow[],
    enabled: !!id,
  });

  const statusMut = useMutation({
    mutationFn: (status: string) => api.post(`/production/lots/${id}/status`, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lot", id] });
      qc.invalidateQueries({ queryKey: ["production-lots"] });
    },
  });

  const reopenMut = useMutation({
    mutationFn: () => api.post(`/production/lots/${id}/reopen`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lot", id] });
      qc.invalidateQueries({ queryKey: ["production-lots"] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: () => api.delete(`/production/lots/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lots"] });
      router.push("/production/lots");
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error;
      setDeleteErr(typeof msg === "string" ? msg : "Failed to delete lot");
    },
  });

  async function handleReport(mode: "download" | "preview") {
    if (!lot) return;
    setReportBusy(mode);
    setReportErr(null);
    try {
      const res = await api.get(`/production/lots/${lot.id}/report.pdf`, {
        params: { preview: mode === "preview" },
        responseType: "blob",
      });
      const blobUrl = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      if (mode === "preview") {
        window.open(blobUrl, "_blank");
      } else {
        const disposition = res.headers["content-disposition"] as string | undefined;
        const match = disposition?.match(/filename="?([^"]+)"?/);
        const filename = match?.[1] ?? `Production_Report_${lot.lot_number.replace(/\//g, "-")}.pdf`;
        const a = document.createElement("a");
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
      setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
    } catch {
      setReportErr("Failed to generate the report. Please try again.");
    } finally {
      setReportBusy(null);
    }
  }

  if (isLoading || !lot) {
    return <div className="p-8"><p className="text-sm text-muted-foreground">Loading lot…</p></div>;
  }

  const sizeById = new Map((sizes.data ?? []).map((s) => [s.id, s.name]));
  const vendorById = new Map((vendors.data ?? []).map((v) => [v.id, v.name]));
  const workerById = new Map((workers.data ?? []).map((w) => [w.id, w.name]));
  const colourById = new Map((colours.data ?? []).map((c) => [c.id, c.name]));
  const nextStatus = STATUS_FLOW[lot.status];

  const cs = lot.cost_summary;

  return (
    <div className="p-8 space-y-8 max-w-6xl">
      <div className="flex items-start gap-4">
        <button onClick={() => router.push("/production/lots")} className="mt-1 p-2 rounded-lg hover:bg-muted text-muted-foreground transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div className="flex-1 flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">PRODUCTION / LOTS</p>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold tracking-tight">{lot.lot_number}</h1>
              <StatusBadge status={lot.status} />
            </div>
            <div className="flex gap-2 flex-wrap mt-3">
              {lot.style_name && (
                <span className="text-xs px-2.5 py-1 rounded" style={{ background: `${INDIGO}18`, color: INDIGO }}>
                  {lot.style_name}{lot.style_version ? ` v${lot.style_version}` : ""}
                </span>
              )}
              {lot.order_ref && <span className="text-xs px-2.5 py-1 rounded bg-muted">Order: {lot.order_ref}</span>}
              {lot.season && <span className="text-xs px-2.5 py-1 rounded bg-muted">{lot.season}</span>}
              {lot.delivery_date && <span className="text-xs px-2.5 py-1 rounded bg-muted">Delivery: {lot.delivery_date}</span>}
              {lot.final_output_unit && <span className="text-xs px-2.5 py-1 rounded bg-muted">Unit: {lot.final_output_unit}</span>}
              {lot.colour_id && (
                <span className="text-xs px-2.5 py-1 rounded bg-muted">
                  Colour: {colourById.get(lot.colour_id) ?? "—"}
                </span>
              )}
              {lot.planned_weight_kg != null && (
                <span className="text-xs px-2.5 py-1 rounded bg-muted">
                  {lot.actual_weight_kg != null ? `${lot.actual_weight_kg} / ` : ""}{lot.planned_weight_kg} kg
                </span>
              )}
            </div>
            {lot.notes && <p className="text-sm text-muted-foreground mt-3">{lot.notes}</p>}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">
            <button
              onClick={() => handleReport("preview")}
              disabled={reportBusy !== null}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border border-input hover:bg-muted transition-colors disabled:opacity-50"
            >
              <FileText className="h-4 w-4" /> {reportBusy === "preview" ? "Generating…" : "Preview Report"}
            </button>
            <button
              onClick={() => handleReport("download")}
              disabled={reportBusy !== null}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
              style={{ background: INDIGO }}
            >
              <Download className="h-4 w-4" /> {reportBusy === "download" ? "Generating…" : "Download Production Report"}
            </button>
            {nextStatus && lot.status !== "cancelled" && (
              <button
                onClick={() => statusMut.mutate(nextStatus)}
                disabled={statusMut.isPending}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 disabled:opacity-50"
                style={{ background: STATUS_HEX[nextStatus] }}
              >
                {statusMut.isPending ? "Updating…" : <>Advance to {nextStatus.replace(/_/g, " ")} <ChevronRight className="h-4 w-4" /></>}
              </button>
            )}
            {(lot.status === "cancelled" || lot.status === "completed") && (
              <button
                onClick={() => reopenMut.mutate()}
                disabled={reopenMut.isPending}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 disabled:opacity-50"
                style={{ background: INDIGO }}
              >
                <RotateCcw className="h-4 w-4" /> {reopenMut.isPending ? "Reopening…" : "Reopen"}
              </button>
            )}
            <button
              onClick={() => setShowEdit(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border border-input hover:bg-muted transition-colors"
            >
              <Pencil className="h-4 w-4" /> Edit
            </button>
            <button
              onClick={() => { setDeleteErr(null); setConfirmDelete(true); }}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border transition-colors"
              style={{ color: "#1D0DB0", borderColor: "#1D0DB04D" }}
            >
              <Trash2 className="h-4 w-4" /> Delete
            </button>
          </div>
        </div>
      </div>
      {reportErr && (
        <p className="text-xs px-3 py-2 rounded-lg -mt-4" style={{ background: "#1D0DB00D", color: "#1D0DB0" }}>
          {reportErr}
        </p>
      )}

      {/* Profitability — actual production economics */}
      <Card
        title="Profitability"
        subtitle="Actual cost, selling price and margin per saleable piece"
        action={
          <span
            className="text-[11px] font-bold px-2.5 py-1 rounded whitespace-nowrap"
            style={cs.is_final ? { background: "#0F78FF18", color: "#0F78FF" } : { background: "#A096F718", color: "#A096F7" }}
          >
            {cs.is_final ? "Final" : "Estimated — production in progress"}
          </span>
        }
      >
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">First Quality Pieces</p>
            <p className="text-2xl font-bold mt-1">{Number(cs.first_quality_qty).toLocaleString("en-IN")}</p>
            {boxesLabel(Number(cs.first_quality_qty), lot.pieces_per_box) && (
              <p className="text-[11px] text-muted-foreground mt-0.5">{boxesLabel(Number(cs.first_quality_qty), lot.pieces_per_box)}</p>
            )}
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Cost / Piece</p>
            <p className="text-2xl font-bold mt-1" style={{ color: INDIGO }}>
              {cs.cost_per_first_quality_piece != null ? INR(Number(cs.cost_per_first_quality_piece)) : "—"}
            </p>
            {cs.first_quality_qty === 0 && <p className="text-[11px] text-muted-foreground mt-0.5">No saleable output yet</p>}
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Selling Price / Piece</p>
              <button onClick={() => setShowEditPrice(true)} className="p-0.5 rounded hover:bg-muted text-muted-foreground transition-colors" title="Set selling price">
                <Pencil className="h-3 w-3" />
              </button>
            </div>
            {cs.actual_selling_price_per_piece != null ? (
              <>
                <p className="text-2xl font-bold mt-1">{INR(Number(cs.actual_selling_price_per_piece))}</p>
                {cs.selling_price_source && <p className="text-[11px] text-muted-foreground mt-0.5">{cs.selling_price_source}</p>}
              </>
            ) : (
              <>
                <p className="text-lg font-semibold mt-1.5 text-muted-foreground">Not configured</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">No sales order or product MRP</p>
              </>
            )}
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Profit / Piece</p>
            <p className="text-2xl font-bold mt-1" style={{ color: cs.profit_per_piece == null ? undefined : Number(cs.profit_per_piece) >= 0 ? "#0F78FF" : "#1D0DB0" }}>
              {cs.profit_per_piece != null ? INR(Number(cs.profit_per_piece)) : "—"}
            </p>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Gross Margin</p>
            <p className="text-2xl font-bold mt-1" style={{ color: cs.gross_margin_pct == null ? undefined : Number(cs.gross_margin_pct) >= 0 ? "#0F78FF" : "#1D0DB0" }}>
              {cs.gross_margin_pct != null ? `${Number(cs.gross_margin_pct).toFixed(2)}%` : "—"}
            </p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 mt-5 pt-5 border-t border-border">
          <div>
            <p className="text-xs text-muted-foreground">Total Revenue</p>
            <p className="text-lg font-semibold mt-1">{cs.actual_revenue != null ? INR(Number(cs.actual_revenue)) : "—"}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Total Actual Cost</p>
            <p className="text-lg font-semibold mt-1">{INR(Number(cs.total_actual))}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Total Profit</p>
            <p className="text-lg font-semibold mt-1" style={{ color: cs.actual_profit == null ? undefined : Number(cs.actual_profit) >= 0 ? "#0F78FF" : "#1D0DB0" }}>
              {cs.actual_profit != null ? INR(Number(cs.actual_profit)) : "—"}
            </p>
          </div>
        </div>
      </Card>

      {/* Planned / Target — comparison reference, kept separate from actuals */}
      <div className="bg-muted/20 border border-border rounded-2xl p-5">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-4">Planned / Target</p>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground text-xs">Planned Qty</p>
            <p className="text-lg font-semibold mt-1">{lot.planned_qty.toLocaleString("en-IN")}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Target Selling Price / Pc</p>
            <p className="text-lg font-semibold mt-1">{lot.target_sp != null ? INR(Number(lot.target_sp)) : "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Target Revenue</p>
            <p className="text-lg font-semibold mt-1">{cs.target_revenue != null ? INR(Number(cs.target_revenue)) : "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Planned Cost</p>
            <p className="text-lg font-semibold mt-1">{cs.total_planned != null ? INR(Number(cs.total_planned)) : "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Expected Margin</p>
            <p className="text-lg font-semibold mt-1">{cs.expected_margin_pct != null ? `${Number(cs.expected_margin_pct).toFixed(2)}%` : "—"}</p>
          </div>
        </div>
      </div>

      {/* Production yield */}
      <Card title="Production Yield" subtitle="How much of what was produced is actually saleable">
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground text-xs">Planned Qty</p>
            <p className="text-xl font-bold mt-1">{lot.planned_qty.toLocaleString("en-IN")}</p>
            {boxesLabel(lot.planned_qty, lot.pieces_per_box) && <p className="text-[11px] text-muted-foreground mt-0.5">{boxesLabel(lot.planned_qty, lot.pieces_per_box)}</p>}
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Total Output</p>
            <p className="text-xl font-bold mt-1">{Number(cs.total_output_qty).toLocaleString("en-IN")}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">First Quality</p>
            <p className="text-xl font-bold mt-1" style={{ color: "#0F78FF" }}>{Number(cs.first_quality_qty).toLocaleString("en-IN")}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Rejected</p>
            <p className="text-xl font-bold mt-1 text-[#1D0DB0]">{Number(cs.rejected_qty).toLocaleString("en-IN")}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Yield</p>
            <p className="text-xl font-bold mt-1">{cs.yield_pct != null ? `${Number(cs.yield_pct).toFixed(1)}%` : "—"}</p>
          </div>
        </div>
      </Card>

      <Card title="Cost Breakdown" subtitle="Every production cost component — planned vs actual, dynamically from this lot's stages">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                <th className="py-2 pr-4">Component</th>
                <th className="py-2 pr-4">Planned</th>
                <th className="py-2 pr-4">Actual</th>
                <th className="py-2 pr-4">Variance</th>
                <th className="py-2 pr-4">Variance %</th>
                <th className="py-2 pr-4">₹ / First Quality Pc</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {cs.components.map((c) => {
                const planned = c.planned_amount != null ? Number(c.planned_amount) : null;
                const actual = c.actual_amount != null ? Number(c.actual_amount) : null;
                const variance = c.variance_amount != null ? Number(c.variance_amount) : null;
                const variancePct = c.variance_pct != null ? Number(c.variance_pct) : null;
                const perPiece = actual != null && Number(cs.first_quality_qty) > 0 ? actual / Number(cs.first_quality_qty) : null;
                return (
                  <tr key={c.name}>
                    <td className="py-2 pr-4 font-medium">
                      {c.name}
                      {c.note && <p className="text-[11px] text-muted-foreground font-normal mt-0.5">{c.note}</p>}
                    </td>
                    <td className="py-2 pr-4">{planned != null ? INR(planned) : "—"}</td>
                    <td className="py-2 pr-4">{actual != null ? INR(actual) : "—"}</td>
                    <td className="py-2 pr-4">
                      {variance != null ? (
                        <span style={{ color: variance > 0 ? "#1D0DB0" : variance < 0 ? "#0F78FF" : undefined }}>
                          {variance > 0 ? "+" : ""}{INR(variance)}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="py-2 pr-4">
                      {variancePct != null ? (
                        <span style={{ color: variancePct > 0 ? "#1D0DB0" : variancePct < 0 ? "#0F78FF" : undefined }}>
                          {variancePct > 0 ? "+" : ""}{variancePct.toFixed(1)}%
                        </span>
                      ) : "—"}
                    </td>
                    <td className="py-2 pr-4 text-muted-foreground">{perPiece != null ? INR(perPiece) : "—"}</td>
                  </tr>
                );
              })}
              <tr className="font-semibold">
                <td className="py-2 pr-4">Total Cost</td>
                <td className="py-2 pr-4">{cs.total_planned != null ? INR(Number(cs.total_planned)) : "—"}</td>
                <td className="py-2 pr-4">{INR(Number(cs.total_actual))}</td>
                <td className="py-2 pr-4">
                  {cs.total_planned != null && (
                    <span style={{ color: Number(cs.total_actual) > Number(cs.total_planned) ? "#1D0DB0" : "#0F78FF" }}>
                      {Number(cs.total_actual) > Number(cs.total_planned) ? "+" : ""}
                      {INR(Number(cs.total_actual) - Number(cs.total_planned))}
                    </span>
                  )}
                </td>
                <td className="py-2 pr-4">
                  {cs.total_planned != null && Number(cs.total_planned) !== 0 ? (
                    <span style={{ color: Number(cs.total_actual) > Number(cs.total_planned) ? "#1D0DB0" : "#0F78FF" }}>
                      {(((Number(cs.total_actual) - Number(cs.total_planned)) / Number(cs.total_planned)) * 100).toFixed(1)}%
                    </span>
                  ) : "—"}
                </td>
                <td className="py-2 pr-4 text-muted-foreground">
                  {cs.cost_per_first_quality_piece != null ? INR(Number(cs.cost_per_first_quality_piece)) : "—"}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        {cs.missing_rate_warnings.length > 0 && (
          <div className="mt-4 space-y-1.5">
            {cs.missing_rate_warnings.map((w, i) => (
              <p key={i} className="text-xs px-3 py-2 rounded-lg" style={{ background: "#A096F718", color: "#A096F7" }}>
                {w}
              </p>
            ))}
          </div>
        )}
      </Card>

      {lot.sizes.length > 0 && (
        <Card title="Size Breakdown">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                  <th className="py-2 pr-4">Size</th>
                  <th className="py-2 pr-4">Planned</th>
                  <th className="py-2 pr-4">Cut</th>
                  <th className="py-2 pr-4">Sewn</th>
                  <th className="py-2 pr-4">Finished</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {lot.sizes.map((s) => (
                  <tr key={s.id}>
                    <td className="py-2 pr-4 font-medium">{sizeById.get(s.size_id) ?? "—"}</td>
                    <td className="py-2 pr-4">{s.planned_qty}</td>
                    <td className="py-2 pr-4">{s.cut_qty}</td>
                    <td className="py-2 pr-4">{s.sewn_qty}</td>
                    <td className="py-2 pr-4">{s.finished_qty}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Card
        title="Fabric Processing"
        subtitle="Dyeing / printing — precedes cutting; a weight gain or loss is expected, not an error"
        action={
          <button onClick={() => setShowStartFabric(true)} className="flex items-center gap-1 text-xs font-semibold hover:opacity-80 transition-opacity" style={{ color: INDIGO }}>
            <Plus className="h-3.5 w-3.5" /> Start Processing
          </button>
        }
      >
        {lot.fabric_processing.length === 0 ? (
          <Empty text="No fabric processing recorded yet." />
        ) : (
          <div className="space-y-2">
            {lot.fabric_processing.map((f) => {
              const gain = f.gain_loss_kg != null && f.gain_loss_kg > 0;
              const loss = f.gain_loss_kg != null && f.gain_loss_kg < 0;
              return (
                <div key={f.id} className="flex items-center justify-between px-4 py-2.5 rounded-xl border border-border text-sm flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] px-2 py-0.5 rounded bg-muted capitalize">{f.process_type}</span>
                    {f.vendor_id && <span className="text-muted-foreground text-xs">{vendorById.get(f.vendor_id) ?? "—"}</span>}
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-muted-foreground">In {Number(f.input_kg)}kg · {f.in_date}</span>
                    {f.status === "in_process" ? (
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold" style={{ background: "#A096F718", color: "#A096F7" }}>
                        In Process
                      </span>
                    ) : (
                      <>
                        <span className="text-muted-foreground">Out {Number(f.output_kg)}kg · {f.out_date}</span>
                        <span className="font-semibold" style={{ color: gain ? "#0F78FF" : loss ? "#1D0DB0" : undefined }}>
                          {gain ? "+" : ""}{f.gain_loss_kg}kg
                        </span>
                      </>
                    )}
                    {f.rate_per_kg != null && <span className="text-muted-foreground">{INR(Number(f.rate_per_kg))}/kg</span>}
                    {f.bill_amount != null && <span className="text-muted-foreground">{INR(Number(f.bill_amount))}</span>}
                    {f.status === "in_process" && (
                      <button onClick={() => setCompleteFabricEntry(f)} className="font-semibold hover:opacity-80 transition-opacity" style={{ color: INDIGO }}>
                        Complete
                      </button>
                    )}
                    <button onClick={() => setEditFabricEntry(f)} className="p-1 rounded hover:bg-muted text-muted-foreground transition-colors" title="Edit">
                      <Pencil className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <Card
        title="Production Stages"
        subtitle="Snapshotted from the Style at creation — editing the Style will not change these"
        action={
          !["completed", "cancelled"].includes(lot.status) && (
            <button
              onClick={() => setShowAddStage(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90"
              style={{ background: INDIGO }}
            >
              <Plus className="h-3.5 w-3.5" /> Add Stage
            </button>
          )
        }
      >
        {lot.stages.length === 0 ? (
          <Empty text="No stages on this lot." />
        ) : (
          <div className="space-y-3">
            {lot.stages.map((s, idx) => (
              <StageCard
                key={s.id}
                stage={s}
                idx={idx}
                lotId={lot.id}
                vendorById={vendorById}
                workerById={workerById}
                onEditRate={() => setRateStage(s)}
                onAddEntry={() => setEntryStage(s)}
                onSendToVendor={() => setVendorStage(s)}
                onReceiveChallan={(c) => setReceiveChallan(c)}
              />
            ))}
          </div>
        )}
      </Card>

      <Card
        title="Additional Costs & Agent Commission"
        subtitle="Optional per-lot costs — record the actual amount as it's incurred"
        action={
          <button onClick={() => setShowAddCost(true)} className="flex items-center gap-1 text-xs font-semibold hover:opacity-80" style={{ color: INDIGO }}>
            <Plus className="h-3.5 w-3.5" /> Add Cost
          </button>
        }
      >
        {lot.additional_costs.length === 0 ? (
          <Empty text="No additional costs on this lot." />
        ) : (
          <div className="space-y-2">
            {lot.additional_costs.map((a) => (
              <div key={a.id} className="flex items-center justify-between px-4 py-2.5 rounded-xl border border-border text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] px-2 py-0.5 rounded bg-muted">
                    {a.cost_type === "agent_commission" ? "Agent Commission" : "Additional"}
                  </span>
                  <span className="font-medium">{a.description}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-muted-foreground text-xs">
                    Planned {a.planned_amount != null ? INR(Number(a.planned_amount)) : "—"}
                  </span>
                  <span className="font-medium">
                    Actual {a.actual_amount != null ? INR(Number(a.actual_amount)) : "—"}
                  </span>
                  <button onClick={() => setActualCost(a)} className="p-1 rounded hover:bg-muted text-muted-foreground transition-colors" title="Record actual">
                    <Pencil className="h-3 w-3" />
                  </button>
                  <button
                    onClick={async () => { await api.delete(`/production/lots/additional-costs/${a.id}`); qc.invalidateQueries({ queryKey: ["production-lot", lot.id] }); }}
                    className="p-1 rounded hover:bg-muted text-muted-foreground transition-colors" title="Remove"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card
        title="Material Issues"
        subtitle="Raw material issued from warehouse to this lot"
        action={
          !["completed", "cancelled"].includes(lot.status) && (
            <button onClick={() => setShowIssueMaterial(true)} className="flex items-center gap-1 text-xs font-semibold hover:opacity-80 transition-opacity" style={{ color: INDIGO }}>
              <Plus className="h-3.5 w-3.5" /> Issue Material
            </button>
          )
        }
      >
        {(misQuery.data ?? []).length === 0 ? (
          <Empty text="No material issued yet." />
        ) : (
          <div className="space-y-2">
            {(misQuery.data ?? []).map((m) => {
              const hasExcess = m.items.some((it) => it.excess_qty != null && Number(it.excess_qty) > 0);
              return (
                <div key={m.id} className="flex items-center justify-between px-4 py-2.5 rounded-xl border border-border text-sm">
                  <span className="font-medium">{m.issue_number}</span>
                  <span className="text-muted-foreground">{m.issue_date}</span>
                  <StatusBadge status={m.status} />
                  {hasExcess && (
                    <span className="px-2 py-0.5 rounded text-[11px] font-bold" style={{ background: "#A096F718", color: "#A096F7" }}>
                      Excess
                    </span>
                  )}
                  <span className="font-medium">{INR(m.items.reduce((s, it) => s + Number(it.total_cost ?? 0), 0))}</span>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <Card
        title="Production Outputs"
        subtitle="Finished goods received into the warehouse from this lot"
        action={
          <button onClick={() => setShowRecordOutput(true)} className="flex items-center gap-1 text-xs font-semibold hover:opacity-80 transition-opacity" style={{ color: INDIGO }}>
            <Plus className="h-3.5 w-3.5" /> Record Output
          </button>
        }
      >
        {(outputsQuery.data ?? []).length === 0 ? (
          <Empty text="No output received yet." />
        ) : (
          <div className="space-y-2">
            {(outputsQuery.data ?? []).map((o) => (
              <div key={o.id} className="flex items-center justify-between px-4 py-2.5 rounded-xl border border-border text-sm flex-wrap gap-1">
                <span className="font-medium">{o.output_number}</span>
                <span className="text-muted-foreground">{o.output_date}</span>
                <span>{Number(o.quantity)} @ {INR(Number(o.unit_cost))}</span>
                {o.rejected_qty != null && Number(o.rejected_qty) > 0 && (
                  <span className="text-[#1D0DB0] text-xs">Rejected: {Number(o.rejected_qty)}</span>
                )}
                <span className="font-medium">{INR(Number(o.total_cost))}</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      {showEdit && <EditLotModal lot={lot} onClose={() => setShowEdit(false)} />}
      {showEditPrice && <EditSellingPriceModal lot={lot} onClose={() => setShowEditPrice(false)} />}
      {rateStage && <EditStageModal stage={rateStage} lotId={lot.id} onClose={() => setRateStage(null)} />}
      {entryStage && <AddEntryModal stage={entryStage} lotId={lot.id} onClose={() => setEntryStage(null)} />}
      {showAddCost && <AddLotCostModal lotId={lot.id} onClose={() => setShowAddCost(false)} />}
      {actualCost && <RecordActualCostModal cost={actualCost} lotId={lot.id} onClose={() => setActualCost(null)} />}
      {vendorStage && <SendToVendorModal stage={vendorStage} lotId={lot.id} onClose={() => setVendorStage(null)} />}
      {receiveChallan && <ReceiveChallanModal challan={receiveChallan} lotId={lot.id} onClose={() => setReceiveChallan(null)} />}
      {showAddStage && <AddStageModal lotId={lot.id} onClose={() => setShowAddStage(false)} />}
      {showIssueMaterial && <IssueMaterialModal lotId={lot.id} onClose={() => setShowIssueMaterial(false)} />}
      {showStartFabric && <StartFabricProcessingModal lotId={lot.id} onClose={() => setShowStartFabric(false)} />}
      {showRecordOutput && <RecordOutputModal lotId={lot.id} onClose={() => setShowRecordOutput(false)} />}
      {completeFabricEntry && <CompleteFabricProcessingModal entry={completeFabricEntry} lotId={lot.id} onClose={() => setCompleteFabricEntry(null)} />}
      {editFabricEntry && <EditFabricProcessingModal entry={editFabricEntry} lotId={lot.id} onClose={() => setEditFabricEntry(null)} />}
      {confirmDelete && (
        <ModalShell maxWidth="max-w-xs" onClose={() => setConfirmDelete(false)}>
          <div className="p-6">
            <p className="text-sm font-medium mb-1">Delete {lot.lot_number}?</p>
            <p className="text-xs text-muted-foreground mb-5">
              This action cannot be undone. Lots with recorded Material Issues or Production Output can't be deleted — cancel them instead.
            </p>
            {deleteErr && <p className="text-xs text-[#1D0DB0] mb-3">{deleteErr}</p>}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDelete(false)}
                className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => { setDeleteErr(null); deleteMut.mutate(); }}
                disabled={deleteMut.isPending}
                className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-colors disabled:opacity-50 hover:opacity-90"
                style={{ background: "#1D0DB0" }}
              >
                {deleteMut.isPending ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </ModalShell>
      )}
    </div>
  );
}
