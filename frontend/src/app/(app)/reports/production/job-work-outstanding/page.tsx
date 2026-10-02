"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useVendorOptions, useWorkerOptions } from "@/components/reports/filter-sources";

const AMBER = "#A096F7";

type Row = {
  challan_number: string; assignee_name: string; assignee_type: string; lot_number: string;
  stage_name: string; stage_type: string; out_date: string; out_qty: number; in_date: string | null;
  in_qty: number; rejected_qty: number; pending_qty: number; age_days: number; status: string;
  bill_amount: string | null; bill_received: boolean;
};

const STAGE_TYPE_OPTIONS = [
  { value: "cutting", label: "Cutting" },
  { value: "stitching", label: "Stitching" },
  { value: "checking", label: "Checking" },
  { value: "ironing", label: "Ironing" },
  { value: "packing", label: "Packing" },
  { value: "finishing", label: "Finishing" },
  { value: "trimming", label: "Trimming" },
];

const columns: Column<Row>[] = [
  { key: "challan_number", header: "Challan #", sortable: true },
  { key: "lot_number", header: "Lot #" },
  { key: "assignee_name", header: "Vendor / Worker", sortable: true },
  { key: "stage_name", header: "Stage" },
  { key: "out_date", header: "Out Date", sortable: true },
  { key: "out_qty", header: "Out Qty" },
  { key: "in_qty", header: "In Qty" },
  { key: "rejected_qty", header: "Rejected" },
  {
    key: "pending_qty", header: "Pending",
    render: (r) => <span className="font-semibold" style={{ color: AMBER }}>{r.pending_qty}</span>,
    sortable: true,
  },
  {
    key: "age_days", header: "Age (days)",
    render: (r) => <span style={{ color: r.age_days > 14 ? "#1D0DB0" : undefined }}>{r.age_days}</span>,
    sortable: true,
  },
];

export default function JobWorkOutstandingPage() {
  const vendors = useVendorOptions();
  const workers = useWorkerOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / PRODUCTION"
      title="Job-Work Outstanding"
      description="Open vendor and worker challans with pending quantity and age, as of today."
      queryKey="report-job-work-outstanding"
      endpoint="/reports/job-work-outstanding"
      dateRange={false}
      filters={[
        { key: "vendor_id", label: "Vendor", options: vendors, width: "200px" },
        { key: "worker_id", label: "Worker", options: workers },
        { key: "stage_type", label: "Stage", options: STAGE_TYPE_OPTIONS },
      ]}
      columns={columns}
      totals={[{ key: "pending_qty", label: "TOTAL PENDING PIECES" }]}
    />
  );
}
