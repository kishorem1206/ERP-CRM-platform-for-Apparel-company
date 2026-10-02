"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";

type Row = {
  lot_number: string; material_type: string; supplier_name: string;
  invoice_number: string | null; invoice_date: string | null; unit_cost: string | null;
  lot_date: string; received_qty: string; unit_symbol: string | null;
};

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const MATERIAL_TYPE_OPTIONS = [
  { value: "yarn", label: "Yarn" },
  { value: "fabric", label: "Fabric" },
  { value: "trim", label: "Trim" },
];

const columns: Column<Row>[] = [
  { key: "lot_number", header: "Lot #", sortable: true },
  { key: "material_type", header: "Material", className: "capitalize" },
  { key: "supplier_name", header: "Supplier", sortable: true },
  { key: "lot_date", header: "Lot Date", sortable: true },
  { key: "invoice_number", header: "Invoice #", render: (r) => r.invoice_number ?? "—" },
  {
    key: "received_qty", header: "Received Qty",
    render: (r) => `${Number(r.received_qty).toLocaleString("en-IN")} ${r.unit_symbol ?? ""}`,
  },
  { key: "unit_cost", header: "Unit Cost", render: (r) => (r.unit_cost ? fmt(r.unit_cost) : "—") },
];

export default function MaterialLotRegisterPage() {
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / INVENTORY"
      title="Material Lot Register"
      description="Yarn, fabric, and trim lots with supplier and cost."
      queryKey="report-material-lot-register"
      endpoint="/reports/material-lot-register"
      filters={[{ key: "material_type", label: "Material", options: MATERIAL_TYPE_OPTIONS }]}
      columns={columns}
    />
  );
}
