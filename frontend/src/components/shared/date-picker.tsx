"use client";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";

const DEFAULT_ACCENT = "#0049A7";
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
const POPOVER_WIDTH = 288;

const pad = (n: number) => String(n).padStart(2, "0");

// Values are "YYYY-MM-DD" (date) or "YYYY-MM-DDTHH:mm" (datetime), same as native inputs.
// Dates are built from parts, never via toISOString, so the local day is always correct.
function toDateString(y: number, m: number, d: number) {
  return `${y}-${pad(m + 1)}-${pad(d)}`;
}

function parseValue(v: string) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(v ?? "");
  return m ? { y: Number(m[1]), m: Number(m[2]) - 1, d: Number(m[3]) } : null;
}

function parseTime(v: string) {
  const t = /T(\d{2}):(\d{2})/.exec(v ?? "");
  return t ? { hh: t[1], mm: t[2] } : null;
}

function todayParts() {
  const now = new Date();
  return { y: now.getFullYear(), m: now.getMonth(), d: now.getDate() };
}

function formatDisplay(v: string, mode: "date" | "datetime") {
  const p = parseValue(v);
  if (!p) return "";
  const base = `${pad(p.d)} ${MONTHS[p.m]} ${p.y}`;
  const t = parseTime(v);
  return mode === "datetime" && t ? `${base}, ${t.hh}:${t.mm}` : base;
}

/** Today as "YYYY-MM-DD" in the user's local timezone. */
export function todayString() {
  const t = todayParts();
  return toDateString(t.y, t.m, t.d);
}

export type PeriodKey =
  | "today" | "yesterday" | "thisWeek" | "lastWeek" | "thisMonth" | "lastMonth"
  | "thisQuarter" | "lastQuarter" | "thisYear";

export type RangePreset = { label: string; value: number | "ytd" | PeriodKey };

/** Preset ranges used by DateRangeFilter. Local calendar days, inclusive. Weeks start Monday. */
export function presetRange(preset: number | "ytd" | PeriodKey) {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth();
  const d = now.getDate();
  const day = (yy: number, mm: number, dd: number) => {
    const x = new Date(yy, mm, dd);
    return toDateString(x.getFullYear(), x.getMonth(), x.getDate());
  };
  const today = todayString();
  const mondayOffset = (now.getDay() + 6) % 7;
  const quarterStart = Math.floor(m / 3) * 3;

  switch (preset) {
    case "today":
      return { from: today, to: today };
    case "yesterday": {
      const v = day(y, m, d - 1);
      return { from: v, to: v };
    }
    case "thisWeek":
      return { from: day(y, m, d - mondayOffset), to: day(y, m, d - mondayOffset + 6) };
    case "lastWeek":
      return { from: day(y, m, d - mondayOffset - 7), to: day(y, m, d - mondayOffset - 1) };
    case "thisMonth":
      return { from: day(y, m, 1), to: day(y, m + 1, 0) };
    case "lastMonth":
      return { from: day(y, m - 1, 1), to: day(y, m, 0) };
    case "thisQuarter":
      return { from: day(y, quarterStart, 1), to: day(y, quarterStart + 3, 0) };
    case "lastQuarter":
      return { from: day(y, quarterStart - 3, 1), to: day(y, quarterStart, 0) };
    case "thisYear":
      return { from: day(y, 0, 1), to: day(y, 12, 0) };
    case "ytd":
      return { from: `${y}-01-01`, to: today };
    default: {
      const start = new Date(y, m, d - preset);
      return { from: toDateString(start.getFullYear(), start.getMonth(), start.getDate()), to: today };
    }
  }
}

export const RANGE_PRESETS: RangePreset[] = [
  { label: "30D", value: 30 },
  { label: "90D", value: 90 },
  { label: "YTD", value: "ytd" },
  { label: "All", value: 3650 },
];

