"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useVendorOptions } from "@/components/reports/filter-sources";

type Row = {
  po_number: string; vendor_name: string; order_date: string; expected_date: string | null;
  status: string; total_amount: string; ordered_qty: string; received_qty: string; received_pct: string;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const STATUS_OPTIONS = [
  { value: "draft", label: "Draft" },
  { value: "approved", label: "Approved" },
  { value: "partially_received", label: "Partially Received" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

const columns: Column<Row>[] = [
  { key: "po_number", header: "PO #", sortable: true },
  { key: "vendor_name", header: "Vendor", sortable: true },
  { key: "order_date", header: "Order Date", sortable: true },
  { key: "expected_date", header: "Expected Date", render: (r) => r.expected_date ?? "—" },
  { key: "ordered_qty", header: "Ordered Qty", render: (r) => Number(r.ordered_qty).toLocaleString("en-IN") },
  { key: "received_qty", header: "Received Qty", render: (r) => Number(r.received_qty).toLocaleString("en-IN") },
  {
    key: "received_pct", header: "Received %",
    render: (r) => {
      const pct = Number(r.received_pct);
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

export default function PurchaseOrderRegisterPage() {
  const vendors = useVendorOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / PURCHASING"
      title="Purchase Order Register"
      description="Every PO with ordered vs received percentage."
      queryKey="report-po-register"
      endpoint="/reports/po-register"
      filters={[
        { key: "vendor_id", label: "Vendor", options: vendors, width: "220px" },
        { key: "status", label: "Status", options: STATUS_OPTIONS },
      ]}
      columns={columns}
      totals={[{ key: "total_amount", label: "TOTAL PO VALUE", format: fmt }]}
    />
  );
}
