"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

const INDIGO   = "#5347CE";
const LAVENDER = "#887CFD";
const BLUE     = "#4896FE";
const TEAL     = "#16C8C7";

type BalanceRow = Record<string, unknown> & {
  product_id: string;
  product_name: string;
  product_type: string;
  warehouse_id: string;
  warehouse_name: string;
  unit_symbol: string;
  balance: string;
};

const TYPE_HEX: Record<string, string> = {
  raw_material: BLUE,
  fabric:       LAVENDER,
  trim:         "#F59E0B",
  packing:      "#F97316",
  finished_good: TEAL,
};

const columns: Column<BalanceRow>[] = [
  { key: "warehouse_name", header: "Warehouse" },
  { key: "product_name", header: "Product" },
  {
    key: "product_type",
    header: "Type",
    render: (row) => {
      const color = TYPE_HEX[row.product_type] ?? "#94A3B8";
      return (
        <span
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"
          style={{ background: `${color}18`, color }}
        >
          {row.product_type.replace(/_/g, " ")}
        </span>
      );
    },
  },
  {
    key: "balance",
    header: "Balance",
    render: (row) => {
      const bal = Number(row.balance);
      return (
        <span className={`font-semibold tabular-nums ${bal < 0 ? "text-red-600" : bal === 0 ? "text-muted-foreground" : "text-emerald-600"}`}>
          {bal.toFixed(4)} {row.unit_symbol}
        </span>
      );
    },
  },
];

export default function StockBalancePage() {
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["inventory-balance"],
    queryFn: async () => {
      const res = await api.get("/inventory/balance");
      return (res.data.data ?? []) as BalanceRow[];
    },
  });

  const filtered = (data ?? []).filter(
    (r) =>
      !search ||
      r.product_name.toLowerCase().includes(search.toLowerCase()) ||
      r.warehouse_name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            INVENTORY / BALANCE
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Stock Balance</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time inventory levels across all warehouses.
          </p>
        </div>
      </div>

      {/* Search */}
      <input
        type="text"
        placeholder="Search product or warehouse…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full max-w-sm rounded-xl border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
      />

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              STOCK LEVELS
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
