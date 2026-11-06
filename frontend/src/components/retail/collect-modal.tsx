"use client";
import Link from "next/link";
import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { ModalShell } from "@/components/shared/modal-shell";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { COLLECTION_MODES } from "@/components/retail/bill-editor";
import { RETAIL_ACCENT, newClientRef, rupees, type CreditRow } from "@/lib/retail";

const inputCls = "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

/** Take one payment from a customer; it settles their oldest-due credit bills first. */
export function CollectModal({ customerId, customerName, onClose }: { customerId: string; customerName: string; onClose: () => void }) {
  const qc = useQueryClient();
  const ref = useRef(newClientRef());
  const bills = useQuery({
    queryKey: ["retail-credit-register", "customer", customerId],
    queryFn: async () => (await api.get("/retail/credit/register", { params: { customer_id: customerId } })).data.data as CreditRow[],
  });
  const owed = (bills.data ?? []).reduce((s, b) => s + Number(b.outstanding), 0);
  const [amount, setAmount] = useState("");
  const [mode, setMode] = useState("cash");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [reference, setReference] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState<{ batch_ref: string; receipt_number: string; allocations: { invoice_number: string; amount: string }[] } | null>(null);

  // Show how the amount will be spread before saving.
  let left = Number(amount) || 0;
  const plan = (bills.data ?? []).map((b) => {
    const take = Math.min(left, Number(b.outstanding));
    left -= take;
    return { ...b, take };
  });

  const save = useMutation({
    mutationFn: async () => (await api.post(`/retail/customers/${customerId}/collect`, {
      client_ref: ref.current, amount: Number(amount), mode, payment_date: date, reference: reference || null,
    })).data.data,
    onSuccess: (d) => {
      setDone(d);
      ["retail-credit-register", "retail-credit-summary", "retail-credit-customers", "retail-collections", "retail-invoices", "retail-customer"]
        .forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
    },
    onError: (e: unknown) => setError(parseApiError(e, "Could not record this payment.")),
  });

  return (
    <ModalShell maxWidth="max-w-lg" onClose={onClose}>
      <div className="flex items-center justify-between px-5 py-4 border-b">
        <h2 className="font-semibold">Collect from {customerName}</h2>
        <button onClick={onClose} aria-label="Close"><X className="h-4 w-4" /></button>
      </div>
      {done ? (
        <div className="p-5 space-y-3">
          <p className="text-sm">Payment recorded — receipt <b>{done.receipt_number}</b>.</p>
          <ul className="text-sm space-y-1">
            {done.allocations.map((a) => <li key={a.invoice_number}>{a.invoice_number}: {rupees(a.amount)}</li>)}
          </ul>
          <div className="flex justify-end gap-2">
            <button onClick={onClose} className="px-4 py-2 rounded-xl border text-sm">Close</button>
            <Link href={`/sales/retail/receipts/${done.batch_ref}`} className="px-4 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: RETAIL_ACCENT }}>
              Print receipt
            </Link>
          </div>
        </div>
      ) : (
        <>
          <div className="p-5 space-y-3">
            <p className="text-sm text-muted-foreground">Owes <b className="text-foreground">{rupees(owed)}</b> on {(bills.data ?? []).length} bill{(bills.data ?? []).length === 1 ? "" : "s"}. Oldest due is settled first.</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted-foreground">Amount (₹)</label>
                <input type="number" min="1" step="0.01" className={inputCls} value={amount} onChange={(e) => setAmount(e.target.value)} />
                <button type="button" onClick={() => setAmount(owed.toFixed(2))} className="mt-1 text-[11px] font-semibold" style={{ color: RETAIL_ACCENT }}>Full amount</button>
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Received by</label>
                <SearchableSelect value={mode} onChange={(v) => setMode(v || "cash")} accent={RETAIL_ACCENT} options={COLLECTION_MODES} />
              </div>
              <div><label className="text-xs text-muted-foreground">Date</label><input type="date" className={inputCls} value={date} onChange={(e) => setDate(e.target.value)} /></div>
              <div><label className="text-xs text-muted-foreground">Reference</label><input className={inputCls} value={reference} onChange={(e) => setReference(e.target.value)} placeholder="UPI / cheque no." /></div>
            </div>
            {Number(amount) > 0 && (
              <table className="w-full text-xs">
                <tbody>
                  {plan.map((b) => (
                    <tr key={b.invoice_id} className="border-t border-border first:border-0">
                      <td className="py-1 pr-2">{b.invoice_number}</td>
                      <td className="py-1 pr-2 text-muted-foreground">due {b.due_date ?? "—"}{b.days_overdue > 0 ? ` · ${b.days_overdue}d overdue` : ""}</td>
                      <td className="py-1 pr-2 text-right tabular-nums">{rupees(b.outstanding)}</td>
                      <td className="py-1 text-right tabular-nums font-semibold">{b.take > 0 ? `− ${rupees(b.take)}` : ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {Number(amount) > owed + 0.001 && <p className="text-xs text-destructive">That&apos;s more than {customerName} owes.</p>}
            {error && <p className="text-xs text-destructive">{error}</p>}
          </div>
          <div className="flex justify-end gap-2 px-5 py-4 border-t">
            <button onClick={onClose} className="px-4 py-2 rounded-xl border text-sm">Cancel</button>
            <button onClick={() => { setError(""); save.mutate(); }} disabled={save.isPending || !(Number(amount) > 0) || Number(amount) > owed + 0.001}
              className="px-4 py-2 rounded-xl text-sm font-semibold text-white disabled:opacity-50" style={{ background: RETAIL_ACCENT }}>
              {save.isPending ? "Saving…" : "Record payment"}
            </button>
          </div>
        </>
      )}
    </ModalShell>
  );
}
