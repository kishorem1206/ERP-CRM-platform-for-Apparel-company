"use client";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, X } from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";

const INDIGO = "#0049A7";
const inputCls =
  "w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

export interface LotSizeRow { size_id: string; qty: string }

/** Total of the size-wise quantities, or 0 when none are filled in. */
export function sizeRowsTotal(rows: LotSizeRow[]): number {
  return rows.reduce((sum, r) => sum + (parseInt(r.qty) || 0), 0);
}

/** The `sizes` payload for POST /production/lots. */
export function sizeRowsPayload(rows: LotSizeRow[]) {
  return rows.filter((r) => parseInt(r.qty) > 0).map((r) => ({ size_id: r.size_id, planned_qty: parseInt(r.qty) }));
}

/**
 * Size-wise quantities for a new lot, then the planned total under them.
 * The rows start from the style's sizes (with any quantities the style
 * still carries) and any master size can be added. Once a size has a
 * quantity, Planned Qty is their sum; with none, it is typed directly.
 */
export function LotSizePlan({
  styleId, rows, onRowsChange, plannedQty, onPlannedQtyChange,
}: {
  styleId: string;
  rows: LotSizeRow[];
  onRowsChange: (rows: LotSizeRow[]) => void;
  plannedQty: string;
  onPlannedQtyChange: (v: string) => void;
}) {
  const { data: styleDetail } = useQuery({
    queryKey: ["style-detail-for-lot", styleId],
    queryFn: async () => (await api.get(`/production/styles/${styleId}`)).data.data as {
      sizes: { size_id: string; quantity: number | null }[];
    },
    enabled: !!styleId,
  });
  const { data: sizesMaster } = useQuery({
    queryKey: ["master-sizes"],
    queryFn: async () => (await api.get("/master/sizes")).data.data as { id: string; name: string }[],
  });

  // A new style choice resets the rows to that style's sizes.
  useEffect(() => {
    if (!styleId) { onRowsChange([]); return; }
    if (!styleDetail) return;
    onRowsChange(styleDetail.sizes.map((s) => ({ size_id: s.size_id, qty: s.quantity != null ? String(Math.round(s.quantity)) : "" })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [styleId, styleDetail]);

  const total = sizeRowsTotal(rows);
  const sizeName = (id: string) => (sizesMaster ?? []).find((m) => m.id === id)?.name ?? "—";
  const addable = (sizesMaster ?? []).filter((m) => !rows.some((r) => r.size_id === m.id));

  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs font-medium text-muted-foreground">Quantity per Size</label>
        <p className="text-[11px] text-muted-foreground mt-0.5 mb-1.5">
          {rows.length ? "Enter how many pieces of each size this lot makes." : "Add the sizes this lot makes, or leave empty and enter the total below."}
        </p>
        <div className="space-y-1.5">
          {rows.map((r) => (
            <div key={r.size_id} className="flex items-center gap-2">
              <span className="text-xs font-medium w-20 flex-shrink-0">{sizeName(r.size_id)}</span>
              <input
                type="number" min="0" placeholder="Pieces"
                value={r.qty}
                onChange={(e) => onRowsChange(rows.map((x) => x.size_id === r.size_id ? { ...x, qty: e.target.value } : x))}
                className="w-28 rounded border border-input bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <button
                type="button" aria-label={`Remove size ${sizeName(r.size_id)}`}
                onClick={() => onRowsChange(rows.filter((x) => x.size_id !== r.size_id))}
                className="text-muted-foreground hover:text-foreground p-1"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
          {addable.length > 0 && (
            <div className="w-48">
              <SearchableSelect
                value=""
                onChange={(v) => v && onRowsChange([...rows, { size_id: v, qty: "" }])}
                placeholder="+ Add size"
                accent={INDIGO}
                options={addable.map((m) => ({ value: m.id, label: m.name }))}
              />
            </div>
          )}
        </div>
      </div>
      <div>
        <label className="text-xs font-medium text-muted-foreground">Planned Qty *</label>
        {total > 0 ? (
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-lg font-semibold tabular-nums">{total.toLocaleString("en-IN")}</span>
            <span className="text-[11px] text-muted-foreground">pieces — total of the sizes above</span>
          </div>
        ) : (
          <input
            required type="number" min="1" placeholder="e.g. 500"
            value={plannedQty === "0" ? "" : plannedQty}
            onChange={(e) => onPlannedQtyChange(e.target.value)}
            className={`mt-1 ${inputCls}`}
          />
        )}
      </div>
    </div>
  );
}

interface PastMistake {
  id: string;
  stage_name: string | null;
  process_name: string | null;
  resolved_staff_name: string | null;
  mistake_date: string;
  description: string;
  problem_type: string | null;
  action_taken: string | null;
}

/**
 * Shown once a style is picked for a new lot: the mistakes logged on the
 * last lot of that style, so they can be avoided this time, or an all-clear.
 */
export function PastMistakesNotice({ styleId }: { styleId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["style-last-lot-mistakes", styleId],
    queryFn: async () => (await api.get(`/production/styles/${styleId}/last-lot-mistakes`)).data.data as {
      lot: { id: string; lot_number: string; status: string } | null;
      mistakes: PastMistake[];
    },
    enabled: !!styleId,
  });
  if (!styleId || isLoading || !data) return null;

  if (!data.lot) {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
        <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-emerald-600" />
        First lot of this style — no earlier mistakes to review.
      </div>
    );
  }
  if (data.mistakes.length === 0) {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300">
        <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
        All clear — no mistakes were logged on the last lot of this style ({data.lot.lot_number}).
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2.5 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
      <div className="flex items-center gap-2 font-semibold">
        <AlertTriangle className="h-4 w-4 flex-shrink-0" />
        {data.mistakes.length} mistake{data.mistakes.length > 1 ? "s" : ""} on the last lot of this style ({data.lot.lot_number}) — avoid these this time
      </div>
      <ul className="mt-2 space-y-2">
        {data.mistakes.map((m) => (
          <li key={m.id} className="border-t border-amber-200 dark:border-amber-900 pt-2">
            <div className="font-medium">
              {[m.stage_name ?? m.process_name, m.problem_type].filter(Boolean).join(" · ") || "Mistake"}
              <span className="font-normal opacity-75"> — {m.mistake_date}{m.resolved_staff_name ? ` · ${m.resolved_staff_name}` : ""}</span>
            </div>
            <p className="mt-0.5">{m.description}</p>
            {m.action_taken && <p className="mt-0.5 opacity-80">Action taken: {m.action_taken}</p>}
          </li>
        ))}
      </ul>
    </div>
  );
}
