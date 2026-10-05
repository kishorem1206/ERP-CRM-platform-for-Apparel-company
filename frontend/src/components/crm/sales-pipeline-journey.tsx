"use client";
import { useEffect, useLayoutEffect, useMemo, useState, type CSSProperties } from "react";
import {
  AlertTriangle, CircleDot, FileText, Handshake, Sparkles, Target, Trophy, XCircle, type LucideIcon,
} from "lucide-react";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { formatIndianCompact, formatIndianFull } from "@/lib/format";

const INDIGO = "#4F46E5";
const GREEN = "#059669";
const MUTED_RED = "#E11D48";
const PALETTE = ["#4F46E5", "#2563EB", "#0891B2", "#7C3AED", "#1D4ED8", "#0E7490", "#6D28D9", "#0369A1"];

const DESKTOP_HEIGHT = 280;
const SPINE_Y = DESKTOP_HEIGHT / 2;
const NODE_R = 15;
const CONNECTOR = 34;
const BLOCK_H = 74;
const BLOCK_W = 150;
const TERMINAL_W = 168;
const TERMINAL_H = 66;

export interface JourneyStage {
  id: string;
  name: string;
  color: string | null;
  isWon: boolean;
  isLost: boolean;
  count: number;
  value: number;
}

const ICON_RULES: [RegExp, LucideIcon][] = [
  [/qualif|target|contact/i, Target],
  [/proposal|quot|document|catalog/i, FileText],
  [/negot|sample|handshake|deal/i, Handshake],
  [/new|inbox|lead/i, Sparkles],
];

function iconFor(stage: JourneyStage): LucideIcon {
  if (stage.isWon) return Trophy;
  if (stage.isLost) return XCircle;
  return ICON_RULES.find(([re]) => re.test(stage.name))?.[1] ?? CircleDot;
}

function accentFor(stage: JourneyStage, index: number): string {
  if (stage.isWon) return GREEN;
  if (stage.isLost) return MUTED_RED;
  return PALETTE[index % PALETTE.length];
}

function oppLabel(count: number) {
  return `${count} ${count === 1 ? "opportunity" : "opportunities"}`;
}

function useMediaQuery(query: string) {
  const [matches, setMatches] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia(query);
    const update = () => setMatches(mql.matches);
    update();
    mql.addEventListener("change", update);
    return () => mql.removeEventListener("change", update);
  }, [query]);
  return matches;
}

function useElementWidth() {
  const [el, setEl] = useState<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    if (!el) return;
    const update = () => setWidth(el.clientWidth);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [el]);
  return { ref: setEl, width };
}

/** Pure geometry: column centres along the spine, and where the terminal branch sits. */
export function layoutDesktop(linearCount: number, width: number) {
  const left = 24;
  const terminalSpace = TERMINAL_W + 56;
  const usable = Math.max(width - left - terminalSpace, linearCount * 90);
  const column = usable / Math.max(linearCount, 1);
  const centers = Array.from({ length: linearCount }, (_, i) => left + (i + 0.5) * column);
  const branchX = left + linearCount * column + 8;
  const cardX = branchX + 24;
  return { centers, column, branchX, cardX, spineEnd: centers[centers.length - 1] ?? left };
}

