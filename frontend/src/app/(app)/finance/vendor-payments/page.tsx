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
  recorded:    BLUE,
  reconciled:  "#0F78FF",
  cancelled:   "#1D0DB0",
  paid:        "#0F78FF",
  unpaid:      "#1D0DB0",
  overdue:     "#1D0DB0",
  pending:     BLUE,
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

type VendorPayment = Record<string, unknown> & {
  id: string;
  payment_number: string;
  vendor_name: string | null;
  payment_date: string;
  amount: string;
  payment_mode: string;
  reference: string | null;
  status: string;
};

const columns: Column<VendorPayment>[] = [
  { key: "payment_number", header: "Payment No." },
  { key: "vendor_name", header: "Vendor" },
  { key: "payment_date", header: "Date" },
  {
    key: "amount",
    header: "Amount",
    render: (row) => `₹${Number(row.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`,
  },
  { key: "payment_mode", header: "Mode" },
  { key: "reference", header: "Reference" },
  {
    key: "status",
    header: "Status",
    render: (row) => <StatusDot status={row.status} />,
  },
];

export default function VendorPaymentsPage() {
  const router = useRouter();
  const { data, isLoading } = useQuery({
    queryKey: ["finance-vendor-payments"],
    queryFn: async () => {
      const res = await api.get("/finance/vendor-payments");
      return (res.data.data ?? []) as VendorPayment[];
    },
  });

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            FINANCE / VENDOR PAYMENTS
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Vendor Payments</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Track outgoing payments to suppliers.
          </p>
        </div>
      </div>

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              PAYMENTS
            </p>
            <p className="text-sm font-medium mt-0.5">
              {data ? `${data.length} payment${data.length !== 1 ? "s" : ""}` : "Loading…"}
            </p>
          </div>
        </div>
        <div className="p-0">
          <DataTable columns={columns} data={data ?? []} loading={isLoading} onRowClick={(row) => router.push(`/finance/vendor-payments/${row.id as string}`)} />
        </div>
      </div>
    </div>
  );
}
