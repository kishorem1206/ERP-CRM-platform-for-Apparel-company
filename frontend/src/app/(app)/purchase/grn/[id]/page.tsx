"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, X } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { Can } from "@/lib/permissions";
import { ModalPortal } from "@/components/shared/modal-portal";
import { DatePicker } from "@/components/shared/date-picker";
import { PdfDocumentPage, fmtDate, money } from "@/components/documents/pdf-document-page";

const actionCls =
  "inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-50";
const inputCls =
  "w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
const cellInputCls =
  "w-20 rounded border border-input bg-background px-1.5 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-ring";

interface GRNLine {
  id: string;
  product_id: string;
  unit_id: string;
  received_qty: string;
  rejected_qty: string;
  accepted_qty: string;
  unit_price: string;
}

interface GRN {
  id: string;
  entry_number: string;
  status: string;
  vendor_name: string | null;
  entry_date: string;
  invoice_number: string | null;
  invoice_date: string | null;
  notes: string | null;
  total_amount: string;
  items: GRNLine[];
}

const num = (v: string) => parseFloat(v) || 0;

/** Admin correction of a saved GRN: header details and each line's received / rejected / rate. */
function EditGRNModal({ grn, onClose, onSaved }: { grn: GRN; onClose: () => void; onSaved: () => void }) {
  const [entryDate, setEntryDate] = useState(grn.entry_date);
  const [invoiceNumber, setInvoiceNumber] = useState(grn.invoice_number ?? "");
  const [invoiceDate, setInvoiceDate] = useState(grn.invoice_date ?? "");
  const [notes, setNotes] = useState(grn.notes ?? "");
  const [lines, setLines] = useState(grn.items.map((it) => ({
    id: it.id, product_id: it.product_id, unit_id: it.unit_id,
    received: String(Number(it.received_qty)), rejected: String(Number(it.rejected_qty)), price: String(Number(it.unit_price)),
  })));
  const [error, setError] = useState("");

  const { data: products } = useQuery({
    queryKey: ["products-list"],
    queryFn: async () => (await api.get("/products?page_size=200")).data.data as { id: string; name: string }[],
  });
  const { data: units } = useQuery({
    queryKey: ["units-list"],
    queryFn: async () => (await api.get("/master/units")).data.data as { id: string; abbreviation: string }[],
  });

  const save = useMutation({
    mutationFn: () => api.put(`/purchase/entries/${grn.id}`, {
      entry_date: entryDate,
      invoice_number: invoiceNumber,
      invoice_date: invoiceDate || null,
      notes,
      items: lines.map((l) => ({ id: l.id, received_qty: num(l.received), rejected_qty: num(l.rejected), unit_price: num(l.price) })),
    }),
    onSuccess: onSaved,
    onError: (e: unknown) => setError(parseApiError(e, "Could not save this GRN.")),
  });

  const badLine = lines.find((l) => num(l.rejected) > num(l.received));
  const total = lines.reduce((sum, l) => sum + Math.max(num(l.received) - num(l.rejected), 0) * num(l.price), 0);
  const set = (id: string, patch: Partial<(typeof lines)[number]>) =>
    setLines((prev) => prev.map((l) => (l.id === id ? { ...l, ...patch } : l)));

  return (
    <ModalPortal>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
        <div className="bg-card border rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between px-5 py-4 border-b">
            <div>
              <h2 className="font-semibold text-base">Edit {grn.entry_number}</h2>
              <p className="text-xs text-muted-foreground mt-0.5">Stock and the purchase order are corrected to match what you save.</p>
            </div>
            <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label="Close"><X className="h-4 w-4" /></button>
          </div>
          <form className="p-5 space-y-4" onSubmit={(e) => { e.preventDefault(); setError(""); save.mutate(); }}>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-muted-foreground">GRN Date *</label>
                <DatePicker value={entryDate} onChange={setEntryDate} required />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Vendor Invoice #</label>
                <input value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} className={`mt-1 ${inputCls}`} placeholder="INV-123" />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Invoice Date</label>
                <DatePicker value={invoiceDate} onChange={setInvoiceDate} />
              </div>
            </div>

            <div className="border rounded overflow-x-auto">
              <table className="w-full text-xs min-w-[560px]">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left px-2 py-1.5 font-medium">Product</th>
                    <th className="text-left px-2 py-1.5 font-medium">Unit</th>
                    <th className="text-right px-2 py-1.5 font-medium">Received</th>
                    <th className="text-right px-2 py-1.5 font-medium">Rejected</th>
                    <th className="text-right px-2 py-1.5 font-medium">Accepted</th>
                    <th className="text-right px-2 py-1.5 font-medium">Price</th>
                  </tr>
                </thead>
                <tbody>
                  {lines.map((l) => (
                    <tr key={l.id} className="border-t">
                      <td className="px-2 py-1.5">{(products ?? []).find((p) => p.id === l.product_id)?.name ?? "—"}</td>
                      <td className="px-2 py-1.5 text-muted-foreground">{(units ?? []).find((u) => u.id === l.unit_id)?.abbreviation ?? "—"}</td>
                      <td className="px-2 py-1 text-right">
                        <input type="number" min="0" step="0.01" required value={l.received} onChange={(e) => set(l.id, { received: e.target.value })} className={cellInputCls} />
                      </td>
                      <td className="px-2 py-1 text-right">
                        <input type="number" min="0" step="0.01" required value={l.rejected} onChange={(e) => set(l.id, { rejected: e.target.value })} className={cellInputCls} />
                      </td>
                      <td className="px-2 py-1.5 text-right tabular-nums">{Math.max(num(l.received) - num(l.rejected), 0)}</td>
                      <td className="px-2 py-1 text-right">
                        <input type="number" min="0" step="0.01" required value={l.price} onChange={(e) => set(l.id, { price: e.target.value })} className={`${cellInputCls} w-24`} />
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t bg-muted/30">
                    <td colSpan={5} className="px-2 py-1.5 text-right font-medium">Total (accepted × price)</td>
                    <td className="px-2 py-1.5 text-right font-semibold tabular-nums">{money(total)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>

            <div>
              <label className="text-xs font-medium text-muted-foreground">Notes</label>
              <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className={`mt-1 ${inputCls} resize-none`} />
            </div>
            {badLine && <p className="text-xs text-destructive">Rejected can&apos;t be more than received.</p>}
            {error && <p className="text-xs text-destructive">{error}</p>}
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" onClick={onClose} className="px-4 py-1.5 rounded border border-input text-sm hover:bg-muted">Cancel</button>
              <button type="submit" disabled={save.isPending || !!badLine}
                className="px-4 py-1.5 rounded bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-60">
                {save.isPending ? "Saving…" : "Save changes"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </ModalPortal>
  );
}

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [pdfVersion, setPdfVersion] = useState(0);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["doc-grn", id],
    queryFn: () => api.get(`/purchase/entries/${id}`).then((r) => r.data.data as GRN),
  });

  return (
    <>
      {editing && data && (
        <EditGRNModal
          grn={data}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            setPdfVersion((v) => v + 1);
            qc.invalidateQueries({ queryKey: ["doc-grn", id] });
            qc.invalidateQueries({ queryKey: ["purchase-entries"] });
            qc.invalidateQueries({ queryKey: ["purchase-orders"] });
          }}
        />
      )}
      <PdfDocumentPage
        title="Goods receipt"
        number={data?.entry_number}
        status={data?.status}
        backHref="/purchase/grn"
        pdfPath={`/documents/goods-receipts/${id}/pdf${pdfVersion ? `?v=${pdfVersion}` : ""}`}
        downloadName={`GoodsReceipt_${data?.entry_number ?? id}.pdf`}
        loading={isLoading}
        error={isError}
        facts={[
          { label: "Vendor", value: data?.vendor_name },
          { label: "Receipt date", value: fmtDate(data?.entry_date) },
          { label: "Vendor invoice", value: data?.invoice_number },
          { label: "Total", value: money(data?.total_amount) }
        ]}
        actions={
          data && data.status !== "cancelled" ? (
            <Can perm="purchase.grn_edit">
              <button className={actionCls} onClick={() => setEditing(true)}>
                <Pencil className="h-4 w-4" /> Edit GRN
              </button>
            </Can>
          ) : undefined
        }
      />
    </>
  );
}
