"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import api from "@/lib/api";
import { formatIndianFull } from "@/lib/format";

interface OutputDetail {
  id: string;
  output_number: string;
  lot_number: string | null;
  production_lot_id: string;
  warehouse_name: string | null;
  output_date: string;
  product_name: string | null;
  quantity: string;
  rejected_qty: string | null;
  unit_abbreviation: string | null;
  unit_cost: string;
  total_cost: string;
  inv_transaction_id: string | null;
}

function fmtQty(v: string | null | undefined, unit: string | null): string {
  if (v === null || v === undefined) return "—";
  return `${Number(v).toLocaleString("en-IN", { maximumFractionDigits: 4 })} ${unit ?? ""}`.trim();
}

export default function OutputDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["production-output-detail", id],
    queryFn: () => api.get(`/production/outputs/${id}`).then((r) => r.data.data as OutputDetail),
  });

  const card = "rounded-2xl border border-border bg-card p-5";
  const label = "text-[11px] font-semibold uppercase tracking-wider text-muted-foreground";
  const hasRejection = data?.rejected_qty && Number(data.rejected_qty) > 0;

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/production/outputs" className="rounded-lg p-2 hover:bg-muted" aria-label="Back">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Production Output</p>
          <h1 className="text-2xl font-bold tracking-tight">{data?.output_number ?? (isLoading ? "Loading…" : "—")}</h1>
        </div>
      </div>

      {isError ? (
        <div className={card + " text-sm text-muted-foreground"}>This output record could not be loaded.</div>
      ) : data && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[
              ["Lot", data.lot_number],
              ["Product", data.product_name],
              ["Warehouse", data.warehouse_name],
              ["Output Date", data.output_date],
            ].map(([k, v]) => (
              <div key={k as string} className={card + " min-w-0"}>
                <p className={label}>{k}</p>
                <p className="mt-1 truncate font-semibold">{(v as string) || "—"}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className={card}>
              <p className={label}>Quantity Produced</p>
              <p className="mt-1 text-xl font-bold tabular-nums">{fmtQty(data.quantity, data.unit_abbreviation)}</p>
            </div>
            <div className={card}>
              <p className={label}>Rejected</p>
              <p className="mt-1 text-xl font-bold tabular-nums" style={hasRejection ? { color: "#B45309" } : undefined}>
                {fmtQty(data.rejected_qty, data.unit_abbreviation)}
              </p>
            </div>
            <div className={card}>
              <p className={label}>Unit Cost</p>
              <p className="mt-1 text-xl font-bold tabular-nums">{formatIndianFull(Number(data.unit_cost))}</p>
            </div>
            <div className={card}>
              <p className={label}>Total Cost</p>
              <p className="mt-1 text-xl font-bold tabular-nums">{formatIndianFull(Number(data.total_cost))}</p>
            </div>
          </div>

          <div className={card}>
            <p className={label}>Linked Inventory Transaction</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {data.inv_transaction_id
                ? "This output posted a receipt to inventory — visible in the Transaction Log."
                : "No inventory transaction linked."}
            </p>
          </div>
        </>
      )}
    </div>
  );
}
