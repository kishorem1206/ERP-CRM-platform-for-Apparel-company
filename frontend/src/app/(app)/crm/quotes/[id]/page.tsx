"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, Pencil, Copy, Send, CheckCircle2, XCircle, ShoppingCart, Trash2,
} from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import { ModalShell } from "@/components/shared/modal-shell";
import { ModalPortal } from "@/components/shared/modal-portal";
import { QuoteFormModal, QuoteStatusBadge } from "../_components";
import type { QuoteFull, QuoteLineItem } from "../_components";
import { Can } from "@/lib/permissions";

// ── Palette ───────────────────────────────────────────────────────────────────
const INDIGO = "#0049A7";

const fmt = (v: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(v);

// ── Toast ─────────────────────────────────────────────────────────────────────
function Toast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <ModalPortal>
      <div className="fixed bottom-6 right-6 z-[60] flex items-center gap-3 bg-foreground text-background rounded-2xl shadow-2xl px-5 py-3 text-sm font-medium">
        {message}
        <button
          onClick={onDismiss}
          className="opacity-60 hover:opacity-100 transition-opacity text-xs"
        >
          ✕
        </button>
      </div>
    </ModalPortal>
  );
}

// ── Line Items Table (read-only) ───────────────────────────────────────────────
function LineItemsTable({ items }: { items: QuoteLineItem[] }) {
  const subtotal = items.reduce((s, it) => {
    return s + it.quantity * it.unit_price * (1 - it.discount_percent / 100);
  }, 0);

  return (
    <div className="border border-border rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              <th className="text-left px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Name
              </th>
              <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Qty
              </th>
              <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Unit Price
              </th>
              <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Disc %
              </th>
              <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Total
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {items.map((it, i) => {
              const rowTotal = it.quantity * it.unit_price * (1 - it.discount_percent / 100);
              return (
                <tr key={it.id ?? i} className="hover:bg-muted/10 transition-colors">
                  <td className="px-4 py-2.5 font-medium">{it.name}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-muted-foreground">
                    {it.quantity}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-muted-foreground">
                    {fmt(it.unit_price)}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-muted-foreground">
                    {it.discount_percent > 0 ? `${it.discount_percent}%` : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums font-medium">
                    {fmt(rowTotal)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {/* Footer */}
      <div className="border-t border-border bg-muted/20 px-4 py-3">
        <div className="flex justify-end">
          <div className="space-y-1 min-w-[200px]">
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>Subtotal</span>
              <span className="tabular-nums">{fmt(subtotal)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Detail Row ────────────────────────────────────────────────────────────────
function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[140px_1fr] gap-2 py-2.5 border-b border-border last:border-0">
      <dt className="text-xs font-medium text-muted-foreground self-start pt-0.5">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function QuoteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [showEdit, setShowEdit] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 4000);
  }

  // ── Data fetch ───────────────────────────────────────────────────────────
  const { data: quoteData, isLoading } = useQuery({
    queryKey: ["crm-quote", id],
    queryFn: async () => {
      const res = await api.get(`/crm/quotes/${id}`);
      return res.data;
    },
  });

  const quote: QuoteFull | null = quoteData?.data ?? null;

  // ── Status mutation ──────────────────────────────────────────────────────
  const statusMutation = useMutation({
    mutationFn: (status: string) =>
      api.patch(`/crm/quotes/${id}/status`, { status }),
    onSuccess: (_data, status) => {
      queryClient.invalidateQueries({ queryKey: ["crm-quote", id] });
      queryClient.invalidateQueries({ queryKey: ["crm-quotes"] });
      if (status === "accepted") {
        showToast("Sales Order flow coming in Phase 3");
      }
    },
  });

  // ── Duplicate mutation ────────────────────────────────────────────────────
  const duplicateMutation = useMutation({
    mutationFn: () => api.post(`/crm/quotes/${id}/duplicate`),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["crm-quotes"] });
      const newId = res.data?.data?.id;
      if (newId) {
        router.push(`/crm/quotes/${newId}`);
      } else {
        showToast("Quote duplicated successfully.");
      }
    },
  });

  // ── Delete mutation ───────────────────────────────────────────────────────
  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/crm/quotes/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-quotes"] });
      router.push("/crm/quotes");
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message;
      showToast(msg ?? "Failed to delete quote.");
    },
  });

  // ── Loading / error states ────────────────────────────────────────────────
  if (isLoading) {
    return <div className="p-8 text-sm text-muted-foreground">Loading…</div>;
  }
  if (!quote) {
    return <div className="p-8 text-sm text-muted-foreground">Quote not found.</div>;
  }

  const status = quote.status;
  const isTerminal = status === "accepted" || status === "declined";

  // ── Totals ────────────────────────────────────────────────────────────────
  const subtotal = (quote.items ?? []).reduce(
    (s, it) => s + it.quantity * it.unit_price * (1 - it.discount_percent / 100),
    0
  );
  const discountAmount = subtotal * ((quote.discount_percent ?? 0) / 100);
  const total = subtotal - discountAmount;

  return (
    <div className="p-8 space-y-8">
      {/* Back */}
      <button
        onClick={() => router.push("/crm/quotes")}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" /> Back to Quotes
      </button>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            CRM / QUOTES
          </p>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="font-mono text-sm text-muted-foreground">{quote.quote_number}</span>
            <h1 className="text-2xl font-bold tracking-tight">{quote.title}</h1>
            <QuoteStatusBadge status={status} />
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Status actions */}
          {status === "draft" && (
            <Can perm="crm.edit"><button
              onClick={() => statusMutation.mutate("sent")}
              disabled={statusMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-[#0049A7] hover:bg-[#003D80] transition-colors disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              {statusMutation.isPending ? "Updating…" : "Mark as Sent"}
            </button></Can>
          )}
          {status === "sent" && (
            <>
              <Can perm="crm.edit"><button
                onClick={() => statusMutation.mutate("accepted")}
                disabled={statusMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-[#0049A7] hover:bg-[#003D80] transition-colors disabled:opacity-50"
              >
                <CheckCircle2 className="h-4 w-4" />
                Mark Accepted
              </button></Can>
              <Can perm="crm.edit"><button
                onClick={() => statusMutation.mutate("declined")}
                disabled={statusMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-[#1D0DB0] hover:bg-[#170a8f] transition-colors disabled:opacity-50"
              >
                <XCircle className="h-4 w-4" />
                Mark Declined
              </button></Can>
            </>
          )}
          {status === "accepted" && (
            <Can perm="crm.edit"><button
              onClick={() => statusMutation.mutate("accepted")}
              disabled={statusMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-colors disabled:opacity-50"
              style={{ background: INDIGO }}
            >
              <ShoppingCart className="h-4 w-4" />
              Convert to Sales Order
            </button></Can>
          )}

          {/* Always visible: Duplicate */}
          <Can perm="crm.create"><button
            onClick={() => duplicateMutation.mutate()}
            disabled={duplicateMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border border-input hover:bg-muted transition-colors disabled:opacity-50"
          >
            <Copy className="h-4 w-4" />
            {duplicateMutation.isPending ? "Duplicating…" : "Duplicate"}
          </button></Can>

          {/* Edit — disabled if terminal */}
          <Can perm="crm.edit"><button
            onClick={() => !isTerminal && setShowEdit(true)}
            disabled={isTerminal}
            title={isTerminal ? "Cannot edit an accepted or declined quote" : "Edit quote"}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border border-input hover:bg-muted transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Pencil className="h-4 w-4" />
            Edit
          </button></Can>

          <Can perm="crm.delete"><button
            onClick={() => setConfirmDelete(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-[#1D0DB0] border border-[#1D0DB0]/30 hover:bg-[#1D0DB0]/10 transition-colors"
          >
            <Trash2 className="h-4 w-4" />
            Delete
          </button></Can>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Left — Details */}
        <div className="lg:col-span-2">
          <div className="bg-card border border-border rounded-2xl p-6">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-4">
              Details
            </p>
            <dl>
              <DetailRow label="Lead">
                {quote.lead_id ? (
                  <Link
                    href={`/crm/leads/${quote.lead_id}`}
                    className="font-medium hover:underline transition-colors"
                    style={{ color: INDIGO }}
                  >
                    {quote.lead_title ?? "View Lead"}
                  </Link>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </DetailRow>

              <DetailRow label="Person">
                {quote.person_name ? (
                  <span>{quote.person_name}</span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </DetailRow>

              <DetailRow label="Organization">
                {quote.org_name ? (
                  <span>{quote.org_name}</span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </DetailRow>

              <DetailRow label="Valid Until">
                {quote.valid_until ? (
                  new Date(quote.valid_until).toLocaleDateString("en-IN", {
                    day: "2-digit",
                    month: "long",
                    year: "numeric",
                  })
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </DetailRow>

              <DetailRow label="Quote Discount">
                {quote.discount_percent > 0
                  ? `${quote.discount_percent}%`
                  : <span className="text-muted-foreground">—</span>}
              </DetailRow>

              <DetailRow label="Assigned To">
                {quote.assigned_to_name ?? (
                  <span className="text-muted-foreground">—</span>
                )}
              </DetailRow>

              {quote.notes && (
                <DetailRow label="Notes">
                  <p className="whitespace-pre-wrap leading-relaxed">{quote.notes}</p>
                </DetailRow>
              )}

              {quote.terms && (
                <DetailRow label="Terms">
                  <p className="whitespace-pre-wrap leading-relaxed">{quote.terms}</p>
                </DetailRow>
              )}
            </dl>
          </div>
        </div>

        {/* Right — Line Items */}
        <div className="lg:col-span-3 space-y-4">
          <div className="bg-card border border-border rounded-2xl p-6">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-4">
              Line Items
            </p>

            {quote.items && quote.items.length > 0 ? (
              <>
                <LineItemsTable items={quote.items} />

                {/* Summary footer */}
                <div className="mt-4 border border-border rounded-xl px-4 py-3 space-y-1.5 bg-muted/10">
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>Subtotal</span>
                    <span className="tabular-nums">{fmt(subtotal)}</span>
                  </div>
                  {quote.discount_percent > 0 && (
                    <div className="flex justify-between text-sm text-muted-foreground">
                      <span>Discount ({quote.discount_percent}%)</span>
                      <span className="tabular-nums text-[#8174F5]">-{fmt(discountAmount)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-base font-semibold pt-1.5 border-t border-border">
                    <span>Total</span>
                    <span className="tabular-nums" style={{ color: INDIGO }}>
                      {fmt(total)}
                    </span>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">No line items.</p>
            )}
          </div>
        </div>
      </div>

      {/* Edit Modal */}
      {showEdit && (
        <QuoteFormModal quote={quote} onClose={() => setShowEdit(false)} />
      )}

      {confirmDelete && (
        <ModalShell maxWidth="max-w-xs" onClose={() => setConfirmDelete(false)}>
          <div className="p-6">
            <p className="text-sm font-medium mb-1">Delete this quote?</p>
            <p className="text-xs text-muted-foreground mb-5">This action cannot be undone.</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDelete(false)}
                className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  deleteMutation.mutate();
                  setConfirmDelete(false);
                }}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 text-sm rounded-xl text-white font-semibold bg-[#1D0DB0] hover:bg-[#170a8f] transition-colors disabled:opacity-50"
              >
                Delete
              </button>
            </div>
          </div>
        </ModalShell>
      )}

      {/* Toast */}
      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </div>
  );
}
