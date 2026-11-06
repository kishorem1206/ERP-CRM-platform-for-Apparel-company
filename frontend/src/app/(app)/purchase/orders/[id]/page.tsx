"use client";
import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Lock, PackageCheck, XCircle } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { Can, usePermissions } from "@/lib/permissions";
import { PdfDocumentPage, fmtDate, money } from "@/components/documents/pdf-document-page";
import { PO_STATUS_LABEL, fmtQty, lineState, rangeText, type LineState } from "@/lib/po-tolerance";

const actionCls =
  "inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-50";
const inputCls =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

interface POItem {
  id: string;
  product_id: string;
  product_name: string | null;
  unit_id: string;
  unit_name: string | null;
  ordered_qty: string;
  received_qty: string;
  tolerance_pct: string | null;
}

interface PO {
  id: string;
  po_number: string;
  status: string;
  vendor_name: string | null;
  order_date: string;
  expected_date: string | null;
  total_amount: string;
  close_reason: string | null;
  close_requested_by_name: string | null;
  close_requested_at: string | null;
  closed_by_name: string | null;
  closed_at: string | null;
  items: POItem[];
}

const STATE_CHIP: Record<LineState, { label: string; cls: string }> = {
  within: { label: "Within range", cls: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300" },
  short: { label: "Short", cls: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300" },
  over: { label: "Over", cls: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300" },
};

const when = (iso: string | null) => (iso ? fmtDate(iso.slice(0, 10)) : "");

/** Ordered vs received per line against its tolerance, with closing and
 *  the admin's approval. Internal only — none of this is on the PDF. */
function ReceiptPanel({ po, onChanged }: { po: PO; onChanged: () => void }) {
  const { can } = usePermissions();
  const [reason, setReason] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const act = useMutation({
    mutationFn: ({ path, body }: { path: string; body?: object }) => api.post(`/purchase/orders/${po.id}/${path}`, body ?? {}),
    onSuccess: (res) => {
      setError("");
      setAsking(false);
      setReason("");
      setNote(res.data.message ?? "");
      onChanged();
    },
    onError: (e: unknown) => setError(parseApiError(e, "Could not update this PO.")),
  });

  const lines = po.items.map((it) => {
    const ordered = Number(it.ordered_qty);
    const received = Number(it.received_qty);
    return { it, ordered, received, state: lineState(ordered, received, it.tolerance_pct) };
  });
  const allWithin = lines.every((l) => l.state === "within");
  const canApproveClose = can("purchase.po_close_approve");
  const open = po.status === "approved" || po.status === "partial";

  function close() {
    setNote("");
    if (allWithin || canApproveClose) {
      const msg = allWithin
        ? "Close this PO? No more goods will be received against it."
        : "Some lines are outside their tolerance. Close this PO anyway (as admin)?";
      if (confirm(msg)) act.mutate({ path: "close", body: { reason: reason || null } });
    } else {
      setAsking(true);
    }
  }

  if (po.status === "draft" || po.status === "cancelled") return null;

  return (
    <div className="rounded-2xl border border-border bg-card">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3">
        <div>
          <p className="text-sm font-semibold">Receipt against order</p>
          <p className="text-xs text-muted-foreground">Tolerance and approvals are internal — they are not printed on the PO.</p>
        </div>
        {open && (
          <Can perm="purchase.edit">
            <button className={actionCls} onClick={close} disabled={act.isPending}>
              <Lock className="h-4 w-4" /> Close PO
            </button>
          </Can>
        )}
      </div>

      {po.status === "close_requested" && (
        <div className="mx-5 mt-4 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-800 dark:bg-amber-950/30">
          <p className="font-semibold text-amber-900 dark:text-amber-200">Waiting for an admin to approve closing this PO</p>
          <p className="mt-1 text-amber-900/80 dark:text-amber-200/80">
            {po.close_reason}
            {po.close_requested_by_name && ` — ${po.close_requested_by_name}`}
            {po.close_requested_at && `, ${when(po.close_requested_at)}`}
          </p>
          {canApproveClose && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button className={actionCls} style={{ color: "#0049A7" }} disabled={act.isPending}
                onClick={() => act.mutate({ path: "close/approve" })}>
                <CheckCircle2 className="h-4 w-4" /> Approve &amp; close
              </button>
              <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason for rejecting (optional)"
                className={`${inputCls} max-w-xs`} />
              <button className={`${actionCls} text-destructive`} disabled={act.isPending}
                onClick={() => act.mutate({ path: "close/reject", body: { reason: reason || null } })}>
                <XCircle className="h-4 w-4" /> Reject
              </button>
            </div>
          )}
        </div>
      )}

      {asking && (
        <div className="mx-5 mt-4 rounded-xl border border-border bg-muted/30 p-4 text-sm space-y-2">
          <p className="font-semibold">Some lines are outside their tolerance, so an admin has to approve closing.</p>
          <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2} autoFocus
            placeholder="Why close it now? e.g. Vendor can't supply the rest" className={`${inputCls} resize-none`} />
          <div className="flex justify-end gap-2">
            <button className="px-4 py-1.5 rounded-lg border border-input text-sm hover:bg-muted" onClick={() => setAsking(false)}>Cancel</button>
            <button className="px-4 py-1.5 rounded-lg bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-60"
              disabled={act.isPending || !reason.trim()} onClick={() => act.mutate({ path: "close", body: { reason } })}>
              {act.isPending ? "Sending…" : "Send for admin approval"}
            </button>
          </div>
        </div>
      )}

      {po.status === "closed" && (
        <p className="mx-5 mt-4 text-xs text-muted-foreground">
          Closed{po.closed_by_name && ` by ${po.closed_by_name}`}{po.closed_at && ` on ${when(po.closed_at)}`}
          {po.close_reason && ` — ${po.close_reason}`}
        </p>
      )}
      {open && po.close_reason?.startsWith("Close rejected") && (
        <p className="mx-5 mt-4 text-xs text-amber-700 dark:text-amber-400">{po.close_reason}</p>
      )}
      {(note || error) && (
        <p className={`mx-5 mt-3 text-xs ${error ? "text-destructive" : "text-muted-foreground"}`}>{error || note}</p>
      )}

      <div className="overflow-x-auto p-5 pt-4">
        <table className="w-full min-w-[620px] text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted-foreground">
              <th className="py-2 pr-3 font-medium">Product</th>
              <th className="py-2 pr-3 text-right font-medium">Ordered</th>
              <th className="py-2 pr-3 text-right font-medium">Received</th>
              <th className="py-2 pr-3 text-right font-medium">Tolerance</th>
              <th className="py-2 pr-3 text-right font-medium">Allowed range</th>
              <th className="py-2 text-right font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {lines.map(({ it, ordered, received, state }) => (
              <tr key={it.id} className="border-b border-border last:border-0">
                <td className="py-2 pr-3">{it.product_name ?? "—"}</td>
                <td className="py-2 pr-3 text-right tabular-nums">{fmtQty(ordered)} {it.unit_name ?? ""}</td>
                <td className="py-2 pr-3 text-right tabular-nums">{fmtQty(received)}</td>
                <td className="py-2 pr-3 text-right tabular-nums">{Number(it.tolerance_pct) ? `±${Number(it.tolerance_pct)}%` : "—"}</td>
                <td className="py-2 pr-3 text-right tabular-nums text-muted-foreground">{rangeText(ordered, it.tolerance_pct, it.unit_name ?? undefined)}</td>
                <td className="py-2 text-right">
                  <span className={`inline-flex rounded px-2 py-0.5 text-[11px] font-bold ${STATE_CHIP[state].cls}`}>{STATE_CHIP[state].label}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [actionError, setActionError] = useState("");
  const [pdfVersion, setPdfVersion] = useState(0);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["doc-purchase-order", id],
    queryFn: () => api.get(`/purchase/orders/${id}`).then((r) => r.data.data as PO),
  });

  const refresh = () => {
    setPdfVersion((v) => v + 1);
    qc.invalidateQueries({ queryKey: ["doc-purchase-order", id] });
    qc.invalidateQueries({ queryKey: ["purchase-orders"] });
  };

  // Draft → approved opens the PO for GRNs; draft/approved → cancelled closes it.
  const statusAction = useMutation({
    mutationFn: (action: "approve" | "cancel") => api.post(`/purchase/orders/${id}/${action}`),
    onSuccess: () => {
      setActionError("");
      refresh();
    },
    onError: (e: unknown) => setActionError(parseApiError(e, "Could not update this PO.")),
  });

  const status: string | undefined = data?.status;

  return (
    <PdfDocumentPage
      title="Purchase order"
      number={data?.po_number}
      status={status ? PO_STATUS_LABEL[status] ?? status : status}
      backHref="/purchase/orders"
      pdfPath={`/documents/purchase-orders/${id}/pdf${pdfVersion ? `?v=${pdfVersion}` : ""}`}
      pdfFields={[{ key: "date", label: "Order date" }, { key: "expected_date", label: "Expected date" }]}
      downloadName={`PurchaseOrder_${data?.po_number ?? id}.pdf`}
      loading={isLoading}
      error={isError}
      facts={[
        { label: "Vendor", value: data?.vendor_name },
        { label: "Order date", value: fmtDate(data?.order_date) },
        { label: "Expected date", value: fmtDate(data?.expected_date ?? undefined) },
        { label: "Total", value: money(data?.total_amount) }
      ]}
      actions={
        <>
          {status === "draft" && (
            <Can perm="purchase.approve">
              <button className={actionCls} style={{ color: "#0049A7" }} disabled={statusAction.isPending}
                onClick={() => statusAction.mutate("approve")}>
                <CheckCircle2 className="h-4 w-4" /> Approve
              </button>
            </Can>
          )}
          {(status === "approved" || status === "partial") && (
            <Can perm="purchase.create">
              <Link href="/purchase/grn" className={actionCls}>
                <PackageCheck className="h-4 w-4" /> Receive goods (GRN)
              </Link>
            </Can>
          )}
          {(status === "draft" || status === "approved") && (
            <Can perm="purchase.edit">
              <button className={`${actionCls} text-destructive`} disabled={statusAction.isPending}
                onClick={() => { if (confirm("Cancel this purchase order?")) statusAction.mutate("cancel"); }}>
                <XCircle className="h-4 w-4" /> Cancel PO
              </button>
            </Can>
          )}
        </>
      }
      extra={
        <>
          {actionError && <p className="text-sm text-destructive">{actionError}</p>}
          {data && <ReceiptPanel po={data} onChanged={refresh} />}
        </>
      }
    />
  );
}
