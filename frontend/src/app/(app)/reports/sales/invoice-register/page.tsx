"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useCustomerOptions } from "@/components/reports/filter-sources";

const INDIGO = "#1D0DB0";

type Row = {
  invoice_number: string; customer_name: string; invoice_date: string; due_date: string | null;
  status: string; total_amount: string; paid_amount: string; balance_amount: string;
  age_days: number; age_bucket: string;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const STATUS_OPTIONS = [
  { value: "unpaid", label: "Unpaid" },
  { value: "partial", label: "Partial" },
  { value: "paid", label: "Paid" },
  { value: "cancelled", label: "Cancelled" },
];

const columns: Column<Row>[] = [
  { key: "invoice_number", header: "Invoice #", sortable: true },
  { key: "customer_name", header: "Customer", sortable: true },
  { key: "invoice_date", header: "Date", sortable: true },
  { key: "due_date", header: "Due Date", render: (r) => r.due_date ?? "—" },
  { key: "total_amount", header: "Total", render: (r) => fmt(r.total_amount), sortable: true },
  { key: "paid_amount", header: "Paid", render: (r) => fmt(r.paid_amount) },
  {
    key: "balance_amount", header: "Balance",
    render: (r) => (
      <span className="font-semibold tabular-nums" style={{ color: Number(r.balance_amount) > 0 ? INDIGO : "#0049A7" }}>
        {fmt(r.balance_amount)}
      </span>
    ),
  },
  {
    key: "age_bucket", header: "Ageing",
    render: (r) => (
      <span
        className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap"
        style={{ background: `${INDIGO}18`, color: INDIGO }}
      >
        {r.age_bucket}
      </span>
    ),
  },
];

export default function InvoiceRegisterPage() {
  const customers = useCustomerOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / SALES"
      title="Invoice Register & AR Ageing"
      description="Every invoice with due date, balance, and overdue ageing bucket."
      queryKey="report-invoice-register"
      endpoint="/reports/invoice-register"
      filters={[
        { key: "customer_id", label: "Customer", options: customers, width: "220px" },
        { key: "status", label: "Status", options: STATUS_OPTIONS },
      ]}
      columns={columns}
      totals={[
        { key: "total_amount", label: "TOTAL INVOICED", format: fmt },
        { key: "balance_amount", label: "OUTSTANDING", format: fmt },
      ]}
    />
  );
}
