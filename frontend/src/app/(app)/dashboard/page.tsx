"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  Wind, Scissors, Package2, Factory, ShieldCheck, Truck,
  TrendingUp, Wallet, ChevronRight,
  Phone, Users, StickyNote, CheckSquare, Mail, X, CalendarClock,
  Receipt, CreditCard,
} from "lucide-react";
import api from "@/lib/api";
import { ModalPortal } from "@/components/shared/modal-portal";

/* ── Brand palette ──────────────────────────────────────── */
const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

/* ── Helpers ─────────────────────────────────────────────── */
const INR = (v: number) =>
  `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

const today    = new Date().toISOString().slice(0, 10);
const ytdStart = `${new Date().getFullYear()}-01-01`;
const mtdStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1)
  .toISOString().slice(0, 10);

/* ── Status meta ─────────────────────────────────────────── */
const STATUS_COLOR: Record<string, string> = {
  cutting:           TEAL,
  checking:          "#A096F7",
  packing:           "#0F78FF",
  completed:         "#0F78FF",
  cancelled:         "#1D0DB0",
};
const STATUS_LABEL: Record<string, string> = {
  cutting:           "Cutting",
  checking:          "Checking",
  packing:           "Packing",
  completed:         "Done",
  cancelled:         "Cancelled",
};

/* ── Skeleton pulse ──────────────────────────────────────── */
function Skeleton({ className = "" }: { className?: string }) {
  return <span className={`block rounded-md bg-muted animate-pulse ${className}`} aria-hidden />;
}

/* ── Custom chart tooltip ────────────────────────────────── */
function ChartTooltip({
  active, payload, label,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold mb-1 text-foreground">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}:{" "}
          ₹{Number(p.value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
        </p>
      ))}
    </div>
  );
}

/* ── Production lot status badge ─────────────────────────── */
function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLOR[status] ?? "#94A3B8";
  const label = STATUS_LABEL[status] ?? status.replace(/_/g, " ");
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded whitespace-nowrap"
      style={{ background: `${color}1A`, color, fontSize: 11, fontWeight: 700 }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {label}
    </span>
  );
}

/* ── KPI metric card ──────────────────────────────────────── */
function KpiCard({
  label, value, sublabel, icon: Icon, accent, loading,
}: {
  label: string; value: string; sublabel?: string;
  icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>;
  accent: string; loading: boolean;
}) {
  return (
    <div className="bg-card border border-border rounded-2xl p-5 flex-1 min-w-[200px]">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">{label}</p>
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: `${accent}14`, border: `1px solid ${accent}28` }}
        >
          <Icon className="h-4 w-4" style={{ color: accent }} />
        </div>
      </div>
      {loading ? (
        <Skeleton className="h-7 w-24 mt-2" />
      ) : (
        <p className="text-2xl font-bold tracking-tight tabular-nums mt-2">{value}</p>
      )}
      {sublabel && <p className="text-xs text-muted-foreground mt-1">{sublabel}</p>}
    </div>
  );
}

/* ── Manufacturing pipeline node ─────────────────────────── */
interface PipelineStage {
  key: string;
  label: string;
  icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>;
  href: string;
  accent: string;
  metric: string | null;
  metricLabel: string;
  loading: boolean;
  active: boolean;
}

function PipelineNode({ stage, isLast }: { stage: PipelineStage; isLast: boolean }) {
  const Icon = stage.icon;
  return (
    <div className="flex items-center flex-shrink-0">
      <Link
        href={stage.href}
        className="group flex flex-col items-center gap-2 px-5 py-3 rounded-xl hover:bg-muted/60 transition-all duration-200 min-w-[110px] text-center"
      >
        {/* Icon */}
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center transition-transform duration-200 group-hover:scale-105"
          style={{
            background: `${stage.accent}14`,
            border: `1.5px solid ${stage.accent}28`,
          }}
        >
          <Icon className="h-4 w-4" style={{ color: stage.accent }} />
        </div>

        {/* Metric */}
        <div className="space-y-0.5">
          {stage.loading ? (
            <Skeleton className="h-5 w-8 mx-auto" />
          ) : (
            <p
              className="text-lg font-bold leading-none tabular-nums"
              style={{ color: stage.active ? stage.accent : undefined }}
            >
              {stage.metric ?? "—"}
            </p>
          )}
          <p className="text-[10px] text-muted-foreground leading-none">{stage.metricLabel}</p>
        </div>

        {/* Label */}
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground group-hover:text-foreground transition-colors leading-none">
          {stage.label}
        </p>

        {/* Activity dot */}
        {stage.active && (
          <span
            className="w-1.5 h-1.5 rounded-full -mt-1"
            style={{ background: stage.accent }}
          />
        )}
      </Link>

      {/* Connector */}
      {!isLast && (
        <div className="flex items-center flex-shrink-0 mx-0.5">
          <div className="w-6 h-px bg-border" />
          <ChevronRight className="h-3 w-3 text-muted-foreground/40 -ml-1" />
        </div>
      )}
    </div>
  );
}

/* ── Today's Activities popup ─────────────────────────────── */
interface TodayActivity {
  id: string;
  type: string;
  title: string;
  schedule_from: string | null;
  is_done: boolean;
  lead_title: string | null;
  person_name: string | null;
}

const TODAY_ACTIVITY_ICONS: Record<string, React.ReactNode> = {
  call: <Phone className="h-3.5 w-3.5" />,
  meeting: <Users className="h-3.5 w-3.5" />,
  note: <StickyNote className="h-3.5 w-3.5" />,
  task: <CheckSquare className="h-3.5 w-3.5" />,
  email: <Mail className="h-3.5 w-3.5" />,
};

const TODAY_ACTIVITY_COLORS: Record<string, string> = {
  call: BLUE,
  meeting: LAVENDER,
  note: "#A096F7",
  task: "#0F78FF",
  email: INDIGO,
};

function dismissedKey() {
  return `today-activities-dismissed-${new Date().toISOString().slice(0, 10)}`;
}

function TodayActivitiesPopup() {
  const [dismissed, setDismissed] = useState(true); // start hidden until we check sessionStorage

  useEffect(() => {
    try {
      setDismissed(sessionStorage.getItem(dismissedKey()) === "1");
    } catch {
      setDismissed(false);
    }
  }, []);

  const { data } = useQuery({
    queryKey: ["dash-today-activities"],
    queryFn: async () => {
      const now = new Date();
      const dayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
      const dayEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
      const res = await api.get("/crm/activities", {
        params: { date_from: dayStart.toISOString(), date_to: dayEnd.toISOString(), page_size: 50 },
      });
      return (res.data.data ?? []) as TodayActivity[];
    },
    staleTime: 60_000,
  });

  const activities = (data ?? []).sort((a, b) => (a.schedule_from ?? "").localeCompare(b.schedule_from ?? ""));

  function dismiss() {
    setDismissed(true);
    try {
      sessionStorage.setItem(dismissedKey(), "1");
    } catch {
      /* private-mode storage may throw — dismissal just won't persist */
    }
  }

  if (dismissed || activities.length === 0) return null;

  const pendingCount = activities.filter((a) => !a.is_done).length;

  return (
    <ModalPortal>
    <div className="fixed bottom-6 right-6 z-50 w-[360px] bg-card border border-border rounded-2xl shadow-2xl overflow-hidden">
      <div className="flex items-start justify-between gap-3 px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ background: `${INDIGO}18`, color: INDIGO }}
          >
            <CalendarClock className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-semibold leading-tight">Today's Activities</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {pendingCount > 0 ? `${pendingCount} pending · ${activities.length} total` : `${activities.length} scheduled`}
            </p>
          </div>
        </div>
        <button onClick={dismiss} className="p-1 rounded-md hover:bg-muted text-muted-foreground transition-colors flex-shrink-0">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="max-h-72 overflow-y-auto divide-y divide-border">
        {activities.map((a) => {
          const color = TODAY_ACTIVITY_COLORS[a.type] ?? INDIGO;
          return (
            <div key={a.id} className="flex items-start gap-2.5 px-4 py-2.5">
              <div
                className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                style={{ background: `${color}18`, color }}
              >
                {TODAY_ACTIVITY_ICONS[a.type] ?? <CheckSquare className="h-3.5 w-3.5" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-xs font-medium leading-snug truncate ${a.is_done ? "line-through text-muted-foreground" : ""}`}>
                  {a.title}
                </p>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  {a.schedule_from
                    ? new Date(a.schedule_from).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })
                    : "No time set"}
                  {(a.lead_title || a.person_name) && ` · ${a.lead_title ?? a.person_name}`}
                </p>
              </div>
            </div>
          );
        })}
      </div>
      <Link
        href="/crm/activities"
        className="block text-center text-xs font-semibold px-4 py-2.5 border-t border-border hover:bg-muted/50 transition-colors"
        style={{ color: INDIGO }}
      >
        View all activities
      </Link>
    </div>
    </ModalPortal>
  );
}

