"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, CalendarDays, ChevronDown } from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { DatePicker, PERIOD_PRESETS, presetRange } from "@/components/shared/date-picker";

const INDIGO = "#0049A7";
const GOOD = "#059669";
const BAD = "#DC2626";

interface Totals {
  new_leads: number;
  qualified_leads: number;
  lead_to_qualified_rate: number | null;
  won_deals: number;
  lead_to_won_conversion: number | null;
  avg_time_to_close_days: number | null;
  time_to_close_sample: number;
}

interface Comparisons {
  new_leads_change_pct: number | null;
  qualified_leads_change_pct: number | null;
  qualification_rate_change_pts: number | null;
  won_deals_change_pct: number | null;
  won_conversion_change_pts: number | null;
  avg_time_to_close_change_days: number | null;
}

interface SalesKpis {
  period: { from: string; to: string };
  previous_period: { from: string; to: string };
  current: Totals;
  previous: Totals;
  comparisons: Comparisons;
  leads_in_pipelines_without_qualification_stage: number;
}

type Tone = "good" | "bad" | "neutral";
interface Delta {
  text: string;
  tone: Tone;
}

function arrow(change: number) {
  return change > 0 ? "↑" : change < 0 ? "↓" : "→";
}

function toneFor(change: number, higherIsBetter: boolean): Tone {
  if (change === 0) return "neutral";
  return change > 0 === higherIsBetter ? "good" : "bad";
}

function countDelta(change: number | null, current: number): Delta {
  if (change === null) {
    return current > 0 ? { text: "New", tone: "neutral" } : { text: "—", tone: "neutral" };
  }
  return { text: `${arrow(change)} ${Math.abs(change).toFixed(1)}% vs prev`, tone: toneFor(change, true) };
}

function pointsDelta(change: number | null): Delta {
  if (change === null) return { text: "—", tone: "neutral" };
  return { text: `${arrow(change)} ${Math.abs(change).toFixed(1)} pts vs prev`, tone: toneFor(change, true) };
}

function daysDelta(change: number | null): Delta {
  if (change === null) return { text: "—", tone: "neutral" };
  return { text: `${arrow(change)} ${Math.abs(change).toFixed(1)} days vs prev`, tone: toneFor(change, false) };
}

const fmtInt = (n: number) => n.toLocaleString("en-IN");
const fmtPct = (n: number | null) => (n === null ? "—" : `${n.toFixed(1)}%`);
const fmtDays = (n: number | null) => (n === null ? "—" : `${n.toFixed(1).replace(/\.0$/, "")} days`);

