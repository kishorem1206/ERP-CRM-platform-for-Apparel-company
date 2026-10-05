"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PdfDocumentPage, fmtDate, money } from "@/components/documents/pdf-document-page";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["doc-sales-order", id],
    queryFn: () => api.get(`/sales/orders/${id}`).then((r) => r.data.data),
  });

  return (
    <PdfDocumentPage
      title="Sales order"
      number={data?.order_number}
      status={data?.status}
      backHref="/sales/orders"
      pdfPath={`/documents/sales-orders/${id}/pdf`}
      downloadName={`SalesOrder_${data?.order_number ?? id}.pdf`}
      loading={isLoading}
      error={isError}
      facts={[
        { label: "Customer", value: data?.customer_name },
        { label: "Order date", value: fmtDate(data?.order_date) },
        { label: "Expected delivery", value: fmtDate(data?.expected_delivery) },
        { label: "Total", value: money(data?.total_amount) }
      ]}
    />
  );
}
