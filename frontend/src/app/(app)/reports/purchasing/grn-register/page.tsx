"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useVendorOptions } from "@/components/reports/filter-sources";

type Row = {
  entry_number: string; vendor_name: string; entry_date: string; status: string; payment_status: string;
  total_amount: string; paid_amount: string; balance_amount: string;
  received_qty: string; accepted_qty: string; rejected_qty: string;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const STATUS_OPTIONS = [
  { value: "draft", label: "Draft" },
  { value: "confirmed", label: "Confirmed" },
  { value: "cancelled", label: "Cancelled" },
];

const columns: Column<Row>[] = [
  { key: "entry_number", header: "GRN #", sortable: true },
  { key: "vendor_name", header: "Vendor", sortable: true },
  { key: "entry_date", header: "Date", sortable: true },
  { key: "received_qty", header: "Received", render: (r) => Number(r.received_qty).toLocaleString("en-IN") },
  { key: "accepted_qty", header: "Accepted", render: (r) => Number(r.accepted_qty).toLocaleString("en-IN") },
  {
    key: "rejected_qty", header: "Rejected",
    render: (r) => (
      <span style={{ color: Number(r.rejected_qty) > 0 ? "#1D0DB0" : undefined }}>
        {Number(r.rejected_qty).toLocaleString("en-IN")}
      </span>
    ),
  },
  { key: "total_amount", header: "Total", render: (r) => fmt(r.total_amount), sortable: true },
  { key: "balance_amount", header: "Balance", render: (r) => fmt(r.balance_amount) },
];

export default function GrnRegisterPage() {
  const vendors = useVendorOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / PURCHASING"
      title="GRN Register"
      description="Goods receipts with received, accepted, and rejected quantities."
      queryKey="report-grn-register"
      endpoint="/reports/grn-register"
      filters={[
        { key: "vendor_id", label: "Vendor", options: vendors, width: "220px" },
        { key: "status", label: "Status", options: STATUS_OPTIONS },
      ]}
      columns={columns}
      totals={[{ key: "total_amount", label: "TOTAL GRN VALUE", format: fmt }]}
    />
  );
}
