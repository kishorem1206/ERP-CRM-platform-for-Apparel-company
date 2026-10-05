"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PdfDocumentPage, fmtDate, money } from "@/components/documents/pdf-document-page";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["fin-credit-notes", id],
    queryFn: () => api.get(`/finance/credit-notes/${id}`).then((r) => r.data.data),
  });

  return (
    <PdfDocumentPage
      title="Credit note"
      number={data?.credit_note_number}
      status={data?.status}
      backHref="/finance/credit-notes"
      pdfPath={`/documents/credit-notes/${id}/pdf`}
      downloadName={`CreditNote_${data?.credit_note_number ?? id}.pdf`}
      loading={isLoading}
      error={isError}
      facts={[
        { label: "Customer", value: data?.customer_name },
        { label: "Date", value: fmtDate(data?.credit_note_date) },
        { label: "Reason", value: data?.reason },
        { label: "Total", value: money(data?.total_amount) }
      ]}
    />
  );
}
