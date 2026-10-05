"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PdfDocumentPage, fmtDate, money } from "@/components/documents/pdf-document-page";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["doc-invoice", id],
    queryFn: () => api.get(`/sales/invoices/${id}`).then((r) => r.data.data),
  });

  return (
    <PdfDocumentPage
      title="Invoice"
      number={data?.invoice_number}
      status={data?.status}
      backHref="/sales/invoices"
      pdfPath={`/documents/invoices/${id}/pdf`}
      downloadName={`Invoice_${data?.invoice_number ?? id}.pdf`}
      loading={isLoading}
      error={isError}
      facts={[
        { label: "Customer", value: data?.customer_name },
        { label: "Invoice date", value: fmtDate(data?.invoice_date) },
        { label: "Total", value: money(data?.total_amount) },
        { label: "Balance due", value: money(data?.balance_amount) }
      ]}
    />
  );
}
