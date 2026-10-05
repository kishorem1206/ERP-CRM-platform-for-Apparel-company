"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PdfDocumentPage, fmtDate, money } from "@/components/documents/pdf-document-page";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["fin-vendor-payments", id],
    queryFn: () => api.get(`/finance/vendor-payments/${id}`).then((r) => r.data.data),
  });

  return (
    <PdfDocumentPage
      title="Payment voucher"
      number={data?.payment_number}
      status={data?.status}
      backHref="/finance/vendor-payments"
      pdfPath={`/documents/vendor-payments/${id}/pdf`}
      downloadName={`PaymentVoucher_${data?.payment_number ?? id}.pdf`}
      loading={isLoading}
      error={isError}
      facts={[
        { label: "Vendor", value: data?.vendor_name },
        { label: "Date", value: fmtDate(data?.payment_date) },
        { label: "Mode", value: data?.payment_mode?.toUpperCase() },
        { label: "Amount", value: money(data?.amount) }
      ]}
    />
  );
}
