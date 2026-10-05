"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PdfDocumentPage, fmtDate, money } from "@/components/documents/pdf-document-page";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["doc-grn", id],
    queryFn: () => api.get(`/purchase/entries/${id}`).then((r) => r.data.data),
  });

  return (
    <PdfDocumentPage
      title="Goods receipt"
      number={data?.entry_number}
      status={data?.status}
      backHref="/purchase/grn"
      pdfPath={`/documents/goods-receipts/${id}/pdf`}
      downloadName={`GoodsReceipt_${data?.entry_number ?? id}.pdf`}
      loading={isLoading}
      error={isError}
      facts={[
        { label: "Vendor", value: data?.vendor_name },
        { label: "Receipt date", value: fmtDate(data?.entry_date) },
        { label: "Vendor invoice", value: data?.invoice_number },
        { label: "Total", value: money(data?.total_amount) }
      ]}
    />
  );
}
