"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PdfDocumentPage, fmtDate, money } from "@/components/documents/pdf-document-page";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["doc-quotation", id],
    queryFn: () => api.get(`/sales/quotations/${id}`).then((r) => r.data.data),
  });

  return (
    <PdfDocumentPage
      title="Quotation"
      number={data?.quotation_number}
      status={data?.status}
      backHref="/sales/quotations"
      pdfPath={`/documents/quotations/${id}/pdf`}
      downloadName={`Quotation_${data?.quotation_number ?? id}.pdf`}
      loading={isLoading}
      error={isError}
      facts={[
        { label: "Customer", value: data?.customer_name },
        { label: "Date", value: fmtDate(data?.quotation_date) },
        { label: "Valid until", value: fmtDate(data?.valid_until) },
        { label: "Total", value: money(data?.total_amount) }
      ]}
    />
  );
}
