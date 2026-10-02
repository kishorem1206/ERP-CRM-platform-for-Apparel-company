"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useVendorOptions } from "@/components/reports/filter-sources";

type Row = {
  debit_note_number: string; vendor_name: string; debit_note_date: string;
  total_amount: string; status: string; reason: string | null; entry_number: string | null;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const columns: Column<Row>[] = [
  { key: "debit_note_number", header: "Debit Note #", sortable: true },
  { key: "vendor_name", header: "Vendor", sortable: true },
  { key: "debit_note_date", header: "Date", sortable: true },
  { key: "entry_number", header: "Against GRN", render: (r) => r.entry_number ?? "—" },
  { key: "reason", header: "Reason", render: (r) => r.reason ?? "—" },
  { key: "total_amount", header: "Amount", render: (r) => fmt(r.total_amount), sortable: true },
];

export default function DebitNoteRegisterPage() {
  const vendors = useVendorOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / FINANCE"
      title="Debit Note Register"
      description="Debit notes issued against vendors and GRNs."
      queryKey="report-debit-note-register"
      endpoint="/reports/debit-note-register"
      filters={[{ key: "vendor_id", label: "Vendor", options: vendors, width: "220px" }]}
      columns={columns}
      totals={[{ key: "total_amount", label: "TOTAL DEBIT NOTES", format: fmt }]}
    />
  );
}
