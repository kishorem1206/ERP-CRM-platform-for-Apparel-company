"use client";
import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Pencil, Trash2 } from "lucide-react";
import api from "@/lib/api";
import { ModalShell } from "@/components/shared/modal-shell";
import {
  INDIGO,
  fmt,
  QuoteSummary,
  QuoteStatusBadge,
  QuoteFormModal,
} from "./_components";
import { Can } from "@/lib/permissions";

const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "draft", label: "Draft" },
  { value: "sent", label: "Sent" },
  { value: "accepted", label: "Accepted" },
  { value: "declined", label: "Declined" },
  { value: "expired", label: "Expired" },
];

export default function QuotesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [showModal, setShowModal] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const { data: quotesData, isLoading } = useQuery({
    queryKey: ["crm-quotes", page, statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      if (statusFilter) params.set("status", statusFilter);
      const res = await api.get(`/crm/quotes?${params}`);
      return res.data;
    },
  });

  const [deleteError, setDeleteError] = useState("");

  const deleteMutation = useMutation({
    mutationFn: (quoteId: string) => api.delete(`/crm/quotes/${quoteId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-quotes"] });
      setDeleteError("");
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message;
      setDeleteError(msg ?? "Failed to delete quote.");
    },
  });

  const quotes: QuoteSummary[] = quotesData?.data ?? [];
  const total: number = quotesData?.meta?.total ?? 0;

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    if (!q) return quotes;
    return quotes.filter((quote) => quote.title.toLowerCase().includes(q));
  }, [quotes, search]);

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            CRM / QUOTES
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Quotes</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Proposals and quote tracking.
          </p>
        </div>
        <Can perm="crm.create"><button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: INDIGO }}
        >
          <Plus className="h-4 w-4" /> New Quote
        </button></Can>
      </div>

      {deleteError && (
        <p className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-xl px-4 py-2.5">
          {deleteError}
        </p>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            className="rounded-xl border border-input bg-background pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Search by title…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit flex-wrap">
          {STATUS_FILTERS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => { setStatusFilter(opt.value); setPage(1); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                statusFilter === opt.value
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              ALL QUOTES
            </p>
            <p className="text-sm font-medium mt-0.5">
              {total} record{total !== 1 ? "s" : ""}
            </p>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
            Loading…
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
            {search || statusFilter
              ? "No quotes match your filters."
              : "No quotes yet — click New Quote to create one."}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Quote #</th>
                  <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Title</th>
                  <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Lead</th>
                  <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Person / Org</th>
                  <th className="text-right px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Total</th>
                  <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Status</th>
                  <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Valid Until</th>
                  <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Created</th>
                  <th className="px-6 py-3 w-16" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map((q) => (
                  <tr
                    key={q.id}
                    onClick={() => router.push(`/crm/quotes/${q.id}`)}
                    className="hover:bg-muted/20 transition-colors cursor-pointer"
                  >
                    <td className="px-6 py-3 font-mono text-xs text-muted-foreground">
                      {q.quote_number}
                    </td>
                    <td className="px-6 py-3 font-medium">{q.title}</td>
                    <td className="px-6 py-3 text-muted-foreground">{q.lead_title ?? "—"}</td>
                    <td className="px-6 py-3 text-muted-foreground">
                      {q.person_name ?? q.org_name ?? "—"}
                    </td>
                    <td className="px-6 py-3 text-right font-medium tabular-nums">
                      {q.total_amount != null ? fmt(q.total_amount) : "—"}
                    </td>
                    <td className="px-6 py-3">
                      <QuoteStatusBadge status={q.status} />
                    </td>
                    <td className="px-6 py-3 text-muted-foreground text-xs">
                      {q.valid_until
                        ? new Date(q.valid_until).toLocaleDateString("en-IN", {
                            day: "2-digit",
                            month: "short",
                            year: "numeric",
                          })
                        : "—"}
                    </td>
                    <td className="px-6 py-3 text-muted-foreground text-xs">
                      {new Date(q.created_at).toLocaleDateString("en-IN", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                      })}
                    </td>
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-0.5">
                        <Can perm="crm.edit"><button
                          onClick={(e) => { e.stopPropagation(); router.push(`/crm/quotes/${q.id}`); }}
                          className="p-1 rounded transition-colors hover:bg-muted text-muted-foreground"
                          title="Edit quote"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button></Can>
                        <Can perm="crm.delete"><button
                          onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(q.id); }}
                          className="p-1 rounded transition-colors hover:bg-[#8174F5]/10 text-muted-foreground hover:text-[#8174F5]"
                          title="Delete quote"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button></Can>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {total > 50 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 rounded border border-input text-sm disabled:opacity-40"
          >
            Prev
          </button>
          <span className="text-sm text-muted-foreground self-center">Page {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={quotes.length < 50}
            className="px-3 py-1 rounded border border-input text-sm disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}

      {/* New Quote Modal */}
      {showModal && <QuoteFormModal onClose={() => setShowModal(false)} />}

      {confirmDeleteId && (
        <ModalShell maxWidth="max-w-xs" onClose={() => setConfirmDeleteId(null)}>
          <div className="p-6">
            <p className="text-sm font-medium mb-1">Delete this quote?</p>
            <p className="text-xs text-muted-foreground mb-5">This action cannot be undone.</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDeleteId(null)}
                className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  deleteMutation.mutate(confirmDeleteId);
                  setConfirmDeleteId(null);
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
    </div>
  );
}
