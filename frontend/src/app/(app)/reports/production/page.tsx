"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, RadialBarChart, RadialBar, PolarAngleAxis,
} from "recharts";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

const INDIGO = "#0049A7";
const TEAL   = "#8174F5";
const GREEN  = "#0F78FF";
const AMBER  = "#A096F7";
const RED    = "#1D0DB0";

const STATUS_HEX: Record<string, string> = {
  cutting:   TEAL,
  checking:  AMBER,
  packing:   "#A096F7",
  completed: GREEN,
  cancelled: RED,
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

type EffRow = Record<string, unknown> & {
  lot_number: string; style_name: string; planned_qty: number;
  actual_qty: number; status: string; delivery_date: string | null;
  lot_date: string; efficiency_pct: string; variance: number;
};

const columns: Column<EffRow>[] = [
  { key: "lot_date",    header: "Date" },
  { key: "lot_number",  header: "Lot No.", sortable: true },
  { key: "style_name",  header: "Style" },
  {
    key: "status", header: "Status",
    render: (r) => <StatusDot status={r.status} />,
  },
  { key: "planned_qty", header: "Planned",  sortable: true },
  { key: "actual_qty",  header: "Actual",   sortable: true },
  {
    key: "variance", header: "Variance",
    render: (r) => (
      <span className="tabular-nums font-medium" style={{ color: r.variance >= 0 ? "#0049A7" : "#1D0DB0" }}>
        {r.variance >= 0 ? "+" : ""}{r.variance}
      </span>
    ),
  },
  {
    key: "efficiency_pct", header: "Efficiency",
    render: (r) => {
      const pct = Number(r.efficiency_pct);
      return (
        <div className="flex items-center gap-2">
          <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.min(pct, 100)}%`,
                background: pct >= 90 ? GREEN : pct >= 70 ? AMBER : RED,
              }}
            />
          </div>
          <span className="text-sm font-semibold tabular-nums">{pct}%</span>
        </div>
      );
    },
  },
  { key: "delivery_date", header: "Delivery" },
];

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-xl shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold mb-1 text-foreground truncate max-w-[160px]">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>{p.name}: {Number(p.value).toLocaleString("en-IN")}</p>
      ))}
    </div>
  );
}

export default function ProductionEfficiencyPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["report-production-efficiency"],
    queryFn: async () => {
      const res = await api.get("/reports/production-efficiency");
      return (res.data.data ?? []) as EffRow[];
    },
  });

  const rows      = data ?? [];
  const completed = rows.filter((r) => r.status === "completed");
  const inProd    = rows.filter((r) => r.status === "cutting");
  const avgEff    = completed.length
    ? Math.round(completed.reduce((s, r) => s + Number(r.efficiency_pct), 0) / completed.length)
    : 0;

  const chartData = [...rows]
    .sort((a, b) => b.lot_date.localeCompare(a.lot_date))
    .slice(0, 10)
    .reverse()
    .map((r) => ({
      name:    r.lot_number.length > 10 ? r.lot_number.slice(-8) : r.lot_number,
      planned: r.planned_qty,
      actual:  r.actual_qty,
    }));

  const gaugeData = [{ name: "Efficiency", value: avgEff, fill: avgEff >= 90 ? GREEN : avgEff >= 70 ? AMBER : RED }];

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            REPORTS / PRODUCTION
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Production Report</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Planned vs actual output per production lot.
          </p>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "TOTAL LOTS",      value: rows.length,       color: undefined },
          { label: "CUTTING",         value: inProd.length,     color: "#0049A7" },
          { label: "COMPLETED",       value: completed.length,  color: "#0049A7" },
          { label: "AVG EFFICIENCY",  value: avgEff ? `${avgEff}%` : "—",
            color: avgEff >= 90 ? "#0049A7" : "#1D0DB0" },
        ].map((kpi) => (
          <div key={kpi.label} className="bg-card border border-border rounded-2xl p-6">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">{kpi.label}</p>
            <p className="text-2xl font-bold tracking-tight tabular-nums mt-1" style={kpi.color ? { color: kpi.color } : undefined}>{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Charts row */}
      {rows.length > 0 && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Planned vs Actual bar chart */}
          <div className="xl:col-span-2 bg-card border border-border rounded-2xl p-6">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">PLANNED VS ACTUAL OUTPUT</p>
            <p className="text-sm font-medium mt-0.5 mb-4">Most recent {chartData.length} lots</p>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(228 18% 88% / 0.6)" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Legend iconType="circle" iconSize={7}
                  formatter={(v) => <span style={{ fontSize: 11, color: "#64748B" }}>{v}</span>} />
                <Bar dataKey="planned" name="Planned" fill={INDIGO} radius={[4, 4, 0, 0]} maxBarSize={32} />
                <Bar dataKey="actual"  name="Actual"  fill={TEAL}   radius={[4, 4, 0, 0]} maxBarSize={32} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Efficiency gauge */}
          <div className="bg-card border border-border rounded-2xl p-6 flex flex-col items-center justify-center">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground self-start">AVG EFFICIENCY</p>
            <p className="text-xs text-muted-foreground mb-2 self-start mt-0.5">Completed lots only</p>
            {avgEff > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={160}>
                  <RadialBarChart cx="50%" cy="70%" innerRadius="60%" outerRadius="100%"
                    startAngle={180} endAngle={0} data={gaugeData}>
                    <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                    <RadialBar background dataKey="value" cornerRadius={8} angleAxisId={0} />
                  </RadialBarChart>
                </ResponsiveContainer>
                <p className="text-4xl font-bold -mt-10" style={{ color: gaugeData[0].fill }}>
                  {avgEff}%
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {avgEff >= 90 ? "Excellent" : avgEff >= 70 ? "Good" : "Needs attention"}
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground mt-8">No completed lots yet</p>
            )}
          </div>
        </div>
      )}

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">PRODUCTION LOTS</p>
            <p className="text-sm font-medium mt-0.5">
              {rows.length} lot{rows.length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
        <div className="p-0">
          <DataTable columns={columns} data={rows} loading={isLoading} />
        </div>
      </div>
    </div>
  );
}
