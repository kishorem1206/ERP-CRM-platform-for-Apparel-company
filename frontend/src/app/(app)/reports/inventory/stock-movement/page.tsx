"use client";

import { useMemo } from "react";
import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useProductOptions, useWarehouseOptions } from "@/components/reports/filter-sources";

type Row = {
  transaction_type: string; product_id: string; warehouse_id: string;
  quantity: string; unit_cost: string; total_cost: string; direction: number;
  transaction_date: string; material_type: string;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const TXN_TYPE_OPTIONS = [
  { value: "purchase_receipt", label: "Purchase Receipt" },
  { value: "material_issue", label: "Material Issue" },
  { value: "production_output", label: "Production Output" },
  { value: "delivery", label: "Delivery" },
  { value: "adjustment", label: "Adjustment" },
  { value: "transfer", label: "Transfer" },
];

export default function StockMovementPage() {
  const products = useProductOptions();
  const warehouses = useWarehouseOptions();

  const productMap = useMemo(() => new Map(products.map((p) => [p.value, p.label])), [products]);
  const warehouseMap = useMemo(() => new Map(warehouses.map((w) => [w.value, w.label])), [warehouses]);

  const columns: Column<Row>[] = [
    { key: "transaction_date", header: "Date", sortable: true },
    { key: "transaction_type", header: "Type", className: "capitalize" },
    { key: "product_id", header: "Product", render: (r) => productMap.get(r.product_id) ?? r.product_id.slice(0, 8) },
    { key: "warehouse_id", header: "Warehouse", render: (r) => warehouseMap.get(r.warehouse_id) ?? r.warehouse_id.slice(0, 8) },
    {
      key: "quantity", header: "Qty",
      render: (r) => (
        <span style={{ color: r.direction > 0 ? "#0049A7" : "#1D0DB0" }}>
          {r.direction > 0 ? "+" : "−"}{Number(r.quantity).toLocaleString("en-IN")}
        </span>
      ),
      sortable: true,
    },
    { key: "unit_cost", header: "Unit Cost", render: (r) => fmt(r.unit_cost) },
    { key: "total_cost", header: "Total Cost", render: (r) => fmt(r.total_cost), sortable: true },
  ];

  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / INVENTORY"
      title="Stock Movement Ledger"
      description="Every inventory transaction — receipts, issues, transfers, and adjustments."
      queryKey="report-stock-movement"
      endpoint="/inventory/transactions"
      filters={[
        { key: "product_id", label: "Product", options: products, width: "200px" },
        { key: "warehouse_id", label: "Warehouse", options: warehouses },
        { key: "transaction_type", label: "Type", options: TXN_TYPE_OPTIONS },
      ]}
      columns={columns}
      csvColumns={[
        { key: "transaction_date", header: "Date" },
        { key: "transaction_type", header: "Type" },
        { key: "product_id", header: "Product ID" },
        { key: "warehouse_id", header: "Warehouse ID" },
        { key: "quantity", header: "Qty" },
        { key: "unit_cost", header: "Unit Cost" },
        { key: "total_cost", header: "Total Cost" },
      ]}
    />
  );
}