function Stage({
  stage, index, x, above, selected, dimmed, onSelect, animated, delay, accent, totalLeads,
}: {
  stage: JourneyStage;
  index: number;
  x: number;
  above: boolean;
  selected: boolean;
  dimmed: boolean;
  onSelect: (id: string) => void;
  animated: boolean;
  delay: number;
  accent: string;
  totalLeads: number;
}) {
  const Icon = iconFor(stage);
  const blockTop = above ? SPINE_Y - NODE_R - CONNECTOR - BLOCK_H : SPINE_Y + NODE_R + CONNECTOR;
  const connectorTop = above ? SPINE_Y - NODE_R - CONNECTOR : SPINE_Y + NODE_R;
  const pct = totalLeads > 0 ? Math.round((stage.count / totalLeads) * 100) : 0;
  const motion: CSSProperties = animated ? { animationDelay: `${delay}ms` } : {};
  return (
    <>
      <svg className="absolute inset-0 h-full w-full overflow-visible pointer-events-none" aria-hidden>
        <line
          x1={x} x2={x} y1={connectorTop} y2={connectorTop + CONNECTOR}
          stroke={accent} strokeOpacity={dimmed ? 0.2 : 0.45} strokeWidth={1.5}
          className={animated ? "journey-fade" : undefined} style={motion}
        />
        <circle
          cx={x} cy={above ? connectorTop : connectorTop + CONNECTOR} r={3.5}
          fill={accent} fillOpacity={dimmed ? 0.3 : 1}
          className={animated ? "journey-fade" : undefined} style={motion}
        />
      </svg>

      <button
        type="button"
        onClick={() => onSelect(selected ? "" : stage.id)}
        aria-pressed={selected}
        aria-label={`${stage.name} stage. ${oppLabel(stage.count)}. Pipeline value ${formatIndianFull(stage.value)}, ${pct}% of pipeline volume. ${selected ? "Press Enter to clear the filter." : "Press Enter to filter."}`}
        className={`group absolute flex flex-col items-center text-center rounded-xl px-2 py-1.5 transition-all duration-200 hover:-translate-y-0.5 focus:outline-none focus-visible:ring-4 focus-visible:ring-primary/30 ${animated ? "journey-fade" : ""}`}
        style={{
          left: x - BLOCK_W / 2,
          top: blockTop,
          width: BLOCK_W,
          height: BLOCK_H,
          opacity: dimmed ? 0.45 : 1,
          ...motion,
        }}
      >
        <span className="flex items-center gap-1.5">
          <span
            className="flex h-5 w-5 items-center justify-center rounded-md"
            style={{ background: `${accent}18`, color: accent }}
          >
            <Icon className="h-3 w-3" aria-hidden />
          </span>
          <span className="max-w-[108px] truncate text-[11px] font-bold uppercase tracking-wider" style={{ color: accent }} title={stage.name}>
            {stage.name}
          </span>
        </span>
        <span className="mt-1 flex items-baseline gap-1 tabular-nums">
          <span className="text-2xl font-bold leading-none text-foreground">{stage.count}</span>
          <span className="text-[11px] text-muted-foreground">{stage.count === 1 ? "opportunity" : "opportunities"}</span>
        </span>
        <span className="mt-0.5 text-xs font-semibold tabular-nums text-muted-foreground">{formatIndianCompact(stage.value)}</span>
      </button>

      <span
        className={`absolute flex h-7 w-7 items-center justify-center rounded-full border-2 bg-card text-[10px] font-bold tabular-nums transition-all duration-200 ${animated ? "journey-fade" : ""}`}
        style={{
          left: x - NODE_R,
          top: SPINE_Y - NODE_R,
          borderColor: accent,
          color: selected ? "#fff" : accent,
          background: selected ? accent : undefined,
          opacity: dimmed ? 0.45 : 1,
          ...motion,
        }}
        aria-hidden
      >
        {String(index + 1).padStart(2, "0")}
      </span>
    </>
  );
}

function TerminalCard({
  stage, cardX, cardY, color, selected, dimmed, onSelect, animated, delay,
}: {
  stage: JourneyStage;
  cardX: number;
  cardY: number;
  color: string;
  selected: boolean;
  dimmed: boolean;
  onSelect: (id: string) => void;
  animated: boolean;
  delay: number;
}) {
  const Icon = iconFor(stage);
  return (
    <button
      type="button"
      onClick={() => onSelect(selected ? "" : stage.id)}
      aria-pressed={selected}
      aria-label={`${stage.name}. ${oppLabel(stage.count)}. Pipeline value ${formatIndianFull(stage.value)}. ${selected ? "Press Enter to clear the filter." : "Press Enter to filter."}`}
      className={`absolute flex items-center gap-2.5 rounded-xl border bg-card px-3 text-left shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus-visible:ring-4 focus-visible:ring-primary/30 ${animated ? "journey-fade" : ""}`}
      style={{
        left: cardX,
        top: cardY,
        width: TERMINAL_W,
        height: TERMINAL_H,
        borderColor: selected ? color : undefined,
        opacity: dimmed ? 0.45 : 1,
        animationDelay: animated ? `${delay}ms` : undefined,
      }}
    >
      <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg" style={{ background: `${color}18`, color }}>
        <Icon className="h-4 w-4" aria-hidden />
      </span>
      <span className="min-w-0">
        <span className="block text-[10px] font-bold uppercase tracking-wider" style={{ color }}>{stage.name}</span>
        <span className="block text-sm font-bold tabular-nums">
          {stage.count} <span className="text-[11px] font-medium text-muted-foreground">{stage.count === 1 ? "deal" : "deals"}</span>
        </span>
        <span className="block text-[11px] tabular-nums text-muted-foreground">{formatIndianCompact(stage.value)}</span>
      </span>
    </button>
  );
}

