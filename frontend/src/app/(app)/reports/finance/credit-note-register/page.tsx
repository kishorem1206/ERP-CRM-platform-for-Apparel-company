"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useCustomerOptions } from "@/components/reports/filter-sources";

type Row = {
  credit_note_number: string; customer_name: string; credit_note_date: string;
  total_amount: string; status: string; reason: string | null; invoice_number: string | null;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const columns: Column<Row>[] = [
  { key: "credit_note_number", header: "Credit Note #", sortable: true },
  { key: "customer_name", header: "Customer", sortable: true },
  { key: "credit_note_date", header: "Date", sortable: true },
  { key: "invoice_number", header: "Against Invoice", render: (r) => r.invoice_number ?? "—" },
  { key: "reason", header: "Reason", render: (r) => r.reason ?? "—" },
  { key: "total_amount", header: "Amount", render: (r) => fmt(r.total_amount), sortable: true },
];

export default function CreditNoteRegisterPage() {
  const customers = useCustomerOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / FINANCE"
      title="Credit Note Register"
      description="Credit notes issued to customers against invoices."
      queryKey="report-credit-note-register"
      endpoint="/reports/credit-note-register"
      filters={[{ key: "customer_id", label: "Customer", options: customers, width: "220px" }]}
      columns={columns}
      totals={[{ key: "total_amount", label: "TOTAL CREDIT NOTES", format: fmt }]}
    />
  );
}
