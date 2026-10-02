"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useProductOptions, useCategoryOptions } from "@/components/reports/filter-sources";

type Row = {
  product_name: string; product_code: string; category_name: string | null;
  qty_ordered: string; revenue: string; order_count: number;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const columns: Column<Row>[] = [
  { key: "product_name", header: "Product", sortable: true },
  { key: "product_code", header: "Code" },
  { key: "category_name", header: "Category", render: (r) => r.category_name ?? "—" },
  { key: "qty_ordered", header: "Qty Ordered", render: (r) => Number(r.qty_ordered).toLocaleString("en-IN"), sortable: true },
  { key: "order_count", header: "Orders" },
  { key: "revenue", header: "Revenue", render: (r) => fmt(r.revenue), sortable: true },
];

export default function SalesByProductPage() {
  const products = useProductOptions();
  const categories = useCategoryOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / SALES"
      title="Sales by Product"
      description="Quantity ordered and revenue per product across sales orders."
      queryKey="report-sales-by-product"
      endpoint="/reports/sales-by-product"
      filters={[
        { key: "product_id", label: "Product", options: products, width: "220px" },
        { key: "category_id", label: "Category", options: categories },
      ]}
      columns={columns}
      totals={[{ key: "revenue", label: "TOTAL REVENUE", format: fmt }]}
    />
  );
}
