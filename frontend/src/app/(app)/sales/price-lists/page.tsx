"use client";
import Link from "next/link";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, ChevronDown, ChevronRight, History } from "lucide-react";
import api from "@/lib/api";
import { ModalShell } from "@/components/shared/modal-shell";
import { PriceListItemModal, PriceListItemEntry } from "@/components/sales/price-list-item-modal";
import { DatePicker } from "@/components/shared/date-picker";
import { Can } from "@/lib/permissions";

const INDIGO = "#0049A7";
const inputCls =
  "w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

interface PriceListSummary {
  id: string;
  name: string;
  is_default: boolean;
  valid_from: string | null;
  valid_to: string | null;
  item_count: number;
}

const fmt = (v: unknown) => `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

export default function PriceListsPage() {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<PriceListSummary | undefined>(undefined);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["price-lists"],
    queryFn: () => api.get("/sales/price-lists").then((r) => r.data),
  });
  const lists: PriceListSummary[] = data?.data ?? [];

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/sales/price-lists/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["price-lists"] }),
  });

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / CATALOGUE</p>
          <h1 className="text-2xl font-bold tracking-tight">Price Lists</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Catalogue and customer-specific pricing, assigned to customers and used in CRM quotes.
          </p>
        </div>
        <Can perm="master_data.create"><button
          onClick={() => { setEditing(undefined); setShowCreate(true); }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: INDIGO }}
        >
          <Plus className="h-4 w-4" /> New Price List
        </button></Can>
      </div>

      <div className="space-y-4">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : lists.length === 0 ? (
          <div className="bg-card border border-border rounded-2xl p-10 text-center">
            <p className="text-sm text-muted-foreground">No price lists yet — click New Price List to create one.</p>
          </div>
        ) : (
          lists.map((pl) => (
            <div key={pl.id} className="bg-card border border-border rounded-2xl overflow-hidden">
              <button
                onClick={() => setExpanded(expanded === pl.id ? null : pl.id)}
                className="w-full flex items-center justify-between px-6 py-4 hover:bg-muted/20 transition-colors text-left"
              >
                <div className="flex items-center gap-3">
                  {expanded === pl.id ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                  <div>
                    <div className="flex items-center gap-2">
                      <Link href={`/sales/price-lists/${pl.id}`} className="font-semibold hover:underline">{pl.name}</Link>
                      {pl.is_default && (
                        <span className="text-[11px] font-bold px-2 py-0.5 rounded" style={{ background: `${INDIGO}18`, color: INDIGO }}>
                          Default
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {pl.item_count} price{pl.item_count !== 1 ? "s" : ""}
                      {pl.valid_from || pl.valid_to ? ` · ${pl.valid_from ?? "…"} → ${pl.valid_to ?? "…"}` : ""}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                  <Can perm="master_data.edit"><button
                    onClick={() => { setEditing(pl); setShowCreate(true); }}
                    className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button></Can>
                  <Can perm="master_data.delete"><button
                    onClick={() => setConfirmDeleteId(pl.id)}
                    className="p-1.5 rounded-lg hover:bg-violet-50 transition-colors text-muted-foreground hover:text-violet-500"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button></Can>
                </div>
              </button>
              {expanded === pl.id && <PriceListItems priceListId={pl.id} />}
            </div>
          ))
        )}
      </div>

      {showCreate && (
        <PriceListFormModal initial={editing} onClose={() => { setShowCreate(false); setEditing(undefined); }} />
      )}

      {confirmDeleteId && (
        <ModalShell maxWidth="max-w-xs" onClose={() => setConfirmDeleteId(null)}>
          <div className="p-6">
            <p className="text-sm font-medium mb-1">Delete this price list?</p>
            <p className="text-xs text-muted-foreground mb-5">
              This can&rsquo;t be undone. Lists assigned to customers can&rsquo;t be deleted.
            </p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setConfirmDeleteId(null)} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
                Cancel
              </button>
              <button
                onClick={() => { deleteMutation.mutate(confirmDeleteId); setConfirmDeleteId(null); }}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 text-sm rounded-xl text-white font-semibold bg-violet-500 hover:bg-violet-600 transition-colors disabled:opacity-50"
              >
                Delete
              </button>
            </div>
          </div>
        </ModalShell>
      )}
    </div>
  );
}

function PriceListItems({ priceListId }: { priceListId: string }) {
  const queryClient = useQueryClient();
  const [showItemModal, setShowItemModal] = useState(false);
  const [editingItem, setEditingItem] = useState<PriceListItemEntry | undefined>(undefined);
  const [historyFor, setHistoryFor] = useState<{ productId: string; variantId: string | null } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["price-list-items", priceListId],
    queryFn: () => api.get(`/sales/price-lists/${priceListId}/items`).then((r) => r.data),
  });
  const items: (PriceListItemEntry & { product_name: string | null; variant_sku: string | null; customer_name: string | null })[] = data?.data ?? [];

  const deleteItemMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/sales/price-lists/items/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["price-list-items", priceListId] }),
  });

  return (
    <div className="border-t border-border">
      <div className="flex items-center justify-between px-6 py-3 bg-muted/10">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Prices</p>
        <Can perm="master_data.create"><button
          onClick={() => { setEditingItem(undefined); setShowItemModal(true); }}
          className="flex items-center gap-1.5 text-xs font-semibold hover:underline"
          style={{ color: INDIGO }}
        >
          <Plus className="h-3.5 w-3.5" /> Add Price
        </button></Can>
      </div>
      {isLoading ? (
        <p className="px-6 py-4 text-sm text-muted-foreground">Loading…</p>
      ) : items.length === 0 ? (
        <p className="px-6 py-6 text-sm text-muted-foreground text-center">No prices in this list yet.</p>
      ) : (
        <div className="divide-y divide-border">
          {items.map((it) => (
            <div key={it.id} className="flex items-center justify-between px-6 py-3">
              <div>
                <p className="text-sm font-medium">
                  {it.product_name}
                  {it.variant_sku && <span className="text-muted-foreground"> · {it.variant_sku}</span>}
                </p>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  {it.customer_name ? `For ${it.customer_name}` : "All customers on this list"}
                  {" · "}Min qty {it.min_quantity}
                  {it.max_quantity ? `–${it.max_quantity}` : "+"}
                  {(it.valid_from || it.valid_to) && ` · ${it.valid_from ?? "…"} → ${it.valid_to ?? "…"}`}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold tabular-nums">{fmt(it.unit_price)}</span>
                <button
                  onClick={() => setHistoryFor({ productId: it.product_id, variantId: it.variant_id })}
                  title="Price history"
                  className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                >
                  <History className="h-3.5 w-3.5" />
                </button>
                <Can perm="master_data.edit"><button
                  onClick={() => { setEditingItem(it); setShowItemModal(true); }}
                  className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button></Can>
                <Can perm="master_data.delete"><button
                  onClick={() => deleteItemMutation.mutate(it.id)}
                  className="p-1.5 rounded-lg hover:bg-violet-50 transition-colors text-muted-foreground hover:text-violet-500"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button></Can>
              </div>
            </div>
          ))}
        </div>
      )}

      {showItemModal && (
        <PriceListItemModal priceListId={priceListId} initial={editingItem} onClose={() => { setShowItemModal(false); setEditingItem(undefined); }} />
      )}
      {historyFor && <PriceHistoryModal productId={historyFor.productId} variantId={historyFor.variantId} onClose={() => setHistoryFor(null)} />}
    </div>
  );
}

function PriceHistoryModal({ productId, variantId, onClose }: { productId: string; variantId: string | null; onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["price-history", productId, variantId],
    queryFn: () => api.get("/sales/price-history", { params: { product_id: productId, variant_id: variantId || undefined } }).then((r) => r.data),
  });
  const rows: { id: string; old_price: string | null; new_price: string; changed_by_name: string | null; changed_at: string }[] = data?.data ?? [];

  return (
    <ModalShell maxWidth="max-w-md" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Price History</h2>
      </div>
      <div className="p-6">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-6">No price changes recorded yet.</p>
        ) : (
          <div className="rounded-xl border border-border divide-y divide-border">
            {rows.map((r) => (
              <div key={r.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                <div>
                  <p>
                    {r.old_price ? `${fmt(r.old_price)} → ` : "Set to "}
                    <span className="font-semibold">{fmt(r.new_price)}</span>
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    {new Date(r.changed_at).toLocaleString("en-IN")} {r.changed_by_name ? `· ${r.changed_by_name}` : ""}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="flex justify-end p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Close
        </button>
      </div>
    </ModalShell>
  );
}

function PriceListFormModal({ initial, onClose }: { initial?: PriceListSummary; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(initial?.name ?? "");
  const [isDefault, setIsDefault] = useState(initial?.is_default ?? false);
  const [validFrom, setValidFrom] = useState(initial?.valid_from ?? "");
  const [validTo, setValidTo] = useState(initial?.valid_to ?? "");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: async () => {
      const payload = { name, is_default: isDefault, valid_from: validFrom || undefined, valid_to: validTo || undefined };
      if (initial) {
        await api.patch(`/sales/price-lists/${initial.id}`, payload);
      } else {
        await api.post("/sales/price-lists", payload);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["price-lists"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Failed to save");
    },
  });

  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">{initial ? "Edit Price List" : "New Price List"}</h2>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Name <span className="text-destructive">*</span>
          </label>
          <input className={inputCls} placeholder="e.g. Wholesale 2026" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} />
          Default price list
        </label>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Valid From</label>
            <DatePicker value={validFrom} onChange={(v) => setValidFrom(v)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Valid To</label>
            <DatePicker value={validTo} onChange={(v) => setValidTo(v)} />
          </div>
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => { setError(""); mutation.mutate(); }}
          disabled={!name.trim() || mutation.isPending}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </ModalShell>
  );
}
