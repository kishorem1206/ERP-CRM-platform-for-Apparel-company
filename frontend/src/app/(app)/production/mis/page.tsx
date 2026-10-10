"use client";

import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

const STATUS_HEX: Record<string, string> = {
  draft: "#94A3B8", planned: "#0049A7", approved: "#0F78FF",
  in_production: "#8174F5", qc: "#A096F7", packing: "#A096F7",
  completed: "#0F78FF", cancelled: "#1D0DB0",
  pending: "#0049A7", received: "#0F78FF", partial: "#A096F7",
  issued: "#8174F5", open: "#0049A7", closed: "#0F78FF",
};

function StatusDot({ status }: { status: string }) {
  const color = STATUS_HEX[status] ?? "#94A3B8";
  const label = status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap"
      style={{ background: `${color}18`, color }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {label}
    </span>
  );
}

interface MISItem {
  used_qty: string | null;
  returned_qty: string | null;
  wastage_qty: string | null;
  issued_qty: string;
}

type MIS = Record<string, unknown> & {
  id: string;
  issue_number: string;
  lot_number: string | null;
  issue_date: string;
  status: string;
  warehouse_name: string | null;
  stage_name: string | null;
  notes: string | null;
  items: MISItem[];
};

function reconciled(items: MISItem[]): boolean {
  if (items.length === 0) return false;
  return items.every((i) => i.used_qty !== null || i.returned_qty !== null || i.wastage_qty !== null);
}

const columns: Column<MIS>[] = [
  { key: "issue_number", header: "MIS No." },
  { key: "lot_number", header: "Lot No." },
  { key: "stage_name", header: "Stage", render: (row) => row.stage_name ?? "—" },
  { key: "issue_date", header: "Issue Date" },
  { key: "warehouse_name", header: "Warehouse", render: (row) => row.warehouse_name ?? "—" },
  {
    key: "status",
    header: "Status",
    render: (row) => <StatusDot status={row.status} />,
  },
  {
    key: "reconciled",
    header: "Material Return",
    render: (row) =>
      reconciled(row.items) ? (
        <span className="text-[11px] font-semibold" style={{ color: "#0F78FF" }}>Recorded</span>
      ) : (
        <span className="text-[11px] text-muted-foreground">Pending</span>
      ),
  },
];

export default function MISPage() {
  const router = useRouter();
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
        <DataTable
          columns={columns}
          data={data ?? []}
          loading={isLoading}
          onRowClick={(row) => router.push(`/production/mis/${row.id as string}`)}
        />
      </div>
    </div>
  );
}
