"use client";
import { useParams } from "next/navigation";
import { PdfDocumentPage } from "@/components/documents/pdf-document-page";

export default function RetailReceiptPage() {
  const { batch } = useParams<{ batch: string }>();
  return (
    <PdfDocumentPage
      title="Payment receipt"
      backHref="/sales/retail/credit"
      pdfPath={`/documents/retail-receipts/${batch}/pdf`}
      downloadName={`Receipt_${batch.slice(0, 8)}.pdf`}
      loading={false}
      error={false}
      facts={[]}
    />
  );
}
