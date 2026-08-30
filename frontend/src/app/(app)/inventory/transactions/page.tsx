"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

const INDIGO   = "#5347CE";
const LAVENDER = "#887CFD";
const BLUE     = "#4896FE";
const TEAL     = "#16C8C7";

type Transaction = Record<string, unknown> & {
  id: string;
  transaction_type: string;
  reference_type: string | null;
  product_id: string;
  warehouse_id: string;
  quantity: string;
  unit_cost: string;
  total_cost: string;
  direction: number;
  transaction_date: string;
  notes: string | null;
  material_type: string;
};

const TYPE_TABS = [
  { value: "all",           label: "All" },
  { value: "stock_in",      label: "Stock In" },
  { value: "stock_out",     label: "Stock Out" },
  { value: "transfer_in",   label: "Transfer In" },
  { value: "transfer_out",  label: "Transfer Out" },
  { value: "adjustment",    label: "Adjustment" },
];

const columns: Column<Transaction>[] = [
  { key: "transaction_date", header: "Date" },
  {
    key: "transaction_type",
    header: "Type",
    render: (row) => {
      const color = TEAL;
      return (
        <span
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"
          style={{ background: `${color}18`, color }}
        >
          {row.transaction_type.replace(/_/g, " ")}
        </span>
      );
    },
  },
  { key: "reference_type", header: "Ref Type" },
  { key: "product_id", header: "Product ID" },
  { key: "warehouse_id", header: "Warehouse ID" },
  {
    key: "quantity",
    header: "Qty",
    render: (row) => (
      <span className={`font-semibold tabular-nums ${row.direction === 1 ? "text-emerald-600" : "text-red-600"}`}>
        {row.direction === 1 ? "+" : "-"}{Number(row.quantity).toFixed(2)}
      </span>
    ),
  },
  { key: "unit_cost", header: "Unit Cost", render: (r) => `₹${Number(r.unit_cost).toFixed(2)}` },
  { key: "total_cost", header: "Total", render: (r) => `₹${Number(r.total_cost).toFixed(2)}` },
  { key: "notes", header: "Notes" },
];

export default function TransactionsPage() {
  const [typeFilter, setTypeFilter] = useState("all");

  const { data, isLoading } = useQuery({
    queryKey: ["inventory-transactions", typeFilter],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (typeFilter !== "all") params.transaction_type = typeFilter;
      const res = await api.get("/inventory/transactions", { params });
      return (res.data.data ?? []) as Transaction[];
    },
  });

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            INVENTORY / TRANSACTIONS
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Stock Transactions</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Every inbound and outbound stock movement.
          </p>
        </div>
      </div>

      {/* Filter tab strip */}
      <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit flex-wrap">
        {TYPE_TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setTypeFilter(t.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
              typeFilter === t.value
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              TRANSACTION LOG
            </p>
            <p className="text-sm font-medium mt-0.5">
              {data ? `${data.length} record${data.length !== 1 ? "s" : ""}` : "Loading…"}
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
