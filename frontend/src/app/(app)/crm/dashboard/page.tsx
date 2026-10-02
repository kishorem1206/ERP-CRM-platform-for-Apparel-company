"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { TrendingUp, CheckCircle2, BarChart2, Clock } from "lucide-react";
import api from "@/lib/api";
import { getCurrentUserId } from "@/lib/auth";

// ── Palette ───────────────────────────────────────────────────────────────────
const INDIGO = "#0049A7";
const GREEN = "#0F78FF";
const RED = "#1D0DB0";
const ORANGE = "#A096F7";
const BLUE = "#0049A7";

const STATUS_HEX: Record<string, string> = {
  open: BLUE,
  won: GREEN,
  lost: RED,
};

// ── Types ─────────────────────────────────────────────────────────────────────
interface PipelineStageSummary {
  stage_id: string;
  stage_name: string;
  sort_order: number;
  is_won: boolean;
  is_lost: boolean;
  lead_count: number;
  total_value: number;
}

interface RecentLead {
  id: string;
  title: string;
  status: string;
  stage_name: string | null;
  lead_value: number;
  created_at: string | null;
}

interface FollowUpDue {
  lead_id: string;
  lead_title: string;
  next_follow_up_at: string | null;
  follow_up_type: string | null;
  assigned_to_name: string | null;
}

interface TaskDue {
  id: string;
  title: string;
  due_at: string | null;
  priority: string;
  lead_id: string | null;
}

interface DashboardData {
  pipeline_summary: PipelineStageSummary[];
  status_counts: { open: number; won: number; lost: number };
  activities_due: number;
  activities_overdue: number;
  follow_ups_today: FollowUpDue[];
  follow_ups_overdue: FollowUpDue[];
  my_tasks_today: TaskDue[];
  my_tasks_overdue: TaskDue[];
  my_tasks_completed_today: number;
  recent_leads: RecentLead[];
  conversion_rate: number;
  total_pipeline_value: number;
  won_value_30d: number;
}

