"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from "recharts";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { DateRangeFilter } from "@/components/shared/date-picker";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const TEAL     = "#8174F5";
const BLUE     = "#0049A7";

type PurchaseRow = Record<string, unknown> & {
  vendor_name: string; vendor_type: string; entry_count: number;
  taxable_amount: string; cgst_amount: string; sgst_amount: string;
  igst_amount: string; total_amount: string; paid_amount: string; outstanding: string;
};

const fmt = (v: unknown) =>
  `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const columns: Column<PurchaseRow>[] = [
  { key: "vendor_name", header: "Vendor", sortable: true },
  {
    key: "vendor_type", header: "Type",
    render: (r) => (
      <span
        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap capitalize"
        style={{ background: `${LAVENDER}18`, color: LAVENDER }}
      >
        {r.vendor_type.replace(/_/g, " ")}
      </span>
    ),
  },
  { key: "entry_count",    header: "GRNs" },
  { key: "taxable_amount", header: "Taxable",  render: (r) => fmt(r.taxable_amount), sortable: true },
  { key: "cgst_amount",    header: "CGST",     render: (r) => fmt(r.cgst_amount) },
  { key: "sgst_amount",    header: "SGST",     render: (r) => fmt(r.sgst_amount) },
  { key: "igst_amount",    header: "IGST",     render: (r) => fmt(r.igst_amount) },
  { key: "total_amount",   header: "Total",    render: (r) => fmt(r.total_amount), sortable: true },
  { key: "paid_amount",    header: "Paid",     render: (r) => fmt(r.paid_amount) },
  {
    key: "outstanding", header: "Payable",
    render: (r) => (
      <span className="font-semibold tabular-nums" style={{ color: Number(r.outstanding) > 0 ? "#1D0DB0" : "#0049A7" }}>
        {fmt(r.outstanding)}
      </span>
    ),
  },
];

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-xl shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold mb-1 text-foreground truncate max-w-[180px]">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: ₹{Number(p.value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
        </p>
      ))}
    </div>
  );
}

const today        = new Date().toISOString().slice(0, 10);
const firstOfMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10);


export default function PurchaseSummaryPage() {
  const [from, setFrom] = useState(firstOfMonth);
  const [to, setTo]     = useState(today);



  const { data, isLoading, refetch } = useQuery({
    queryKey: ["report-purchases", from, to],
    queryFn:  async () => {
      const res = await api.get("/reports/purchase-summary", { params: { from_date: from, to_date: to } });
      return (res.data.data ?? []) as PurchaseRow[];
    },
  });

  const top8 = [...(data ?? [])]
    .sort((a, b) => Number(b.total_amount) - Number(a.total_amount))
    .slice(0, 8)
    .map((r) => ({
      name:    r.vendor_name.length > 16 ? r.vendor_name.slice(0, 15) + "…" : r.vendor_name,
      spend:   Number(r.total_amount),
      payable: Number(r.outstanding),
    }));

  const totals = (data ?? []).reduce(
    (acc, r) => ({ total: acc.total + Number(r.total_amount), outstanding: acc.outstanding + Number(r.outstanding) }),
    { total: 0, outstanding: 0 },
  );

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            REPORTS / PURCHASES
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Purchase Report</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Spend by vendor with GST breakdown.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <DateRangeFilter from={from} to={to} accent={TEAL}
            onChange={(f, t) => { setFrom(f); setTo(t); }} />
        </div>
      </div>

      {/* Stat cards */}
      {data && data.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-card border border-border rounded-2xl p-6">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">TOTAL PURCHASED</p>
            <p className="text-2xl font-bold tracking-tight tabular-nums mt-1">{fmt(totals.total)}</p>
          </div>
          <div className="bg-card border border-border rounded-2xl p-6">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">TOTAL PAYABLE</p>
            <p className="text-2xl font-bold tracking-tight tabular-nums mt-1" style={{ color: totals.outstanding > 0 ? "#1D0DB0" : "#0049A7" }}>
              {fmt(totals.outstanding)}
            </p>
          </div>
        </div>
      )}

      {/* Chart */}
      {top8.length > 0 && (
        <div className="bg-card border border-border rounded-2xl p-6">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">SPEND BY VENDOR</p>
          <p className="text-sm font-medium mt-0.5 mb-4">Top {top8.length} vendors — purchased vs payable</p>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={top8} margin={{ top: 4, right: 8, left: 0, bottom: 0 }} barGap={4}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(228 18% 88% / 0.6)" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false}
                tickFormatter={(v) => `₹${v >= 1000 ? (v / 1000).toFixed(0) + "k" : v}`} />
              <Tooltip content={<ChartTooltip />} />
              <Legend iconType="circle" iconSize={7}
                formatter={(v) => <span style={{ fontSize: 11, color: "#64748B" }}>{v}</span>} />
              <Bar dataKey="spend"   name="Spend"   fill={TEAL} radius={[4, 4, 0, 0]} maxBarSize={36} />
              <Bar dataKey="payable" name="Payable" fill={BLUE} radius={[4, 4, 0, 0]} maxBarSize={36} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">VENDOR BREAKDOWN</p>
            <p className="text-sm font-medium mt-0.5">
              {data ? `${data.length} vendor${data.length !== 1 ? "s" : ""}` : "Loading…"}
            </p>
          </div>
        </div>
        <div className="p-0">
          <DataTable columns={columns} data={data ?? []} loading={isLoading} />
        </div>
      </div>
    </div>
  );
}