export function SalesPipelineJourney({
  pipelineName, stages, stageFilter, onSelect, isLoading, isError, onRetry,
  pipelines, selectedPipelineId, onSelectPipeline,
}: {
  pipelineName: string;
  stages: JourneyStage[];
  stageFilter: string;
  onSelect: (id: string) => void;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  pipelines: { id: string; name: string }[];
  selectedPipelineId: string;
  onSelectPipeline: (id: string) => void;
}) {
  const isMobile = useMediaQuery("(max-width: 767px)");
  const reducedMotion = useMediaQuery("(prefers-reduced-motion: reduce)");
  const animated = !reducedMotion;
  const { ref: frameRef, width } = useElementWidth();

  const linear = useMemo(() => stages.filter((s) => !s.isWon && !s.isLost), [stages]);
  const terminal = useMemo(() => stages.filter((s) => s.isWon || s.isLost), [stages]);
  const totalLeads = useMemo(() => stages.reduce((sum, s) => sum + s.count, 0), [stages]);
  const layout = useMemo(() => layoutDesktop(linear.length, width || 900), [linear.length, width]);

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-2xl p-6">
        <div className="mb-8 h-3 w-40 animate-pulse rounded bg-muted" />
        <div className="relative h-[200px]">
          <div className="absolute left-6 right-6 top-1/2 h-0.5 -translate-y-1/2 animate-pulse rounded bg-muted" />
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="absolute top-1/2 h-4 w-4 -translate-y-1/2 animate-pulse rounded-full bg-muted" style={{ left: `${8 + i * 18}%` }} />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-card border border-border rounded-2xl p-8 flex flex-col items-center text-center gap-2">
        <AlertTriangle className="h-5 w-5 text-muted-foreground" />
        <p className="text-sm font-medium">Sales Pipeline</p>
        <p className="text-sm text-muted-foreground">Unable to load pipeline data.</p>
        <button onClick={onRetry} className="mt-1 text-xs font-semibold hover:underline" style={{ color: INDIGO }}>
          Retry
        </button>
      </div>
    );
  }

  if (stages.length === 0) {
    return (
      <div className="bg-card border border-border rounded-2xl p-8 flex flex-col items-center text-center gap-2">
        <p className="text-sm font-semibold">No pipeline stages configured</p>
        <p className="text-sm text-muted-foreground max-w-xs">Add stages to this pipeline to see the sales journey.</p>
      </div>
    );
  }

  const header = (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="min-w-0">
        <p className="text-base font-bold tracking-tight">{pipelineName || "Sales Pipeline"}</p>
        <p className="text-xs text-muted-foreground">Track opportunities through your sales journey. Click a stage to filter.</p>
      </div>
      <div className="flex items-center gap-2">
        {stageFilter && (
          <button type="button" onClick={() => onSelect("")} className="rounded-lg px-2.5 py-1.5 text-xs font-semibold hover:underline" style={{ color: INDIGO }}>
            Clear filter
          </button>
        )}
        {pipelines.length > 1 && (
          <div className="w-52">
            <SearchableSelect
              options={pipelines.map((p) => ({ value: p.id, label: p.name }))}
              value={selectedPipelineId}
              onChange={onSelectPipeline}
              placeholder="Select pipeline…"
              accent={INDIGO}
            />
          </div>
        )}
      </div>
    </div>
  );

  const spineColors = linear.map((s, i) => accentFor(s, i));
  const gradientId = `spine-${pipelineName.replace(/\W+/g, "") || "pipeline"}`;

  const desktop = (
    <div ref={frameRef} className="relative mt-4 w-full" style={{ height: DESKTOP_HEIGHT }}>
      {width > 0 && (
        <svg className="absolute inset-0 h-full w-full overflow-visible" aria-hidden>
          <defs>
            <linearGradient id={gradientId} gradientUnits="userSpaceOnUse" x1={layout.centers[0]} x2={layout.spineEnd} y1={SPINE_Y} y2={SPINE_Y}>
              {spineColors.map((c, i) => (
                <stop key={i} offset={`${spineColors.length > 1 ? (i / (spineColors.length - 1)) * 100 : 0}%`} stopColor={c} />
              ))}
            </linearGradient>
          </defs>
          {linear.length > 0 && (
            <line
              x1={layout.centers[0]} x2={layout.spineEnd} y1={SPINE_Y} y2={SPINE_Y}
              stroke={`url(#${gradientId})`} strokeWidth={3} strokeLinecap="round"
              pathLength={1}
              className={animated ? "journey-draw" : undefined}
            />
          )}
          {layout.centers.slice(0, -1).map((c, i) => {
            const mx = (c + layout.centers[i + 1]) / 2;
            return (
              <polyline
                key={i}
                points={`${mx - 3},${SPINE_Y - 4} ${mx + 2},${SPINE_Y} ${mx - 3},${SPINE_Y + 4}`}
                fill="none" stroke={spineColors[i]} strokeOpacity={0.55} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round"
              />
            );
          })}
          {terminal.length > 0 && linear.length > 0 && terminal.map((t, j) => {
            const y = SPINE_Y + (terminal.length === 1 ? 0 : j === 0 ? -(TERMINAL_H / 2 + 14) : TERMINAL_H / 2 + 14);
            const x0 = layout.spineEnd + NODE_R;
            const x1 = layout.cardX;
            const color = accentFor(t, 0);
            return (
              <path
                key={t.id}
                d={`M ${x0} ${SPINE_Y} C ${x0 + 20} ${SPINE_Y}, ${x1 - 20} ${y}, ${x1} ${y}`}
                fill="none" stroke={color} strokeOpacity={t.isLost ? 0.5 : 0.8} strokeWidth={1.75} strokeLinecap="round"
                className={animated ? "journey-draw" : undefined}
                pathLength={1}
              />
            );
          })}
        </svg>
      )}

      {width > 0 && linear.map((stage, i) => {
        const selected = stageFilter === stage.id;
        return (
          <Stage
            key={stage.id}
            stage={stage}
            index={i}
            x={layout.centers[i]}
            above={i % 2 === 0}
            selected={selected}
            dimmed={!!stageFilter && !selected}
            onSelect={onSelect}
            animated={animated}
            delay={120 + i * 110}
            accent={accentFor(stage, i)}
            totalLeads={totalLeads}
          />
        );
      })}

      {width > 0 && terminal.map((t, j) => {
        const selected = stageFilter === t.id;
        const cardY = SPINE_Y + (terminal.length === 1 ? -TERMINAL_H / 2 : j === 0 ? -(TERMINAL_H / 2 + 14) - TERMINAL_H / 2 : TERMINAL_H / 2 + 14 - TERMINAL_H / 2);
        return (
          <TerminalCard
            key={t.id}
            stage={t}
            cardX={layout.cardX}
            cardY={cardY}
            color={accentFor(t, 0)}
            selected={selected}
            dimmed={!!stageFilter && !selected}
            onSelect={onSelect}
            animated={animated}
            delay={120 + linear.length * 110 + j * 110}
          />
        );
      })}
    </div>
  );

  const mobile = (
    <ol className="mt-5 space-y-0">
      {[...linear, ...terminal].map((stage, i, all) => {
        const index = linear.indexOf(stage);
        const color = index >= 0 ? accentFor(stage, index) : accentFor(stage, 0);
        const Icon = iconFor(stage);
        const selected = stageFilter === stage.id;
        const dimmed = !!stageFilter && !selected;
        return (
          <li key={stage.id} className="relative pl-10">
            {i < all.length - 1 && <span className="absolute left-[13px] top-7 h-full w-px bg-border" aria-hidden />}
            <span
              className="absolute left-0 top-1 flex h-7 w-7 items-center justify-center rounded-full border-2 bg-card text-[10px] font-bold"
              style={{ borderColor: color, color: selected ? "#fff" : color, background: selected ? color : undefined }}
              aria-hidden
            >
              {index >= 0 ? String(index + 1).padStart(2, "0") : <Icon className="h-3.5 w-3.5" />}
            </span>
            <button
              type="button"
              onClick={() => onSelect(selected ? "" : stage.id)}
              aria-pressed={selected}
              aria-label={`${stage.name} stage. ${oppLabel(stage.count)}. Pipeline value ${formatIndianFull(stage.value)}.`}
              className="mb-4 flex w-full items-center justify-between gap-3 rounded-xl border border-border bg-card px-3 py-2.5 text-left focus:outline-none focus-visible:ring-4 focus-visible:ring-primary/30"
              style={{ opacity: dimmed ? 0.45 : 1, borderColor: selected ? color : undefined }}
            >
              <span className="min-w-0">
                <span className="flex items-center gap-1.5">
                  <Icon className="h-3.5 w-3.5 flex-shrink-0" style={{ color }} aria-hidden />
                  <span className="truncate text-[11px] font-bold uppercase tracking-wider" style={{ color }}>{stage.name}</span>
                </span>
                <span className="mt-0.5 block text-sm font-semibold tabular-nums">
                  {stage.count} {stage.count === 1 ? "opportunity" : "opportunities"}
                </span>
              </span>
              <span className="shrink-0 text-right text-xs font-semibold tabular-nums text-muted-foreground">
                {formatIndianCompact(stage.value)}
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );

  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      {header}
      {isMobile ? mobile : desktop}
      {totalLeads === 0 && (
        <p className="mt-4 text-center text-xs text-muted-foreground">No active opportunities yet. The stages show the pipeline structure.</p>
      )}
      <style jsx>{`
        @keyframes journey-fade {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes journey-draw {
          from { stroke-dashoffset: 1; }
          to { stroke-dashoffset: 0; }
        }
        .journey-fade {
          animation: journey-fade 420ms ease-out both;
        }
        .journey-draw {
          stroke-dasharray: 1;
          animation: journey-draw 900ms ease-out both;
        }
        @media (prefers-reduced-motion: reduce) {
          .journey-fade, .journey-draw { animation: none; }
        }
      `}</style>
    </div>
  );
}
