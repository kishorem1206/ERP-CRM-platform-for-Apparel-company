"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { usePipelineOptions, useLeadSourceOptions } from "@/components/reports/filter-sources";

const TEAL = "#8174F5";

type Row = {
  title: string; stage_name: string; source_name: string; lead_value: string;
  status: string; temperature: string; created_date: string; closed_date: string | null; days_in_stage: number;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const columns: Column<Row>[] = [
  { key: "title", header: "Lead", sortable: true },
  { key: "stage_name", header: "Stage" },
  { key: "source_name", header: "Source" },
  {
    key: "temperature", header: "Temp",
    render: (r) => (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold capitalize whitespace-nowrap"
        style={{ background: `${TEAL}18`, color: TEAL }}>
        {r.temperature}
      </span>
    ),
  },
  { key: "created_date", header: "Created", sortable: true },
  {
    key: "days_in_stage", header: "Days in Stage",
    render: (r) => <span style={{ color: r.days_in_stage > 14 ? "#1D0DB0" : undefined }}>{r.days_in_stage}</span>,
    sortable: true,
  },
  { key: "lead_value", header: "Value", render: (r) => fmt(r.lead_value), sortable: true },
  { key: "status", header: "Status", className: "capitalize" },
];

export default function LeadConversionAgeingPage() {
  const pipelines = usePipelineOptions();
  const sources = useLeadSourceOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / CRM"
      title="Lead Conversion & Ageing"
      description="Every lead with current stage, source, value, and time-in-stage."
      queryKey="report-lead-ageing"
      endpoint="/reports/lead-conversion-ageing"
      filters={[
        { key: "pipeline_id", label: "Pipeline", options: pipelines, width: "200px" },
        { key: "source_id", label: "Source", options: sources },
      ]}
      columns={columns}
      totals={[{ key: "lead_value", label: "TOTAL PIPELINE VALUE", format: fmt }]}
    />
  );
}
