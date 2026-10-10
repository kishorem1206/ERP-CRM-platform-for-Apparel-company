"use client";

import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { formatIndianFull } from "@/lib/format";

type ProductionOutput = Record<string, unknown> & {
  id: string;
  output_number: string;
  lot_number: string | null;
  product_name: string | null;
  warehouse_name: string | null;
  output_date: string;
  quantity: string;
  rejected_qty: string | null;
  unit_abbreviation: string | null;
  unit_cost: string;
  total_cost: string;
};

const columns: Column<ProductionOutput>[] = [
  { key: "output_number", header: "Output No." },
  { key: "lot_number", header: "Lot No." },
  { key: "product_name", header: "Product", render: (row) => row.product_name ?? "—" },
  { key: "warehouse_name", header: "Warehouse", render: (row) => row.warehouse_name ?? "—" },
  { key: "output_date", header: "Date" },
  {
    key: "quantity",
    header: "Qty",
    render: (row) => `${Number(row.quantity).toLocaleString("en-IN", { maximumFractionDigits: 4 })} ${row.unit_abbreviation ?? ""}`,
  },
  {
    key: "rejected_qty",
    header: "Rejected",
    render: (row) =>
      row.rejected_qty && Number(row.rejected_qty) > 0 ? (
        <span className="font-semibold" style={{ color: "#B45309" }}>
          {Number(row.rejected_qty).toLocaleString("en-IN", { maximumFractionDigits: 4 })} {row.unit_abbreviation ?? ""}
        </span>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
  },
  {
    key: "total_cost",
    header: "Total Cost",
    render: (row) => formatIndianFull(Number(row.total_cost)),
  },
];

export default function ProductionOutputsPage() {
  const router = useRouter();
  const { data, isLoading } = useQuery({
    queryKey: ["production-outputs"],
    queryFn: async () => {
      const res = await api.get("/production/outputs");
      return (res.data.data ?? []) as ProductionOutput[];
    },
  });

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">PRODUCTION / OUTPUT</p>
          <h1 className="text-2xl font-bold tracking-tight">Production Output</h1>
          <p className="text-sm text-muted-foreground mt-1">Record finished goods quantities per lot and stage.</p>
        </div>
      </div>

      {/* Card-wrapped table */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">OUTPUT RECORDS</p>
            <p className="text-sm font-medium mt-0.5">All recorded production outputs</p>
          </div>
        </div>
        <DataTable
          columns={columns}
          data={data ?? []}
          loading={isLoading}
          onRowClick={(row) => router.push(`/production/outputs/${row.id as string}`)}
        />
      </div>
    </div>
  );
}
