"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { Can } from "@/lib/permissions";
import { ModalShell } from "@/components/shared/modal-shell";
import { formatIndianFull } from "@/lib/format";

const INDIGO = "#0049A7";

const STATUS_HEX: Record<string, string> = {
  issued: "#8174F5", open: "#0049A7", closed: "#0F78FF",
};

function StatusDot({ status }: { status: string }) {
  const color = STATUS_HEX[status] ?? "#94A3B8";
  const label = status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap"
      style={{ background: `${color}18`, color }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {label}
    </span>
  );
}

interface MISItem {
  id: string;
  product_id: string;
  product_name: string | null;
  unit_abbreviation: string | null;
  planned_qty: string | null;
  issued_qty: string;
  unit_cost: string;
  total_cost: string;
  material_lot_number: string | null;
  excess_qty: string | null;
  used_qty: string | null;
  returned_qty: string | null;
  wastage_qty: string | null;
  return_notes: string | null;
}

interface MISDetail {
  id: string;
  issue_number: string;
  lot_number: string | null;
  production_lot_id: string;
  stage_name: string | null;
  warehouse_name: string | null;
  issue_date: string;
  status: string;
  notes: string | null;
  items: MISItem[];
}

function fmtQty(v: string | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return Number(v).toLocaleString("en-IN", { maximumFractionDigits: 4 });
}

function ReturnModal({ item, onClose }: { item: MISItem; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [usedQty, setUsedQty] = useState(item.used_qty ?? "");
  const [returnedQty, setReturnedQty] = useState(item.returned_qty ?? "");
  const [wastageQty, setWastageQty] = useState(item.wastage_qty ?? "");
  const [notes, setNotes] = useState(item.return_notes ?? "");
  const [error, setError] = useState("");

  const issued = Number(item.issued_qty);
  const total = (Number(usedQty) || 0) + (Number(returnedQty) || 0) + (Number(wastageQty) || 0);
  const remaining = issued - total;
  const overLimit = total > issued;

  const mutation = useMutation({
    mutationFn: () =>
      api.patch(`/production/mis/items/${item.id}/return`, {
        used_qty: usedQty === "" ? null : Number(usedQty),
        returned_qty: returnedQty === "" ? null : Number(returnedQty),
        wastage_qty: wastageQty === "" ? null : Number(wastageQty),
        notes: notes || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["production-mis-detail"] });
      queryClient.invalidateQueries({ queryKey: ["production-mis"] });
      onClose();
    },
    onError: (err: unknown) => setError(parseApiError(err, "Could not record the return.")),
  });

  const inputClass = "w-full rounded-xl border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40";
  const labelClass = "block text-xs font-medium mb-1 text-muted-foreground";

  return (
    <ModalShell onClose={onClose} maxWidth="max-w-md">
      <div className="p-6 space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Record Return</h2>
          <p className="text-sm text-muted-foreground mt-0.5">{item.product_name ?? "Material"}</p>
        </div>

        <p className="text-xs text-muted-foreground">
          Issued: <span className="font-semibold text-foreground">{fmtQty(item.issued_qty)} {item.unit_abbreviation}</span>
        </p>

        {error && (
          <div className="rounded-xl border px-3 py-2 text-sm" style={{ background: "#1D0DB00D", borderColor: "#1D0DB04D", color: "#1D0DB0" }}>
            {error}
          </div>
        )}

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className={labelClass}>Used</label>
            <input type="number" min="0" step="0.0001" className={inputClass} value={usedQty} onChange={(e) => setUsedQty(e.target.value)} />
          </div>
          <div>
            <label className={labelClass}>Returned</label>
            <input type="number" min="0" step="0.0001" className={inputClass} value={returnedQty} onChange={(e) => setReturnedQty(e.target.value)} />
          </div>
          <div>
            <label className={labelClass}>Wastage</label>
            <input type="number" min="0" step="0.0001" className={inputClass} value={wastageQty} onChange={(e) => setWastageQty(e.target.value)} />
          </div>
        </div>

        <p className={`text-xs ${overLimit ? "font-semibold" : "text-muted-foreground"}`} style={overLimit ? { color: "#1D0DB0" } : undefined}>
          {overLimit
            ? `Used + Returned + Wastage (${total}) exceeds the issued quantity (${issued}).`
            : `Unaccounted remainder: ${remaining.toLocaleString("en-IN", { maximumFractionDigits: 4 })} ${item.unit_abbreviation ?? ""}`}
        </p>

        <div>
          <label className={labelClass}>Notes</label>
          <textarea className={inputClass} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || overLimit}
            className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-colors disabled:opacity-50"
            style={{ background: INDIGO }}
          >
            {mutation.isPending ? "Saving…" : "Save Return"}
          </button>
        </div>
      </div>
    </ModalShell>
  );
}

