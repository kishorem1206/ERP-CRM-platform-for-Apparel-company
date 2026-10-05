"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { SearchableSelect } from "@/components/shared/searchable-select";
import {
  useProductOptions, useCategoryOptions, useWarehouseOptions, useCustomerOptions,
} from "@/components/reports/filter-sources";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

type BalanceRow = Record<string, unknown> & {
  product_id: string;
  product_name: string;
  product_type: string;
  category_id: string | null;
  category_name: string | null;
  variant_id: string | null;
  sku: string | null;
  warehouse_id: string;
  warehouse_name: string;
  unit_symbol: string;
  balance: string;
  stock_value: string | null;
};

const STATUS_TABS = [
  { label: "In Stock", value: "in_stock" },
  { label: "Out of Stock", value: "out_of_stock" },
  { label: "All", value: "all" },
] as const;

const TYPE_HEX: Record<string, string> = {
  raw_material: BLUE,
  fabric:       LAVENDER,
  trim:         "#A096F7",
  packing:      "#A096F7",
  finished_good: TEAL,
};

const columns: Column<BalanceRow>[] = [
  { key: "warehouse_name", header: "Warehouse" },
  { key: "product_name", header: "Product" },
  { key: "sku", header: "SKU", render: (row) => row.sku ?? "—" },
  {
    key: "product_type",
    header: "Type",
    render: (row) => {
      const color = TYPE_HEX[row.product_type] ?? "#94A3B8";
      return (
        <span
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap"
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
        <span className={`font-semibold tabular-nums ${bal < 0 ? "text-[#1D0DB0]" : bal === 0 ? "text-muted-foreground" : "text-[#0F78FF]"}`}>
          {bal.toFixed(4)} {row.unit_symbol}
        </span>
      );
    },
  },
  {
    key: "stock_value",
    header: "Value",
    className: "text-right",
    render: (row) =>
      // null means the backend withheld it (ERP Upgrade §11, admin-only) -
      // never rendered as ₹0.00, which would misreport "no access" as
      // "zero value".
      row.stock_value == null
        ? "—"
        : new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(Number(row.stock_value)),
  },
];

export default function StockBalancePage() {
  const [search, setSearch] = useState("");
  const [productId, setProductId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [status, setStatus] = useState<(typeof STATUS_TABS)[number]["value"]>("in_stock");

  const productOptions = useProductOptions();
  const categoryOptions = useCategoryOptions();
  const warehouseOptions = useWarehouseOptions();
  const customerOptions = useCustomerOptions();

  const { data, isLoading } = useQuery({
    queryKey: ["inventory-balance", productId, categoryId, warehouseId, customerId, status],
    queryFn: async () => {
      const res = await api.get("/inventory/balance", {
        params: {
          product_id: productId || undefined,
          category_id: categoryId || undefined,
          warehouse_id: warehouseId || undefined,
          customer_id: customerId || undefined,
          status,
        },
      });
      return (res.data.data ?? []) as BalanceRow[];
    },
  });

  const filtered = (data ?? []).filter(
    (r) =>
      !search ||
      r.product_name.toLowerCase().includes(search.toLowerCase()) ||
      r.warehouse_name.toLowerCase().includes(search.toLowerCase()) ||
      (r.sku ?? "").toLowerCase().includes(search.toLowerCase()),
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

      {/* Status tabs */}
      <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit">
        {STATUS_TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setStatus(t.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
              status === t.value ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <SearchableSelect
          options={productOptions}
          value={productId}
          onChange={setProductId}
          placeholder="All products"
          accent={INDIGO}
        />
        <SearchableSelect
          options={categoryOptions}
          value={categoryId}
          onChange={setCategoryId}
          placeholder="All categories"
          accent={INDIGO}
        />
        <SearchableSelect
          options={warehouseOptions}
          value={warehouseId}
          onChange={setWarehouseId}
          placeholder="All warehouses"
          accent={INDIGO}
        />
        <SearchableSelect
          options={customerOptions}
          value={customerId}
          onChange={setCustomerId}
          placeholder="Any customer's orders"
          accent={INDIGO}
        />
      </div>

      {/* Search */}
      <input
        type="text"
        placeholder="Search product, SKU, or warehouse…"
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
