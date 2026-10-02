"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useVendorOptions } from "@/components/reports/filter-sources";

const RED = "#1D0DB0";

type Row = {
  vendor_name: string; entry_number: string; entry_date: string;
  total_amount: string; balance_amount: string; age_days: number; age_bucket: string;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const columns: Column<Row>[] = [
  { key: "vendor_name", header: "Vendor", sortable: true },
  { key: "entry_number", header: "GRN #", sortable: true },
  { key: "entry_date", header: "Date", sortable: true },
  { key: "total_amount", header: "Total", render: (r) => fmt(r.total_amount) },
  {
    key: "balance_amount", header: "Outstanding",
    render: (r) => <span className="font-semibold" style={{ color: RED }}>{fmt(r.balance_amount)}</span>,
    sortable: true,
  },
  {
    key: "age_bucket", header: "Ageing",
    render: (r) => (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap"
        style={{ background: `${RED}18`, color: RED }}>
        {r.age_bucket}
      </span>
    ),
  },
];

export default function VendorPayableAgeingPage() {
  const vendors = useVendorOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / PURCHASING"
      title="Vendor Payable Ageing"
      description="Outstanding GRN balances bucketed by age, as of today."
      queryKey="report-vendor-payable-ageing"
      endpoint="/reports/vendor-payable-ageing"
      dateRange={false}
      filters={[{ key: "vendor_id", label: "Vendor", options: vendors, width: "220px" }]}
      columns={columns}
      totals={[{ key: "balance_amount", label: "TOTAL OUTSTANDING", format: fmt }]}
    />
  );
}
