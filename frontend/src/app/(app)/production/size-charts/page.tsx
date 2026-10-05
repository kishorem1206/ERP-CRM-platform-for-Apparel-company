"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Pencil, X } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { Can } from "@/lib/permissions";

const INDIGO = "#0049A7";

interface SizeChartItem { id: string; size_id: string; quantity: string | null; sort_order: number }
interface SizeChart { id: string; name: string; items: SizeChartItem[] }

function parseApiError(e: unknown, fallback: string): string {
  const data = (e as { response?: { data?: Record<string, unknown> } })?.response?.data;
  if (!data) return fallback;
  const err = data.error;
  if (typeof err === "string") return err;
  if (err && typeof (err as { message?: string }).message === "string") return (err as { message: string }).message;
  return fallback;
}

let rowSeq = 0;
function newId() {
  rowSeq += 1;
  return `row-${Date.now()}-${rowSeq}`;
}

interface ItemRow { key: string; size_id: string; quantity: string }

function ChartEditor({ chart, onClose }: { chart: SizeChart | null; onClose: () => void }) {
  const qc = useQueryClient();
  const isEdit = !!chart;
  const [name, setName] = useState(chart?.name ?? "");
  const [rows, setRows] = useState<ItemRow[]>(
    chart ? [...chart.items].sort((a, b) => a.sort_order - b.sort_order).map((i) => ({
      key: newId(), size_id: i.size_id, quantity: i.quantity ?? "",
    })) : []
  );
  const [error, setError] = useState("");

  const sizes = useQuery({
    queryKey: ["master-sizes"],
    queryFn: async () => (await api.get("/master/sizes")).data.data as { id: string; name: string }[],
  });

  function addRow() {
    setRows((r) => [...r, { key: newId(), size_id: "", quantity: "" }]);
  }
  function updateRow(key: string, patch: Partial<ItemRow>) {
    setRows((r) => r.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }
  function removeRow(key: string) {
    setRows((r) => r.filter((row) => row.key !== key));
  }

  const mut = useMutation({
    mutationFn: () => {
      const payload = {
        name: name.trim(),
        items: rows.filter((r) => r.size_id).map((r, i) => ({
          size_id: r.size_id,
          quantity: r.quantity ? Number(r.quantity) : undefined,
          sort_order: i,
        })),
      };
      return isEdit
        ? api.patch(`/production/size-charts/${chart!.id}`, payload)
        : api.post("/production/size-charts", payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["size-charts"] });
      onClose();
    },
    onError: (e: unknown) => setError(parseApiError(e, `Failed to ${isEdit ? "update" : "create"} size chart`)),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
      <div className="bg-card border rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="font-semibold text-base">{isEdit ? "Edit Size Chart" : "New Size Chart"}</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
        </div>
        <form className="p-5 space-y-4" onSubmit={(e) => { e.preventDefault(); setError(""); mut.mutate(); }}>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Chart Name</label>
            <input
              value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. T-Shirt Standard"
              className="w-full rounded border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              required
            />
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">Sizes &amp; Quantities</p>
            <div className="space-y-2">
              {rows.map((r) => (
                <div key={r.key} className="flex items-center gap-2">
                  <div className="flex-1">
                    <SearchableSelect
                      value={r.size_id}
                      onChange={(v) => updateRow(r.key, { size_id: v })}
                      placeholder="Select size"
                      accent={INDIGO}
                      options={(sizes.data ?? []).map((s) => ({ value: s.id, label: s.name }))}
                    />
                  </div>
                  <input
                    type="number" step="0.001" value={r.quantity}
                    onChange={(e) => updateRow(r.key, { quantity: e.target.value })}
                    placeholder="Quantity"
                    className="w-28 rounded border border-input bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                  <button type="button" onClick={() => removeRow(r.key)} className="p-1.5 rounded-md text-muted-foreground hover:text-[#1D0DB0] hover:bg-[#1D0DB0]/10 flex-shrink-0">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
              <button
                type="button" onClick={addRow}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border border-dashed border-border text-muted-foreground hover:text-foreground hover:border-foreground/40 transition-colors"
              >
                <Plus className="h-3.5 w-3.5" /> Add Size
              </button>
            </div>
          </div>
          {error && <p className="text-sm text-[#1D0DB0] bg-[#1D0DB0]/10 border border-[#1D0DB0]/20 rounded-xl px-4 py-3">{error}</p>}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg border border-border text-sm font-medium hover:bg-muted transition-colors">
              Cancel
            </button>
            <button
              type="submit" disabled={!name.trim() || mut.isPending}
              className="px-5 py-2 rounded-lg text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50 transition-all"
              style={{ background: INDIGO }}
            >
              {mut.isPending ? "Saving…" : "Save Chart"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function SizeChartsPage() {
  const qc = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingChart, setEditingChart] = useState<SizeChart | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["size-charts"],
    queryFn: async () => (await api.get("/production/size-charts")).data.data as SizeChart[],
  });

  const sizes = useQuery({
    queryKey: ["master-sizes"],
    queryFn: async () => (await api.get("/master/sizes")).data.data as { id: string; name: string }[],
  });
  const sizeById = new Map((sizes.data ?? []).map((s) => [s.id, s.name]));

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/production/size-charts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["size-charts"] }),
  });

  const columns: Column<SizeChart & Record<string, unknown>>[] = [
    { key: "name", header: "Chart Name" },
    {
      key: "items", header: "Sizes",
      render: (row) => (
        <div className="flex gap-1.5 flex-wrap">
          {[...row.items].sort((a, b) => a.sort_order - b.sort_order).map((i) => (
            <span key={i.id} className="text-[11px] px-2 py-0.5 rounded bg-muted">
              {sizeById.get(i.size_id) ?? "—"}{i.quantity ? `: ${Number(i.quantity)}` : ""}
            </span>
          ))}
          {row.items.length === 0 && <span className="text-muted-foreground text-xs">No sizes</span>}
        </div>
      ),
    },
    {
      key: "id", header: "",
      className: "w-24",
      render: (row) => (
        <div className="flex items-center gap-1 justify-end">
          <button
            onClick={(e) => { e.stopPropagation(); setEditingChart(row); setEditorOpen(true); }}
            className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
            title="Edit"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <Can perm="production.delete"><button
            onClick={(e) => { e.stopPropagation(); if (confirm(`Delete "${row.name}"?`)) deleteMut.mutate(row.id); }}
            className="p-1.5 rounded-lg text-muted-foreground hover:bg-[#1D0DB0]/10 hover:text-[#1D0DB0]"
            title="Delete"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button></Can>
        </div>
      ),
    },
  ];

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">PRODUCTION / SIZE CHARTS</p>
          <h1 className="text-2xl font-bold tracking-tight">Size Chart Master</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Reusable named size groups with a default quantity per size — load one from Style Creation instead of
            entering quantities from scratch on every style.
          </p>
        </div>
        <button
          onClick={() => { setEditingChart(null); setEditorOpen(true); }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: INDIGO }}
        >
          <Plus className="h-4 w-4" /> New Size Chart
        </button>
      </div>

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <DataTable columns={columns} data={(data ?? []) as (SizeChart & Record<string, unknown>)[]} loading={isLoading} emptyMessage="No size charts yet." />
      </div>

      {editorOpen && <ChartEditor chart={editingChart} onClose={() => setEditorOpen(false)} />}
    </div>
  );
}