export default function MISDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [returnItem, setReturnItem] = useState<MISItem | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["production-mis-detail", id],
    queryFn: () => api.get(`/production/mis/${id}`).then((r) => r.data.data as MISDetail),
  });

  const card = "rounded-2xl border border-border bg-card p-5";
  const label = "text-[11px] font-semibold uppercase tracking-wider text-muted-foreground";

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/production/mis" className="rounded-lg p-2 hover:bg-muted" aria-label="Back">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex items-center gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Material Issue Slip</p>
            <h1 className="text-2xl font-bold tracking-tight">{data?.issue_number ?? (isLoading ? "Loading…" : "—")}</h1>
          </div>
          {data?.status && <StatusDot status={data.status} />}
        </div>
      </div>

      {isError ? (
        <div className={card + " text-sm text-muted-foreground"}>This material issue could not be loaded.</div>
      ) : data && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            {[
              ["Lot", data.lot_number],
              ["Stage", data.stage_name],
              ["Warehouse", data.warehouse_name],
              ["Issue Date", data.issue_date],
              ["Notes", data.notes],
            ].map(([k, v]) => (
              <div key={k as string} className={card + " min-w-0"}>
                <p className={label}>{k}</p>
                <p className="mt-1 truncate font-semibold">{(v as string) || "—"}</p>
              </div>
            ))}
          </div>

          <div className="rounded-2xl border border-border bg-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border">
              <p className="text-sm font-semibold">Materials</p>
              <p className="text-xs text-muted-foreground mt-0.5">Planned vs. issued, and what actually happened to it after it left the warehouse.</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2.5">Product</th>
                    <th className="px-4 py-2.5 text-right">Planned</th>
                    <th className="px-4 py-2.5 text-right">Issued</th>
                    <th className="px-4 py-2.5 text-right">Used</th>
                    <th className="px-4 py-2.5 text-right">Returned</th>
                    <th className="px-4 py-2.5 text-right">Wastage</th>
                    <th className="px-4 py-2.5 text-right">Unit Cost</th>
                    <th className="px-4 py-2.5 text-right">Total Cost</th>
                    <th className="px-4 py-2.5"></th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((it) => (
                    <tr key={it.id} className="border-t border-border">
                      <td className="px-4 py-2.5 font-medium">
                        {it.product_name || "—"}
                        {it.material_lot_number && (
                          <span className="ml-2 text-[10px] font-normal text-muted-foreground">from {it.material_lot_number}</span>
                        )}
                        {it.excess_qty && Number(it.excess_qty) > 0 && (
                          <span className="ml-2 inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold" style={{ background: "#F59E0B18", color: "#B45309" }}>
                            +{fmtQty(it.excess_qty)} over plan
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{fmtQty(it.planned_qty)}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{fmtQty(it.issued_qty)} {it.unit_abbreviation}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{fmtQty(it.used_qty)}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{fmtQty(it.returned_qty)}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{fmtQty(it.wastage_qty)}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{formatIndianFull(Number(it.unit_cost))}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums font-semibold">{formatIndianFull(Number(it.total_cost))}</td>
                      <td className="px-4 py-2.5 text-right">
                        <Can perm="production.edit">
                          <button
                            onClick={() => setReturnItem(it)}
                            className="text-xs font-semibold hover:underline"
                            style={{ color: INDIGO }}
                          >
                            {it.used_qty !== null || it.returned_qty !== null || it.wastage_qty !== null ? "Edit Return" : "Record Return"}
                          </button>
                        </Can>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {returnItem && <ReturnModal item={returnItem} onClose={() => setReturnItem(null)} />}
    </div>
  );
}
