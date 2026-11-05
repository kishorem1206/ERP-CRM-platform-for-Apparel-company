"use client";
import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, PackageCheck, XCircle } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { Can } from "@/lib/permissions";
import { PdfDocumentPage, fmtDate, money } from "@/components/documents/pdf-document-page";

const actionCls =
  "inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-50";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [actionError, setActionError] = useState("");
  const { data, isLoading, isError } = useQuery({
    queryKey: ["doc-purchase-order", id],
    queryFn: () => api.get(`/purchase/orders/${id}`).then((r) => r.data.data),
  });

  // Draft → approved opens the PO for GRNs; draft/approved → cancelled closes it.
  const statusAction = useMutation({
    mutationFn: (action: "approve" | "cancel") => api.post(`/purchase/orders/${id}/${action}`),
    onSuccess: () => {
      setActionError("");
      qc.invalidateQueries({ queryKey: ["doc-purchase-order", id] });
      qc.invalidateQueries({ queryKey: ["purchase-orders"] });
    },
    onError: (e: unknown) => setActionError(parseApiError(e, "Could not update this PO.")),
  });

  const status: string | undefined = data?.status;

  return (
    <PdfDocumentPage
      title="Purchase order"
      number={data?.po_number}
      status={status}
      backHref="/purchase/orders"
      pdfPath={`/documents/purchase-orders/${id}/pdf`}
      downloadName={`PurchaseOrder_${data?.po_number ?? id}.pdf`}
      loading={isLoading}
      error={isError}
      facts={[
        { label: "Vendor", value: data?.vendor_name },
        { label: "Order date", value: fmtDate(data?.order_date) },
        { label: "Expected date", value: fmtDate(data?.expected_date) },
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
      extra={actionError ? <p className="text-sm text-destructive">{actionError}</p> : undefined}
    />
  );
}
