"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useLeadSourceOptions } from "@/components/reports/filter-sources";

const INDIGO = "#0049A7";

type Row = {
  source_name: string; total_leads: number; qualified_leads: number; converted_leads: number;
  revenue_generated: string; total_ad_spend: string;
  cost_per_lead: string | null; cost_per_qualified_lead: string | null;
  cost_per_conversion: string | null; roas: string | null;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
const fmtOrDash = (v: string | null) => (v === null ? "—" : fmt(v));

const columns: Column<Row>[] = [
  { key: "source_name", header: "Platform", sortable: true },
  { key: "total_leads", header: "Total Leads", sortable: true },
  { key: "qualified_leads", header: "Qualified" },
  { key: "converted_leads", header: "Converted" },
  { key: "revenue_generated", header: "Revenue", render: (r) => fmt(r.revenue_generated), sortable: true },
  { key: "total_ad_spend", header: "Ad Spend", render: (r) => fmt(r.total_ad_spend), sortable: true },
  { key: "cost_per_lead", header: "Cost / Lead", render: (r) => fmtOrDash(r.cost_per_lead) },
  { key: "cost_per_qualified_lead", header: "Cost / Qualified Lead", render: (r) => fmtOrDash(r.cost_per_qualified_lead) },
  { key: "cost_per_conversion", header: "Cost / Conversion", render: (r) => fmtOrDash(r.cost_per_conversion) },
  {
    key: "roas", header: "ROAS",
    render: (r) => (r.roas === null ? "—" : `${Number(r.roas).toFixed(2)}×`),
  },
];

export default function LeadAcquisitionCostPage() {
  const sources = useLeadSourceOptions();

  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / CRM"
      title="Lead Acquisition Cost"
      description="Cost per lead, per qualified lead, per conversion, and ROAS by platform. A dash means no ad spend was logged for that platform in this range — not zero cost."
      queryKey="report-lead-acquisition-cost"
      endpoint="/reports/lead-acquisition-cost"
      filters={[{ key: "source_id", label: "Platform", options: sources, width: "200px" }]}
      columns={columns}
      totals={[
        { key: "total_leads", label: "TOTAL LEADS" },
        { key: "total_ad_spend", label: "TOTAL AD SPEND", format: fmt },
        { key: "revenue_generated", label: "TOTAL REVENUE", format: fmt },
      ]}
      accent={INDIGO}
    />
  );
}
