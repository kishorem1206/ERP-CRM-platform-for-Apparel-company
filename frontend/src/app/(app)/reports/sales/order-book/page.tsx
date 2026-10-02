"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useCustomerOptions } from "@/components/reports/filter-sources";

type Row = {
  order_number: string; customer_name: string; order_date: string; expected_delivery: string | null;
  status: string; total_amount: string; ordered_qty: string; delivered_qty: string; fulfilment_pct: string;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const STATUS_OPTIONS = [
  { value: "confirmed", label: "Confirmed" },
  { value: "in_production", label: "In Production" },
  { value: "partially_delivered", label: "Partially Delivered" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

const columns: Column<Row>[] = [
  { key: "order_number", header: "Order #", sortable: true },
  { key: "customer_name", header: "Customer", sortable: true },
  { key: "order_date", header: "Order Date", sortable: true },
  { key: "expected_delivery", header: "Expected Delivery", render: (r) => r.expected_delivery ?? "—" },
  { key: "ordered_qty", header: "Ordered Qty", render: (r) => Number(r.ordered_qty).toLocaleString("en-IN") },
  { key: "delivered_qty", header: "Delivered Qty", render: (r) => Number(r.delivered_qty).toLocaleString("en-IN") },
  {
    key: "fulfilment_pct", header: "Fulfilment",
    render: (r) => {
      const pct = Number(r.fulfilment_pct);
      return (
        <span className="font-semibold tabular-nums" style={{ color: pct >= 100 ? "#0049A7" : "#1D0DB0" }}>
          {pct.toFixed(1)}%
        </span>
      );
    },
    sortable: true,
  },
  { key: "total_amount", header: "Total", render: (r) => fmt(r.total_amount), sortable: true },
];

export default function SalesOrderBookPage() {
  const customers = useCustomerOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / SALES"
      title="Sales Order Book"
      description="Open and closed orders with delivery fulfilment percentage."
      queryKey="report-sales-order-book"
      endpoint="/reports/sales-order-book"
      filters={[
        { key: "customer_id", label: "Customer", options: customers, width: "220px" },
        { key: "status", label: "Status", options: STATUS_OPTIONS },
      ]}
      columns={columns}
      totals={[{ key: "total_amount", label: "TOTAL ORDER VALUE", format: fmt }]}
    />
  );
}
