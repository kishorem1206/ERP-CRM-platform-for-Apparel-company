"use client";

import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, Upload, Calendar } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { ModalShell } from "@/components/shared/modal-shell";
import { AdSpendFormModal, AdSpendEntry } from "@/components/crm/ad-spend-form-modal";
import { AdSpendImportModal } from "@/components/crm/ad-spend-import-modal";

const INDIGO = "#0049A7";

type SpendRow = Record<string, unknown> & AdSpendEntry & {
  source_name: string | null;
  created_by_name: string | null;
};

interface AcquisitionRow {
  source_name: string;
  total_leads: number;
  qualified_leads: number;
  converted_leads: number;
  revenue_generated: string;
  total_ad_spend: string;
  cost_per_lead: string | null;
  cost_per_qualified_lead: string | null;
  cost_per_conversion: string | null;
  roas: string | null;
}

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
const fmtOrDash = (v: number | null) => (v === null ? "—" : fmt(v));

const PRESETS: { label: string; value: number | "ytd" }[] = [
  { label: "30D", value: 30 },
  { label: "90D", value: 90 },
  { label: "YTD", value: "ytd" },
  { label: "All", value: 3650 },
];

export default function AdSpendPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [editing, setEditing] = useState<SpendRow | undefined>(undefined);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const today = new Date().toISOString().slice(0, 10);
  const [from, setFrom] = useState(new Date(Date.now() - 90 * 86_400_000).toISOString().slice(0, 10));
  const [to, setTo] = useState(today);

  const applyPreset = (days: number | "ytd") => {
    const toStr = new Date().toISOString().slice(0, 10);
    const fromStr = days === "ytd"
      ? `${new Date().getFullYear()}-01-01`
      : new Date(Date.now() - days * 86_400_000).toISOString().slice(0, 10);
    setFrom(fromStr);
    setTo(toStr);
  };

  const { data, isLoading } = useQuery({
    queryKey: ["crm-ad-spend"],
    queryFn: async () => {
      const res = await api.get("/crm/ad-spend?page_size=100");
      return res.data;
    },
  });
  const rows: SpendRow[] = data?.data ?? [];
  const totalSpend = rows.reduce((acc, r) => acc + Number(r.amount), 0);

  const { data: acquisitionData } = useQuery({
    queryKey: ["crm-ad-spend-acquisition", from, to],
    queryFn: async () => {
      const res = await api.get("/reports/lead-acquisition-cost", { params: { from_date: from, to_date: to } });
      return (res.data.data ?? []) as AcquisitionRow[];
    },
  });
  const acquisitionRows = acquisitionData ?? [];

  // Company-wide KPI roll-up — summed from the same per-platform rows the
  // Phase 5 report returns, not a separate backend aggregate. Each ratio is
  // null (never 0) when its denominator or total spend is 0.
  const kpis = useMemo(() => {
    const totalSpendInRange = acquisitionRows.reduce((a, r) => a + Number(r.total_ad_spend), 0);
    const totalLeads = acquisitionRows.reduce((a, r) => a + r.total_leads, 0);
    const totalConverted = acquisitionRows.reduce((a, r) => a + r.converted_leads, 0);
    const totalRevenue = acquisitionRows.reduce((a, r) => a + Number(r.revenue_generated), 0);
    return {
      totalSpend: totalSpendInRange,
      totalLeads,
      costPerLead: totalSpendInRange > 0 && totalLeads > 0 ? totalSpendInRange / totalLeads : null,
      totalConverted,
      costPerConversion: totalSpendInRange > 0 && totalConverted > 0 ? totalSpendInRange / totalConverted : null,
      totalRevenue,
      roas: totalSpendInRange > 0 ? totalRevenue / totalSpendInRange : null,
    };
  }, [acquisitionRows]);

  // Spend by campaign — pure spend aggregation from the ledger rows already
  // fetched on this page. No lead counts: campaigns aren't attributable to
  // individual leads (only platforms are), so this never claims a
  // cost-per-lead-by-campaign.
  const spendByCampaign = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of rows) {
      const key = r.campaign || "No campaign";
      map.set(key, (map.get(key) ?? 0) + Number(r.amount));
    }
    return [...map.entries()].sort((a, b) => b[1] - a[1]);
  }, [rows]);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/crm/ad-spend/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["crm-ad-spend"] }),
  });

  const columns: Column<SpendRow>[] = [
    { key: "period_start", header: "Period", render: (r) => `${r.period_start} → ${r.period_end}`, sortable: true },
    { key: "source_name", header: "Platform", render: (r) => r.source_name ?? "—", sortable: true },
    { key: "campaign", header: "Campaign", render: (r) => r.campaign ?? "—" },
    { key: "ad_set", header: "Ad Set", render: (r) => r.ad_set ?? "—" },
    { key: "amount", header: "Amount", render: (r) => fmt(r.amount), sortable: true },
    {
      key: "impressions", header: "Impr. / Clicks",
      render: (r) => (r.impressions == null && r.clicks == null ? "—" : `${r.impressions ?? "—"} / ${r.clicks ?? "—"}`),
    },
    { key: "created_by_name", header: "Logged By", render: (r) => r.created_by_name ?? "—" },
    {
      key: "id", header: "", className: "w-16",
      render: (r) => (
        <div className="flex items-center gap-1">
          <button
            onClick={() => { setEditing(r); setShowForm(true); }}
            className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setConfirmDeleteId(r.id)}
            className="p-1.5 rounded-lg hover:bg-violet-50 transition-colors text-muted-foreground hover:text-violet-500"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">CRM / MARKETING</p>
          <h1 className="text-2xl font-bold tracking-tight">Ad Spend</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Log spend by platform and campaign to compute cost per lead and ROAS.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowImport(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border border-input hover:bg-muted transition-colors"
          >
            <Upload className="h-4 w-4" /> Import CSV
          </button>
          <button
            onClick={() => { setEditing(undefined); setShowForm(true); }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
            style={{ background: INDIGO }}
          >
            <Plus className="h-4 w-4" /> Log Spend
          </button>
        </div>
      </div>

      {/* Dashboard: date range + KPI roll-up */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => applyPreset(p.value)}
              className="px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 text-muted-foreground hover:text-foreground"
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 bg-card border border-border rounded-xl pl-3 pr-1 py-1">
          <Calendar className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
          <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="text-sm bg-transparent border-none outline-none w-[124px]" />
          <span className="text-muted-foreground/50 text-xs">to</span>
          <input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="text-sm bg-transparent border-none outline-none w-[124px]" />
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "TOTAL SPEND", value: fmt(kpis.totalSpend) },
          { label: "LEADS GENERATED", value: String(kpis.totalLeads) },
          { label: "COST / LEAD", value: fmtOrDash(kpis.costPerLead) },
          { label: "CONVERSIONS", value: String(kpis.totalConverted) },
          { label: "COST / CONVERSION", value: fmtOrDash(kpis.costPerConversion) },
          { label: "REVENUE", value: fmt(kpis.totalRevenue) },
          { label: "ROAS", value: kpis.roas === null ? "—" : `${kpis.roas.toFixed(2)}×` },
        ].map((k) => (
          <div key={k.label} className="bg-card border border-border rounded-2xl p-5">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">{k.label}</p>
            <p className="text-xl font-bold tracking-tight tabular-nums mt-1">{k.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
          <div className="px-5 py-3 border-b border-border">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Spend by Platform</p>
          </div>
          <div className="divide-y divide-border">
            {acquisitionRows.filter((r) => Number(r.total_ad_spend) > 0).length === 0 ? (
              <p className="px-5 py-6 text-sm text-muted-foreground text-center">No spend logged in this range.</p>
            ) : (
              acquisitionRows
                .filter((r) => Number(r.total_ad_spend) > 0)
                .map((r) => (
                  <div key={r.source_name} className="flex items-center justify-between px-5 py-2.5">
                    <span className="text-sm">{r.source_name}</span>
                    <span className="text-sm font-semibold tabular-nums">{fmt(r.total_ad_spend)}</span>
                  </div>
                ))
            )}
          </div>
        </div>

        <div className="bg-card border border-border rounded-2xl overflow-hidden">
          <div className="px-5 py-3 border-b border-border">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Spend by Campaign</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">Spend only — leads aren&rsquo;t attributable to individual campaigns</p>
          </div>
          <div className="divide-y divide-border">
            {spendByCampaign.length === 0 ? (
              <p className="px-5 py-6 text-sm text-muted-foreground text-center">No spend logged yet.</p>
            ) : (
              spendByCampaign.map(([name, amt]) => (
                <div key={name} className="flex items-center justify-between px-5 py-2.5">
                  <span className="text-sm">{name}</span>
                  <span className="text-sm font-semibold tabular-nums">{fmt(amt)}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <p className="text-sm font-medium">{rows.length} entr{rows.length !== 1 ? "ies" : "y"} · {fmt(totalSpend)} total logged</p>
        </div>
        <DataTable columns={columns} data={rows} loading={isLoading} emptyMessage="No ad spend logged yet — click Log Spend to add one." />
      </div>

      {showForm && (
        <AdSpendFormModal initial={editing} onClose={() => { setShowForm(false); setEditing(undefined); }} />
      )}

      {showImport && <AdSpendImportModal onClose={() => setShowImport(false)} />}

      {confirmDeleteId && (
        <ModalShell maxWidth="max-w-xs" onClose={() => setConfirmDeleteId(null)}>
          <div className="p-6">
            <p className="text-sm font-medium mb-1">Delete this spend entry?</p>
            <p className="text-xs text-muted-foreground mb-5">This can&rsquo;t be undone.</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDeleteId(null)}
                className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => { deleteMutation.mutate(confirmDeleteId); setConfirmDeleteId(null); }}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 text-sm rounded-xl text-white font-semibold bg-violet-500 hover:bg-violet-600 transition-colors disabled:opacity-50"
              >
                Delete
              </button>
            </div>
          </div>
        </ModalShell>
      )}
    </div>
  );
}
