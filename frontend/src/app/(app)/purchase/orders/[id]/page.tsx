"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PdfDocumentPage, fmtDate, money } from "@/components/documents/pdf-document-page";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["doc-purchase-order", id],
    queryFn: () => api.get(`/purchase/orders/${id}`).then((r) => r.data.data),
  });

  return (
    <PdfDocumentPage
      title="Purchase order"
      number={data?.po_number}
      status={data?.status}
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
    />
  );
}