/** Calendar periods for reporting screens. Each full period compares against the previous full period. */
export const PERIOD_PRESETS: RangePreset[] = [
  { label: "Today", value: "today" },
  { label: "Yesterday", value: "yesterday" },
  { label: "This Week", value: "thisWeek" },
  { label: "Last Week", value: "lastWeek" },
  { label: "This Month", value: "thisMonth" },
  { label: "Last Month", value: "lastMonth" },
  { label: "This Quarter", value: "thisQuarter" },
  { label: "Last Quarter", value: "lastQuarter" },
  { label: "This Year", value: "thisYear" },
];

interface DatePickerProps {
  value: string;
  onChange: (value: string) => void;
  /** "datetime" adds an hour/minute row (value becomes YYYY-MM-DDTHH:mm). */
  mode?: "date" | "datetime";
  min?: string;
  max?: string;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  accent?: string;
  /** Extra classes for the outer wrapper (e.g. a width). */
  className?: string;
  /** "field" = form input look; "pill" = compact filter-group look. */
  variant?: "field" | "pill";
}

export function DatePicker({
  value,
  onChange,
  mode = "date",
  min,
  max,
  placeholder = "Select date…",
  disabled = false,
  required = false,
  accent = DEFAULT_ACCENT,
  className = "",
  variant = "field",
}: DatePickerProps) {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<"days" | "months" | "years">("days");
  const [viewYear, setViewYear] = useState(() => todayParts().y);
  const [viewMonth, setViewMonth] = useState(() => todayParts().m);
  const [yearStart, setYearStart] = useState(0);
  const [coords, setCoords] = useState<{ top: number; left: number } | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const popRef = useRef<HTMLDivElement>(null);

  const selected = parseValue(value);
  const time = parseTime(value);
  const minDay = min?.slice(0, 10);
  const maxDay = max?.slice(0, 10);

  function position() {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return null;
    const height = mode === "datetime" ? 420 : 380;
    const spaceBelow = window.innerHeight - rect.bottom;
    const top = spaceBelow < height && rect.top > spaceBelow ? rect.top - height - 6 : rect.bottom + 6;
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - POPOVER_WIDTH - 8));
    return { top, left };
  }

  function openPicker() {
    if (disabled) return;
    const base = selected ?? todayParts();
    setViewYear(base.y);
    setViewMonth(base.m);
    setView("days");
    setCoords(position());
    setOpen(true);
  }

  function close() {
    setOpen(false);
    setView("days");
  }

  // Close on outside click, Escape (without closing a parent modal), or scroll.
  useEffect(() => {
    if (!open) return;
    function onMouseDown(e: MouseEvent) {
      const target = e.target as Node;
      if (ref.current?.contains(target) || popRef.current?.contains(target)) return;
      close();
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.stopPropagation();
        close();
      }
    }
    function onScroll(e: Event) {
      if (popRef.current?.contains(e.target as Node)) return;
      close();
    }
    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("keydown", onKeyDown);
    window.addEventListener("scroll", onScroll, true);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("scroll", onScroll, true);
    };
  }, [open]);

  function commit(dateStr: string, hh?: string, mm?: string) {
    if (mode === "datetime") {
      const t = hh !== undefined ? `${hh}:${mm}` : time ? `${time.hh}:${time.mm}` : "09:00";
      onChange(`${dateStr}T${t}`);
    } else {
      onChange(dateStr);
    }
  }

  function pickDay(y: number, m: number, d: number) {
    commit(toDateString(y, m, d));
    if (mode === "date") close();
  }

  function setTimePart(hh: string, mm: string) {
    const base = selected ? value.slice(0, 10) : todayString();
    onChange(`${base}T${hh}:${mm}`);
  }

  function shift(dir: -1 | 1) {
    if (view === "years") setYearStart((s) => s + dir * 12);
    else if (view === "months") setViewYear((y) => y + dir);
    else {
      const next = new Date(viewYear, viewMonth + dir, 1);
      setViewYear(next.getFullYear());
      setViewMonth(next.getMonth());
    }
  }

  function isDisabledDay(dateStr: string) {
    return (minDay !== undefined && dateStr < minDay) || (maxDay !== undefined && dateStr > maxDay);
  }

  const today = todayParts();
  const todayStr = toDateString(today.y, today.m, today.d);
  const firstWeekday = new Date(viewYear, viewMonth, 1).getDay();
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const cells: (number | null)[] = [
    ...Array(firstWeekday).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  const trigger = variant === "field"
    ? "flex w-full items-center justify-between gap-2 rounded-xl border bg-background px-3 py-2 text-sm text-left transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
    : "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold tabular-nums transition-all duration-150 disabled:opacity-50";

  const triggerStyle: React.CSSProperties = variant === "field"
    ? {
        borderColor: open ? accent : "hsl(var(--border))",
        boxShadow: open ? `0 0 0 3px ${accent}20` : undefined,
      }
    : open
      ? { background: "hsl(var(--card))", color: accent, boxShadow: "var(--shadow-xs)" }
      : { color: value ? "hsl(var(--foreground))" : "hsl(var(--muted-foreground))" };

  const display = formatDisplay(value, mode);

  const popover = open && coords && (
    <div
      ref={popRef}
      className="fixed z-[10000] rounded-2xl border border-border bg-card shadow-lg p-3 text-sm"
      style={{ top: coords.top, left: coords.left, width: POPOVER_WIDTH }}
    >
      {/* Header: prev / month / year / next */}
      <div className="flex items-center justify-between mb-2">
        <button type="button" onClick={() => shift(-1)} className="p-1.5 rounded-lg hover:bg-muted transition-colors" aria-label="Previous">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setView(view === "months" ? "days" : "months")}
            className="px-2 py-1 rounded-lg font-semibold hover:bg-muted transition-colors"
            style={view === "months" ? { color: accent } : undefined}
          >
            {MONTHS_LONG[viewMonth]}
          </button>
          <button
            type="button"
            onClick={() => {
              setYearStart(viewYear - 5);
              setView(view === "years" ? "days" : "years");
            }}
            className="px-2 py-1 rounded-lg font-semibold tabular-nums hover:bg-muted transition-colors"
            style={view === "years" ? { color: accent } : undefined}
          >
            {viewYear}
          </button>
        </div>
        <button type="button" onClick={() => shift(1)} className="p-1.5 rounded-lg hover:bg-muted transition-colors" aria-label="Next">
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      {view === "years" && (
        <div className="grid grid-cols-4 gap-1">
          {Array.from({ length: 12 }, (_, i) => yearStart + i).map((y) => (
            <button
              key={y}
              type="button"
              onClick={() => { setViewYear(y); setView("days"); }}
              className="py-2 rounded-lg text-sm tabular-nums transition-colors hover:bg-muted"
              style={y === viewYear ? { background: accent, color: "#fff" } : undefined}
            >
              {y}
            </button>
          ))}
        </div>
      )}

      {view === "months" && (
        <div className="grid grid-cols-3 gap-1">
          {MONTHS.map((name, i) => (
            <button
              key={name}
              type="button"
              onClick={() => { setViewMonth(i); setView("days"); }}
              className="py-2 rounded-lg text-sm transition-colors hover:bg-muted"
              style={i === viewMonth ? { background: accent, color: "#fff" } : undefined}
            >
              {name}
            </button>
          ))}
        </div>
      )}

      {view === "days" && (
        <>
          <div className="grid grid-cols-7 gap-y-0.5 mb-1">
            {WEEKDAYS.map((w) => (
              <span key={w} className="text-center text-[11px] font-semibold text-muted-foreground py-1">{w}</span>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-y-0.5">
            {cells.map((d, i) => {
              if (d === null) return <span key={`blank-${i}`} />;
              const dateStr = toDateString(viewYear, viewMonth, d);
              const isSelected = selected !== null && dateStr === value.slice(0, 10);
              const isToday = dateStr === todayStr;
              const blocked = isDisabledDay(dateStr);
              return (
                <button
                  key={dateStr}
                  type="button"
                  disabled={blocked}
                  onClick={() => pickDay(viewYear, viewMonth, d)}
                  className="h-8 rounded-lg text-sm tabular-nums transition-colors hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent"
                  style={
                    isSelected
                      ? { background: accent, color: "#fff", fontWeight: 600 }
                      : isToday
                        ? { color: accent, fontWeight: 700, boxShadow: `inset 0 0 0 1px ${accent}` }
                        : undefined
                  }
                >
                  {d}
                </button>
              );
            })}
          </div>
        </>
      )}

      {mode === "datetime" && (
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border">
          <span className="text-xs font-semibold text-muted-foreground">Time</span>
          <input
            type="number" min={0} max={23}
            value={time?.hh ?? "09"}
            onChange={(e) => setTimePart(pad(Math.min(23, Math.max(0, Number(e.target.value) || 0))), time?.mm ?? "00")}
            className="w-14 rounded-lg border border-border bg-background px-2 py-1 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
          <span className="text-muted-foreground">:</span>
          <input
            type="number" min={0} max={59}
            value={time?.mm ?? "00"}
            onChange={(e) => setTimePart(time?.hh ?? "09", pad(Math.min(59, Math.max(0, Number(e.target.value) || 0))))}
            className="w-14 rounded-lg border border-border bg-background px-2 py-1 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>
      )}

      <div className="flex items-center justify-between mt-3 pt-2 border-t border-border">
        <button
          type="button"
          onClick={() => { onChange(""); close(); }}
          className="px-2 py-1 rounded-lg text-xs font-semibold text-muted-foreground hover:bg-muted transition-colors"
        >
          Clear
        </button>
        <button
          type="button"
          onClick={() => {
            const t = todayParts();
            setViewYear(t.y);
            setViewMonth(t.m);
            pickDay(t.y, t.m, t.d);
          }}
          className="px-2 py-1 rounded-lg text-xs font-semibold transition-colors hover:bg-muted"
          style={{ color: accent }}
        >
          Today
        </button>
      </div>
    </div>
  );

  return (
    <div ref={ref} className={`relative ${variant === "field" ? "w-full" : "inline-flex"} ${className}`}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => (open ? close() : openPicker())}
        className={trigger}
        style={triggerStyle}
      >
        {variant === "pill" && <Calendar className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />}
        <span className={`truncate ${value ? "" : "text-muted-foreground"}`}>{display || placeholder}</span>
        {variant === "field" && <Calendar className="h-4 w-4 text-muted-foreground flex-shrink-0" />}
      </button>
      {required && (
        // Keeps native "required" validation working for forms that rely on it.
        <input
          tabIndex={-1}
          aria-hidden
          required
          value={value}
          onChange={() => {}}
          className="absolute inset-0 opacity-0 pointer-events-none"
        />
      )}
      {popover && createPortal(popover, document.body)}
    </div>
  );
}

interface DateRangeFilterProps {
  from: string;
  to: string;
  onChange: (from: string, to: string) => void;
  accent?: string;
  presets?: RangePreset[];
}

/** Preset pills (30D / 90D / YTD / All) plus a from–to picker, in one muted group. */
export function DateRangeFilter({ from, to, onChange, accent = DEFAULT_ACCENT, presets = RANGE_PRESETS }: DateRangeFilterProps) {
  const activeLabel = presets.find((p) => {
    const r = presetRange(p.value);
    return r.from === from && r.to === to;
  })?.label ?? null;

  return (
    <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl flex-wrap">
      {presets.map((p) => (
        <button
          key={p.label}
          type="button"
          onClick={() => {
            const r = presetRange(p.value);
            onChange(r.from, r.to);
          }}
          className="px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150"
          style={
            activeLabel === p.label
              ? { background: "hsl(var(--card))", color: accent, boxShadow: "var(--shadow-xs)" }
              : { color: "hsl(var(--muted-foreground))" }
          }
        >
          {p.label}
        </button>
      ))}
      <span className="mx-1 h-4 w-px bg-border" />
      <DatePicker variant="pill" value={from} placeholder="Select…" max={to || undefined} accent={accent} onChange={(v) => onChange(v, to)} />
      <span className="text-xs text-muted-foreground/60">to</span>
      <DatePicker variant="pill" value={to} placeholder="Select…" min={from || undefined} accent={accent} onChange={(v) => onChange(from, v)} />
    </div>
  );
}
