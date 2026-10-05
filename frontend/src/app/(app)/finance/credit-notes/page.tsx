"use client";
import { useRouter } from "next/navigation";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

const STATUS_HEX: Record<string, string> = {
  issued:    BLUE,
  applied:   "#0F78FF",
  cancelled: "#1D0DB0",
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

type CreditNote = Record<string, unknown> & {
  id: string;
  credit_note_number: string;
  customer_name: string | null;
  credit_note_date: string;
  taxable_amount: string;
  total_amount: string;
  status: string;
};

const columns: Column<CreditNote>[] = [
  { key: "credit_note_number", header: "CN No." },
  { key: "customer_name", header: "Customer" },
  { key: "credit_note_date", header: "Date" },
  {
    key: "taxable_amount",
    header: "Taxable",
    render: (row) => `₹${Number(row.taxable_amount).toFixed(2)}`,
  },
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

export default function CreditNotesPage() {
  const router = useRouter();
  const { data, isLoading } = useQuery({
    queryKey: ["finance-credit-notes"],
    queryFn: async () => {
      const res = await api.get("/finance/credit-notes");
      return (res.data.data ?? []) as CreditNote[];
    },
  });

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            FINANCE / CREDIT NOTES
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Credit Notes</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Customer credit notes and adjustments.
          </p>
        </div>
      </div>

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              CREDIT NOTES
            </p>
            <p className="text-sm font-medium mt-0.5">
              {data ? `${data.length} note${data.length !== 1 ? "s" : ""}` : "Loading…"}
            </p>
          </div>
        </div>
        <div className="p-0">
          <DataTable columns={columns} data={data ?? []} loading={isLoading} onRowClick={(row) => router.push(`/finance/credit-notes/${row.id as string}`)} />
        </div>
      </div>
    </div>
  );
}
