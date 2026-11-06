"use client";
import { useRef, useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, IndianRupee, X } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { Can } from "@/lib/permissions";
import { ModalShell } from "@/components/shared/modal-shell";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { PdfDocumentPage, fmtDate } from "@/components/documents/pdf-document-page";
import { COLLECTION_MODES } from "@/components/retail/bill-editor";
import { RETAIL_ACCENT, newClientRef, payStatusLabel, rupees, type RetailInvoice } from "@/lib/retail";

const actionCls = "inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-50";
const inputCls = "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

function PaymentModal({ invoice, onClose, onSaved }: { invoice: RetailInvoice; onClose: () => void; onSaved: () => void }) {
  const ref = useRef(newClientRef());
  const [amount, setAmount] = useState(String(Number(invoice.outstanding)));
  const [mode, setMode] = useState("cash");
  const [reference, setReference] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [error, setError] = useState("");
  const save = useMutation({
    mutationFn: () => api.post(`/retail/invoices/${invoice.id}/payments`, {
      client_ref: ref.current, amount: Number(amount), mode, reference: reference || null, payment_date: date,
    }),
    onSuccess: onSaved,
    onError: (e: unknown) => setError(parseApiError(e, "Could not record this payment.")),
  });
  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between px-5 py-4 border-b">
        <h2 className="font-semibold">Record payment — {invoice.invoice_number}</h2>
        <button onClick={onClose} aria-label="Close"><X className="h-4 w-4" /></button>
      </div>
      <div className="p-5 space-y-3">
        <p className="text-sm text-muted-foreground">Outstanding {rupees(invoice.outstanding)}</p>
        <div>
          <label className="text-xs text-muted-foreground">Amount (₹)</label>
          <input type="number" min="1" step="0.01" className={inputCls} value={amount} onChange={(e) => setAmount(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-muted-foreground">Received by</label>
            <SearchableSelect value={mode} onChange={(v) => setMode(v || "cash")} accent={RETAIL_ACCENT} options={COLLECTION_MODES} />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Date</label>
            <input type="date" className={inputCls} value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
        </div>
        <div>
          <label className="text-xs text-muted-foreground">Reference (UPI / cheque no.)</label>
          <input className={inputCls} value={reference} onChange={(e) => setReference(e.target.value)} />
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
      <div className="flex justify-end gap-2 px-5 py-4 border-t">
        <button onClick={onClose} className="px-4 py-2 rounded-xl border text-sm">Cancel</button>
        <button onClick={() => { setError(""); save.mutate(); }} disabled={save.isPending || !(Number(amount) > 0)}
          className="px-4 py-2 rounded-xl text-sm font-semibold text-white disabled:opacity-50" style={{ background: RETAIL_ACCENT }}>
          {save.isPending ? "Saving…" : "Record payment"}
        </button>
      </div>
    </ModalShell>
  );
}

export default function RetailInvoicePage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [paying, setPaying] = useState(false);
  const [version, setVersion] = useState(0);
  const [error, setError] = useState("");
  const { data, isLoading, isError } = useQuery({
    queryKey: ["retail-invoice", id],
    queryFn: async () => (await api.get(`/retail/invoices/${id}`)).data.data as RetailInvoice,
  });
  const refresh = () => {
    setVersion((v) => v + 1);
    qc.invalidateQueries({ queryKey: ["retail-invoice", id] });
    qc.invalidateQueries({ queryKey: ["retail-invoices"] });
  };
  const cancel = useMutation({
    mutationFn: (reason: string) => api.post(`/retail/invoices/${id}/cancel`, { reason }),
    onSuccess: () => { setError(""); refresh(); },
    onError: (e: unknown) => setError(parseApiError(e, "Could not cancel this bill.")),
  });
  const active = data?.status === "active";

  return (
    <>
      {paying && data && <PaymentModal invoice={data} onClose={() => setPaying(false)} onSaved={() => { setPaying(false); refresh(); }} />}
      <PdfDocumentPage
        title="Retail bill"
        number={data?.invoice_number}
        status={data ? (data.status === "cancelled" ? "Cancelled" : payStatusLabel(data.payment_status)) : undefined}
        backHref="/sales/retail/invoices"
        pdfPath={`/documents/retail-invoices/${id}/pdf${version ? `?v=${version}` : ""}`}
        downloadName={`RetailBill_${data?.invoice_number ?? id}.pdf`}
        loading={isLoading}
        error={isError}
        facts={[
          { label: "Customer", value: data ? (data.customer_name ? `${data.customer_name} · ${data.customer_mobile}` : "Walk-in") : null },
          { label: "Date", value: fmtDate(data?.invoice_date) },
          { label: "Total", value: data ? rupees(data.total_amount, 0) : null },
          { label: data?.payment_mode === "credit" ? "Outstanding" : "Payment", value: data ? (data.payment_mode === "credit" ? rupees(data.outstanding) : "Cash") : null },
        ]}
        actions={active ? (
          <>
            {Number(data?.outstanding) > 0 && (
              <Can perm="retail.collect">
                <button className={actionCls} style={{ color: RETAIL_ACCENT }} onClick={() => setPaying(true)}>
                  <IndianRupee className="h-4 w-4" /> Record payment
                </button>
              </Can>
            )}
            <Can perm="retail.manage">
              <button className={`${actionCls} text-destructive`} disabled={cancel.isPending}
                onClick={() => {
                  const reason = prompt("Why is this bill being cancelled? Its stock goes back and its payments are reversed.");
                  if (reason && reason.trim()) cancel.mutate(reason.trim());
                }}>
                <Ban className="h-4 w-4" /> Cancel bill
              </button>
            </Can>
          </>
        ) : undefined}
        extra={data && (
          <div className="space-y-3">
            {error && <p className="text-sm text-destructive">{error}</p>}
            {data.status === "cancelled" && (
              <p className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm">
                Cancelled — {data.cancel_reason}. Stock was returned to the warehouse.
              </p>
            )}
            {data.discount_approved && (
              <p className="text-xs text-amber-700 dark:text-amber-400">Discount above the usual maximum — approved when billed.</p>
            )}
            {data.payments.length > 0 && (
              <div className="rounded-2xl border border-border bg-card p-4">
                <p className="text-sm font-semibold mb-2">Payments</p>
                <table className="w-full text-sm">
                  <tbody>
                    {data.payments.map((p) => (
                      <tr key={p.id} className="border-t border-border first:border-0">
                        <td className="py-1.5 pr-3 font-mono text-xs">{p.receipt_number}</td>
                        <td className="py-1.5 pr-3">{fmtDate(p.payment_date)}</td>
                        <td className="py-1.5 pr-3 capitalize">{p.mode}{p.reference ? ` · ${p.reference}` : ""}</td>
                        <td className={`py-1.5 text-right tabular-nums ${p.status === "cancelled" ? "line-through text-muted-foreground" : ""}`}>{rupees(p.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      />
    </>
  );
}
