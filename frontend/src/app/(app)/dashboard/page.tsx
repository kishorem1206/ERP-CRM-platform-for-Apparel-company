"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  Wind, Scissors, Package2, Factory, ShieldCheck, Truck,
  TrendingUp, Wallet, ChevronRight, ArrowUpRight,
} from "lucide-react";
import api from "@/lib/api";

/* ── Brand palette ──────────────────────────────────────── */
const INDIGO   = "#5347CE";
const LAVENDER = "#887CFD";
const BLUE     = "#4896FE";
const TEAL     = "#16C8C7";

/* ── Helpers ─────────────────────────────────────────────── */
const INR = (v: number) =>
  `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

const today    = new Date().toISOString().slice(0, 10);
const ytdStart = `${new Date().getFullYear()}-01-01`;
const mtdStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1)
  .toISOString().slice(0, 10);

/* ── Status meta ─────────────────────────────────────────── */
const STATUS_COLOR: Record<string, string> = {
  draft:             "#94A3B8",
  planned:           BLUE,
  approved:          LAVENDER,
  in_production:     TEAL,
  qc:                "#F59E0B",
  packing:           "#F97316",
  ready_to_dispatch: "#22C55E",
  completed:         "#10B981",
  cancelled:         "#EF4444",
};
const STATUS_LABEL: Record<string, string> = {
  draft:             "Draft",
  planned:           "Planned",
  approved:          "Approved",
  in_production:     "In Production",
  qc:                "QC",
  packing:           "Packing",
  ready_to_dispatch: "Ready",
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
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"
      style={{ background: `${color}1A`, color }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {label}
    </span>
  );
}

/* ── Inline header stat ───────────────────────────────────── */
function HeaderStat({
  label, value, loading, trend,
}: {
  label: string; value: string; loading: boolean; trend?: "up";
}) {
  return (
    <div className="text-right">
      {loading ? (
        <Skeleton className="h-7 w-28 mb-1 ml-auto" />
      ) : (
        <div className="flex items-center justify-end gap-1">
          {trend === "up" && <ArrowUpRight className="h-3.5 w-3.5 text-emerald-500" />}
          <p className="text-xl font-bold tracking-tight tabular-nums">{value}</p>
        </div>
      )}
      <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
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
  const trendData = Object.values(monthMap)
    .sort((a, b) => a.month.localeCompare(b.month))
    .map((r) => ({ ...r, month: r.month.slice(0, 7) }));

  const mtdOutput  = outputData.filter((r) => r.month >= mtdStart);
  const revenueMTD = mtdOutput.reduce((s, r) => s + Number(r.total_amount), 0);
  const outstanding = (salesQ.data ?? []).reduce((s, r) => s + Number(r.outstanding), 0);
  const totalPayable = (purchaseQ.data ?? []).reduce((s, r) => s + Number(r.outstanding), 0);

  const lots = prodQ.data ?? [];
  const activeLots = lots.filter((r) =>
    ["in_production", "planned", "approved"].includes(r.status)
  ).length;
  const qcLots = lots.filter((r) => ["qc", "packing"].includes(r.status)).length;
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
      accent: "#D97706",
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
      accent: "#F97316",
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
      accent: "#22C55E",
      metric: null,
      metricLabel: "ready to ship",
      loading: false,
      active: false,
    },
  ];

  const financialLoading = gstQ.isLoading || salesQ.isLoading;

  const hour     = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  /* ── Render ─────────────────────────────────────────────── */
  return (
    <div className="p-8 space-y-8">

      {/* ── Header ──────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-8 flex-wrap">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            {new Date().toLocaleDateString("en-IN", {
              weekday: "long", day: "numeric", month: "long", year: "numeric",
            })}
          </p>
          <h1 className="text-2xl font-bold tracking-tight">{greeting}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Here's where your manufacturing stands today.
          </p>
        </div>

        <div className="flex items-start gap-10 flex-wrap">
          <HeaderStat
            label="Revenue this month"
            value={financialLoading ? "…" : INR(revenueMTD)}
            loading={financialLoading}
            trend="up"
          />
          <HeaderStat
            label="Receivable"
            value={financialLoading ? "…" : INR(outstanding)}
            loading={financialLoading}
          />
          <HeaderStat
            label="Payable"
            value={purchaseQ.isLoading ? "…" : INR(totalPayable)}
            loading={purchaseQ.isLoading}
          />
        </div>
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
