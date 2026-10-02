"use client";

import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Calendar, FileDown, Download } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { SearchableSelect, SelectOption } from "@/components/shared/searchable-select";
import { exportRowsToCsv, CsvColumn } from "@/lib/csv-export";

const INDIGO = "#0049A7";

const PRESETS: { label: string; value: number | "ytd" }[] = [
  { label: "7D", value: 7 },
  { label: "30D", value: 30 },
  { label: "90D", value: 90 },
  { label: "YTD", value: "ytd" },
];

export interface ReportFilterConfig {
  key: string;
  label: string;
  options: SelectOption[];
  width?: string;
}

export interface ReportTotalConfig {
  key: string;
  label: string;
  format?: (v: number) => string;
}

interface ReportPageProps<T extends Record<string, unknown>> {
  breadcrumb: string;
  title: string;
  description: string;
  queryKey: string;
  endpoint: string;
  dateRange?: boolean;
  filters?: ReportFilterConfig[];
  columns: Column<T>[];
  csvColumns?: CsvColumn[];
  totals?: ReportTotalConfig[];
  accent?: string;
}

export function ReportPage<T extends Record<string, unknown>>({
  breadcrumb, title, description, queryKey, endpoint,
  dateRange = true, filters = [], columns, csvColumns, totals, accent = INDIGO,
}: ReportPageProps<T>) {
  const today = new Date().toISOString().slice(0, 10);
  const firstOfMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1)
    .toISOString().slice(0, 10);
  const [from, setFrom] = useState(firstOfMonth);
  const [to, setTo] = useState(today);
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [pdfBusy, setPdfBusy] = useState(false);

  const applyPreset = useCallback((days: number | "ytd") => {
    const toStr = new Date().toISOString().slice(0, 10);
    const fromStr = days === "ytd"
      ? `${new Date().getFullYear()}-01-01`
      : new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    setFrom(fromStr);
    setTo(toStr);
  }, []);

  const activePreset = (() => {
    if (!dateRange || to !== today) return null;
    const days = Math.round((new Date(today).getTime() - new Date(from).getTime()) / 86_400_000);
    if (from === `${new Date().getFullYear()}-01-01`) return "ytd";
    if (days === 7) return 7;
    if (days === 30) return 30;
    if (days === 90) return 90;
    return null;
  })();

  const { data, isLoading, refetch } = useQuery({
    queryKey: [queryKey, dateRange ? from : null, dateRange ? to : null, filterValues],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (dateRange) {
        params.from_date = from;
        params.to_date = to;
      }
      filters.forEach((f) => {
        if (filterValues[f.key]) params[f.key] = filterValues[f.key];
      });
      const res = await api.get(endpoint, { params });
      return (res.data.data ?? []) as T[];
    },
  });

  const rows = data ?? [];

  const totalValues = totals?.map((t) => ({
    ...t,
    value: rows.reduce((acc, r) => acc + Number(r[t.key] ?? 0), 0),
  }));

  const pdfColumns = csvColumns ?? columns.map((c) => ({ key: String(c.key), header: c.header }));

  async function handleExportPdf() {
    setPdfBusy(true);
    try {
      const subtitleParts: string[] = [];
      if (dateRange) subtitleParts.push(`${from} to ${to}`);
      Object.entries(filterValues).forEach(([key, val]) => {
        if (!val) return;
        const f = filters.find((x) => x.key === key);
        const opt = f?.options.find((o) => o.value === val);
        if (f && opt) subtitleParts.push(`${f.label}: ${opt.label}`);
      });
      const res = await api.post(
        "/reports/export/pdf",
        {
          title,
          subtitle: subtitleParts.join("  •  "),
          columns: pdfColumns,
          rows,
          totals: totalValues?.map((t) => ({
            label: t.label,
            value: t.format ? t.format(t.value) : t.value.toLocaleString("en-IN"),
          })) ?? [],
        },
        { responseType: "blob" },
      );
      const blobUrl = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const disposition = res.headers["content-disposition"] as string | undefined;
      const match = disposition?.match(/filename="?([^"]+)"?/);
      const filename = match?.[1] ?? `${title.replace(/\s+/g, "_")}.pdf`;
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
    } finally {
      setPdfBusy(false);
    }
  }

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            {breadcrumb}
          </p>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="text-sm text-muted-foreground mt-1">{description}</p>
        </div>

        <div className="flex items-end gap-2 flex-wrap">
          {filters.map((f) => (
            <div key={f.key} style={{ width: f.width ?? "180px" }}>
              <SearchableSelect
                value={filterValues[f.key] ?? ""}
                onChange={(v) => setFilterValues((s) => ({ ...s, [f.key]: v }))}
                placeholder={f.label}
                accent={accent}
                options={[{ value: "", label: `All — ${f.label}` }, ...f.options]}
              />
            </div>
          ))}

          {dateRange && (
            <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl flex-shrink-0">
              {PRESETS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => applyPreset(p.value)}
                  className="px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150"
                  style={
                    activePreset === p.value
                      ? { background: "hsl(var(--card))", color: accent, boxShadow: "var(--shadow-xs)" }
                      : { color: "hsl(var(--muted-foreground))" }
                  }
                >
                  {p.label}
                </button>
              ))}
            </div>
          )}

          {dateRange && (
            <div className="flex items-center gap-2 bg-card border border-border rounded-xl pl-3 pr-1 py-2.5">
              <Calendar className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
              <input
                type="date" value={from} onChange={(e) => setFrom(e.target.value)}
                className="text-sm bg-transparent border-none outline-none w-[124px]"
              />
              <span className="text-muted-foreground/50 text-xs flex-shrink-0">to</span>
              <input
                type="date" value={to} onChange={(e) => setTo(e.target.value)}
                className="text-sm bg-transparent border-none outline-none w-[124px]"
              />
            </div>
          )}

          <button
            onClick={() => refetch()}
            className="px-3 py-2.5 rounded-xl text-xs font-semibold text-white transition-all hover:opacity-90 active:scale-95 flex-shrink-0"
            style={{ background: accent }}
          >
            Apply
          </button>

          <button
            onClick={() => exportRowsToCsv(title.replace(/\s+/g, "_"), pdfColumns, rows)}
            disabled={rows.length === 0}
            className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold border border-border transition-all hover:bg-muted/50 disabled:opacity-40 flex-shrink-0"
          >
            <Download className="h-3.5 w-3.5" /> CSV
          </button>

          <button
            onClick={handleExportPdf}
            disabled={rows.length === 0 || pdfBusy}
            className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold border border-border transition-all hover:bg-muted/50 disabled:opacity-40 flex-shrink-0"
          >
            <FileDown className="h-3.5 w-3.5" /> {pdfBusy ? "Generating…" : "PDF"}
          </button>
        </div>
      </div>

      {totalValues && totalValues.length > 0 && rows.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {totalValues.map((t) => (
            <div key={t.key} className="bg-card border border-border rounded-2xl p-6">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                {t.label}
              </p>
              <p className="text-2xl font-bold tracking-tight tabular-nums mt-1">
                {t.format ? t.format(t.value) : t.value.toLocaleString("en-IN")}
              </p>
            </div>
          ))}
        </div>
      )}

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">RESULTS</p>
            <p className="text-sm font-medium mt-0.5">
              {data ? `${rows.length} record${rows.length !== 1 ? "s" : ""}` : "Loading…"}
            </p>
          </div>
        </div>
        <div className="p-0">
          <DataTable columns={columns} data={rows} loading={isLoading} />
        </div>
      </div>
    </div>
  );
}
