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
import { RETAIL_ACCENT, payStatusLabel, rupees } from "@/lib/retail";

const FILTERS = [
  { label: "All", mode: "", status: "" },
  { label: "Cash", mode: "cash", status: "" },
  { label: "Credit", mode: "credit", status: "" },
  { label: "Unpaid", mode: "", status: "unpaid" },
  { label: "Partially paid", mode: "", status: "partially_paid" },
];

const columns: Column<Record<string, unknown>>[] = [
  { key: "invoice_number", header: "Bill #" },
  { key: "invoice_date", header: "Date" },
  {
    key: "customer_name", header: "Customer",
    render: (r) => r.customer_name ? <span>{r.customer_name as string} <span className="text-xs text-muted-foreground">{r.customer_mobile as string}</span></span> : <span className="text-muted-foreground">Walk-in</span>,
  },
  { key: "payment_mode", header: "Mode", render: (r) => (r.payment_mode === "cash" ? "Cash" : "Credit") },
  {
    key: "payment_status", header: "Status",
    render: (r) => r.status === "cancelled"
      ? <StatusBadge status="cancelled" />
      : <StatusBadge status={r.payment_status === "paid" ? "completed" : r.payment_status === "unpaid" ? "pending" : "partial"} label={payStatusLabel(r.payment_status as string)} />,
  },
  { key: "total_amount", header: "Total", className: "text-right", render: (r) => rupees(r.total_amount as string, 0) },
  { key: "outstanding", header: "Outstanding", className: "text-right", render: (r) => Number(r.outstanding) > 0 ? rupees(r.outstanding as string) : "—" },
];

export default function RetailInvoicesPage() {
  const router = useRouter();
  const [filter, setFilter] = useState(0);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const f = FILTERS[filter];
  const { data, isLoading } = useQuery({
    queryKey: ["retail-invoices", filter, search, page],
    queryFn: async () => (await api.get("/retail/invoices", {
      params: { page, page_size: 50, search: search || undefined, payment_mode: f.mode || undefined, payment_status: f.status || undefined },
    })).data,
  });
  const total: number = data?.meta?.total ?? 0;

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / RETAIL</p>
          <h1 className="text-2xl font-bold tracking-tight">Retail Bills</h1>
          <p className="text-sm text-muted-foreground mt-1">Counter bills — cash and credit.</p>
        </div>
        <Can perm="retail.create">
          <Link href="/sales/retail/bill" className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: RETAIL_ACCENT }}>
            <Plus className="h-4 w-4" /> New bill
          </Link>
        </Can>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input className="rounded-lg border border-input bg-background pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Bill #, customer or mobile…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        </div>
        <div className="flex flex-wrap items-center gap-1 p-1 bg-muted/50 rounded-xl">
          {FILTERS.map((x, i) => (
            <button key={x.label} onClick={() => { setFilter(i); setPage(1); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${filter === i ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>
              {x.label}
            </button>
          ))}
        </div>
        <span className="text-sm text-muted-foreground">{total} bills</span>
      </div>
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <DataTable columns={columns} data={(data?.data ?? []) as Record<string, unknown>[]} loading={isLoading}
          onRowClick={(r) => router.push(`/sales/retail/invoices/${r.id as string}`)} emptyMessage="No retail bills yet" />
      </div>
      {total > 50 && (
        <div className="flex justify-end gap-2">
          <button disabled={page === 1} onClick={() => setPage((p) => p - 1)} className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40">Previous</button>
          <button disabled={page * 50 >= total} onClick={() => setPage((p) => p + 1)} className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40">Next</button>
        </div>
      )}
    </div>
  );
}
