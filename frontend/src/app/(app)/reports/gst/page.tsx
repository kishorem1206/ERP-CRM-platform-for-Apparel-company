"use client";

import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Calendar, ArrowRight } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from "recharts";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

type GSTRow = Record<string, unknown> & {
  month: string; taxable_amount: string; cgst_amount: string;
  sgst_amount: string; igst_amount: string; total_amount: string;
  invoice_count?: number; entry_count?: number;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const outputCols: Column<GSTRow>[] = [
  { key: "month",          header: "Month" },
  { key: "invoice_count",  header: "Invoices" },
  { key: "taxable_amount", header: "Taxable",       render: (r) => fmt(r.taxable_amount) },
  { key: "cgst_amount",    header: "CGST",          render: (r) => fmt(r.cgst_amount) },
  { key: "sgst_amount",    header: "SGST",          render: (r) => fmt(r.sgst_amount) },
  { key: "igst_amount",    header: "IGST",          render: (r) => fmt(r.igst_amount) },
  { key: "total_amount",   header: "Invoice Total", render: (r) => fmt(r.total_amount) },
];

const inputCols: Column<GSTRow>[] = [
  { key: "month",          header: "Month" },
  { key: "entry_count",    header: "GRNs" },
  { key: "taxable_amount", header: "Taxable",        render: (r) => fmt(r.taxable_amount) },
  { key: "cgst_amount",    header: "CGST (ITC)",    render: (r) => fmt(r.cgst_amount) },
  { key: "sgst_amount",    header: "SGST (ITC)",    render: (r) => fmt(r.sgst_amount) },
  { key: "igst_amount",    header: "IGST (ITC)",    render: (r) => fmt(r.igst_amount) },
  { key: "total_amount",   header: "Purchase Total", render: (r) => fmt(r.total_amount) },
];

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-xl shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold mb-1 text-foreground">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: ₹{Number(p.value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
        </p>
      ))}
    </div>
  );
}

const today       = new Date().toISOString().slice(0, 10);
const firstOfYear = `${new Date().getFullYear()}-01-01`;

const GST_TABS = [
  { value: "output", label: "Output (GSTR-1)" },
  { value: "input",  label: "Input ITC (GSTR-2A)" },
] as const;

const PRESETS: { label: string; value: number | "ytd" }[] = [
  { label: "7D", value: 7 },
  { label: "30D", value: 30 },
  { label: "90D", value: 90 },
  { label: "YTD", value: "ytd" },
];

export default function GSTSummaryPage() {
  const [from, setFrom] = useState(firstOfYear);
  const [to, setTo]     = useState(today);
  const [tab, setTab]   = useState<"output" | "input">("output");

  const applyPreset = useCallback((days: number | "ytd") => {
    const toStr = new Date().toISOString().slice(0, 10);
    const fromStr = days === "ytd"
      ? `${new Date().getFullYear()}-01-01`
      : new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    setFrom(fromStr);
    setTo(toStr);
  }, []);

  const activePreset = (() => {
    if (to !== today) return null;
    const days = Math.round((new Date(today).getTime() - new Date(from).getTime()) / 86_400_000);
    if (from === `${new Date().getFullYear()}-01-01`) return "ytd";
    if (days === 7) return 7;
    if (days === 30) return 30;
    if (days === 90) return 90;
    return null;
  })();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["report-gst", from, to],
    queryFn: async () => {
      const res = await api.get("/reports/gst-summary", { params: { from_date: from, to_date: to } });
      return res.data.data as { output: GSTRow[]; input: GSTRow[] };
    },
  });

  const rows   = tab === "output" ? (data?.output ?? []) : (data?.input ?? []);
  const sumGST = rows.reduce(
    (acc, r) => ({
      cgst: acc.cgst + Number(r.cgst_amount),
      sgst: acc.sgst + Number(r.sgst_amount),
      igst: acc.igst + Number(r.igst_amount),
    }),
    { cgst: 0, sgst: 0, igst: 0 },
  );

  const chartData = rows.map((r) => ({
    month: r.month.slice(0, 7),
    CGST:  Number(r.cgst_amount),
    SGST:  Number(r.sgst_amount),
    IGST:  Number(r.igst_amount),
  }));

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            REPORTS / GST
          </p>
          <h1 className="text-2xl font-bold tracking-tight">GST Report</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Monthly CGST / SGST / IGST breakdown.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                onClick={() => applyPreset(p.value)}
                className="px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150"
                style={
                  activePreset === p.value
                    ? { background: "hsl(var(--card))", color: LAVENDER, boxShadow: "var(--shadow-xs)" }
                    : { color: "hsl(var(--muted-foreground))" }
                }
              >
                {p.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 bg-card border border-border rounded-xl pl-3 pr-1 py-1">
            <Calendar className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
            <input
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              className="text-sm bg-transparent border-none outline-none w-[124px]"
            />
            <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/50 flex-shrink-0" />
            <input
              type="date"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              className="text-sm bg-transparent border-none outline-none w-[124px]"
            />
            <button
              onClick={() => refetch()}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white transition-all hover:opacity-90 active:scale-95 flex-shrink-0"
              style={{ background: LAVENDER }}
            >
              Apply
            </button>
          </div>
        </div>
      </div>

      {/* Tab strip */}
      <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit flex-wrap">
        {GST_TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
              tab === t.value
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* KPI strip */}
      {rows.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { label: "TOTAL CGST", value: fmt(sumGST.cgst), color: INDIGO },
            { label: "TOTAL SGST", value: fmt(sumGST.sgst), color: LAVENDER },
            { label: "TOTAL IGST", value: fmt(sumGST.igst), color: TEAL },
          ].map((kpi) => (
            <div key={kpi.label} className="bg-card border border-border rounded-2xl p-6">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">{kpi.label}</p>
              <p className="text-2xl font-bold tracking-tight tabular-nums mt-1" style={{ color: kpi.color }}>{kpi.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Chart */}
      {chartData.length > 0 && (
        <div className="bg-card border border-border rounded-2xl p-6">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
            {tab === "output" ? "OUTPUT GST" : "INPUT ITC"} — MONTHLY
          </p>
          <p className="text-sm font-medium mt-0.5 mb-4">Stacked CGST + SGST + IGST per month</p>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(228 18% 88% / 0.6)" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false}
                tickFormatter={(v) => `₹${v >= 1000 ? (v / 1000).toFixed(0) + "k" : v}`} />
              <Tooltip content={<ChartTooltip />} />
              <Legend iconType="circle" iconSize={7}
                formatter={(v) => <span style={{ fontSize: 11, color: "#64748B" }}>{v}</span>} />
              <Bar dataKey="CGST" stackId="gst" fill={INDIGO}   radius={[0, 0, 0, 0]} maxBarSize={40} />
              <Bar dataKey="SGST" stackId="gst" fill={LAVENDER} radius={[0, 0, 0, 0]} maxBarSize={40} />
              <Bar dataKey="IGST" stackId="gst" fill={TEAL}     radius={[4, 4, 0, 0]} maxBarSize={40} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              {tab === "output" ? "OUTPUT REGISTER" : "INPUT REGISTER"}
            </p>
            <p className="text-sm font-medium mt-0.5">
              {rows.length} month{rows.length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
        <div className="p-0">
          <DataTable
            columns={tab === "output" ? outputCols : inputCols}
            data={rows}
            loading={isLoading}
          />
        </div>
      </div>
    </div>
  );
}
