"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import api from "@/lib/api";
import { formatIndianFull } from "@/lib/format";
import { fmtDate } from "@/components/documents/pdf-document-page";

interface PriceListSummary { id: string; name: string; is_default: boolean; valid_from: string | null; valid_to: string | null; item_count: number }
interface PriceListItem {
  id: string; product_name: string | null; variant_sku: string | null; customer_name: string | null;
  min_quantity: string; max_quantity: string | null; unit_price: string; discount_pct: string;
  valid_from: string | null; valid_to: string | null;
}

export default function PriceListDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: lists } = useQuery({
    queryKey: ["crm-price-lists-summary"],
    queryFn: () => api.get("/sales/price-lists").then((r) => r.data.data as PriceListSummary[]),
  });
  const list = lists?.find((l) => l.id === id);
  const { data: items, isLoading, isError } = useQuery({
    queryKey: ["price-list-detail-items", id],
    queryFn: () => api.get(`/sales/price-lists/${id}/items`).then((r) => r.data.data as PriceListItem[]),
  });

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/sales/price-lists" className="rounded-lg p-2 hover:bg-muted" aria-label="Back">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Price list</p>
          <h1 className="text-2xl font-bold tracking-tight">{list?.name ?? "—"}</h1>
          <p className="text-sm text-muted-foreground">
            {list ? `${list.item_count} items · ${fmtDate(list.valid_from) ?? "No start"} – ${fmtDate(list.valid_to) ?? "open ended"}` : ""}
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-card overflow-hidden">
        {isError ? (
          <p className="p-6 text-sm text-muted-foreground">Items could not be loaded.</p>
        ) : isLoading ? (
          <p className="p-6 text-sm text-muted-foreground">Loading items…</p>
        ) : !items || items.length === 0 ? (
          <p className="p-6 text-sm text-muted-foreground">No items in this price list.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-4 py-2.5">Product</th>
                  <th className="px-4 py-2.5">Variant</th>
                  <th className="px-4 py-2.5">Customer</th>
                  <th className="px-4 py-2.5 text-right">Qty range</th>
                  <th className="px-4 py-2.5 text-right">Unit price</th>
                  <th className="px-4 py-2.5 text-right">Discount</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.id} className="border-t border-border">
                    <td className="px-4 py-2.5 font-medium">{it.product_name || "—"}</td>
                    <td className="px-4 py-2.5">{it.variant_sku || "All variants"}</td>
                    <td className="px-4 py-2.5">{it.customer_name || "All customers"}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      {Number(it.min_quantity)}{it.max_quantity ? ` – ${Number(it.max_quantity)}` : "+"}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{formatIndianFull(Number(it.unit_price))}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{Number(it.discount_pct) ? `${Number(it.discount_pct)}%` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
