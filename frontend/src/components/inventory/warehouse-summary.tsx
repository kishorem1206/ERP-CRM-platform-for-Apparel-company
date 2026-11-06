"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

interface Warehouse { id: string; name: string; code: string | null }
interface BalanceRow { warehouse_id: string; product_id: string; variant_id: string | null; balance: string; stock_value: string | null }

const inr = (n: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

/** Stock value and item count per warehouse, from the stock ledger. */
export function WarehouseSummary() {
  const warehouses = useQuery({
    queryKey: ["warehouses-list"],
    queryFn: async () => (await api.get("/master/warehouses")).data.data as Warehouse[],
  });
  const balance = useQuery({
    queryKey: ["stock-balance", "in_stock", "summary"],
    queryFn: async () => (await api.get("/inventory/balance", { params: { status: "in_stock" } })).data.data as BalanceRow[],
  });

  const rows = balance.data ?? [];
  const valueHidden = rows.length > 0 && rows.every((r) => r.stock_value == null);
  const byWarehouse = new Map<string, { value: number; items: number; unpriced: number }>();
  for (const r of rows) {
    const agg = byWarehouse.get(r.warehouse_id) ?? { value: 0, items: 0, unpriced: 0 };
    agg.items += 1;
    const v = r.stock_value == null ? 0 : Number(r.stock_value);
    agg.value += v;
    if (r.stock_value != null && v <= 0) agg.unpriced += 1;
    byWarehouse.set(r.warehouse_id, agg);
  }
  const loading = warehouses.isLoading || balance.isLoading;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
      {loading && <p className="text-sm text-muted-foreground col-span-full">Loading…</p>}
      {(warehouses.data ?? []).map((wh) => {
        const agg = byWarehouse.get(wh.id) ?? { value: 0, items: 0, unpriced: 0 };
        return (
          <Link key={wh.id} href="/inventory/balance"
            className="bg-background border border-border rounded-xl p-3 space-y-1 hover:border-primary/30 transition-colors">
            <p className="text-xs font-medium truncate">{wh.name}</p>
            <p className="text-xs text-muted-foreground">{wh.code ?? "—"}</p>
            <p className="text-lg font-semibold tabular-nums">{valueHidden ? "—" : inr(agg.value)}</p>
            <p className="text-xs text-muted-foreground">
              {agg.items} item{agg.items === 1 ? "" : "s"} in stock
              {agg.unpriced > 0 && <span className="text-amber-600 dark:text-amber-400"> · {agg.unpriced} without a rate</span>}
            </p>
          </Link>
        );
      })}
    </div>
  );
}
