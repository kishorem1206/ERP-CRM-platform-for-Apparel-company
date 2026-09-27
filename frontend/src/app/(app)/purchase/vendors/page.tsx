"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, X } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { StatusBadge } from "@/components/shared/status-badge";
import { ModalPortal } from "@/components/shared/modal-portal";
import { SearchableSelect } from "@/components/shared/searchable-select";

const LAVENDER = "#0F78FF";

type VendorType = "supplier" | "job_worker" | "transporter" | "agent";

interface Vendor {
  id: string;
  code: string;
  name: string;
  gstin: string | null;
  pan: string | null;
  vendor_type: VendorType;
  payment_terms: number;
  is_active: boolean;
}

const TYPE_LABELS: Record<VendorType, string> = {
  supplier: "Supplier",
  job_worker: "Job Worker",
  transporter: "Transporter",
  agent: "Agent",
};

const TYPE_FILTERS = [
  { label: "All", value: "" },
  { label: "Suppliers", value: "supplier" },
  { label: "Job Workers", value: "job_worker" },
  { label: "Transporters", value: "transporter" },
  { label: "Agents", value: "agent" },
];

const columns: Column<Record<string, unknown>>[] = [
  { key: "code", header: "Code", sortable: true },
  { key: "name", header: "Vendor Name", sortable: true },
  {
    key: "vendor_type",
    header: "Type",
    render: (row) => (
      <span className="text-xs text-muted-foreground">
        {TYPE_LABELS[(row.vendor_type as VendorType)] ?? (row.vendor_type as string)}
      </span>
    ),
  },
  { key: "gstin", header: "GSTIN", render: (row) => (row.gstin as string) || "—" },
  { key: "pan", header: "PAN", render: (row) => (row.pan as string) || "—" },
  {
    key: "payment_terms",
    header: "Payment Terms",
    render: (row) => `${row.payment_terms} days`,
    className: "text-right",
  },
  {
    key: "is_active",
    header: "Status",
    render: (row) => <StatusBadge status={row.is_active ? "active" : "inactive"} />,
  },
];

const EMPTY = {
  code: "",
  name: "",
  gstin: "",
  pan: "",
  vendor_type: "supplier",
  payment_terms: "30",
};

function parseApiError(e: unknown, fallback: string): string {
  const data = (e as { response?: { data?: Record<string, unknown> } })?.response?.data;
  if (!data) return fallback;
  const err = data.error;
  if (typeof err === "string") return err;
  if (err && typeof (err as { message?: string }).message === "string")
    return (err as { message: string }).message;
  const detail = data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0)
    return (detail as Array<{ msg: string }>)[0]?.msg ?? fallback;
  return fallback;
}

function autoCode(name: string): string {
  const prefix = name.trim().toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 4) || "V";
  return `${prefix}-${Math.floor(1000 + Math.random() * 9000)}`;
}

function AddVendorModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");

  const mut = useMutation({
    mutationFn: (body: typeof EMPTY) =>
      api.post("/purchase/vendors", {
        ...body,
        payment_terms: parseInt(body.payment_terms) || 30,
        gstin: body.gstin || null,
        pan: body.pan || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vendors"] });
      onClose();
    },
    onError: (e: unknown) => {
      setError(parseApiError(e, "Failed to create vendor"));
    },
  });

  const set = (k: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <ModalPortal>
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
      <div className="bg-card border rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="font-semibold text-base">New Vendor</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
        </div>
        <form
          className="p-5 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            setError("");
            const finalForm = { ...form, code: form.code || autoCode(form.name || "V") };
            setForm(finalForm);
            mut.mutate(finalForm);
          }}
        >
          <div>
            <label className="text-xs font-medium text-muted-foreground">Vendor Name *</label>
            <input required value={form.name}
              onChange={(e) => {
                const name = e.target.value;
                setForm((f) => ({ ...f, name, code: f.code || autoCode(name) }));
              }}
              className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Vendor Company Name" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Code *</label>
              <div className="flex gap-1 mt-1">
                <input required value={form.code} onChange={set("code")}
                  className="w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="e.g. SUPP-1234" />
                <button type="button"
                  onClick={() => setForm((f) => ({ ...f, code: autoCode(f.name || "V") }))}
                  className="shrink-0 px-2 py-1 rounded border border-input text-xs hover:bg-muted text-muted-foreground"
                  title="Auto-generate">
                  ↻
                </button>
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Type *</label>
              <div className="mt-1">
                <SearchableSelect
                  value={form.vendor_type}
                  onChange={(v) => setForm((f) => ({ ...f, vendor_type: v as typeof EMPTY["vendor_type"] }))}
                  accent={LAVENDER}
                  options={[
                    { value: "supplier", label: "Supplier" },
                    { value: "job_worker", label: "Job Worker" },
                    { value: "transporter", label: "Transporter" },
                    { value: "agent", label: "Agent" },
                  ]}
                />
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">GSTIN</label>
              <input value={form.gstin} onChange={set("gstin")}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="22AAAAA0000A1Z5" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">PAN</label>
              <input value={form.pan} onChange={set("pan")}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="AAAAA0000A" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Payment Terms (days)</label>
            <input type="number" min="0" value={form.payment_terms} onChange={set("payment_terms")}
              className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose}
              className="px-4 py-1.5 rounded border border-input text-sm hover:bg-muted">Cancel</button>
            <button type="submit" disabled={mut.isPending}
              className="px-4 py-1.5 rounded bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-60">
              {mut.isPending ? "Saving…" : "Save Vendor"}
            </button>
          </div>
        </form>
      </div>
    </div>
    </ModalPortal>
  );
}

export default function VendorsPage() {
  const [typeFilter, setTypeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showAdd, setShowAdd] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["vendors", typeFilter, search, page],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      if (typeFilter) params.set("vendor_type", typeFilter);
      if (search) params.set("search", search);
      const res = await api.get(`/purchase/vendors?${params}`);
      return res.data;
    },
  });

  const vendors: Vendor[] = data?.data ?? [];
  const total: number = data?.meta?.total ?? 0;

  return (
    <div className="p-8 space-y-8">
      {showAdd && <AddVendorModal onClose={() => setShowAdd(false)} />}

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">PURCHASE / VENDORS</p>
          <h1 className="text-2xl font-bold tracking-tight">Vendors</h1>
          <p className="text-sm text-muted-foreground mt-1">Yarn mills, fabric suppliers, job workers, agents, and trim vendors.</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all duration-200 hover:opacity-90 active:scale-95"
          style={{ background: LAVENDER }}
        >
          <Plus className="h-4 w-4" /> New Vendor
        </button>
      </div>

      {/* Search + filter strip */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            className="rounded-lg border border-input bg-background pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Search vendors…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit">
          {TYPE_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => { setTypeFilter(f.value); setPage(1); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                typeFilter === f.value
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <span className="text-sm text-muted-foreground ml-1">{total} vendors</span>
      </div>

      {/* Card-wrapped table */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">VENDOR DIRECTORY</p>
            <p className="text-sm font-medium mt-0.5">
              {typeFilter ? TYPE_LABELS[typeFilter as VendorType] ?? typeFilter : "All types"}
            </p>
          </div>
        </div>
        <DataTable
          columns={columns}
          data={vendors as unknown as Record<string, unknown>[]}
          loading={isLoading}
          emptyMessage="No vendors found"
        />
      </div>
    </div>
  );
}
