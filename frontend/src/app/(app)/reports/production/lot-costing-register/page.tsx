"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";
import { useCustomerOptions, useStyleOptions } from "@/components/reports/filter-sources";

type Row = {
  lot_number: string; style_name: string; customer_name: string; status: string; lot_date: string;
  planned_qty: number; first_quality_qty: string; rejected_qty: string; yield_pct: string | null;
  cost_per_piece: string | null; selling_price_per_piece: string | null; profit_per_piece: string | null;
  margin_pct: string | null; total_actual_cost: string; total_profit: string | null; is_final: boolean;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
const fmtOrDash = (v: unknown) => (v === null || v === undefined ? "—" : fmt(v));

const STATUS_OPTIONS = [
  { value: "cutting", label: "Cutting" },
  { value: "checking", label: "Checking" },
  { value: "packing", label: "Packing" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

const columns: Column<Row>[] = [
  { key: "lot_number", header: "Lot #", sortable: true },
  { key: "style_name", header: "Style" },
  { key: "customer_name", header: "Customer", sortable: true },
  { key: "lot_date", header: "Date", sortable: true },
  { key: "first_quality_qty", header: "First Quality", render: (r) => Number(r.first_quality_qty).toLocaleString("en-IN") },
  {
    key: "yield_pct", header: "Yield %",
    render: (r) => (r.yield_pct === null ? "—" : `${Number(r.yield_pct).toFixed(1)}%`),
  },
  { key: "cost_per_piece", header: "Cost/Piece", render: (r) => fmtOrDash(r.cost_per_piece) },
  { key: "selling_price_per_piece", header: "Selling Price/Piece", render: (r) => fmtOrDash(r.selling_price_per_piece) },
  { key: "profit_per_piece", header: "Profit/Piece", render: (r) => fmtOrDash(r.profit_per_piece) },
  {
    key: "margin_pct", header: "Margin %",
    render: (r) => {
      if (r.margin_pct === null) return "—";
      const pct = Number(r.margin_pct);
      return <span style={{ color: pct >= 0 ? "#0049A7" : "#1D0DB0" }}>{pct.toFixed(1)}%</span>;
    },
    sortable: true,
  },
  {
    key: "is_final", header: "Status",
    render: (r) => (
      <span
        className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold capitalize whitespace-nowrap"
        style={{ background: r.is_final ? "#0049A718" : "#A096F718", color: r.is_final ? "#0049A7" : "#8174F5" }}
      >
        {r.is_final ? "Final" : r.status}
      </span>
    ),
  },
];

export default function LotCostingRegisterPage() {
  const customers = useCustomerOptions();
  const styles = useStyleOptions();
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / PRODUCTION"
      title="Lot Costing Register"
      description="Cost/piece, selling price, profit, and margin across all lots — same engine as the lot detail page."
      queryKey="report-lot-costing-register"
      endpoint="/reports/lot-costing-register"
      filters={[
        { key: "customer_id", label: "Customer", options: customers, width: "200px" },
        { key: "style_id", label: "Style", options: styles },
        { key: "status", label: "Status", options: STATUS_OPTIONS },
      ]}
      columns={columns}
      totals={[
        { key: "total_actual_cost", label: "TOTAL ACTUAL COST", format: fmt },
        { key: "total_profit", label: "TOTAL PROFIT", format: fmt },
      ]}
    />
  );
}
