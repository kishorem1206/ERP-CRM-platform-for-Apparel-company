"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, TrendingUp, TrendingDown, Trophy, Activity as ActivityIcon } from "lucide-react";
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  FunnelChart, Funnel, LabelList, PieChart, Pie, Cell,
  RadialBarChart, RadialBar, PolarAngleAxis,
  BarChart,
} from "recharts";
import api from "@/lib/api";
import { DateRangeFilter, RangePreset, presetRange } from "@/components/shared/date-picker";

// ── Palette — every colour is a shade of the sidebar's Blue/Purple ─────────────
const INDIGO = "#0049A7";
const VIOLET_LIGHT = "#A096F7";
const GREEN = "#0F78FF";
const RED = "#1D0DB0";
const AMBER = "#A096F7";
const BLUE = "#0049A7";
const VIOLET = "#8174F5";
const CYAN = "#8FC0FF";
const TEAL = "#0F233D";
const ORANGE = "#A096F7";
const SLATE = "#64748B";

const SOURCE_COLORS = ["#0F233D", "#0049A7", "#0F78FF", "#1D0DB0", "#8174F5", "#A096F7"];

const ACTIVITY_COLORS: Record<string, string> = {
  call: BLUE,
  meeting: GREEN,
  note: AMBER,
  task: INDIGO,
  email: VIOLET,
  lunch: ORANGE,
};

// ── Types ─────────────────────────────────────────────────────────────────────
interface PipelineRow {
  stage_name: string;
  sort_order: number;
  is_won: boolean;
  is_lost: boolean;
  lead_count: number;
  total_value: number;
}

interface SourceRow {
  source_name: string;
  count: number;
  total_value: number;
  won_count: number;
}

interface ActivityRow {
  type: string;
  count: number;
  done_count: number;
  completion_rate: number;
}

interface QuoteData {
  draft: number;
  sent: number;
  accepted: number;
  declined: number;
  expired: number;
  accepted_value: number;
  total_sent_value: number;
}

interface MonthlyTrendRow {
  month: string;
  count: number;
  value: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtRupee(n: number): string {
  if (n >= 10_000_000) return `₹${(n / 10_000_000).toFixed(1)}Cr`;
  if (n >= 100_000) return `₹${(n / 100_000).toFixed(1)}L`;
  if (n >= 1_000) return `₹${(n / 1_000).toFixed(1)}K`;
  return `₹${n.toLocaleString("en-IN")}`;
}

function abbrevMonth(m: string): string {
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const match = m.match(/^(\d{4})-(\d{2})$/);
  if (match) return months[parseInt(match[2], 10) - 1] ?? m;
  return m.slice(0, 3);
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function SkeletonBlock({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return <div className={`animate-pulse bg-muted rounded ${className ?? ""}`} style={style} />;
}

function ChartSkeleton({ height = 240 }: { height?: number }) {
  return <SkeletonBlock className="w-full rounded-xl" style={{ height }} />;
}

// ── Shared tooltip (matches Production Report's visual language) ──────────────
function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-xl shadow-lg px-3 py-2 text-xs">
      {label && <p className="font-semibold mb-1 text-foreground truncate max-w-[180px]">{label}</p>}
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: {typeof p.value === "number" && p.value > 999 ? fmtRupee(p.value) : p.value}
        </p>
      ))}
    </div>
  );
}

// ── KPI Stat Card ─────────────────────────────────────────────────────────────
function StatCard({
  label, value, sublabel, icon: Icon, color, trend,
}: {
  label: string; value: string; sublabel?: string;
  icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>; color: string; trend?: "up" | "down" | null;
}) {
  return (
    <div className="bg-card border border-border rounded-2xl p-6 relative overflow-hidden">
      <div className="absolute -right-4 -top-4 w-20 h-20 rounded-full opacity-[0.07]" style={{ background: color }} />
      <div className="flex items-start justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">{label}</p>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: `${color}16` }}>
          <Icon className="h-4 w-4" style={{ color }} />
        </div>
      </div>
      <div className="flex items-baseline gap-2 mt-2">
        <p className="text-2xl font-bold tracking-tight tabular-nums" style={{ color }}>{value}</p>
        {trend && (trend === "up" ? <TrendingUp className="h-4 w-4 text-blue-500" /> : <TrendingDown className="h-4 w-4 text-violet-500" />)}
      </div>
      {sublabel && <p className="text-xs text-muted-foreground mt-1">{sublabel}</p>}
    </div>
  );
}

