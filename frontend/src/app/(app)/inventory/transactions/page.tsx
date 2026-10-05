"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

type Transaction = Record<string, unknown> & {
  id: string;
  transaction_type: string;
  reference_type: string | null;
  product_id: string;
  product_name: string | null;
  sku: string | null;
  warehouse_id: string;
  warehouse_name: string | null;
  quantity: string;
  unit_cost: string | null;
  total_cost: string | null;
  direction: number;
  transaction_date: string;
  notes: string | null;
  material_type: string;
  created_by_name: string | null;
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
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap"
          style={{ background: `${color}18`, color }}
        >
          {row.transaction_type.replace(/_/g, " ")}
        </span>
      );
    },
  },
  { key: "reference_type", header: "Ref Type" },
  {
    key: "product_name",
    header: "Product",
    render: (row) => (
      <span>
        {row.product_name ?? "—"}
        {row.sku && <span className="text-muted-foreground"> ({row.sku})</span>}
      </span>
    ),
  },
  { key: "warehouse_name", header: "Warehouse", render: (r) => r.warehouse_name ?? "—" },
  {
    key: "quantity",
    header: "Qty",
    render: (row) => (
      <span className={`font-semibold tabular-nums ${row.direction === 1 ? "text-[#0F78FF]" : "text-[#1D0DB0]"}`}>
        {row.direction === 1 ? "+" : "-"}{Number(row.quantity).toFixed(2)}
      </span>
    ),
  },
  // null means the backend withheld it (ERP Upgrade §11, admin-only) -
  // never rendered as ₹NaN, which the raw Number(null) coercion used to
  // produce even for an ordinarily-populated field.
  { key: "unit_cost", header: "Unit Cost", render: (r) => (r.unit_cost == null ? "—" : `₹${Number(r.unit_cost).toFixed(2)}`) },
  { key: "total_cost", header: "Total", render: (r) => (r.total_cost == null ? "—" : `₹${Number(r.total_cost).toFixed(2)}`) },
  { key: "created_by_name", header: "Account", render: (r) => r.created_by_name ?? "—" },
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
