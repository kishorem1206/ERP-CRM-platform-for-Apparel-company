"use client";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

const INDIGO = "#0049A7";

interface DashboardRow {
  lot_id: string;
  lot_number: string;
  style_name: string | null;
  customer_name: string | null;
  status: string;
  planned_qty: number;
  produced_qty: number;
  pending_qty: number;
  rejected_qty: number;
  rework_qty: number;
  yield_pct: string | null;
  material_shortage_lines: number;
  cost_planned: string;
  cost_actual: string;
  cost_variance_amount: string;
  dispatched_qty: string;
  returned_qty: string;
  undispatched_qty: string;
}
interface DashboardTotals {
  lots: number;
  planned_qty: number;
  produced_qty: number;
  pending_qty: number;
  rejected_qty: number;
  rework_qty: number;
  material_shortage_lines: number;
  cost_planned: string;
  cost_actual: string;
  cost_variance_amount: string;
  dispatched_qty: string;
  returned_qty: string;
}
interface DashboardData {
  rows: DashboardRow[];
  totals: DashboardTotals;
  lots_by_status: Record<string, number>;
}

function StatCard({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-xl border border-border px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold tabular-nums mt-0.5" style={accent ? { color: accent } : undefined}>{value}</p>
    </div>
  );
}

const STATUS_LABEL: Record<string, string> = {
  cutting: "Cutting", checking: "Checking", packing: "Packing", completed: "Completed", cancelled: "Cancelled",
};

const columns: Column<Record<string, unknown>>[] = [
  { key: "lot_number", header: "Lot #", sortable: true },
  { key: "style_name", header: "Style", render: (r) => (r.style_name as string) || "—" },
  { key: "customer_name", header: "Customer", render: (r) => (r.customer_name as string) || "—" },
  { key: "status", header: "Status", render: (r) => STATUS_LABEL[r.status as string] ?? (r.status as string) },
  { key: "planned_qty", header: "Planned", className: "text-right" },
  { key: "produced_qty", header: "Produced", className: "text-right" },
  { key: "pending_qty", header: "Pending", className: "text-right" },
  {
    key: "rejected_qty", header: "Rejected", className: "text-right",
    render: (r) => <span style={Number(r.rejected_qty) > 0 ? { color: "#1D0DB0", fontWeight: 600 } : undefined}>{String(r.rejected_qty)}</span>,
  },
  { key: "rework_qty", header: "Rework", className: "text-right" },
  {
    key: "material_shortage_lines", header: "Shortages", className: "text-right",
    render: (r) => (Number(r.material_shortage_lines) > 0
      ? <span className="px-2 py-0.5 rounded text-[11px] font-bold" style={{ background: "#1D0DB018", color: "#1D0DB0" }}>{String(r.material_shortage_lines)}</span>
      : "—"),
  },
  {
    key: "cost_variance_amount", header: "Cost Variance", className: "text-right",
    render: (r) => {
      const v = Number(r.cost_variance_amount);
      return <span style={{ color: v < 0 ? "#1D0DB0" : "#0F78FF" }}>{v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</span>;
    },
  },
  { key: "dispatched_qty", header: "Dispatched", className: "text-right" },
  { key: "returned_qty", header: "Returned", className: "text-right" },
];

export default function ProductionDashboardPage() {
  const router = useRouter();
  const { data, isLoading } = useQuery({
    queryKey: ["production-dashboard"],
    queryFn: async () => (await api.get("/production/dashboard")).data.data as DashboardData,
  });

  const totals = data?.totals;

  return (
    <div className="p-8 space-y-8">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">PRODUCTION / DASHBOARD</p>
        <h1 className="text-2xl font-bold tracking-tight">Production Progress Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Size/colour-wise pending quantities, material shortages, process-wise rejection &amp; rework, cost variance,
          and dispatch reconciliation — across every non-cancelled lot.
        </p>
      </div>

      {data && (
        <div className="flex items-center gap-2 flex-wrap">
          {Object.entries(data.lots_by_status).map(([status, count]) => (
            <span key={status} className="text-xs px-3 py-1.5 rounded-xl border border-border font-semibold">
              {STATUS_LABEL[status] ?? status}: <span className="tabular-nums">{count}</span>
            </span>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <StatCard label="Active Lots" value={totals?.lots ?? "—"} />
        <StatCard label="Planned Qty" value={totals?.planned_qty.toLocaleString("en-IN") ?? "—"} />
        <StatCard label="Produced Qty" value={totals?.produced_qty.toLocaleString("en-IN") ?? "—"} />
        <StatCard label="Pending Qty" value={totals?.pending_qty.toLocaleString("en-IN") ?? "—"} />
        <StatCard label="Rejected" value={totals?.rejected_qty.toLocaleString("en-IN") ?? "—"} accent={totals && totals.rejected_qty > 0 ? "#1D0DB0" : undefined} />
        <StatCard label="Rework" value={totals?.rework_qty.toLocaleString("en-IN") ?? "—"} />
        <StatCard label="Material Shortage Lines" value={totals?.material_shortage_lines ?? "—"} accent={totals && totals.material_shortage_lines > 0 ? "#1D0DB0" : undefined} />
        <StatCard label="Cost Planned" value={totals ? Number(totals.cost_planned).toLocaleString("en-IN", { maximumFractionDigits: 0 }) : "—"} />
        <StatCard label="Cost Actual" value={totals ? Number(totals.cost_actual).toLocaleString("en-IN", { maximumFractionDigits: 0 }) : "—"} />
        <StatCard
          label="Cost Variance"
          value={totals ? Number(totals.cost_variance_amount).toLocaleString("en-IN", { maximumFractionDigits: 0 }) : "—"}
          accent={totals && Number(totals.cost_variance_amount) < 0 ? "#1D0DB0" : "#0F78FF"}
        />
        <StatCard label="Dispatched" value={totals ? Number(totals.dispatched_qty).toLocaleString("en-IN") : "—"} />
        <StatCard label="Returned" value={totals ? Number(totals.returned_qty).toLocaleString("en-IN") : "—"} />
      </div>

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">LOT-WISE BREAKDOWN</p>
            <p className="text-sm font-medium mt-0.5">{data?.rows.length ?? 0} lot{(data?.rows.length ?? 0) !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <div className="p-6">
          <DataTable
            columns={columns}
            data={(data?.rows ?? []) as unknown as Record<string, unknown>[]}
            loading={isLoading}
            onRowClick={(row) => router.push(`/production/lots/${row.lot_id as string}`)}
            emptyMessage="No active production lots"
          />
        </div>
      </div>
    </div>
  );
}
