"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PdfDocumentPage, fmtDate, money } from "@/components/documents/pdf-document-page";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["doc-delivery", id],
    queryFn: () => api.get(`/sales/deliveries/${id}`).then((r) => r.data.data),
  });

  return (
    <PdfDocumentPage
      title="Delivery challan"
      number={data?.delivery_number}
      status={data?.status}
      backHref="/sales/deliveries"
      pdfPath={`/documents/deliveries/${id}/pdf`}
      downloadName={`DeliveryChallan_${data?.delivery_number ?? id}.pdf`}
      loading={isLoading}
      error={isError}
      facts={[
        { label: "Customer", value: data?.customer_name },
        { label: "Dispatch date", value: fmtDate(data?.delivery_date) },
        { label: "Transporter", value: data?.transporter },
        { label: "LR / Vehicle", value: [data?.lr_number, data?.vehicle_number].filter(Boolean).join(" · ") || null }
      ]}
    />
  );
}
