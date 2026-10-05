"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PdfDocumentPage, fmtDate, money } from "@/components/documents/pdf-document-page";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["fin-debit-notes", id],
    queryFn: () => api.get(`/finance/debit-notes/${id}`).then((r) => r.data.data),
  });

  return (
    <PdfDocumentPage
      title="Debit note"
      number={data?.debit_note_number}
      status={data?.status}
      backHref="/finance/debit-notes"
      pdfPath={`/documents/debit-notes/${id}/pdf`}
      downloadName={`DebitNote_${data?.debit_note_number ?? id}.pdf`}
      loading={isLoading}
      error={isError}
      facts={[
        { label: "Vendor", value: data?.vendor_name },
        { label: "Date", value: fmtDate(data?.debit_note_date) },
        { label: "Reason", value: data?.reason },
        { label: "Total", value: money(data?.total_amount) }
      ]}
    />
  );
}
