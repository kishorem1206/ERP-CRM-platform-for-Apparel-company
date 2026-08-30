"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

type ProductionOutput = Record<string, unknown> & {
  id: string;
  output_number: string;
  lot_number: string | null;
  output_date: string;
  quantity: string;
  unit_cost: string;
  total_cost: string;
};

const columns: Column<ProductionOutput>[] = [
  { key: "output_number", header: "Output No." },
  { key: "lot_number", header: "Lot No." },
  { key: "output_date", header: "Date" },
  { key: "quantity", header: "Qty" },
  {
    key: "unit_cost",
    header: "Unit Cost",
    render: (row) => `₹${Number(row.unit_cost).toFixed(2)}`,
  },
  {
    key: "total_cost",
    header: "Total Cost",
    render: (row) => `₹${Number(row.total_cost).toFixed(2)}`,
  },
];

export default function ProductionOutputsPage() {
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
        <DataTable columns={columns} data={data ?? []} loading={isLoading} />
      </div>
    </div>
  );
}