/* ══════════════════════════════════════════════════════════ */
export default function DashboardPage() {

  /* ── Data ──────────────────────────────────────────────── */
  const gstQ = useQuery({
    queryKey: ["dash-gst-ytd"],
    queryFn: async () => {
      const res = await api.get("/reports/gst-summary", {
        params: { from_date: ytdStart, to_date: today },
      });
      return res.data.data as {
        output: { month: string; total_amount: string }[];
        input:  { month: string; total_amount: string }[];
      };
    },
  });

  const salesQ = useQuery({
    queryKey: ["dash-sales-ytd"],
    queryFn: async () => {
      const res = await api.get("/reports/sales-summary", {
        params: { from_date: ytdStart, to_date: today },
      });
      return (res.data.data ?? []) as {
        customer_name: string; customer_type: string;
        total_amount: string; outstanding: string;
      }[];
    },
  });

  const prodQ = useQuery({
    queryKey: ["dash-production"],
    queryFn: async () => {
      const res = await api.get("/reports/production-efficiency");
      return (res.data.data ?? []) as {
        status: string; planned_qty: number; actual_qty: number;
        lot_number: string; style_name?: string; delivery_date?: string;
      }[];
    },
  });

  const purchaseQ = useQuery({
    queryKey: ["dash-purchase-ytd"],
    queryFn: async () => {
      const res = await api.get("/reports/purchase-summary", {
        params: { from_date: ytdStart, to_date: today },
      });
      return (res.data.data ?? []) as {
        vendor_name: string; total_amount: string; outstanding: string;
      }[];
    },
  });

  // Pipeline: lightweight counts from materials
  const yarnQ = useQuery({
    queryKey: ["dash-yarn-count"],
    queryFn: async () => {
      const res = await api.get("/materials/lots", { params: { material_type: "yarn", page_size: 1 } });
      return (res.data.meta?.total ?? 0) as number;
    },
    staleTime: 60_000,
  });
  const fabricStockQ = useQuery({
    queryKey: ["dash-fabric-count"],
    queryFn: async () => {
      const res = await api.get("/materials/lots", { params: { material_type: "fabric", page_size: 1 } });
      return (res.data.meta?.total ?? 0) as number;
    },
    staleTime: 60_000,
  });
  const runsQ = useQuery({
    queryKey: ["dash-runs-count"],
    queryFn: async () => {
      const res = await api.get("/materials/fabric-runs", { params: { page_size: 1 } });
      return (res.data.meta?.total ?? 0) as number;
    },
    staleTime: 60_000,
  });

  /* ── Derived ───────────────────────────────────────────── */
  const outputData = gstQ.data?.output ?? [];
  const inputData  = gstQ.data?.input  ?? [];

  const monthMap: Record<string, { month: string; revenue: number; purchase: number }> = {};
  outputData.forEach((r) => {
    if (!monthMap[r.month]) monthMap[r.month] = { month: r.month, revenue: 0, purchase: 0 };
    monthMap[r.month].revenue = Number(r.total_amount);
  });
  inputData.forEach((r) => {
    if (!monthMap[r.month]) monthMap[r.month] = { month: r.month, revenue: 0, purchase: 0 };
    monthMap[r.month].purchase = Number(r.total_amount);
  });

  // Zero-fill every month from Jan through the current month so a month with
  // no invoices renders as a flat 0 instead of being skipped entirely —
  // skipping it left a visual gap where the line jumped straight past it.
  const trendData: { month: string; revenue: number; purchase: number }[] = [];
  const ytdCursor = new Date(new Date().getFullYear(), 0, 1);
  const ytdEnd = new Date();
  while (ytdCursor <= ytdEnd) {
    const key = ytdCursor.toISOString().slice(0, 7); // "YYYY-MM"
    const found = Object.values(monthMap).find((r) => r.month.startsWith(key));
    trendData.push({
      month: ytdCursor.toLocaleDateString("en-IN", { month: "short" }),
      revenue: found?.revenue ?? 0,
      purchase: found?.purchase ?? 0,
    });
    ytdCursor.setMonth(ytdCursor.getMonth() + 1);
  }

  const mtdOutput  = outputData.filter((r) => r.month >= mtdStart);
  const revenueMTD = mtdOutput.reduce((s, r) => s + Number(r.total_amount), 0);
  const outstanding = (salesQ.data ?? []).reduce((s, r) => s + Number(r.outstanding), 0);
  const totalPayable = (purchaseQ.data ?? []).reduce((s, r) => s + Number(r.outstanding), 0);

  const lots = prodQ.data ?? [];
  const activeLots = lots.filter((r) => r.status === "cutting").length;
  const qcLots = lots.filter((r) => ["checking", "packing"].includes(r.status)).length;
  const recentLots = lots.slice(0, 8);

  const topCustomers = [...(salesQ.data ?? [])]
    .sort((a, b) => Number(b.total_amount) - Number(a.total_amount))
    .slice(0, 6)
    .map((r) => ({
      name: r.customer_name.length > 14 ? r.customer_name.slice(0, 13) + "…" : r.customer_name,
      revenue: Number(r.total_amount),
      outstanding: Number(r.outstanding),
    }));

  const custTypeMap: Record<string, number> = {};
  (salesQ.data ?? []).forEach((r) => {
    custTypeMap[r.customer_type] = (custTypeMap[r.customer_type] ?? 0) + Number(r.total_amount);
  });
  const custDistData = Object.entries(custTypeMap).map(([type, amount], i) => ({
    name: type.charAt(0).toUpperCase() + type.slice(1),
    value: amount,
    color: [INDIGO, TEAL, BLUE, LAVENDER][i % 4],
  }));
  const totalRevenue = (salesQ.data ?? []).reduce((s, r) => s + Number(r.total_amount), 0);

  // Pipeline stages
  const pipeline: PipelineStage[] = [
    {
      key: "yarn",
      label: "Yarn",
      icon: Wind,
      href: "/inventory/lots",
      accent: "#A096F7",
      metric: yarnQ.isSuccess ? String(yarnQ.data) : null,
      metricLabel: "in stock",
      loading: yarnQ.isLoading,
      active: (yarnQ.data ?? 0) > 0,
    },
    {
      key: "runs",
      label: "Knitting",
      icon: Scissors,
      href: "/inventory/lots",
      accent: TEAL,
      metric: runsQ.isSuccess ? String(runsQ.data) : null,
      metricLabel: "fabric runs",
      loading: runsQ.isLoading,
      active: (runsQ.data ?? 0) > 0,
    },
    {
      key: "fabric",
      label: "Fabric",
      icon: Package2,
      href: "/inventory/lots",
      accent: BLUE,
      metric: fabricStockQ.isSuccess ? String(fabricStockQ.data) : null,
      metricLabel: "in stock",
      loading: fabricStockQ.isLoading,
      active: (fabricStockQ.data ?? 0) > 0,
    },
    {
      key: "production",
      label: "Production",
      icon: Factory,
      href: "/production",
      accent: INDIGO,
      metric: prodQ.isSuccess ? String(activeLots) : null,
      metricLabel: "active lots",
      loading: prodQ.isLoading,
      active: activeLots > 0,
    },
    {
      key: "qc",
      label: "QC & Pack",
      icon: ShieldCheck,
      href: "/production",
      accent: "#A096F7",
      metric: prodQ.isSuccess ? String(qcLots) : null,
      metricLabel: "in QC / packing",
      loading: prodQ.isLoading,
      active: qcLots > 0,
    },
    {
      key: "dispatch",
      label: "Dispatch",
      icon: Truck,
      href: "/sales",
      accent: "#0F78FF",
      metric: null,
      metricLabel: "ready to ship",
      loading: false,
      active: false,
    },
  ];

  const financialLoading = gstQ.isLoading || salesQ.isLoading;

  // This page is statically prerendered at build time, so `new Date()` must
  // not be evaluated during the initial render (server and client would
  // disagree on "now" and produce a hydration mismatch). Render a neutral
  // placeholder until mounted, then swap in the real client-side date.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const now = mounted ? new Date() : null;
  const hour = now?.getHours() ?? null;
  const greeting = hour === null ? "Welcome back" : hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const dateLabel = now
    ? now.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" })
    : "";

  /* ── Render ─────────────────────────────────────────────── */
  return (
    <div className="p-8 space-y-8">
      <TodayActivitiesPopup />

      {/* ── Header ──────────────────────────────────────────── */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          {dateLabel}
        </p>
        <h1 className="text-2xl font-bold tracking-tight">{greeting}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Here's where your manufacturing stands today.
        </p>
      </div>

      {/* ── KPI Cards ─────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-4">
        <KpiCard
          label="Revenue this month"
          value={financialLoading ? "…" : INR(revenueMTD)}
          sublabel="Month to date"
          icon={TrendingUp}
          accent={INDIGO}
          loading={financialLoading}
        />
        <KpiCard
          label="Receivable"
          value={financialLoading ? "…" : INR(outstanding)}
          sublabel="Outstanding from customers"
          icon={Receipt}
          accent={TEAL}
          loading={financialLoading}
        />
        <KpiCard
          label="Payable"
          value={purchaseQ.isLoading ? "…" : INR(totalPayable)}
          sublabel="Outstanding to vendors"
          icon={CreditCard}
          accent="#A096F7"
          loading={purchaseQ.isLoading}
        />
        <KpiCard
          label="Active Lots"
          value={prodQ.isLoading ? "…" : String(activeLots)}
          sublabel="In planning or production"
          icon={Factory}
          accent="#0F78FF"
          loading={prodQ.isLoading}
        />
      </div>

      {/* ── Manufacturing Pipeline ───────────────────────────── */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 pt-5 pb-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              Manufacturing Pipeline
            </p>
            <p className="text-sm font-medium mt-0.5">Live production journey</p>
          </div>
          <Link
            href="/production"
            className="flex items-center gap-1 text-xs text-primary hover:underline font-medium"
          >
            All lots <ChevronRight className="h-3 w-3" />
          </Link>
        </div>
        <div className="flex items-center px-4 pb-5 overflow-x-auto">
          {pipeline.map((stage, i) => (
            <PipelineNode key={stage.key} stage={stage} isLast={i === pipeline.length - 1} />
          ))}
        </div>
      </div>

      {/* ── Row 2: Revenue chart + Production lots list ──────── */}
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">

        {/* Revenue vs Purchase — area chart */}
        <div className="xl:col-span-3 bg-card border border-border rounded-2xl p-6">
          <div className="flex items-start justify-between mb-5">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Revenue vs Purchase</p>
              <p className="text-sm font-medium mt-0.5">Year-to-date, monthly</p>
            </div>
            <div className="flex items-center gap-5 text-[11px] text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: INDIGO }} />
                Revenue
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: TEAL }} />
                Purchase
              </span>
            </div>
          </div>
          {trendData.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-52 gap-3">
              <TrendingUp className="h-9 w-9 text-muted-foreground/20" />
              <div className="text-center">
                <p className="text-sm text-muted-foreground">No transactions yet</p>
                <p className="text-xs text-muted-foreground/60 mt-0.5">
                  Revenue and purchase history will appear here
                </p>
              </div>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={trendData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradRev" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={INDIGO} stopOpacity={0.14} />
                    <stop offset="95%" stopColor={INDIGO} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradPur" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={TEAL} stopOpacity={0.14} />
                    <stop offset="95%" stopColor={TEAL} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(228 18% 88% / 0.5)" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
                <YAxis
                  tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false}
                  tickFormatter={(v) =>
                    v >= 100000 ? `₹${(v / 100000).toFixed(0)}L`
                    : v >= 1000  ? `₹${(v / 1000).toFixed(0)}k`
                    : `₹${v}`
                  }
                />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="revenue" name="Revenue" stroke={INDIGO} strokeWidth={2}
                  fill="url(#gradRev)" dot={false} activeDot={{ r: 4, strokeWidth: 0, fill: INDIGO }} />
                <Area type="monotone" dataKey="purchase" name="Purchase" stroke={TEAL} strokeWidth={2}
                  fill="url(#gradPur)" dot={false} activeDot={{ r: 4, strokeWidth: 0, fill: TEAL }} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Live production lots */}
        <div className="xl:col-span-2 bg-card border border-border rounded-2xl p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Production</p>
              <p className="text-sm font-medium mt-0.5">Recent lots</p>
            </div>
            <Link href="/production" className="text-xs text-primary hover:underline font-medium">
              View all
            </Link>
          </div>

          {prodQ.isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3">
                  <Skeleton className="w-8 h-8 rounded-xl flex-shrink-0" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-3 w-28" />
                    <Skeleton className="h-2.5 w-16" />
                  </div>
                  <Skeleton className="h-5 w-20 rounded-full" />
                </div>
              ))}
            </div>
          ) : recentLots.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-52 gap-3 text-center">
              <Factory className="h-10 w-10 text-muted-foreground/20" />
              <div>
                <p className="text-sm font-medium">No lots yet</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Create a lot to start your first manufacturing run
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-0.5">
              {recentLots.map((lot) => (
                <Link
                  key={lot.lot_number}
                  href="/production"
                  className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-muted/50 transition-colors group"
                >
                  <div
                    className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: `${STATUS_COLOR[lot.status] ?? INDIGO}14` }}
                  >
                    <Factory
                      className="h-3.5 w-3.5"
                      style={{ color: STATUS_COLOR[lot.status] ?? INDIGO }}
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold truncate">{lot.lot_number}</p>
                    <p className="text-[11px] text-muted-foreground tabular-nums truncate">
                      {lot.planned_qty.toLocaleString("en-IN")} pcs
                      {lot.style_name && lot.style_name !== "—"
                        ? ` · ${lot.style_name}`
                        : ""}
                    </p>
                  </div>
                  <StatusBadge status={lot.status} />
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Row 3: Top Customers + Sales mix ────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">

        {/* Top Customers bar */}
        <div className="xl:col-span-3 bg-card border border-border rounded-2xl p-6">
          <div className="flex items-start justify-between mb-5">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Top Customers</p>
              <p className="text-sm font-medium mt-0.5">Revenue & outstanding — year to date</p>
            </div>
            <div className="flex items-center gap-5 text-[11px] text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: INDIGO }} />
                Revenue
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: LAVENDER }} />
                Outstanding
              </span>
            </div>
          </div>
          {topCustomers.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-52 gap-3">
              <Wallet className="h-9 w-9 text-muted-foreground/20" />
              <div className="text-center">
                <p className="text-sm text-muted-foreground">No sales data yet</p>
                <p className="text-xs text-muted-foreground/60 mt-0.5">
                  Customer revenue will appear here once orders are invoiced
                </p>
              </div>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={topCustomers} margin={{ top: 4, right: 4, left: 0, bottom: 0 }} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(228 18% 88% / 0.5)" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
                <YAxis
                  tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false}
                  tickFormatter={(v) =>
                    v >= 100000 ? `₹${(v / 100000).toFixed(0)}L`
                    : v >= 1000  ? `₹${(v / 1000).toFixed(0)}k`
                    : `₹${v}`
                  }
                />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="revenue" name="Revenue" fill={INDIGO} radius={[4, 4, 0, 0]} maxBarSize={28} />
                <Bar dataKey="outstanding" name="Outstanding" fill={LAVENDER} radius={[4, 4, 0, 0]} maxBarSize={28} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Sales mix donut */}
        <div className="xl:col-span-2 bg-card border border-border rounded-2xl p-6">
          <div className="mb-5">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Sales Mix</p>
            <p className="text-sm font-medium mt-0.5">By customer type — year to date</p>
          </div>
          {custDistData.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-52 gap-3">
              <TrendingUp className="h-9 w-9 text-muted-foreground/20" />
              <p className="text-sm text-muted-foreground">No data yet</p>
            </div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={custDistData} cx="50%" cy="50%"
                    innerRadius={46} outerRadius={68}
                    paddingAngle={2} dataKey="value" strokeWidth={0}
                  >
                    {custDistData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => [`₹${Number(v).toLocaleString("en-IN")}`, ""]} />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-3 space-y-2.5">
                {custDistData.map((s) => (
                  <div key={s.name} className="flex items-center gap-2.5 text-xs">
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: s.color }} />
                    <span className="text-muted-foreground flex-1 capitalize">{s.name}</span>
                    <div className="text-right">
                      <p className="font-semibold tabular-nums">
                        {totalRevenue > 0 ? Math.round((s.value / totalRevenue) * 100) : 0}%
                      </p>
                      <p className="text-muted-foreground text-[10px] tabular-nums">{INR(s.value)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
