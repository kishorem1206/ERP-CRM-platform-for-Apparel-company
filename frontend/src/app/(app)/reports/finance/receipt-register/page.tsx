"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useCustomerOptions } from "@/components/reports/filter-sources";

type Row = {
  payment_number: string; customer_name: string; payment_date: string;
  amount: string; payment_mode: string; reference: string | null; status: string;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const MODE_OPTIONS = [
  { value: "cash", label: "Cash" },
  { value: "cheque", label: "Cheque" },
  { value: "neft", label: "NEFT" },
  { value: "rtgs", label: "RTGS" },
  { value: "upi", label: "UPI" },
  { value: "card", label: "Card" },
];

const columns: Column<Row>[] = [
  { key: "payment_number", header: "Receipt #", sortable: true },
  { key: "customer_name", header: "Customer", sortable: true },
  { key: "payment_date", header: "Date", sortable: true },
  { key: "payment_mode", header: "Mode", className: "uppercase" },
  { key: "reference", header: "Reference", render: (r) => r.reference ?? "—" },
  { key: "amount", header: "Amount", render: (r) => fmt(r.amount), sortable: true },
];

export default function ReceiptRegisterPage() {
  const customers = useCustomerOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / FINANCE"
      title="Receipt Register"
      description="Customer payments received, by mode and reference."
      queryKey="report-receipt-register"
      endpoint="/reports/receipt-register"
      filters={[
        { key: "customer_id", label: "Customer", options: customers, width: "220px" },
        { key: "payment_mode", label: "Mode", options: MODE_OPTIONS },
      ]}
      columns={columns}
      totals={[{ key: "amount", label: "TOTAL RECEIVED", format: fmt }]}
    />
  );
}
