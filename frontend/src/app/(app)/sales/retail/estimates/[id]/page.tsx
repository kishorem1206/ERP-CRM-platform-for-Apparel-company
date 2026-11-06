"use client";
import Link from "next/link";
import { useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Pencil, Receipt, Send, X, XCircle } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { Can } from "@/lib/permissions";
import { ModalShell } from "@/components/shared/modal-shell";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { PdfDocumentPage, fmtDate } from "@/components/documents/pdf-document-page";
import { COLLECTION_MODES } from "@/components/retail/bill-editor";
import { RETAIL_ACCENT, newClientRef, rupees, type RetailEstimate } from "@/lib/retail";

const actionCls = "inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-50";
const inputCls = "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

function ConvertModal({ estimate, onClose }: { estimate: RetailEstimate; onClose: () => void }) {
  const router = useRouter();
  const qc = useQueryClient();
  const ref = useRef(newClientRef());
  const [mode, setMode] = useState<"cash" | "credit">("cash");
  const [paidNow, setPaidNow] = useState("");
  const [collection, setCollection] = useState("cash");
  const [error, setError] = useState("");
  const convert = useMutation({
    mutationFn: async () => (await api.post(`/retail/estimates/${estimate.id}/convert`, {
      client_ref: ref.current, payment_mode: mode, collection_mode: collection,
      amount_paid_now: mode === "credit" && paidNow ? Number(paidNow) : null,
    })).data.data as { id: string },
    onSuccess: (inv) => {
      qc.invalidateQueries({ queryKey: ["retail-estimates"] });
      qc.invalidateQueries({ queryKey: ["retail-invoices"] });
      router.push(`/sales/retail/invoices/${inv.id}`);
    },
    onError: (e: unknown) => setError(parseApiError(e, "Could not bill this estimate.")),
  });
  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between px-5 py-4 border-b">
        <h2 className="font-semibold">Bill {estimate.estimate_number}</h2>
        <button onClick={onClose} aria-label="Close"><X className="h-4 w-4" /></button>
      </div>
      <div className="p-5 space-y-3">
        <p className="text-sm">Total <b>{rupees(estimate.total_amount, 0)}</b> — stock is taken from the retail warehouse.</p>
        <div className="grid grid-cols-2 gap-1 rounded-xl bg-muted/50 p-1">
          {(["cash", "credit"] as const).map((m) => (
            <button key={m} type="button" onClick={() => setMode(m)} className="rounded-lg py-1.5 text-sm font-semibold"
              style={mode === m ? { background: RETAIL_ACCENT, color: "#fff" } : { color: "hsl(var(--muted-foreground))" }}>
              {m === "cash" ? "Cash" : "Credit"}
            </button>
          ))}
        </div>
        {mode === "credit" && !estimate.customer_id && (
          <p className="text-xs text-destructive">A credit bill needs a customer — edit the estimate to add one.</p>
        )}
        {mode === "credit" && (
          <div>
            <label className="text-xs text-muted-foreground">Paid now (₹)</label>
            <input type="number" min="0" className={inputCls} value={paidNow} onChange={(e) => setPaidNow(e.target.value)} />
          </div>
        )}
        {(mode === "cash" || Number(paidNow) > 0) && (
          <div>
            <label className="text-xs text-muted-foreground">Received by</label>
            <SearchableSelect value={collection} onChange={(v) => setCollection(v || "cash")} accent={RETAIL_ACCENT} options={COLLECTION_MODES} />
          </div>
        )}
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
      <div className="flex justify-end gap-2 px-5 py-4 border-t">
        <button onClick={onClose} className="px-4 py-2 rounded-xl border text-sm">Cancel</button>
        <button onClick={() => { setError(""); convert.mutate(); }} disabled={convert.isPending}
          className="px-4 py-2 rounded-xl text-sm font-semibold text-white disabled:opacity-50" style={{ background: RETAIL_ACCENT }}>
          {convert.isPending ? "Billing…" : "Create bill"}
        </button>
      </div>
    </ModalShell>
  );
}

export default function RetailEstimatePage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [converting, setConverting] = useState(false);
  const [version, setVersion] = useState(0);
  const [error, setError] = useState("");
  const { data, isLoading, isError } = useQuery({
    queryKey: ["retail-estimate", id],
    queryFn: async () => (await api.get(`/retail/estimates/${id}`)).data.data as RetailEstimate,
  });
  const setStatus = useMutation({
    mutationFn: (status: string) => api.post(`/retail/estimates/${id}/status`, { status }),
    onSuccess: () => {
      setError("");
      setVersion((v) => v + 1);
      qc.invalidateQueries({ queryKey: ["retail-estimate", id] });
      qc.invalidateQueries({ queryKey: ["retail-estimates"] });
    },
    onError: (e: unknown) => setError(parseApiError(e, "Could not update this estimate.")),
  });
  const status = data?.status;
  const open = status === "draft" || status === "sent" || status === "accepted";

  return (
    <>
      {converting && data && <ConvertModal estimate={data} onClose={() => setConverting(false)} />}
      <PdfDocumentPage
        title="Retail estimate"
        number={data?.estimate_number}
        status={status ? status[0].toUpperCase() + status.slice(1) : undefined}
        backHref="/sales/retail/estimates"
        pdfPath={`/documents/retail-estimates/${id}/pdf${version ? `?v=${version}` : ""}`}
        downloadName={`RetailEstimate_${data?.estimate_number ?? id}.pdf`}
        loading={isLoading}
        error={isError}
        pdfFields={[{ key: "valid_until", label: "Valid until" }]}
        facts={[
          { label: "Customer", value: data ? (data.customer_name ? `${data.customer_name} · ${data.customer_mobile}` : "Walk-in") : null },
          { label: "Date", value: fmtDate(data?.estimate_date) },
          { label: "Valid until", value: fmtDate(data?.valid_until) },
          { label: "Total", value: data ? rupees(data.total_amount, 0) : null },
        ]}
        actions={
          <Can perm="retail.create">
            {open && (
              <button className={actionCls} style={{ color: RETAIL_ACCENT }} onClick={() => setConverting(true)}>
                <Receipt className="h-4 w-4" /> Convert to bill
              </button>
            )}
            {(status === "draft" || status === "sent" || status === "expired") && (
              <Link href={`/sales/retail/estimates/create?from=${id}`} className={actionCls}><Pencil className="h-4 w-4" /> Change</Link>
            )}
            {status === "draft" && (
              <button className={actionCls} onClick={() => setStatus.mutate("sent")}><Send className="h-4 w-4" /> Mark sent</button>
            )}
            {(status === "draft" || status === "sent") && (
              <>
                <button className={actionCls} onClick={() => setStatus.mutate("accepted")}><CheckCircle2 className="h-4 w-4" /> Accepted</button>
                <button className={`${actionCls} text-destructive`} onClick={() => setStatus.mutate("rejected")}><XCircle className="h-4 w-4" /> Rejected</button>
              </>
            )}
          </Can>
        }
        extra={
          <>
            {error && <p className="text-sm text-destructive">{error}</p>}
            {status === "expired" && (
              <p className="rounded-xl border border-amber-300 bg-amber-50 dark:bg-amber-950/30 px-4 py-3 text-sm">
                This estimate has expired. Change it to set a new validity date before billing.
              </p>
            )}
            {data?.converted_invoice_id && (
              <p className="text-sm">Billed as{" "}
                <Link className="font-semibold underline" href={`/sales/retail/invoices/${data.converted_invoice_id}`}>{data.converted_invoice_number}</Link>
              </p>
            )}
          </>
        }
      />
    </>
  );
}
