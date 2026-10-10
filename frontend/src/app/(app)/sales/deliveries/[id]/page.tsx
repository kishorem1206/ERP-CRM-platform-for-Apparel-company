"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PdfDocumentPage, fmtDate, money } from "@/components/documents/pdf-document-page";

interface DeliveryItem {
  id: string;
  product_name: string | null;
  sku: string | null;
  size_name: string | null;
  colour_name: string | null;
  lot_number: string | null;
  quantity: string;
  unit_price: string;
  returnable: boolean;
  weight_kg: string | null;
  returned_qty: string;
}
interface SalesReturn {
  id: string;
  return_number: string;
  return_date: string;
  status: string;
  reason: string | null;
}
interface DeliveryDetail {
  delivery_number: string;
  customer_name: string | null;
  status: string;
  delivery_date: string;
  transporter: string | null;
  lr_number: string | null;
  vehicle_number: string | null;
  purpose: string;
  items: DeliveryItem[];
  returns: SalesReturn[];
}

const PURPOSE_LABEL: Record<string, string> = {
  sale: "Sale", sample: "Sample", job_work_return: "Job-work return",
  branch_transfer: "Branch transfer", other: "Other",
};

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["doc-delivery", id],
    queryFn: () => api.get(`/sales/deliveries/${id}`).then((r) => r.data.data as DeliveryDetail),
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
        { label: "Purpose", value: data ? (PURPOSE_LABEL[data.purpose] ?? data.purpose) : null },
        { label: "Transporter", value: data?.transporter },
        { label: "LR / Vehicle", value: [data?.lr_number, data?.vehicle_number].filter(Boolean).join(" · ") || null },
      ]}
      extra={
        data ? (
          <div className="space-y-4">
            <div className="rounded-2xl border border-border bg-card overflow-hidden">
              <div className="px-4 py-3 border-b border-border">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Items</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="text-left px-3 py-2 font-medium">Product</th>
                      <th className="text-left px-3 py-2 font-medium">Size / Colour</th>
                      <th className="text-left px-3 py-2 font-medium">Lot</th>
                      <th className="text-right px-3 py-2 font-medium">Qty</th>
                      <th className="text-right px-3 py-2 font-medium">Weight</th>
                      <th className="text-right px-3 py-2 font-medium">Returned</th>
                      <th className="text-left px-3 py-2 font-medium">Returnable</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((it) => (
                      <tr key={it.id} className="border-t border-border">
                        <td className="px-3 py-2 font-medium">{it.product_name ?? "—"}{it.sku ? ` (${it.sku})` : ""}</td>
                        <td className="px-3 py-2 text-muted-foreground">
                          {[it.size_name, it.colour_name].filter(Boolean).join(" · ") || "—"}
                        </td>
                        <td className="px-3 py-2 text-muted-foreground">{it.lot_number ?? "—"}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{it.quantity}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{it.weight_kg ?? "—"}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{Number(it.returned_qty) > 0 ? it.returned_qty : "—"}</td>
                        <td className="px-3 py-2">{it.returnable ? "Yes" : "No"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {data.returns.length > 0 && (
              <div className="rounded-2xl border border-border bg-card overflow-hidden">
                <div className="px-4 py-3 border-b border-border">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Linked Returns</p>
                </div>
                <div className="divide-y divide-border">
                  {data.returns.map((r) => (
                    <Link
                      key={r.id} href={`/sales/returns/${r.id}`}
                      className="flex items-center justify-between px-4 py-2.5 text-sm hover:bg-muted/50"
                    >
                      <span className="font-medium">{r.return_number}</span>
                      <span className="text-muted-foreground">{fmtDate(r.return_date)}</span>
                      <span className="text-muted-foreground">{r.reason ?? "—"}</span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : undefined
      }
    />
  );
}
