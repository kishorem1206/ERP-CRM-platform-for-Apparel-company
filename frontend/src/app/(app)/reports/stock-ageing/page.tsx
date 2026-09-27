"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

const INDIGO   = "#0049A7";
const AMBER    = "#A096F7";

const BUCKET_ORDER = ["0-30 days", "31-60 days", "61-90 days", "90+ days"];

const BUCKET_HEX: Record<string, string> = {
  "0-30 days":  "#0F78FF",
  "31-60 days": AMBER,
  "61-90 days": "#A096F7",
  "90+ days":   "#1D0DB0",
};

const INR = (v: number) =>
  `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

function AgeBucket({ bucket }: { bucket: string }) {
  const color = BUCKET_HEX[bucket] ?? "#94A3B8";
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap"
      style={{ background: `${color}18`, color }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {bucket}
    </span>
  );
}

type AgingRow = Record<string, unknown> & {
  product_name: string;
  product_type: string;
  warehouse_name: string;
  unit_symbol: string;
  balance: string;
  stock_value: string | null;
  oldest_receipt_date: string | null;
  age_days: number | null;
  age_bucket: string;
};

function ChartTooltip({
  active, payload, label,
}: {
  active?: boolean;
  payload?: { name: string; value: number; payload: { color?: string } }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-lg shadow-lg px-3 py-2 text-xs">
      {label && <p className="font-semibold mb-1 text-foreground">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.payload?.color ?? "hsl(var(--foreground))" }}>
          {p.name}: {INR(p.value)}
        </p>
      ))}
    </div>
  );
}

const columns: Column<AgingRow>[] = [
  { key: "warehouse_name",       header: "Warehouse" },
  { key: "product_name",         header: "Product" },
  { key: "product_type",         header: "Type" },
  {
    key: "balance",
    header: "On-Hand",
    render: (r) => `${Number(r.balance).toFixed(2)} ${r.unit_symbol}`,
  },
  {
    key: "stock_value",
    header: "Value",
    render: (r) => (r.stock_value ? INR(Number(r.stock_value)) : "—"),
  },
  { key: "oldest_receipt_date",  header: "First Receipt" },
  { key: "age_days",             header: "Age (days)" },
  {
    key: "age_bucket",
    header: "Age Bucket",
    render: (r) => <AgeBucket bucket={r.age_bucket} />,
  },
];

const BUCKETS = ["All", ...BUCKET_ORDER];

export default function StockAgeingPage() {
  const [bucket, setBucket] = useState("All");
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["report-stock-ageing"],
    queryFn: async () => {
      const res = await api.get("/reports/stock-ageing");
      return (res.data.data ?? []) as AgingRow[];
    },
  });

  const filtered = (data ?? []).filter((r) => {
    const matchBucket = bucket === "All" || r.age_bucket === bucket;
    const matchSearch =
      !search ||
      r.product_name.toLowerCase().includes(search.toLowerCase()) ||
      r.warehouse_name.toLowerCase().includes(search.toLowerCase());
    return matchBucket && matchSearch;
  });

  const bucketAgg = useMemo(() => {
    const agg: Record<string, { count: number; value: number }> = {};
    for (const b of BUCKET_ORDER) agg[b] = { count: 0, value: 0 };
    for (const r of data ?? []) {
      if (!agg[r.age_bucket]) agg[r.age_bucket] = { count: 0, value: 0 };
      agg[r.age_bucket].count += 1;
      agg[r.age_bucket].value += Number(r.stock_value ?? 0);
    }
    return agg;
  }, [data]);

  const barData = BUCKET_ORDER.map((b) => ({
    bucket: b,
    value: bucketAgg[b]?.value ?? 0,
    count: bucketAgg[b]?.count ?? 0,
    color: BUCKET_HEX[b],
  }));

  const pieData = barData.filter((d) => d.value > 0);
  const totalValue = barData.reduce((sum, d) => sum + d.value, 0);

  // Clicking a chart segment filters the table to that bucket; clicking the
  // already-selected one clears the filter back to "All".
  function toggleBucket(b: string) {
    setBucket((prev) => (prev === b ? "All" : b));
  }

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            REPORTS / INVENTORY
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Stock Ageing</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Identify slow-moving and stale inventory.
          </p>
        </div>
      </div>

      {/* Bucket stat cards */}
      {data && data.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {BUCKET_ORDER.map((b) => (
            <div key={b} className="bg-card border border-border rounded-2xl p-6 text-center">
              <AgeBucket bucket={b} />
              <p className="text-2xl font-bold tabular-nums mt-3">{bucketAgg[b]?.count ?? 0}</p>
              <p className="text-xs text-muted-foreground mt-0.5">SKUs</p>
              <p className="text-sm font-semibold tabular-nums mt-2" style={{ color: BUCKET_HEX[b] }}>
                {INR(bucketAgg[b]?.value ?? 0)}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Charts */}
      {data && data.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-3 bg-card border border-border rounded-2xl p-6">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">VALUE BY AGE</p>
            <p className="text-sm font-medium mt-0.5 mb-4">Stock value at risk, by ageing bucket</p>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={barData} margin={{ left: 8, right: 8 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                <XAxis dataKey="bucket" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis
                  tick={{ fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "hsl(var(--muted))", opacity: 0.4 }} />
                <Bar dataKey="value" name="Stock Value" radius={[8, 8, 0, 0]}>
                  {barData.map((d) => (
                    <Cell
                      key={d.bucket}
                      fill={d.color}
                      fillOpacity={bucket === "All" || bucket === d.bucket ? 1 : 0.3}
                      cursor="pointer"
                      onClick={() => toggleBucket(d.bucket)}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="lg:col-span-2 bg-card border border-border rounded-2xl p-6">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">VALUE SHARE</p>
            <p className="text-sm font-medium mt-0.5 mb-4">% of total inventory value</p>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="bucket"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={pieData.length > 1 ? 3 : 0}
                >
                  {pieData.map((d) => (
                    <Cell
                      key={d.bucket}
                      fill={d.color}
                      fillOpacity={bucket === "All" || bucket === d.bucket ? 1 : 0.3}
                      cursor="pointer"
                      onClick={() => toggleBucket(d.bucket)}
                    />
                  ))}
                </Pie>
                <Tooltip content={<ChartTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-2 space-y-2">
              {barData.map((d) => (
                <button
                  key={d.bucket}
                  onClick={() => toggleBucket(d.bucket)}
                  className="w-full flex items-center gap-2 text-xs rounded-md px-1.5 py-1 -mx-1.5 hover:bg-muted/60 transition-colors"
                  style={{ opacity: bucket === "All" || bucket === d.bucket ? 1 : 0.45 }}
                >
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: d.color }} />
                  <span className="text-muted-foreground flex-1 text-left">{d.bucket}</span>
                  <span className="font-semibold tabular-nums">
                    {totalValue > 0 ? Math.round((d.value / totalValue) * 100) : 0}%
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 flex-wrap items-center">
        <input
          type="text"
          placeholder="Search product or warehouse…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded-xl border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 w-64"
        />
        <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl flex-wrap">
          {BUCKETS.map((b) => (
            <button
              key={b}
              onClick={() => setBucket(b)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                bucket === b
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {b}
            </button>
          ))}
        </div>
      </div>

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              AGEING DETAIL
            </p>
            <p className="text-sm font-medium mt-0.5">
              {filtered.length} item{filtered.length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
        <div className="p-0">
          <DataTable columns={columns} data={filtered} loading={isLoading} />
        </div>
      </div>
    </div>
  );
}
