"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useProductOptions } from "@/components/reports/filter-sources";

type Row = {
  lot_number: string; product_name: string; issue_number: string; issue_date: string;
  issued_qty: string; unit_symbol: string; unit_cost: string; total_cost: string; stage_name: string;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const columns: Column<Row>[] = [
  { key: "issue_number", header: "Issue #", sortable: true },
  { key: "lot_number", header: "Lot #", sortable: true },
  { key: "product_name", header: "Product", sortable: true },
  { key: "stage_name", header: "Stage" },
  { key: "issue_date", header: "Date", sortable: true },
  { key: "issued_qty", header: "Qty Issued", render: (r) => `${Number(r.issued_qty).toLocaleString("en-IN")} ${r.unit_symbol}` },
  { key: "total_cost", header: "Total Cost", render: (r) => fmt(r.total_cost), sortable: true },
];

export default function MaterialConsumptionPage() {
  const products = useProductOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / PRODUCTION"
      title="Material Consumption"
      description="Materials issued to production lots by stage and product."
      queryKey="report-material-consumption"
      endpoint="/reports/material-consumption"
      filters={[{ key: "product_id", label: "Product", options: products, width: "220px" }]}
      columns={columns}
      totals={[{ key: "total_cost", label: "TOTAL MATERIAL COST", format: fmt }]}
    />
  );
}
