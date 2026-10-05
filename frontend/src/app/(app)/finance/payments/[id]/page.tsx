"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PdfDocumentPage, fmtDate, money } from "@/components/documents/pdf-document-page";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["fin-payments", id],
    queryFn: () => api.get(`/finance/payments/${id}`).then((r) => r.data.data),
  });

  return (
    <PdfDocumentPage
      title="Payment receipt"
      number={data?.payment_number}
      status={data?.status}
      backHref="/finance/payments"
      pdfPath={`/documents/payments/${id}/pdf`}
      downloadName={`PaymentReceipt_${data?.payment_number ?? id}.pdf`}
      loading={isLoading}
      error={isError}
      facts={[
        { label: "Customer", value: data?.customer_name },
        { label: "Date", value: fmtDate(data?.payment_date) },
        { label: "Mode", value: data?.payment_mode?.toUpperCase() },
        { label: "Amount", value: money(data?.amount) }
      ]}
    />
  );
}
