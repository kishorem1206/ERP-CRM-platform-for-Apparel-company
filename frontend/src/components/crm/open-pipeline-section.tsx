"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight } from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { formatIndianCompact } from "@/lib/format";

const INDIGO = "#0049A7";
const PROCESS_COLORS = ["#10B981", "#14B8A6", "#06B6D4", "#3B82F6", "#6366F1", "#8B5CF6"];
const GOOD = "#059669";
const BAD = "#DC2626";

interface StageRow {
  stage_id: string;
  stage_name: string;
  pipeline_id: string;
  count: number;
  value: number;
}

interface OpenPipeline {
  open_count: number;
  open_value: number;
  older_than_30_days_count: number;
  by_stage: StageRow[];
  previous: { reference_date: string; available: boolean; count: number | null; stage_history_since: string | null };
  change_pct: number | null;
  movement: { added: number; won: number; lost: number; other: number; reconciles: boolean } | null;
  data_notes: {
    reopened_count: number;
    won_lost_without_close_date: number;
    open_without_qualification_stage: number;
    open_status_at_terminal_stage: number;
  };
}

function fmtDate(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function OpenPipelineSection() {
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

  const params = new URLSearchParams({ utc_offset_minutes: String(utcOffsetMinutes) });
  if (pipelineId) params.set("pipeline_id", pipelineId);
  if (assignedTo) params.set("assigned_to", assignedTo);
  if (sourceId) params.set("source_id", sourceId);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["crm-open-pipeline", utcOffsetMinutes, pipelineId, assignedTo, sourceId],
    queryFn: async () => (await api.get(`/crm/reports/open-pipeline?${params}`)).data.data as OpenPipeline,
  });

  const drill = (kpi: string, extra: Record<string, string> = {}) => {
    const q = new URLSearchParams({ kpi, utc_offset_minutes: String(utcOffsetMinutes), ...extra });
    if (pipelineId) q.set("pipeline_id", pipelineId);
    if (assignedTo) q.set("assigned_to", assignedTo);
    if (sourceId) q.set("source_id", sourceId);
    return `/crm/leads?${q}`;
  };


  const prev = data?.previous;
  const change = data?.change_pct ?? null;
  const changeColor = change === null || change === 0 ? undefined : change < 0 ? BAD : GOOD;
  const tile = "rounded-2xl border border-border bg-card p-5 shadow-sm min-w-0";
  const label = "text-[11px] font-bold uppercase tracking-wider text-muted-foreground";

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold tracking-tight">Current open pipeline</h2>
        <p className="text-xs text-muted-foreground">
          All currently open qualified opportunities, regardless of when they were created. The period above does not apply here.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
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

      {data?.data_notes && data.data_notes.open_status_at_terminal_stage > 0 && (
        <div className="flex items-start gap-2 rounded-xl border border-amber-300/60 bg-amber-50 px-4 py-3 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <p>
            {data.data_notes.open_status_at_terminal_stage} lead(s) are marked open but sit in a Won or Lost stage. They are
            left out of the open pipeline until the record is corrected.
          </p>
        </div>
      )}

      {isError ? (
        <div className="flex items-center justify-between rounded-2xl border border-border bg-card p-5 text-sm">
          <p className="text-muted-foreground">Could not load the open pipeline.</p>
          <button onClick={() => refetch()} className="text-xs font-semibold" style={{ color: INDIGO }}>
            Retry
          </button>
        </div>
      ) : (
        <>
          <div className={`grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4 ${isLoading ? "opacity-60" : ""}`}>
            <div className={tile}>
              <p className={label}>Open opportunities</p>
              <Link href={drill("open")} className="mt-2 block text-4xl font-bold tabular-nums tracking-tight hover:underline" style={{ color: INDIGO }}>
                {data ? data.open_count.toLocaleString("en-IN") : "—"}
              </Link>
              <p className="mt-1 text-xs text-muted-foreground">All open qualified</p>
            </div>

            <div className={tile}>
              <p className={label}>Vs previous snapshot</p>
              <p className="mt-2 text-2xl font-bold tabular-nums" style={{ color: changeColor }}>
                {prev?.available && change !== null
                  ? `${change < 0 ? "↓" : change > 0 ? "↑" : "→"} ${Math.abs(change).toFixed(1)}%`
                  : "—"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {prev?.reference_date ? `vs ${fmtDate(prev.reference_date)}${prev.available && prev.count !== null ? ` (${prev.count})` : ""}` : ""}
              </p>
              {prev && !prev.available && (
                <p className="mt-2 text-[11px] leading-snug text-muted-foreground">
                  Not available yet: stage history {prev.stage_history_since ? `starts ${fmtDate(prev.stage_history_since.slice(0, 10))}` : "has no entries yet"}.
                </p>
              )}
            </div>

            <div className={tile}>
              <p className={label}>Movement since then</p>
              {data?.movement ? (
                <div className="mt-2 flex flex-wrap gap-1.5 text-xs font-semibold tabular-nums">
                  <span className="rounded-md px-2 py-1" style={{ background: `${GOOD}1a`, color: GOOD }}>+{data.movement.added} new</span>
                  <span className="rounded-md px-2 py-1" style={{ background: `${BAD}1a`, color: BAD }}>−{data.movement.won} won</span>
                  <span className="rounded-md px-2 py-1" style={{ background: `${BAD}1a`, color: BAD }}>−{data.movement.lost} lost</span>
                  {data.movement.other > 0 && (
                    <span className="rounded-md bg-muted px-2 py-1 text-muted-foreground">{data.movement.other} other</span>
                  )}
                </div>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">—</p>
              )}
              <p className="mt-2 text-[11px] text-muted-foreground">Needs stage history to compare.</p>
            </div>

            <div className={tile}>
              <p className={label}>Older than 30 days</p>
              <Link href={drill("aged")} className="mt-2 block text-4xl font-bold tabular-nums tracking-tight hover:underline" style={{ color: INDIGO }}>
                {data ? data.older_than_30_days_count : "—"}
              </Link>
              <p className="mt-1 text-xs text-muted-foreground">
                {data ? `of ${data.open_count} open` : ""}
              </p>
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <div className="flex flex-wrap items-end justify-between gap-2">
              <div>
                <p className={label}>Where open opportunities sit</p>
                <p className="mt-1 text-xs text-muted-foreground">Click a stage to see its leads.</p>
              </div>
              <div className="text-right">
                <p className={label}>Open pipeline value</p>
                <p className="text-xl font-bold tabular-nums">{data ? formatIndianCompact(data.open_value) : "—"}</p>
                <p className="text-[11px] text-muted-foreground">Expected value of open deals. Not revenue.</p>
              </div>
            </div>

            {data && data.by_stage.length === 0 && (
              <p className="mt-6 text-sm text-muted-foreground">No open qualified opportunities.</p>
            )}

            {data && data.by_stage.length > 0 && (
              <div className="mt-6 flex flex-wrap items-stretch">
                {data.by_stage.map((row, i) => {
                  const color = PROCESS_COLORS[i % PROCESS_COLORS.length];
                  const first = i === 0;
                  return (
                    <Link
                      key={row.stage_id}
                      href={drill("open", { stage_id: row.stage_id, stage_name: row.stage_name })}
                      className="group flex min-w-[150px] flex-1 flex-col items-center text-center"
                      aria-label={`${row.stage_name}: ${row.count} opportunities`}
                    >
                      <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-foreground/80 group-hover:underline">
                        {String(i + 1).padStart(2, "0")} · {row.stage_name}
                      </p>
                      <div
                        className="flex h-20 w-full items-center justify-center text-white transition-transform duration-150 group-hover:-translate-y-0.5"
                        style={{
                          background: color,
                          clipPath: first
                            ? "polygon(0 0, calc(100% - 22px) 0, 100% 50%, calc(100% - 22px) 100%, 0 100%)"
                            : "polygon(22px 0, calc(100% - 22px) 0, 100% 50%, calc(100% - 22px) 100%, 22px 100%, 0 50%)",
                          marginLeft: first ? 0 : -6,
                        }}
                      >
                        <span className="text-2xl font-bold tabular-nums">{row.count}</span>
                      </div>
                      <p className="mt-2 text-xs tabular-nums text-muted-foreground">{formatIndianCompact(row.value)}</p>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
