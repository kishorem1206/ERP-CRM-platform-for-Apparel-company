"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";
const ORANGE   = "#A096F7";

const STATUS_HEX: Record<string, string> = {
  issued:    BLUE,
  applied:   "#0F78FF",
  cancelled: "#1D0DB0",
  pending:   BLUE,
};

function StatusDot({ status }: { status: string }) {
  const color = STATUS_HEX[status?.toLowerCase()] ?? "#94A3B8";
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

type DebitNote = Record<string, unknown> & {
  id: string;
  debit_note_number: string;
  vendor_name: string | null;
  debit_note_date: string;
  total_amount: string;
  status: string;
};

const columns: Column<DebitNote>[] = [
  { key: "debit_note_number", header: "DN No." },
  { key: "vendor_name", header: "Vendor" },
  { key: "debit_note_date", header: "Date" },
  {
    key: "total_amount",
    header: "Total",
    render: (row) => `₹${Number(row.total_amount).toFixed(2)}`,
  },
  {
    key: "status",
    header: "Status",
    render: (row) => <StatusDot status={row.status} />,
  },
];

export default function DebitNotesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["finance-debit-notes"],
    queryFn: async () => {
      const res = await api.get("/finance/debit-notes");
      return (res.data.data ?? []) as DebitNote[];
    },
  });

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            FINANCE / DEBIT NOTES
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Debit Notes</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Vendor debit notes and purchase returns.
          </p>
        </div>
      </div>

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              DEBIT NOTES
            </p>
            <p className="text-sm font-medium mt-0.5">
              {data ? `${data.length} note${data.length !== 1 ? "s" : ""}` : "Loading…"}
            </p>
          </div>
        </div>
        <div className="p-0">
          <DataTable columns={columns} data={data ?? []} loading={isLoading} />
        </div>
      </div>
    </div>
  );
}
