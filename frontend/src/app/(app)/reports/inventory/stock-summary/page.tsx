"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useWarehouseOptions, useCategoryOptions } from "@/components/reports/filter-sources";

type Row = {
  product_name: string; product_code: string; product_type: string; category_name: string | null;
  warehouse_name: string; unit_symbol: string; balance: string; stock_value: string;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const PRODUCT_TYPE_OPTIONS = [
  { value: "finished_good", label: "Finished Good" },
  { value: "raw_material", label: "Raw Material" },
  { value: "yarn", label: "Yarn" },
  { value: "fabric", label: "Fabric" },
  { value: "trim", label: "Trim" },
];

const columns: Column<Row>[] = [
  { key: "product_name", header: "Product", sortable: true },
  { key: "product_code", header: "Code" },
  { key: "product_type", header: "Type", className: "capitalize" },
  { key: "category_name", header: "Category", render: (r) => r.category_name ?? "—" },
  { key: "warehouse_name", header: "Warehouse", sortable: true },
  { key: "balance", header: "Balance", render: (r) => `${Number(r.balance).toLocaleString("en-IN")} ${r.unit_symbol}`, sortable: true },
  { key: "stock_value", header: "Stock Value", render: (r) => fmt(r.stock_value), sortable: true },
];

export default function StockSummaryPage() {
  const warehouses = useWarehouseOptions();
  const categories = useCategoryOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / INVENTORY"
      title="Stock Summary"
      description="Current stock balance and value by product and warehouse."
      queryKey="report-stock-summary"
      endpoint="/reports/stock-summary"
      dateRange={false}
      filters={[
        { key: "warehouse_id", label: "Warehouse", options: warehouses, width: "200px" },
        { key: "category_id", label: "Category", options: categories },
        { key: "product_type", label: "Type", options: PRODUCT_TYPE_OPTIONS },
      ]}
      columns={columns}
      totals={[{ key: "stock_value", label: "TOTAL STOCK VALUE", format: fmt }]}
    />
  );
}