interface LeadNeedingAction {
  id: string;
  title: string;
  next_follow_up_at: string | null;
  follow_up_type: string | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtRupee(n: number): string {
  if (n >= 10_000_000) return `₹${(n / 10_000_000).toFixed(1)}Cr`;
  if (n >= 100_000) return `₹${(n / 100_000).toFixed(1)}L`;
  if (n >= 1_000) return `₹${(n / 1_000).toFixed(1)}K`;
  return `₹${n.toLocaleString("en-IN")}`;
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

// ── SVG Donut Chart ───────────────────────────────────────────────────────────
function DonutChart({ open, won, lost }: { open: number; won: number; lost: number }) {
  const total = open + won + lost;
  const r = 36;
  const cx = 44;
  const cy = 44;
  const circumference = 2 * Math.PI * r; // ≈ 226.19
  const quarterC = circumference / 4;

  const segs = [
    { value: open, color: INDIGO },
    { value: won, color: GREEN },
    { value: lost, color: RED },
  ];

  let cumArc = 0;
  const rendered = segs.map(({ value, color }) => {
    const arc = total > 0 ? (value / total) * circumference : 0;
    const dashoffset = quarterC - cumArc;
    cumArc += arc;
    return { arc, color, dashoffset };
  });

  return (
    <svg width="88" height="88" viewBox="0 0 88 88" aria-label="Lead status donut chart">
      {total === 0 ? (
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#e5e7eb" strokeWidth="10" />
      ) : (
        rendered.map(({ arc, color, dashoffset }, i) =>
          arc > 0 ? (
            <circle
              key={i}
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={color}
              strokeWidth="10"
              strokeDasharray={`${arc} ${circumference - arc}`}
              strokeDashoffset={dashoffset}
            />
          ) : null
        )
      )}
      <text
        x={cx}
        y={cy}
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize="14"
        fontWeight="bold"
        fill="currentColor"
      >
        {total}
      </text>
    </svg>
  );
}

// ── KPI Tile ──────────────────────────────────────────────────────────────────
function FollowUpList({ title, accent, items }: { title: string; accent: string; items: FollowUpDue[] }) {
  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden">
      <div className="px-5 py-3 border-b border-border">
        <p className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: accent }}>{title}</p>
      </div>
      <div className="divide-y divide-border">
        {items.map((f) => (
          <Link
            key={f.lead_id}
            href={`/crm/leads/${f.lead_id}`}
            className="flex items-center justify-between gap-3 px-5 py-2.5 hover:bg-muted/40 transition-colors"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{f.lead_title}</p>
              <p className="text-[11px] text-muted-foreground">
                {f.follow_up_type ?? "Follow-up"}
                {f.assigned_to_name ? ` · ${f.assigned_to_name}` : ""}
              </p>
            </div>
            {f.next_follow_up_at && (
              <span className="text-xs text-muted-foreground flex-shrink-0">
                {new Date(f.next_follow_up_at).toLocaleDateString("en-IN")}
              </span>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}

const PRIORITY_HEX: Record<string, string> = { low: "#64748B", medium: "#A096F7", high: "#1D0DB0" };

function TaskList({ title, accent, items }: { title: string; accent: string; items: TaskDue[] }) {
  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-border">
        <p className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: accent }}>{title}</p>
        <Link href="/crm/tasks" className="text-[11px] text-muted-foreground hover:underline">View all</Link>
      </div>
      <div className="divide-y divide-border">
        {items.map((t) => {
          const row = (
            <div className="flex items-center justify-between gap-3 px-5 py-2.5 hover:bg-muted/40 transition-colors">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{t.title}</p>
                <span
                  className="inline-flex items-center px-1.5 py-0 rounded text-[10px] font-bold capitalize"
                  style={{ color: PRIORITY_HEX[t.priority] ?? accent }}
                >
                  {t.priority} priority
                </span>
              </div>
              {t.due_at && (
                <span className="text-xs text-muted-foreground flex-shrink-0">
                  {new Date(t.due_at).toLocaleDateString("en-IN")}
                </span>
              )}
            </div>
          );
          return t.lead_id ? (
            <Link key={t.id} href={`/crm/leads/${t.lead_id}`}>{row}</Link>
          ) : (
            <div key={t.id}>{row}</div>
          );
        })}
      </div>
    </div>
  );
}

function LeadActionList({ items }: { items: LeadNeedingAction[] }) {
  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden">
      <div className="px-5 py-3 border-b border-border">
        <p className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: INDIGO }}>Leads Requiring Action</p>
      </div>
      <div className="divide-y divide-border">
        {items.map((l) => (
          <Link
            key={l.id}
            href={`/crm/leads/${l.id}`}
            className="flex items-center justify-between gap-3 px-5 py-2.5 hover:bg-muted/40 transition-colors"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{l.title}</p>
              <p className="text-[11px] text-muted-foreground">{l.follow_up_type ?? "Follow-up due"}</p>
            </div>
            {l.next_follow_up_at && (
              <span className="text-xs text-muted-foreground flex-shrink-0">
                {new Date(l.next_follow_up_at).toLocaleDateString("en-IN")}
              </span>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}

function KpiTile({
  label,
  value,
  sub,
  icon: Icon,
  color,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="bg-card border border-border rounded-2xl p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
          {label}
        </p>
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: `${color}14`, border: `1.5px solid ${color}28` }}
        >
          <Icon className="h-4 w-4" style={{ color }} />
        </div>
      </div>
      <div>
        <p className="text-2xl font-bold tracking-tight">{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

// ── Skeleton shimmer ──────────────────────────────────────────────────────────
function SkeletonBlock({ className }: { className?: string }) {
  return <div className={`animate-pulse bg-muted rounded ${className ?? ""}`} />;
}

function KpiSkeleton() {
  return (
    <div className="bg-card border border-border rounded-2xl p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <SkeletonBlock className="h-3 w-28" />
        <SkeletonBlock className="w-8 h-8 rounded-lg" />
      </div>
      <SkeletonBlock className="h-8 w-32 mt-1" />
      <SkeletonBlock className="h-3 w-20" />
    </div>
  );
}

// ── Pipeline Funnel ───────────────────────────────────────────────────────────
function PipelineFunnel({ stages }: { stages: PipelineStageSummary[] }) {
  const maxCount = Math.max(...stages.map((s) => s.lead_count), 1);

  function barColor(s: PipelineStageSummary): string {
    if (s.is_won) return GREEN;
    if (s.is_lost) return RED;
    return INDIGO;
  }

  if (stages.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">
        No pipeline stages configured.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {stages.map((s) => {
        const widthPct = (s.lead_count / maxCount) * 100;
        const color = barColor(s);
        return (
          <div key={s.stage_id}>
            <div className="flex items-center justify-between mb-0.5 text-xs">
              <span className="font-medium text-foreground truncate max-w-[160px]">
                {s.stage_name}
              </span>
              <span className="text-muted-foreground ml-2 flex-shrink-0">
                {s.lead_count} &middot; {fmtRupee(s.total_value)}
              </span>
            </div>
            <div className="h-5 w-full bg-muted/40 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${widthPct}%`,
                  minWidth: s.lead_count > 0 ? "6px" : "0",
                  background:
                    s.is_won || s.is_lost
                      ? color
                      : `linear-gradient(90deg, ${INDIGO} 0%, #A096F7 100%)`,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Status Badge ──────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const color = STATUS_HEX[status?.toLowerCase()] ?? "#94A3B8";
  const label = status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded whitespace-nowrap"
      style={{ background: `${color}18`, color, fontSize: 11, fontWeight: 700 }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {label}
    </span>
  );
}

// ── Stage Badge ───────────────────────────────────────────────────────────────
function StageBadge({ name }: { name: string }) {
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded whitespace-nowrap"
      style={{ background: `${INDIGO}14`, color: INDIGO, fontSize: 11, fontWeight: 700 }}
    >
      {name}
    </span>
  );
}

// ── Empty State ───────────────────────────────────────────────────────────────
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
      <svg width="72" height="72" viewBox="0 0 72 72" fill="none" aria-hidden="true">
        <circle cx="36" cy="36" r="34" stroke={INDIGO} strokeWidth="2.5" strokeOpacity="0.3" />
        <circle cx="36" cy="36" r="22" stroke={INDIGO} strokeWidth="2.5" strokeOpacity="0.5" />
        <circle cx="36" cy="36" r="10" stroke={INDIGO} strokeWidth="2.5" strokeOpacity="0.8" />
        <circle cx="36" cy="36" r="3" fill={INDIGO} />
        <line x1="36" y1="2" x2="36" y2="12" stroke={INDIGO} strokeWidth="2" strokeOpacity="0.4" strokeLinecap="round" />
        <line x1="70" y1="36" x2="60" y2="36" stroke={INDIGO} strokeWidth="2" strokeOpacity="0.4" strokeLinecap="round" />
        <line x1="36" y1="70" x2="36" y2="60" stroke={INDIGO} strokeWidth="2" strokeOpacity="0.4" strokeLinecap="round" />
        <line x1="2" y1="36" x2="12" y2="36" stroke={INDIGO} strokeWidth="2" strokeOpacity="0.4" strokeLinecap="round" />
      </svg>
      <div>
        <p className="font-semibold text-foreground">No leads yet</p>
        <p className="text-sm text-muted-foreground mt-1">
          Create your first lead to see pipeline analytics.
        </p>
      </div>
      <Link
        href="/crm/leads"
        className="px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90"
        style={{ background: INDIGO }}
      >
        Go to Leads
      </Link>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function CRMDashboardPage() {
  const currentUserId = getCurrentUserId();

  const { data, isLoading } = useQuery<DashboardData>({
    queryKey: ["crm-dashboard"],
    queryFn: () => api.get("/crm/dashboard").then((r) => r.data.data),
    refetchInterval: 60_000,
  });

  const { data: leadsNeedingActionData } = useQuery({
    queryKey: ["crm-leads-needing-action", currentUserId],
    queryFn: () =>
      api
        .get(`/crm/leads?assigned_to=${currentUserId}&follow_up_due=true&page_size=10`)
        .then((r) => r.data.data as LeadNeedingAction[]),
    enabled: !!currentUserId,
  });
  const leadsNeedingAction = leadsNeedingActionData ?? [];

  const totalLeads =
    (data?.status_counts.open ?? 0) +
    (data?.status_counts.won ?? 0) +
    (data?.status_counts.lost ?? 0);

  const hasLeads = totalLeads > 0;

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          CRM / DASHBOARD
        </p>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Pipeline analytics, conversion rates, and activity summary.
        </p>
      </div>

      {/* Activity alerts */}
      {!isLoading && (
        <div className="space-y-2">
          {(data?.activities_overdue ?? 0) > 0 && (
            <div
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium border"
              style={{
                background: `${RED}0F`,
                borderColor: `${RED}30`,
                color: RED,
              }}
            >
              <Clock className="h-4 w-4 flex-shrink-0" />
              You have {data!.activities_overdue} overdue{" "}
              {data!.activities_overdue === 1 ? "activity" : "activities"}.{" "}
              <Link href="/crm/activities" className="underline underline-offset-2 font-semibold">
                View activities
              </Link>
            </div>
          )}
          {(data?.activities_due ?? 0) > 0 && (
            <div
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium border"
              style={{
                background: `${ORANGE}0F`,
                borderColor: `${ORANGE}30`,
                color: ORANGE,
              }}
            >
              <Clock className="h-4 w-4 flex-shrink-0" />
              You have {data!.activities_due}{" "}
              {data!.activities_due === 1 ? "activity" : "activities"} due in the next 24 hours.{" "}
              <Link href="/crm/activities" className="underline underline-offset-2 font-semibold">
                View activities
              </Link>
            </div>
          )}
        </div>
      )}

      {!isLoading && (data?.my_tasks_completed_today ?? 0) > 0 && (
        <div
          className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium border"
          style={{ background: `${GREEN}0F`, borderColor: `${GREEN}30`, color: GREEN }}
        >
          <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
          You completed {data!.my_tasks_completed_today} task{data!.my_tasks_completed_today === 1 ? "" : "s"} today.
        </div>
      )}

      {/* My Tasks + leads requiring action — personal, shown before company-wide data */}
      {!isLoading && ((data?.my_tasks_overdue.length ?? 0) > 0 || (data?.my_tasks_today.length ?? 0) > 0 || leadsNeedingAction.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {(data?.my_tasks_overdue.length ?? 0) > 0 && (
            <TaskList title="My Overdue Tasks" accent={RED} items={data!.my_tasks_overdue} />
          )}
          {(data?.my_tasks_today.length ?? 0) > 0 && (
            <TaskList title="My Tasks Today" accent={ORANGE} items={data!.my_tasks_today} />
          )}
          {leadsNeedingAction.length > 0 && <LeadActionList items={leadsNeedingAction} />}
        </div>
      )}

      {/* Follow-ups needing action */}
      {!isLoading && ((data?.follow_ups_overdue.length ?? 0) > 0 || (data?.follow_ups_today.length ?? 0) > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {(data?.follow_ups_overdue.length ?? 0) > 0 && (
            <FollowUpList title="Overdue Follow-ups" accent={RED} items={data!.follow_ups_overdue} />
          )}
          {(data?.follow_ups_today.length ?? 0) > 0 && (
            <FollowUpList title="Follow-ups Due Today" accent={ORANGE} items={data!.follow_ups_today} />
          )}
        </div>
      )}

      {/* ── Row 1 — KPI tiles ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <KpiSkeleton key={i} />)
        ) : (
          <>
            <KpiTile
              label="Total Pipeline"
              value={fmtRupee(data?.total_pipeline_value ?? 0)}
              sub={`${data?.status_counts.open ?? 0} open leads`}
              icon={TrendingUp}
              color={INDIGO}
            />
            <KpiTile
              label="Won (30 days)"
              value={fmtRupee(data?.won_value_30d ?? 0)}
              sub={`${data?.status_counts.won ?? 0} total won`}
              icon={CheckCircle2}
              color={GREEN}
            />
            <KpiTile
              label="Conversion Rate"
              value={`${data?.conversion_rate ?? 0}%`}
              sub="Won / (won + lost)"
              icon={BarChart2}
              color={BLUE}
            />
            <KpiTile
              label="Activities"
              value={`${data?.activities_due ?? 0} due, ${data?.activities_overdue ?? 0} overdue`}
              sub="Next 24 hours / past due"
              icon={Clock}
              color={ORANGE}
            />
          </>
        )}
      </div>

      {/* ── Empty state ───────────────────────────────────────────────────── */}
      {!isLoading && !hasLeads && <EmptyState />}

      {/* ── Row 2 — Pipeline funnel + Donut ───────────────────────────────── */}
      {(isLoading || hasLeads) && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Pipeline Funnel — 2/3 */}
          <div className="lg:col-span-2 bg-card border border-border rounded-2xl p-6">
            <div className="mb-4">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                Pipeline Funnel
              </p>
              <p className="text-sm font-medium mt-0.5">Open leads by stage</p>
            </div>
            {isLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="space-y-1">
                    <SkeletonBlock className="h-3 w-40" />
                    <SkeletonBlock className="h-5 w-full rounded-full" />
                  </div>
                ))}
              </div>
            ) : (
              <PipelineFunnel stages={data?.pipeline_summary ?? []} />
            )}
          </div>

          {/* Status Donut — 1/3 */}
          <div className="bg-card border border-border rounded-2xl p-6 flex flex-col">
            <div className="mb-4">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                Lead Status
              </p>
              <p className="text-sm font-medium mt-0.5">All leads by status</p>
            </div>
            {isLoading ? (
              <div className="flex-1 flex flex-col items-center gap-4 pt-4">
                <SkeletonBlock className="w-24 h-24 rounded-full" />
                <div className="space-y-2 w-full">
                  <SkeletonBlock className="h-4 w-full" />
                  <SkeletonBlock className="h-4 w-full" />
                  <SkeletonBlock className="h-4 w-3/4" />
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center gap-4">
                <DonutChart
                  open={data?.status_counts.open ?? 0}
                  won={data?.status_counts.won ?? 0}
                  lost={data?.status_counts.lost ?? 0}
                />
                {/* Legend */}
                <div className="w-full space-y-2 mt-2">
                  {[
                    { label: "Open", value: data?.status_counts.open ?? 0, color: INDIGO },
                    { label: "Won", value: data?.status_counts.won ?? 0, color: GREEN },
                    { label: "Lost", value: data?.status_counts.lost ?? 0, color: RED },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                          style={{ background: color }}
                        />
                        <span className="text-muted-foreground">{label}</span>
                      </div>
                      <span className="font-semibold">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Row 3 — Recent Leads table ────────────────────────────────────── */}
      {(isLoading || hasLeads) && (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
          <div className="px-6 py-4 border-b border-border">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              Recent Leads
            </p>
            <p className="text-sm font-medium mt-0.5">Last 5 created</p>
          </div>

          {isLoading ? (
            <div className="p-6 space-y-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <SkeletonBlock className="flex-1 h-4" />
                  <SkeletonBlock className="h-5 w-16 rounded-full" />
                  <SkeletonBlock className="h-4 w-20" />
                  <SkeletonBlock className="h-4 w-24" />
                </div>
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/30">
                    <th className="px-6 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Title
                    </th>
                    <th className="px-6 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Stage
                    </th>
                    <th className="px-6 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Status
                    </th>
                    <th className="px-6 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Value
                    </th>
                    <th className="px-6 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Created
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {(data?.recent_leads ?? []).length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-muted-foreground">
                        No leads yet.
                      </td>
                    </tr>
                  ) : (
                    (data?.recent_leads ?? []).map((lead) => (
                      <tr
                        key={lead.id}
                        className="hover:bg-muted/30 transition-colors duration-100"
                      >
                        <td className="px-6 py-3 font-medium max-w-[260px] truncate">
                          <Link
                            href={`/crm/leads/${lead.id}`}
                            className="hover:underline transition-colors"
                            style={{ color: INDIGO }}
                          >
                            {lead.title}
                          </Link>
                        </td>
                        <td className="px-6 py-3">
                          {lead.stage_name ? (
                            <StageBadge name={lead.stage_name} />
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="px-6 py-3">
                          <StatusBadge status={lead.status} />
                        </td>
                        <td className="px-6 py-3 text-right font-medium">
                          {lead.lead_value > 0 ? fmtRupee(lead.lead_value) : "—"}
                        </td>
                        <td className="px-6 py-3 text-right text-muted-foreground">
                          {fmtDate(lead.created_at)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
