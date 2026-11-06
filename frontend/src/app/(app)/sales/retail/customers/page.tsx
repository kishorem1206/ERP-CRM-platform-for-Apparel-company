"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, UserPlus } from "lucide-react";
import api from "@/lib/api";
import { Can } from "@/lib/permissions";
import { DataTable, Column } from "@/components/shared/data-table";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { RETAIL_ACCENT, rupees } from "@/lib/retail";
import { CustomerFormModal } from "@/components/retail/customer-form";

const SORTS = [
  { value: "recent", label: "Most recent purchase" },
  { value: "frequent", label: "Most frequent" },
  { value: "spending", label: "Highest spending" },
  { value: "products", label: "Most products bought" },
  { value: "lapsed", label: "Not purchased recently" },
  { value: "outstanding", label: "Outstanding credit" },
  { value: "newest", label: "Newly registered" },
  { value: "name", label: "Name A–Z" },
];
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

const columns: Column<Record<string, unknown>>[] = [
  { key: "name", header: "Customer", render: (r) => <span><span className="font-medium">{r.name as string}</span> <span className="text-xs text-muted-foreground">{r.mobile as string}</span></span> },
  { key: "city", header: "City", render: (r) => (r.city as string) || "—" },
  { key: "purchase_count", header: "Bills", className: "text-right" },
  { key: "products_purchased", header: "Items", className: "text-right", render: (r) => Number(r.products_purchased) },
  { key: "total_spent", header: "Spent", className: "text-right", render: (r) => rupees(r.total_spent as string, 0) },
  { key: "last_purchase_date", header: "Last purchase", render: (r) => (r.last_purchase_date as string) || "—" },
  { key: "outstanding", header: "Outstanding", className: "text-right", render: (r) => Number(r.outstanding) > 0 ? rupees(r.outstanding as string) : "—" },
];

export default function RetailCustomersPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("recent");
  const [city, setCity] = useState("");
  const [month, setMonth] = useState("");
  const [adding, setAdding] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["retail-customers", search, sort, city, month],
    queryFn: async () => (await api.get("/retail/customers", {
      params: { search: search || undefined, sort, city: city || undefined, birthday_month: month || undefined, page_size: 100 },
    })).data,
  });
  return (
    <div className="p-8 space-y-6">
      {adding && (
        <CustomerFormModal onClose={() => setAdding(false)}
          onSaved={(id) => { setAdding(false); qc.invalidateQueries({ queryKey: ["retail-customers"] }); router.push(`/sales/retail/customers/${id}`); }} />
      )}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / RETAIL</p>
          <h1 className="text-2xl font-bold tracking-tight">Retail Customers</h1>
          <p className="text-sm text-muted-foreground mt-1">Counter customers, kept apart from B2B customers. Mobile number is the key.</p>
        </div>
        <Can perm="retail.create">
          <button onClick={() => setAdding(true)} className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: RETAIL_ACCENT }}>
            <UserPlus className="h-4 w-4" /> Register customer
          </button>
        </Can>
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input className="w-full rounded-lg border border-input bg-background pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Name, mobile or email…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <SearchableSelect value={sort} onChange={(v) => setSort(v || "recent")} accent={RETAIL_ACCENT} options={SORTS} />
        <input className="rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="City" value={city} onChange={(e) => setCity(e.target.value)} />
        <SearchableSelect clearable value={month} onChange={setMonth} accent={RETAIL_ACCENT} placeholder="Birthday month"
          options={MONTHS.map((m, i) => ({ value: String(i + 1), label: `Birthday in ${m}` }))} />
      </div>
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <DataTable columns={columns} data={(data?.data ?? []) as Record<string, unknown>[]} loading={isLoading}
          onRowClick={(r) => router.push(`/sales/retail/customers/${r.id as string}`)} emptyMessage="No retail customers yet" />
      </div>
    </div>
  );
}
