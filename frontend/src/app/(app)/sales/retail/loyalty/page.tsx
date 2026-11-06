"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { Can } from "@/lib/permissions";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { settingsInputCls as inputCls, useSaveRetailSettings } from "@/components/retail/settings-section";
import { RETAIL_ACCENT, rupees, type RetailSettings } from "@/lib/retail";

interface Summary {
  enabled: boolean; customers_with_points: number; points_issued: number; points_redeemed: number; points_expired: number;
  points_outstanding: number; liability: string; top_customers: { id: string; name: string; mobile: string; points: number }[];
}

export default function RetailLoyaltyPage() {
  const summary = useQuery({ queryKey: ["retail-loyalty-summary"], queryFn: async () => (await api.get("/retail/loyalty/summary")).data.data as Summary });
  const settings = useQuery({ queryKey: ["retail-settings"], queryFn: async () => (await api.get("/retail/settings")).data.data as RetailSettings });
  const categories = useQuery({ queryKey: ["master-categories"], queryFn: async () => (await api.get("/master/categories")).data.data as { id: string; name: string }[] });
  const { save, status, button } = useSaveRetailSettings();
  const [f, setF] = useState({ enabled: false, per: "", min_bill: "", min_redeem: "", value: "", max_pct: "", expiry: "" });
  const [excluded, setExcluded] = useState<string[]>([]);
  useEffect(() => {
    const s = settings.data;
    if (s) {
      setF({
        enabled: s.loyalty_enabled, per: String(Number(s.amount_per_point)), min_bill: String(Number(s.min_bill_for_points)),
        min_redeem: String(s.min_redeem_points), value: String(Number(s.point_value)), max_pct: String(Number(s.max_redeem_pct)),
        expiry: String(s.points_expiry_days),
      });
      setExcluded(s.loyalty_excluded_category_ids ?? []);
    }
  }, [settings.data]);
  const s = summary.data;
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF((x) => ({ ...x, [k]: e.target.value }));

  return (
    <div className="p-8 space-y-6 max-w-5xl">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / RETAIL</p>
        <h1 className="text-2xl font-bold tracking-tight">Loyalty Programme</h1>
        <p className="text-sm text-muted-foreground mt-1">Customers earn points on what they pay and spend them on later bills.</p>
      </div>
      {s && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          {[
            ["Members with points", String(s.customers_with_points)], ["Points issued", s.points_issued.toLocaleString("en-IN")],
            ["Points redeemed", s.points_redeemed.toLocaleString("en-IN")], ["Points outstanding", s.points_outstanding.toLocaleString("en-IN")],
            ["Liability", rupees(s.liability, 0)],
          ].map(([k, v]) => (
            <div key={k} className="rounded-2xl border border-border bg-card p-4"><p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{k}</p><p className="mt-1 text-lg font-semibold tabular-nums">{v}</p></div>
          ))}
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <Can perm="retail.manage">
          <div className="rounded-2xl border border-border bg-card p-5 space-y-4">
            <label className="flex items-center gap-2 text-sm font-semibold">
              <input type="checkbox" checked={f.enabled} onChange={(e) => setF((x) => ({ ...x, enabled: e.target.checked }))} /> Loyalty programme switched on
            </label>
            <div className="grid gap-3 md:grid-cols-3">
              <div><label className="text-xs text-muted-foreground">1 point for every ₹</label><input type="number" min="1" className={inputCls} value={f.per} onChange={set("per")} /></div>
              <div><label className="text-xs text-muted-foreground">Bill must be at least ₹</label><input type="number" min="0" className={inputCls} value={f.min_bill} onChange={set("min_bill")} /></div>
              <div><label className="text-xs text-muted-foreground">Points expire after (days, 0 = never)</label><input type="number" min="0" className={inputCls} value={f.expiry} onChange={set("expiry")} /></div>
              <div><label className="text-xs text-muted-foreground">1 point is worth ₹</label><input type="number" min="0.01" step="0.01" className={inputCls} value={f.value} onChange={set("value")} /></div>
              <div><label className="text-xs text-muted-foreground">Redeem at least (points)</label><input type="number" min="0" className={inputCls} value={f.min_redeem} onChange={set("min_redeem")} /></div>
              <div><label className="text-xs text-muted-foreground">Points can pay up to % of a bill</label><input type="number" min="0" max="100" className={inputCls} value={f.max_pct} onChange={set("max_pct")} /></div>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Categories that don&apos;t earn points</label>
              <SearchableSelect value="" onChange={(v) => v && setExcluded((x) => (x.includes(v) ? x : [...x, v]))} accent={RETAIL_ACCENT} placeholder="Add a category"
                options={(categories.data ?? []).filter((c) => !excluded.includes(c.id)).map((c) => ({ value: c.id, label: c.name }))} />
              <div className="flex flex-wrap gap-1 mt-1">
                {excluded.map((id) => (
                  <button key={id} type="button" onClick={() => setExcluded((x) => x.filter((y) => y !== id))} className="rounded-full bg-muted px-2 py-0.5 text-[11px]">
                    {(categories.data ?? []).find((c) => c.id === id)?.name ?? "…"} ×
                  </button>
                ))}
              </div>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Points are worked out on the amount after discounts, coupons and points used. Cash bills earn at once; credit bills earn once fully paid. A cancelled bill gives back the points used and takes back the points earned.
            </p>
            {status}
            <div className="flex justify-end">
              {button(() => save.mutate({
                loyalty_enabled: f.enabled, amount_per_point: Number(f.per) || 100, min_bill_for_points: Number(f.min_bill) || 0,
                min_redeem_points: Number(f.min_redeem) || 0, point_value: Number(f.value) || 1, max_redeem_pct: Number(f.max_pct) || 0,
                points_expiry_days: Number(f.expiry) || 0, loyalty_excluded_category_ids: excluded,
              }))}
            </div>
          </div>
        </Can>
        <div className="rounded-2xl border border-border bg-card p-5">
          <p className="text-sm font-semibold mb-3">Top loyalty customers</p>
          {(s?.top_customers ?? []).length === 0 ? <p className="text-sm text-muted-foreground">No points earned yet.</p> : (
            <div className="space-y-1.5">
              {(s?.top_customers ?? []).map((c) => (
                <Link key={c.id} href={`/sales/retail/customers/${c.id}`} className="flex justify-between text-sm hover:underline">
                  <span>{c.name} <span className="text-xs text-muted-foreground">{c.mobile}</span></span>
                  <span className="font-semibold tabular-nums">{c.points}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
