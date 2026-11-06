"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { ModalShell } from "@/components/shared/modal-shell";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { COLLECTION_MODES } from "@/components/retail/bill-editor";
import { RETAIL_ACCENT, newClientRef, rupees, type RetailInvoice } from "@/lib/retail";

/** Hand back some items from a bill: stock returns, the balance drops, any excess is refunded. */
export function ReturnModal({ invoice, onClose }: { invoice: RetailInvoice; onClose: () => void }) {
  const router = useRouter();
  const qc = useQueryClient();
  const ref = useRef(newClientRef());
  const [qty, setQty] = useState<Record<string, string>>({});
  const [reason, setReason] = useState("");
  const [refundMode, setRefundMode] = useState("cash");
  const [error, setError] = useState("");
  const left = (id: string, sold: string) => Number(sold) - Number(invoice.returned_qty?.[id] ?? 0);
  const value = invoice.items.reduce((t, i) => {
    const q = Math.min(Number(qty[i.id]) || 0, left(i.id, i.quantity));
    return t + (q > 0 ? (Number(i.net_amount) * q) / Number(i.quantity) : 0);
  }, 0);
  const owed = Number(invoice.outstanding);
  const refund = Math.max(0, value - owed);

  const save = useMutation({
    mutationFn: async () => (await api.post(`/retail/invoices/${invoice.id}/returns`, {
      client_ref: ref.current, reason, refund_mode: refundMode,
      items: invoice.items.filter((i) => Number(qty[i.id]) > 0).map((i) => ({ invoice_item_id: i.id, quantity: Number(qty[i.id]) })),
    })).data.data as { id: string },
    onSuccess: (r) => {
      ["retail-invoice", "retail-invoices", "retail-returns", "retail-credit-register", "retail-credit-summary", "retail-products"]
        .forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
      router.push(`/sales/retail/returns/${r.id}`);
    },
    onError: (e: unknown) => setError(parseApiError(e, "Could not save this return.")),
  });
  const anything = invoice.items.some((i) => Number(qty[i.id]) > 0);

  return (
    <ModalShell maxWidth="max-w-xl" onClose={onClose}>
      <div className="flex items-center justify-between px-5 py-4 border-b">
        <h2 className="font-semibold">Return items — {invoice.invoice_number}</h2>
        <button onClick={onClose} aria-label="Close"><X className="h-4 w-4" /></button>
      </div>
      <div className="p-5 space-y-3">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-muted-foreground border-b border-border">
            <th className="py-1.5 font-medium">Item</th><th className="py-1.5 font-medium text-right">Can return</th>
            <th className="py-1.5 font-medium text-right">Return qty</th><th className="py-1.5 font-medium text-right">Value</th>
          </tr></thead>
          <tbody>
            {invoice.items.map((i) => {
              const can = left(i.id, i.quantity);
              const q = Math.min(Number(qty[i.id]) || 0, can);
              return (
                <tr key={i.id} className="border-b border-border last:border-0">
                  <td className="py-2 pr-2">{i.description}<p className="text-[11px] text-muted-foreground">{rupees(i.net_amount)} for {Number(i.quantity)}</p></td>
                  <td className="py-2 pr-2 text-right">{can}</td>
                  <td className="py-2 pr-2 text-right">
                    <input type="number" min="0" max={can} step="1" disabled={can <= 0} value={qty[i.id] ?? ""} placeholder="0"
                      onChange={(e) => setQty((x) => ({ ...x, [i.id]: e.target.value }))}
                      className="w-20 rounded-lg border border-input bg-background px-2 py-1 text-right text-sm disabled:opacity-40" />
                  </td>
                  <td className="py-2 text-right tabular-nums">{q > 0 ? rupees((Number(i.net_amount) * q) / Number(i.quantity)) : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div>
          <label className="text-xs text-muted-foreground">Reason *</label>
          <input className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Size didn't fit" />
        </div>
        {value > 0 && (
          <div className="rounded-xl bg-muted/40 px-3 py-2 text-sm space-y-0.5">
            <p>Return value <b>{rupees(value)}</b></p>
            {owed > 0 && <p className="text-xs text-muted-foreground">{rupees(Math.min(value, owed))} comes off what they still owe ({rupees(owed)}).</p>}
            {refund > 0 && <p className="text-xs">Refund <b>{rupees(refund)}</b> to the customer.</p>}
          </div>
        )}
        {refund > 0 && (
          <div className="w-48">
            <label className="text-xs text-muted-foreground">Refund by</label>
            <SearchableSelect value={refundMode} onChange={(v) => setRefundMode(v || "cash")} accent={RETAIL_ACCENT} options={COLLECTION_MODES} />
          </div>
        )}
        {invoice.points_earned > 0 && <p className="text-[11px] text-muted-foreground">Points earned on this bill are reduced in proportion.</p>}
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
      <div className="flex justify-end gap-2 px-5 py-4 border-t">
        <button onClick={onClose} className="px-4 py-2 rounded-xl border text-sm">Cancel</button>
        <button onClick={() => { setError(""); save.mutate(); }} disabled={save.isPending || !anything || reason.trim().length < 3}
          className="px-4 py-2 rounded-xl text-sm font-semibold text-white disabled:opacity-50" style={{ background: RETAIL_ACCENT }}>
          {save.isPending ? "Saving…" : "Save return"}
        </button>
      </div>
    </ModalShell>
  );
}
