"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Users, Plus, Search, Edit2 } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

// ── Palette ───────────────────────────────────────────────────────────────────
const INDIGO = "#5347CE";

// ── StatusDot ─────────────────────────────────────────────────────────────────
const STATUS_HEX: Record<string, string> = {
  draft: "#94A3B8", planned: "#4896FE", approved: "#887CFD",
  in_production: "#16C8C7", qc: "#F59E0B", packing: "#F97316",
  completed: "#10B981", cancelled: "#EF4444",
  pending: "#4896FE", received: "#10B981", partial: "#F59E0B",
  paid: "#10B981", unpaid: "#EF4444", overdue: "#EF4444",
  sent: "#887CFD", confirmed: "#10B981", delivered: "#10B981",
  converted: "#10B981", domestic: "#4896FE", export: "#5347CE",
  active: "#10B981", inactive: "#94A3B8", sez: "#F59E0B",
};

function StatusDot({ status }: { status: string }) {
  const color = STATUS_HEX[status?.toLowerCase()] ?? "#94A3B8";
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

// ── Types ─────────────────────────────────────────────────────────────────────
interface Customer {
  id: string;
  code: string;
  legal_name: string;
  trade_name: string | null;
  mobile: string | null;
  email: string | null;
  gstin: string | null;
  customer_type: string;
  is_active: boolean;
}

const TYPE_FILTERS = [
  { label: "All", value: "" },
  { label: "Domestic", value: "domestic" },
  { label: "Export", value: "export" },
  { label: "SEZ", value: "sez" },
];

// ── Page ──────────────────────────────────────────────────────────────────────
export default function CustomersPage() {
  const router = useRouter();
  const [typeFilter, setTypeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["customers", typeFilter, search, page],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      if (typeFilter) params.set("customer_type", typeFilter);
      if (search) params.set("search", search);
      const res = await api.get(`/sales/customers?${params}`);
      return res.data;
    },
  });

  const customers: Customer[] = data?.data ?? [];
  const total: number = data?.meta?.total ?? 0;

  const columns: Column<Record<string, unknown>>[] = [
    { key: "code", header: "Code", sortable: true },
    { key: "legal_name", header: "Legal Name", sortable: true },
    { key: "trade_name", header: "Trade Name", render: (row) => (row.trade_name as string) || "—" },
    { key: "mobile", header: "Mobile", render: (row) => (row.mobile as string) || "—" },
    { key: "email", header: "Email", render: (row) => (row.email as string) || "—" },
    { key: "gstin", header: "GSTIN", render: (row) => (row.gstin as string) || "—" },
    {
      key: "customer_type",
      header: "Type",
      render: (row) => <StatusDot status={row.customer_type as string} />,
    },
    {
      key: "is_active",
      header: "Status",
      render: (row) => <StatusDot status={row.is_active ? "active" : "inactive"} />,
    },
    {
      key: "actions",
      header: "",
      render: (row) => (
        <button
          onClick={(e) => { e.stopPropagation(); router.push(`/crm/customers/${row.id as string}`); }}
          className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          title="Edit"
        >
          <Edit2 className="h-4 w-4" />
        </button>
      ),
    },
  ];

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">CRM / CUSTOMERS</p>
          <h1 className="text-2xl font-bold tracking-tight">Customers</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage buyer profiles, credit terms, and contact details.</p>
        </div>
        <button
          onClick={() => router.push("/crm/customers/new")}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: INDIGO }}
        >
          <Plus className="h-4 w-4" /> New Customer
        </button>
      </div>

      {/* Search + filter strip */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            className="rounded-xl border border-input bg-background pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Search customers…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit flex-wrap">
          {TYPE_FILTERS.map((t) => (
            <button
              key={t.value}
              onClick={() => { setTypeFilter(t.value); setPage(1); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                typeFilter === t.value
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">ALL CUSTOMERS</p>
            <p className="text-sm font-medium mt-0.5">{total} record{total !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <div className="p-6">
          <DataTable
            columns={columns}
            data={customers as unknown as Record<string, unknown>[]}
            loading={isLoading}
            emptyMessage="No customers found — click New Customer to add one"
            onRowClick={(row) => router.push(`/crm/customers/${row.id as string}`)}
          />
        </div>
      </div>

      {total > 50 && (
        <div className="flex justify-center gap-2">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
            className="px-3 py-1 rounded border border-input text-sm disabled:opacity-40">Prev</button>
          <span className="text-sm text-muted-foreground self-center">Page {page}</span>
          <button onClick={() => setPage((p) => p + 1)} disabled={customers.length < 50}
            className="px-3 py-1 rounded border border-input text-sm disabled:opacity-40">Next</button>
        </div>
      )}
    </div>
  );
}
