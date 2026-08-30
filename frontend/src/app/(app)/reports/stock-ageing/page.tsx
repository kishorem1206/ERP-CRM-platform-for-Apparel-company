"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

const INDIGO   = "#5347CE";
const LAVENDER = "#887CFD";
const BLUE     = "#4896FE";
const TEAL     = "#16C8C7";
const AMBER    = "#F59E0B";

const BUCKET_HEX: Record<string, string> = {
  "0-30 days":  "#10B981",
  "31-60 days": AMBER,
  "61-90 days": "#F97316",
  "90+ days":   "#EF4444",
};

function AgeBucket({ bucket }: { bucket: string }) {
  const color = BUCKET_HEX[bucket] ?? "#94A3B8";
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"
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
  oldest_receipt_date: string | null;
  age_days: number | null;
  age_bucket: string;
};

const columns: Column<AgingRow>[] = [
  { key: "warehouse_name",       header: "Warehouse" },
  { key: "product_name",         header: "Product" },
  { key: "product_type",         header: "Type" },
  {
    key: "balance",
    header: "On-Hand",
    render: (r) => `${Number(r.balance).toFixed(2)} ${r.unit_symbol}`,
  },
  { key: "oldest_receipt_date",  header: "First Receipt" },
  { key: "age_days",             header: "Age (days)" },
  {
    key: "age_bucket",
    header: "Age Bucket",
    render: (r) => <AgeBucket bucket={r.age_bucket} />,
  },
];

const BUCKETS = ["All", "0-30 days", "31-60 days", "61-90 days", "90+ days"];

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

  const bucketCounts = (data ?? []).reduce<Record<string, number>>((acc, r) => {
    acc[r.age_bucket] = (acc[r.age_bucket] ?? 0) + 1;
    return acc;
  }, {});

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
          {Object.entries(BUCKET_HEX).map(([b, color]) => (
            <div key={b} className="bg-card border border-border rounded-2xl p-6 text-center">
              <AgeBucket bucket={b} />
              <p className="text-2xl font-bold tabular-nums mt-3">{bucketCounts[b] ?? 0}</p>
              <p className="text-xs text-muted-foreground mt-0.5">SKUs</p>
            </div>
          ))}
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