function fmtDate(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function PeriodPicker({ from, to, onChange }: { from: string; to: string; onChange: (from: string, to: string) => void }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);
  const active = PERIOD_PRESETS.find((p) => {
    const r = presetRange(p.value);
    return r.from === from && r.to === to;
  });
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-sm font-semibold shadow-sm hover:border-primary/40"
        aria-expanded={open}
      >
        <CalendarDays className="h-4 w-4 text-muted-foreground" />
        <span style={{ color: INDIGO }}>{active?.label ?? "Custom range"}</span>
        <span className="font-normal text-muted-foreground tabular-nums">
          {fmtDate(from)} – {fmtDate(to)}
        </span>
        <ChevronDown className="h-4 w-4 text-muted-foreground" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-50 mt-2 w-[340px] max-w-[calc(100vw-2rem)] rounded-2xl border border-border bg-card p-3 shadow-xl">
            <div className="grid grid-cols-2 gap-1">
              {PERIOD_PRESETS.map((p) => {
                const isActive = active?.label === p.label;
                return (
                  <button
                    key={p.label}
                    type="button"
                    onClick={() => {
                      const r = presetRange(p.value);
                      onChange(r.from, r.to);
                      setOpen(false);
                    }}
                    className="rounded-lg px-3 py-2 text-left text-sm font-medium hover:bg-muted"
                    style={isActive ? { color: INDIGO, background: `${INDIGO}10` } : undefined}
                  >
                    {p.label}
                  </button>
                );
              })}
            </div>
            <div className="mt-3 space-y-2 border-t border-border pt-3">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Custom range</p>
              <div className="flex items-center gap-2">
                <DatePicker variant="field" value={from} max={to} onChange={(v) => onChange(v, to)} />
                <span className="text-xs text-muted-foreground">to</span>
                <DatePicker variant="field" value={to} min={from} onChange={(v) => onChange(from, v)} />
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

const TONE_COLOR: Record<Tone, string> = { good: GOOD, bad: BAD, neutral: "hsl(var(--muted-foreground))" };

function KpiCard({
  label,
  value,
  delta,
  note,
  href,
}: {
  label: string;
  value: string;
  delta: Delta | null;
  note?: string;
  href?: string;
}) {
  const body = (
    <>
      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-2 text-3xl font-bold tabular-nums tracking-tight" style={{ color: INDIGO }}>
        {value}
      </p>
      {delta && (
        <p className="mt-2 text-xs font-semibold tabular-nums" style={{ color: TONE_COLOR[delta.tone] }}>
          {delta.text}
        </p>
      )}
      {note && <p className="mt-1 text-[11px] text-muted-foreground">{note}</p>}
      {href && (
        <p className="mt-3 inline-flex items-center gap-1 text-xs font-semibold" style={{ color: INDIGO }}>
          View leads <ArrowRight className="h-3 w-3" />
        </p>
      )}
    </>
  );
  const cls = "block bg-card border border-border rounded-2xl p-5 shadow-sm";
  if (!href) return <div className={`${cls} min-w-0`}>{body}</div>;
  return (
    <Link href={href} className={`${cls} min-w-0 transition-all duration-150 hover:shadow-md hover:border-primary/30`}>
      {body}
    </Link>
  );
}

const TIER_META: Record<string, { label: string; color: string; hint: string }> = {
  high: { label: "High quality", color: "#DC2626", hint: "Score 80+" },
  medium: { label: "Medium quality", color: "#D97706", hint: "Score 50–79" },
  low: { label: "Low quality", color: "#64748B", hint: "Score below 50" },
  unscored: { label: "Not scored", color: "#94A3B8", hint: "Created before scoring" },
};

interface QualityTier {
  tier: string;
  leads: number;
  share_pct: number | null;
  average_score: number | null;
  won: number;
  open: number;
}

function LeadQualityRow({
  from, to, utcOffsetMinutes, pipelineId, assignedTo, sourceId,
}: {
  from: string; to: string; utcOffsetMinutes: number; pipelineId: string; assignedTo: string; sourceId: string;
}) {
  const params = new URLSearchParams({ date_from: from, date_to: to, utc_offset_minutes: String(utcOffsetMinutes) });
  if (pipelineId) params.set("pipeline_id", pipelineId);
  if (assignedTo) params.set("assigned_to", assignedTo);
  if (sourceId) params.set("source_id", sourceId);
  const { data } = useQuery({
    queryKey: ["crm-lead-quality", from, to, utcOffsetMinutes, pipelineId, assignedTo, sourceId],
    queryFn: async () => (await api.get(`/crm/reports/lead-quality?${params}`)).data.data as { tiers: QualityTier[]; total_leads: number },
    enabled: !!from && !!to,
  });
  const link = (tier: string) => {
    const q = new URLSearchParams({ kpi: "new", priority: tier, created_from: from, created_to: to, utc_offset_minutes: String(utcOffsetMinutes) });
    if (pipelineId) q.set("pipeline_id", pipelineId);
    if (assignedTo) q.set("assigned_to", assignedTo);
    if (sourceId) q.set("source_id", sourceId);
    return `/crm/leads?${q}`;
  };
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Lead quality (same leads as above)</p>
        <p className="text-xs text-muted-foreground tabular-nums">{data ? `${data.total_leads} leads` : ""}</p>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {(data?.tiers ?? ["high", "medium", "low", "unscored"].map((t) => ({ tier: t }) as QualityTier)).map((t) => {
          const meta = TIER_META[t.tier];
          return (
            <Link
              key={t.tier}
              href={link(t.tier)}
              className="block min-w-0 rounded-2xl border border-border bg-card p-4 shadow-sm transition-all duration-150 hover:border-primary/30 hover:shadow-md"
            >
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full" style={{ background: meta.color }} />
                <p className="text-xs font-semibold">{meta.label}</p>
              </div>
              <p className="mt-2 text-2xl font-bold tabular-nums" style={{ color: meta.color }}>
                {data ? fmtInt(t.leads) : "—"}
              </p>
              <p className="mt-1 text-[11px] text-muted-foreground tabular-nums">
                {t.share_pct !== undefined && t.share_pct !== null ? `${t.share_pct.toFixed(1)}% of leads` : "—"}
                {t.average_score !== null && t.average_score !== undefined ? ` · avg score ${t.average_score.toFixed(1)}` : ""}
              </p>
              <p className="mt-1 text-[11px] text-muted-foreground tabular-nums">
                {t.won !== undefined ? `${fmtInt(t.won)} won · ${fmtInt(t.open ?? 0)} open` : ""}
              </p>
              <p className="mt-1 text-[10px] text-muted-foreground/80">{meta.hint}</p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

export function SalesKpiSection() {
  const [range, setRange] = useState(() => presetRange("thisMonth"));
  const [pipelineId, setPipelineId] = useState("");
  const [assignedTo, setAssignedTo] = useState("");
  const [sourceId, setSourceId] = useState("");
  const utcOffsetMinutes = -new Date().getTimezoneOffset();

  const { data: pipelinesData } = useQuery({
    queryKey: ["kpi-pipelines"],
    queryFn: async () => (await api.get("/crm/pipelines")).data.data as { id: string; name: string }[],
  });
  const { data: usersData } = useQuery({
    queryKey: ["kpi-users"],
    queryFn: async () => (await api.get("/crm/assignable-users")).data.data as { id: string; name: string; email?: string }[],
  });
  const { data: sourcesData } = useQuery({
    queryKey: ["kpi-sources"],
    queryFn: async () => (await api.get("/crm/lead-sources")).data.data as { id: string; name: string }[],
  });

  const params = new URLSearchParams({
    date_from: range.from,
    date_to: range.to,
    utc_offset_minutes: String(utcOffsetMinutes),
  });
  if (pipelineId) params.set("pipeline_id", pipelineId);
  if (assignedTo) params.set("assigned_to", assignedTo);
  if (sourceId) params.set("source_id", sourceId);

  const { data: kpis, isLoading, isError, refetch } = useQuery({
    queryKey: ["crm-sales-kpis", range.from, range.to, utcOffsetMinutes, pipelineId, assignedTo, sourceId],
    queryFn: async () => (await api.get(`/crm/reports/sales-kpis?${params}`)).data.data as SalesKpis,
    enabled: !!range.from && !!range.to,
  });

  const drillHref = (kpi: string) => {
    const q = new URLSearchParams({
      kpi,
      created_from: range.from,
      created_to: range.to,
      utc_offset_minutes: String(utcOffsetMinutes),
    });
    if (pipelineId) q.set("pipeline_id", pipelineId);
    if (assignedTo) q.set("assigned_to", assignedTo);
    if (sourceId) q.set("source_id", sourceId);
    return `/crm/leads?${q}`;
  };

  const cur = kpis?.current;
  const cmp = kpis?.comparisons;
  const dash = "—";

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold tracking-tight">Sales KPIs</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Leads created in the selected period, followed to their outcome. Outcomes can happen after the period ends.
          </p>
        </div>
        <PeriodPicker from={range.from} to={range.to} onChange={(from, to) => setRange({ from, to })} />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <SearchableSelect
          options={[{ value: "", label: "All pipelines" }, ...(pipelinesData ?? []).map((p) => ({ value: p.id, label: p.name }))]}
          value={pipelineId}
          onChange={setPipelineId}
          placeholder="All pipelines"
          accent={INDIGO}
        />
        <SearchableSelect
          options={[
            { value: "", label: "All employees" },
            ...(usersData ?? []).map((u) => ({ value: u.id, label: u.name, meta: u.email })),
          ]}
          value={assignedTo}
          onChange={setAssignedTo}
          placeholder="All employees"
          accent={INDIGO}
        />
        <SearchableSelect
          options={[{ value: "", label: "All sources" }, ...(sourcesData ?? []).map((s) => ({ value: s.id, label: s.name }))]}
          value={sourceId}
          onChange={setSourceId}
          placeholder="All sources"
          accent={INDIGO}
        />
      </div>

      {kpis && (
        <p className="text-xs text-muted-foreground">
          Period {fmtDate(kpis.period.from)} – {fmtDate(kpis.period.to)} · compared with {fmtDate(kpis.previous_period.from)} – {fmtDate(kpis.previous_period.to)}
        </p>
      )}

      {kpis && kpis.leads_in_pipelines_without_qualification_stage > 0 && (
        <div className="flex items-start gap-2 rounded-xl border border-amber-300/60 bg-amber-50 px-4 py-3 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <p>
            {fmtInt(kpis.leads_in_pipelines_without_qualification_stage)} leads in this period are not in a pipeline with a
            qualification stage set, so they cannot count as qualified. Set one in{" "}
            <Link href="/crm/settings" className="font-semibold underline">CRM Settings</Link>.
          </p>
        </div>
      )}

      {isError ? (
        <div className="flex items-center justify-between rounded-2xl border border-border bg-card p-5 text-sm">
          <p className="text-muted-foreground">Could not load sales KPIs.</p>
          <button onClick={() => refetch()} className="text-xs font-semibold" style={{ color: INDIGO }}>
            Retry
          </button>
        </div>
      ) : (
        <div className={`grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 ${isLoading ? "opacity-60" : ""}`}>
          <KpiCard
            label="New leads"
            value={cur ? fmtInt(cur.new_leads) : dash}
            delta={cur && cmp ? countDelta(cmp.new_leads_change_pct, cur.new_leads) : null}
            href={cur ? drillHref("new") : undefined}
          />
          <KpiCard
            label="Qualified leads"
            value={cur ? fmtInt(cur.qualified_leads) : dash}
            delta={cur && cmp ? countDelta(cmp.qualified_leads_change_pct, cur.qualified_leads) : null}
            href={cur ? drillHref("qualified") : undefined}
          />
          <KpiCard
            label="Lead → Qualified"
            value={fmtPct(cur?.lead_to_qualified_rate ?? null)}
            delta={cmp ? pointsDelta(cmp.qualification_rate_change_pts) : null}
          />
          <KpiCard
            label="Won deals"
            value={cur ? fmtInt(cur.won_deals) : dash}
            delta={cur && cmp ? countDelta(cmp.won_deals_change_pct, cur.won_deals) : null}
            href={cur ? drillHref("won") : undefined}
          />
          <KpiCard
            label="Lead → Won"
            value={fmtPct(cur?.lead_to_won_conversion ?? null)}
            delta={cmp ? pointsDelta(cmp.won_conversion_change_pts) : null}
          />
          <KpiCard
            label="Avg. time to close"
            value={fmtDays(cur?.avg_time_to_close_days ?? null)}
            delta={cmp ? daysDelta(cmp.avg_time_to_close_change_days) : null}
            note={
              cur
                ? cur.time_to_close_sample > 0
                  ? `From created to won, across ${fmtInt(cur.time_to_close_sample)} won ${cur.time_to_close_sample === 1 ? "deal" : "deals"}`
                  : "No won deals with a close date in this cohort"
                : undefined
            }
          />
        </div>
      )}

      <LeadQualityRow
        from={range.from}
        to={range.to}
        utcOffsetMinutes={utcOffsetMinutes}
        pipelineId={pipelineId}
        assignedTo={assignedTo}
        sourceId={sourceId}
      />
    </section>
  );
}
