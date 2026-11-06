"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { rupees, type RetailReturn } from "@/lib/retail";

const columns: Column<Record<string, unknown>>[] = [
  { key: "return_number", header: "Return #" },
  { key: "return_date", header: "Date" },
  { key: "invoice_number", header: "Bill" },
  { key: "customer_name", header: "Customer", render: (r) => (r.customer_name as string) || "Walk-in" },
  { key: "reason", header: "Reason" },
  { key: "return_amount", header: "Value", className: "text-right", render: (r) => rupees(r.return_amount as string) },
  { key: "refund_amount", header: "Refunded", className: "text-right", render: (r) => Number(r.refund_amount) > 0 ? rupees(r.refund_amount as string) : "—" },
];

export default function RetailReturnsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["retail-returns", search],
    queryFn: async () => (await api.get("/retail/returns", { params: { search: search || undefined } })).data.data as RetailReturn[],
  });
  return (
    <div className="p-8 space-y-6">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / RETAIL</p>
        <h1 className="text-2xl font-bold tracking-tight">Retail Returns</h1>
        <p className="text-sm text-muted-foreground mt-1">Items handed back from retail bills. Start a return from the bill.</p>
      </div>
      <div className="relative w-fit">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <input className="rounded-lg border border-input bg-background pl-8 pr-3 py-2 text-sm" placeholder="Return #, customer or mobile…" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <DataTable columns={columns} data={(data ?? []) as unknown as Record<string, unknown>[]} loading={isLoading}
          onRowClick={(r) => router.push(`/sales/retail/returns/${r.id as string}`)} emptyMessage="No returns yet" />
      </div>
    </div>
  );
}
