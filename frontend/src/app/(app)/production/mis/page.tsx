"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

const TEAL = "#16C8C7";

const STATUS_HEX: Record<string, string> = {
  draft: "#94A3B8", planned: "#4896FE", approved: "#887CFD",
  in_production: "#16C8C7", qc: "#F59E0B", packing: "#F97316",
  completed: "#10B981", cancelled: "#EF4444",
  pending: "#4896FE", received: "#10B981", partial: "#F59E0B",
  issued: TEAL, open: "#4896FE", closed: "#10B981",
};

function StatusDot({ status }: { status: string }) {
  const color = STATUS_HEX[status] ?? "#94A3B8";
  const label = status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"
      style={{ background: `${color}18`, color }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {label}
    </span>
  );
}

type MIS = Record<string, unknown> & {
  id: string;
  issue_number: string;
  lot_number: string | null;
  issue_date: string;
  status: string;
  warehouse_id: string;
  notes: string | null;
};

const columns: Column<MIS>[] = [
  { key: "issue_number", header: "MIS No." },
  { key: "lot_number", header: "Lot No." },
  { key: "issue_date", header: "Issue Date" },
  { key: "warehouse_id", header: "Warehouse" },
  {
    key: "status",
    header: "Status",
    render: (row) => <StatusDot status={row.status} />,
  },
  { key: "notes", header: "Notes" },
];

export default function MISPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["production-mis"],
    queryFn: async () => {
      const res = await api.get("/production/mis");
      return (res.data.data ?? []) as MIS[];
    },
  });

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">PRODUCTION / MATERIALS</p>
          <h1 className="text-2xl font-bold tracking-tight">Material Issue Slips</h1>
          <p className="text-sm text-muted-foreground mt-1">Track raw material issued from warehouse to production.</p>
        </div>
      </div>

      {/* Card-wrapped table */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">ISSUE SLIPS</p>
            <p className="text-sm font-medium mt-0.5">All material issue records</p>
          </div>
        </div>
        <DataTable columns={columns} data={data ?? []} loading={isLoading} />
      </div>
    </div>
  );
}
