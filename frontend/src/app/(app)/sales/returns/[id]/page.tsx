"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PdfDocumentPage, fmtDate } from "@/components/documents/pdf-document-page";

interface SalesReturnItem {
  id: string;
  product_name: string | null;
  quantity: string;
  disposition: string;
  unit_cost: string | null;
  total_cost: string | null;
  notes: string | null;
}
interface SalesReturnDetail {
  return_number: string;
  customer_name: string | null;
  return_date: string;
  status: string;
  reason: string | null;
  items: SalesReturnItem[];
}

const DISPOSITION_LABEL: Record<string, string> = {
  usable_stock: "Usable stock", resale_stock: "Resale stock", scrap: "Scrap", wastage: "Wastage",
};

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["doc-sales-return", id],
    queryFn: () => api.get(`/sales/returns/${id}`).then((r) => r.data.data as SalesReturnDetail),
  });

  return (
    <PdfDocumentPage
      title="Sales return"
      number={data?.return_number}
      status={data?.status}
      backHref="/sales/returns"
      pdfPath={`/documents/returns/${id}/pdf`}
      downloadName={`SalesReturn_${data?.return_number ?? id}.pdf`}
      loading={isLoading}
      error={isError}
      facts={[
        { label: "Customer", value: data?.customer_name },
        { label: "Return date", value: fmtDate(data?.return_date) },
        { label: "Reason", value: data?.reason },
      ]}
      extra={
        data ? (
          <div className="rounded-2xl border border-border bg-card overflow-hidden">
            <div className="px-4 py-3 border-b border-border">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Items</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left px-3 py-2 font-medium">Product</th>
                    <th className="text-right px-3 py-2 font-medium">Qty</th>
                    <th className="text-left px-3 py-2 font-medium">Disposition</th>
                    <th className="text-right px-3 py-2 font-medium">Unit Cost</th>
                    <th className="text-right px-3 py-2 font-medium">Total</th>
                    <th className="text-left px-3 py-2 font-medium">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((it) => (
                    <tr key={it.id} className="border-t border-border">
                      <td className="px-3 py-2 font-medium">{it.product_name ?? "—"}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{it.quantity}</td>
                      <td className="px-3 py-2">{DISPOSITION_LABEL[it.disposition] ?? it.disposition}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{it.unit_cost ?? "—"}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{it.total_cost ?? "—"}</td>
                      <td className="px-3 py-2 text-muted-foreground">{it.notes ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : undefined
      }
    />
  );
}
