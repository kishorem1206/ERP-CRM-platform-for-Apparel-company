"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useLeadSourceOptions, useEmployeeOptions, useCustomerOptions } from "@/components/reports/filter-sources";

const INDIGO = "#0049A7";

type Row = {
  source_name: string; total_leads: number; qualified_leads: number; converted_leads: number;
  lost_leads: number; conversion_rate: string | null; revenue_generated: string; avg_lead_value: string;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const STATUS_OPTIONS = [
  { value: "open", label: "Open" },
  { value: "won", label: "Won" },
  { value: "lost", label: "Lost" },
];

const columns: Column<Row>[] = [
  { key: "source_name", header: "Platform", sortable: true },
  { key: "total_leads", header: "Total Leads", sortable: true },
  { key: "qualified_leads", header: "Qualified" },
  { key: "converted_leads", header: "Converted" },
  { key: "lost_leads", header: "Lost" },
  {
    key: "conversion_rate", header: "Conversion %",
    render: (r) => (r.conversion_rate === null ? "—" : `${Number(r.conversion_rate).toFixed(1)}%`),
    sortable: true,
  },
  { key: "revenue_generated", header: "Revenue Generated", render: (r) => fmt(r.revenue_generated), sortable: true },
  { key: "avg_lead_value", header: "Avg Lead Value", render: (r) => fmt(r.avg_lead_value) },
];

export default function PlatformAnalyticsPage() {
  const sources = useLeadSourceOptions();
  const employees = useEmployeeOptions();
  const customers = useCustomerOptions();

  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / CRM"
      title="Platform-Wise Lead Analytics"
      description="Leads, qualification, conversion, and revenue by source/platform. Ad spend, cost-per-lead/conversion, and ROI/ROAS aren't shown — no ad-spend data exists yet; these arrive with ad-spend tracking in a later phase."
      queryKey="report-platform-analytics"
      endpoint="/reports/platform-lead-analytics"
      filters={[
        { key: "source_id", label: "Platform", options: sources, width: "180px" },
        { key: "assigned_to", label: "Employee", options: employees, width: "180px" },
        { key: "status", label: "Status", options: STATUS_OPTIONS },
        { key: "customer_id", label: "Customer", options: customers, width: "200px" },
      ]}
      columns={columns}
      totals={[
        { key: "total_leads", label: "TOTAL LEADS" },
        { key: "revenue_generated", label: "TOTAL REVENUE", format: fmt },
      ]}
      accent={INDIGO}
    />
  );
}
