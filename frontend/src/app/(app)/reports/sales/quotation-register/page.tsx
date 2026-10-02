"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useCustomerOptions } from "@/components/reports/filter-sources";

type Row = {
  quotation_number: string; customer_name: string; quotation_date: string; valid_until: string | null;
  status: string; total_amount: string; converted_order_number: string | null;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const STATUS_OPTIONS = [
  { value: "draft", label: "Draft" },
  { value: "sent", label: "Sent" },
  { value: "accepted", label: "Accepted" },
  { value: "declined", label: "Declined" },
  { value: "expired", label: "Expired" },
];

const columns: Column<Row>[] = [
  { key: "quotation_number", header: "Quote #", sortable: true },
  { key: "customer_name", header: "Customer", sortable: true },
  { key: "quotation_date", header: "Date", sortable: true },
  { key: "valid_until", header: "Valid Until", render: (r) => r.valid_until ?? "—" },
  {
    key: "status", header: "Status",
    render: (r) => (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold capitalize whitespace-nowrap"
        style={{ background: "#0049A718", color: "#0049A7" }}>
        {r.status}
      </span>
    ),
  },
  { key: "total_amount", header: "Total", render: (r) => fmt(r.total_amount), sortable: true },
  { key: "converted_order_number", header: "Converted Order", render: (r) => r.converted_order_number ?? "—" },
];

export default function QuotationRegisterPage() {
  const customers = useCustomerOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / SALES"
      title="Quotation Register"
      description="Every quotation with status and the order it converted to."
      queryKey="report-quotation-register"
      endpoint="/reports/quotation-register"
      filters={[
        { key: "customer_id", label: "Customer", options: customers, width: "220px" },
        { key: "status", label: "Status", options: STATUS_OPTIONS },
      ]}
      columns={columns}
      totals={[{ key: "total_amount", label: "TOTAL QUOTED", format: fmt }]}
    />
  );
}
