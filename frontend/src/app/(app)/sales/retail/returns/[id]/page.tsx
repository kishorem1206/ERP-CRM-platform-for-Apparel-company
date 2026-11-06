"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PdfDocumentPage, fmtDate } from "@/components/documents/pdf-document-page";
import { rupees, type RetailReturn } from "@/lib/retail";

export default function RetailReturnPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["retail-return", id],
    queryFn: async () => (await api.get(`/retail/returns/${id}`)).data.data as RetailReturn,
  });
  return (
    <PdfDocumentPage
      title="Retail return"
      number={data?.return_number}
      backHref="/sales/retail/returns"
      pdfPath={`/documents/retail-returns/${id}/pdf`}
      downloadName={`RetailReturn_${data?.return_number ?? id}.pdf`}
      loading={isLoading}
      error={isError}
      facts={[
        { label: "Bill", value: data?.invoice_number },
        { label: "Date", value: fmtDate(data?.return_date) },
        { label: "Value", value: data ? rupees(data.return_amount) : null },
        { label: "Refunded", value: data ? (Number(data.refund_amount) > 0 ? `${rupees(data.refund_amount)} (${data.refund_mode ?? "cash"})` : "—") : null },
      ]}
      extra={data && (
        <p className="text-sm">
          Against bill <Link className="font-semibold underline" href={`/sales/retail/invoices/${data.invoice_id}`}>{data.invoice_number}</Link>
          {Number(data.applied_to_balance) > 0 && <> · {rupees(data.applied_to_balance)} taken off the balance due</>}
          {data.points_reversed > 0 && <> · {data.points_reversed} points taken back</>}
          {" · "}Reason: {data.reason}
        </p>
      )}
    />
  );
}