// ── Monthly Trend Chart (Recharts ComposedChart, dual axis) ───────────────────
function MonthlyTrendChart({ data }: { data: MonthlyTrendRow[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-16">No data for selected period</p>;
  }
  const chartData = data.map((d) => ({ month: abbrevMonth(d.month), Leads: d.count, Value: d.value }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="trendBarFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={INDIGO} stopOpacity={0.95} />
            <stop offset="100%" stopColor={VIOLET_LIGHT} stopOpacity={0.75} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(228 18% 88% / 0.6)" vertical={false} />
        <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
        <YAxis yAxisId="left" tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
        <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10, fill: AMBER }} axisLine={false} tickLine={false}
          tickFormatter={(v) => fmtRupee(Number(v))} />
        <Tooltip content={<ChartTooltip />} />
        <Legend iconType="circle" iconSize={7} formatter={(v) => <span style={{ fontSize: 11, color: "#64748B" }}>{v}</span>} />
        <Bar yAxisId="left" dataKey="Leads" name="Lead Count" fill="url(#trendBarFill)" radius={[6, 6, 0, 0]} maxBarSize={40} />
        <Line yAxisId="right" dataKey="Value" name="Pipeline Value" stroke={AMBER} strokeWidth={2.5}
          dot={{ r: 4, fill: AMBER, strokeWidth: 0 }} activeDot={{ r: 6 }} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

// ── Pipeline Funnel (real Recharts funnel + win/lost callouts) ────────────────
function PipelineFunnelReport({ stages }: { stages: PipelineRow[] }) {
  if (stages.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-8">No pipeline stages configured.</p>;
  }

  const wonStage = stages.find((s) => s.is_won);
  const lostStage = stages.find((s) => s.is_lost);
  const wonValue = wonStage?.total_value ?? 0;
  const lostValue = lostStage?.total_value ?? 0;
  const winRate = wonValue + lostValue > 0 ? Math.round((wonValue / (wonValue + lostValue)) * 100) : null;

  const funnelStages = [...stages]
    .filter((s) => !s.is_lost)
    .sort((a, b) => a.sort_order - b.sort_order);
  const funnelData = funnelStages.map((s, i) => ({
    name: s.stage_name,
    value: s.lead_count,
    total_value: s.total_value,
    fill: s.is_won ? GREEN : [INDIGO, "#8174F5", VIOLET_LIGHT, "#8FC0FF", BLUE][i % 5],
  }));

  return (
    <div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 items-center">
        <ResponsiveContainer width="100%" height={200}>
          <FunnelChart>
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload as { name: string; value: number; total_value: number };
                return (
                  <div className="bg-card border border-border rounded-xl shadow-lg px-3 py-2 text-xs">
                    <p className="font-semibold text-foreground">{d.name}</p>
                    <p className="text-muted-foreground">{d.value} leads · {fmtRupee(d.total_value)}</p>
                  </div>
                );
              }}
            />
            <Funnel dataKey="value" data={funnelData} isAnimationActive nameKey="name">
              {funnelData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
            </Funnel>
          </FunnelChart>
        </ResponsiveContainer>
        <div className="space-y-2 min-w-0">
          {funnelData.map((s) => (
            <div key={s.name} className="flex items-center justify-between text-xs gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: s.fill }} />
                <span className="font-medium text-foreground truncate">{s.name}</span>
              </div>
              <div className="flex items-center gap-1.5 text-muted-foreground flex-shrink-0">
                <span className="font-semibold text-foreground">{s.value}</span>
                <span className="opacity-40">·</span>
                <span>{fmtRupee(s.total_value)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {winRate !== null && (
        <div className="mt-2 pt-4 border-t border-border flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Win Rate (by value)</span>
          <div className="flex items-center gap-4">
            <span className="text-xs text-muted-foreground">
              <span style={{ color: GREEN }} className="font-semibold">{fmtRupee(wonValue)}</span> won ·{" "}
              <span style={{ color: RED }} className="font-semibold">{fmtRupee(lostValue)}</span> lost
            </span>
            <span className="font-bold text-base" style={{ color: GREEN }}>{winRate}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Lead Sources (donut) ───────────────────────────────────────────────────────
function LeadSourcesChart({ data }: { data: SourceRow[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-8">No source data available.</p>;
  }
  const sorted = [...data].sort((a, b) => b.count - a.count);
  const total = sorted.reduce((s, r) => s + r.count, 0);

  return (
    <div className="flex flex-col sm:flex-row items-center gap-4">
      <div className="relative flex-shrink-0" style={{ width: 160, height: 160 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload as SourceRow;
                return (
                  <div className="bg-card border border-border rounded-xl shadow-lg px-3 py-2 text-xs">
                    <p className="font-semibold text-foreground">{d.source_name || "Unknown"}</p>
                    <p className="text-muted-foreground">{d.count} leads · {fmtRupee(d.total_value)}</p>
                    <p style={{ color: GREEN }}>{d.won_count} won</p>
                  </div>
                );
              }}
            />
            <Pie data={sorted} dataKey="count" nameKey="source_name" innerRadius={48} outerRadius={72} paddingAngle={2} isAnimationActive>
              {sorted.map((_, i) => <Cell key={i} fill={SOURCE_COLORS[i % SOURCE_COLORS.length]} stroke="none" />)}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <p className="text-2xl font-bold">{total}</p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Leads</p>
        </div>
      </div>
      <div className="flex-1 w-full space-y-2 min-w-0">
        {sorted.map((s, i) => (
          <div key={s.source_name} className="flex items-center justify-between text-xs gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: SOURCE_COLORS[i % SOURCE_COLORS.length] }} />
              <span className="font-medium text-foreground truncate">{s.source_name || "Unknown"}</span>
            </div>
            <div className="flex items-center gap-1.5 text-muted-foreground flex-shrink-0">
              <span className="font-semibold text-foreground">{s.count}</span>
              <span className="opacity-40">·</span>
              <span>{fmtRupee(s.total_value)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Quote Funnel (Recharts funnel + close-rate gauge) ─────────────────────────
function QuoteFunnelChart({ data }: { data: QuoteData }) {
  const total = data.draft + data.sent + data.accepted + data.declined + data.expired;
  if (total === 0) {
    return <p className="text-sm text-muted-foreground text-center py-8">No quote data available.</p>;
  }

  const funnelData = [
    { name: "Draft", value: data.draft, fill: SLATE },
    { name: "Sent", value: data.sent, fill: BLUE },
    { name: "Accepted", value: data.accepted, fill: GREEN },
  ].filter((d) => d.value > 0 || d.name === "Draft");

  const closeRate = data.total_sent_value > 0 ? Math.round((data.accepted_value / data.total_sent_value) * 100) : 0;
  const gaugeColor = closeRate >= 50 ? GREEN : closeRate >= 25 ? AMBER : RED;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
      <div>
        <ResponsiveContainer width="100%" height={170}>
          <FunnelChart>
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload as { name: string; value: number };
                return (
                  <div className="bg-card border border-border rounded-xl shadow-lg px-3 py-2 text-xs">
                    <p className="font-semibold text-foreground">{d.name}</p>
                    <p className="text-muted-foreground">{d.value} quotes</p>
                  </div>
                );
              }}
            />
            <Funnel dataKey="value" data={funnelData} isAnimationActive nameKey="name">
              {funnelData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
            </Funnel>
          </FunnelChart>
        </ResponsiveContainer>
        <div className="flex items-center justify-center gap-4 mt-1">
          {funnelData.map((d) => (
            <span key={d.name} className="flex items-center gap-1.5 text-xs">
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: d.fill }} />
              <span className="font-medium text-foreground">{d.name}</span>
              <span className="text-muted-foreground">({d.value})</span>
            </span>
          ))}
        </div>
      </div>

      <div className="flex flex-col items-center">
        <ResponsiveContainer width="100%" height={130}>
          <RadialBarChart cx="50%" cy="80%" innerRadius="65%" outerRadius="100%" startAngle={180} endAngle={0}
            data={[{ name: "Close Rate", value: closeRate, fill: gaugeColor }]}>
            <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
            <RadialBar background dataKey="value" cornerRadius={8} angleAxisId={0} />
          </RadialBarChart>
        </ResponsiveContainer>
        <p className="text-3xl font-bold -mt-8" style={{ color: gaugeColor }}>{closeRate}%</p>
        <p className="text-xs text-muted-foreground mt-0.5">Close Rate (by value)</p>

        <div className="w-full mt-4 pt-3 border-t border-border space-y-1.5 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground text-xs">Accepted Value</span>
            <span className="font-bold text-xs" style={{ color: GREEN }}>{fmtRupee(data.accepted_value)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground text-xs">Total Sent Value</span>
            <span className="font-semibold text-xs">{fmtRupee(data.total_sent_value)}</span>
          </div>
          <div className="flex items-center gap-4 pt-1">
            <span className="flex items-center gap-1.5 text-xs">
              <span className="w-2 h-2 rounded-full" style={{ background: RED }} />
              <span className="text-muted-foreground">Declined:</span>
              <span className="font-semibold" style={{ color: RED }}>{data.declined}</span>
            </span>
            <span className="flex items-center gap-1.5 text-xs">
              <span className="w-2 h-2 rounded-full" style={{ background: ORANGE }} />
              <span className="text-muted-foreground">Expired:</span>
              <span className="font-semibold" style={{ color: ORANGE }}>{data.expired}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Activity Completion (horizontal grouped bar) ──────────────────────────────
function ActivityCompletionChart({ data }: { data: ActivityRow[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-8">No activity data available.</p>;
  }
  const chartData = [...data].sort((a, b) => b.count - a.count).map((r) => ({
    type: r.type.charAt(0).toUpperCase() + r.type.slice(1),
    Done: r.done_count,
    Pending: Math.max(r.count - r.done_count, 0),
    rateLabel: `${Math.min(Math.round(r.completion_rate), 100)}%`,
    color: ACTIVITY_COLORS[r.type.toLowerCase()] ?? INDIGO,
  }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(180, chartData.length * 44)}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 0 }} barGap={2}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(228 18% 88% / 0.6)" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 10, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="type" tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} width={70} />
        <Tooltip content={<ChartTooltip />} />
        <Legend iconType="circle" iconSize={7} formatter={(v) => <span style={{ fontSize: 11, color: "#64748B" }}>{v}</span>} />
        <Bar dataKey="Done" name="Done" stackId="a" fill={GREEN} radius={[0, 0, 0, 0]} maxBarSize={18} />
        <Bar dataKey="Pending" name="Pending" stackId="a" fill="#CBD5E1" radius={[0, 6, 6, 0]} maxBarSize={18}>
          <LabelList dataKey="rateLabel" position="right" style={{ fontSize: 11, fill: "#64748B", fontWeight: 600 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── Section Card ──────────────────────────────────────────────────────────────
function SectionCard({
  title, subtitle, children, className,
}: {
  title: string; subtitle: string; children: React.ReactNode; className?: string;
}) {
  return (
    <div className={`bg-card border border-border rounded-2xl p-6 ${className ?? ""}`}>
      <div className="mb-5">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">{title}</p>
        <p className="text-sm font-medium mt-0.5">{subtitle}</p>
      </div>
      {children}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function CRMReportsPage() {
  const [appliedRange, setAppliedRange] = useState(() => presetRange(90));
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const { from, to } = appliedRange;
  const REPORT_PRESETS: RangePreset[] = [
    { label: "7D", value: 7 },
    { label: "30D", value: 30 },
    { label: "90D", value: 90 },
    { label: "YTD", value: "ytd" },
  ];

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const params = { date_from: from, date_to: to };

  const pipelineQ = useQuery<PipelineRow[]>({
    queryKey: ["crm-reports-pipeline", from, to],
    queryFn: () => api.get("/crm/reports/pipeline", { params }).then((r) => r.data.data),
  });
  const sourcesQ = useQuery<SourceRow[]>({
    queryKey: ["crm-reports-sources", from, to],
    queryFn: () => api.get("/crm/reports/sources", { params }).then((r) => r.data.data),
  });
  const activitiesQ = useQuery<ActivityRow[]>({
    queryKey: ["crm-reports-activities", from, to],
    queryFn: () => api.get("/crm/reports/activities", { params }).then((r) => r.data.data),
  });
  const quotesQ = useQuery<QuoteData>({
    queryKey: ["crm-reports-quotes", from, to],
    queryFn: () => api.get("/crm/reports/quotes", { params }).then((r) => r.data.data),
  });
  const trendQ = useQuery<MonthlyTrendRow[]>({
    queryKey: ["crm-reports-trend", from, to],
    queryFn: () => api.get("/crm/reports/monthly-trend", { params }).then((r) => r.data.data),
  });

  // ── Derived KPIs ─────────────────────────────────────────────────────────
  const pipeline = pipelineQ.data ?? [];
  const openValue = pipeline.filter((s) => !s.is_won && !s.is_lost).reduce((s, r) => s + r.total_value, 0);
  const wonStage = pipeline.find((s) => s.is_won);
  const lostStage = pipeline.find((s) => s.is_lost);
  const winRate = (wonStage?.total_value ?? 0) + (lostStage?.total_value ?? 0) > 0
    ? Math.round(((wonStage?.total_value ?? 0) / ((wonStage?.total_value ?? 0) + (lostStage?.total_value ?? 0))) * 100)
    : null;

  const quotes = quotesQ.data;
  const closeRate = quotes && quotes.total_sent_value > 0 ? Math.round((quotes.accepted_value / quotes.total_sent_value) * 100) : null;

  const activities = activitiesQ.data ?? [];
  const avgActivityRate = activities.length
    ? Math.round(activities.reduce((s, r) => s + r.completion_rate, 0) / activities.length)
    : null;

  return (
    <div className="p-8 space-y-8">
      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50 px-5 py-3 rounded-xl text-sm font-semibold text-white shadow-xl" style={{ background: INDIGO }}>
          {toastMsg}
        </div>
      )}

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">CRM / REPORTS</p>
          <h1 className="text-2xl font-bold tracking-tight">CRM Reports</h1>
          <p className="text-sm text-muted-foreground mt-1">Pipeline analytics, source breakdown, activity performance, and quote metrics.</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <DateRangeFilter
            from={from} to={to} accent={INDIGO} presets={REPORT_PRESETS}
            onChange={(f, t) => setAppliedRange({ from: f, to: t })}
          />

          <button onClick={() => showToast("Export coming soon")} className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border border-border bg-card hover:bg-muted/50 transition-all active:scale-95">
            <Download className="h-4 w-4" /> Export
          </button>
        </div>
      </div>

      {/* ── KPI Row ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Open Pipeline" value={fmtRupee(openValue)} sublabel={`${pipeline.filter((s) => !s.is_won && !s.is_lost).reduce((s, r) => s + r.lead_count, 0)} open leads`} icon={TrendingUp} color={INDIGO} />
        <StatCard label="Win Rate" value={winRate !== null ? `${winRate}%` : "—"} sublabel="By pipeline value" icon={Trophy} color={winRate !== null && winRate >= 50 ? GREEN : AMBER} />
        <StatCard label="Quote Close Rate" value={closeRate !== null ? `${closeRate}%` : "—"} sublabel="Accepted / sent value" icon={TrendingUp} color={closeRate !== null && closeRate >= 50 ? GREEN : AMBER} />
        <StatCard label="Activity Completion" value={avgActivityRate !== null ? `${avgActivityRate}%` : "—"} sublabel="Average across types" icon={ActivityIcon} color={avgActivityRate !== null && avgActivityRate >= 70 ? GREEN : AMBER} />
      </div>

      {/* ── Section 1: Monthly Pipeline Trend (full width) ────────────────── */}
      <SectionCard title="Monthly Pipeline Trend" subtitle="Lead count and pipeline value by month">
        {trendQ.isLoading ? <ChartSkeleton /> : <MonthlyTrendChart data={trendQ.data ?? []} />}
      </SectionCard>

      {/* ── Section 2: Pipeline Funnel + Lead Sources ─────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionCard title="Pipeline Funnel" subtitle="Lead count and value by stage with win rate">
          {pipelineQ.isLoading ? <ChartSkeleton height={220} /> : <PipelineFunnelReport stages={pipelineQ.data ?? []} />}
        </SectionCard>
        <SectionCard title="Lead Sources" subtitle="Leads by acquisition channel, sorted by volume">
          {sourcesQ.isLoading ? <ChartSkeleton height={220} /> : <LeadSourcesChart data={sourcesQ.data ?? []} />}
        </SectionCard>
      </div>

      {/* ── Section 3: Quote Funnel + Activity Completion ─────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionCard title="Quote Funnel" subtitle="Draft → Sent → Accepted conversion and value">
          {quotesQ.isLoading ? (
            <ChartSkeleton height={200} />
          ) : quotesQ.data ? (
            <QuoteFunnelChart data={quotesQ.data} />
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">No quote data.</p>
          )}
        </SectionCard>
        <SectionCard title="Activity Completion" subtitle="Done vs total tasks by activity type">
          {activitiesQ.isLoading ? <ChartSkeleton height={200} /> : <ActivityCompletionChart data={activitiesQ.data ?? []} />}
        </SectionCard>
      </div>
    </div>
  );
}
