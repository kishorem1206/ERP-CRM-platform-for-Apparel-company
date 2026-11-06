"use client";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { StatusBadge } from "@/components/shared/status-badge";
import { Can } from "@/lib/permissions";
import { RETAIL_ACCENT, rupees } from "@/lib/retail";

const STATUSES = ["", "draft", "sent", "accepted", "rejected", "expired", "converted"];
const label = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : "All");
const badge = (s: string) => ({ converted: "completed", accepted: "approved", expired: "inactive", sent: "open" }[s] ?? s);

const columns: Column<Record<string, unknown>>[] = [
  { key: "estimate_number", header: "Estimate #" },
  { key: "estimate_date", header: "Date" },
  { key: "customer_name", header: "Customer", render: (r) => (r.customer_name as string) || <span className="text-muted-foreground">Walk-in</span> },
  { key: "valid_until", header: "Valid until", render: (r) => (r.valid_until as string) || "—" },
  { key: "status", header: "Status", render: (r) => <StatusBadge status={badge(r.status as string)} label={label(r.status as string)} /> },
  { key: "total_amount", header: "Total", className: "text-right", render: (r) => rupees(r.total_amount as string, 0) },
];

export default function RetailEstimatesPage() {
  const router = useRouter();
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["retail-estimates", status, search],
    queryFn: async () => (await api.get("/retail/estimates", { params: { status: status || undefined, search: search || undefined, page_size: 100 } })).data,
  });
  return (
    <div className="p-8 space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / RETAIL</p>
          <h1 className="text-2xl font-bold tracking-tight">Retail Estimates</h1>
          <p className="text-sm text-muted-foreground mt-1">Price quotes for walk-in and retail customers — convert one into a bill when they buy.</p>
        </div>
        <Can perm="retail.create">
          <Link href="/sales/retail/estimates/create" className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: RETAIL_ACCENT }}>
            <Plus className="h-4 w-4" /> New estimate
          </Link>
        </Can>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input className="rounded-lg border border-input bg-background pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Estimate #, customer or mobile…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="flex flex-wrap items-center gap-1 p-1 bg-muted/50 rounded-xl">
          {STATUSES.map((s) => (
            <button key={s || "all"} onClick={() => setStatus(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${status === s ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>
              {label(s)}
            </button>
          ))}
        </div>
      </div>
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <DataTable columns={columns} data={(data?.data ?? []) as Record<string, unknown>[]} loading={isLoading}
          onRowClick={(r) => router.push(`/sales/retail/estimates/${r.id as string}`)} emptyMessage="No estimates yet" />
      </div>
    </div>
  );
}
