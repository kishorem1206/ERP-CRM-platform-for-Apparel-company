"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, X } from "lucide-react";
import api from "@/lib/api";
import { Can } from "@/lib/permissions";
import { ModalShell } from "@/components/shared/modal-shell";
import { StatusBadge } from "@/components/shared/status-badge";
import { CouponFormModal } from "@/components/retail/coupon-form";
import { RETAIL_ACCENT, couponText, rupees, type RetailCoupon } from "@/lib/retail";

const KINDS = [{ value: "", label: "All" }, { value: "manual", label: "Manual" }, { value: "promo", label: "Promotional" }, { value: "birthday", label: "Birthday" }];
const STATE_BADGE: Record<string, { status: string; label: string }> = {
  active: { status: "active", label: "Active" }, scheduled: { status: "pending", label: "Scheduled" },
  expired: { status: "inactive", label: "Expired" }, used_up: { status: "completed", label: "Used up" }, inactive: { status: "cancelled", label: "Off" },
};

function Redemptions({ coupon, onClose }: { coupon: RetailCoupon; onClose: () => void }) {
  const { data } = useQuery({
    queryKey: ["coupon-redemptions", coupon.id],
    queryFn: async () => (await api.get(`/retail/coupons/${coupon.id}/redemptions`)).data.data as {
      invoice_id: string; invoice_number: string; invoice_date: string; customer_name: string | null; discount_amount: string; status: string;
    }[],
  });
  return (
    <ModalShell maxWidth="max-w-lg" onClose={onClose}>
      <div className="flex items-center justify-between px-5 py-4 border-b">
        <h2 className="font-semibold">{coupon.code} — used {coupon.times_used} time{coupon.times_used === 1 ? "" : "s"}</h2>
        <button onClick={onClose} aria-label="Close"><X className="h-4 w-4" /></button>
      </div>
      <div className="p-5">
        {(data ?? []).length === 0 ? <p className="text-sm text-muted-foreground">Not used yet.</p> : (
          <table className="w-full text-sm">
            <tbody>
              {(data ?? []).map((r) => (
                <tr key={r.invoice_id} className="border-t border-border first:border-0">
                  <td className="py-1.5 pr-3"><Link className="hover:underline" href={`/sales/retail/invoices/${r.invoice_id}`}>{r.invoice_number}</Link></td>
                  <td className="py-1.5 pr-3">{r.invoice_date}</td>
                  <td className="py-1.5 pr-3">{r.customer_name ?? "Walk-in"}</td>
                  <td className={`py-1.5 text-right tabular-nums ${r.status === "reversed" ? "line-through text-muted-foreground" : ""}`}>{rupees(r.discount_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </ModalShell>
  );
}

export default function RetailCouponsPage() {
  const qc = useQueryClient();
  const [kind, setKind] = useState("");
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<RetailCoupon | null | undefined>(undefined);
  const [viewing, setViewing] = useState<RetailCoupon | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["retail-coupons", kind, search],
    queryFn: async () => (await api.get("/retail/coupons", { params: { kind: kind || undefined, search: search || undefined } })).data.data as RetailCoupon[],
  });
  return (
    <div className="p-8 space-y-6">
      {editing !== undefined && (
        <CouponFormModal coupon={editing} onClose={() => setEditing(undefined)}
          onSaved={() => { setEditing(undefined); qc.invalidateQueries({ queryKey: ["retail-coupons"] }); }} />
      )}
      {viewing && <Redemptions coupon={viewing} onClose={() => setViewing(null)} />}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / RETAIL</p>
          <h1 className="text-2xl font-bold tracking-tight">Coupons</h1>
          <p className="text-sm text-muted-foreground mt-1">Codes the counter can apply on a bill. Birthday coupons are made automatically.</p>
        </div>
        <Can perm="retail.manage">
          <button onClick={() => setEditing(null)} className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: RETAIL_ACCENT }}>
            <Plus className="h-4 w-4" /> New coupon
          </button>
        </Can>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input className="rounded-lg border border-input bg-background pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Code or name…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="flex flex-wrap items-center gap-1 p-1 bg-muted/50 rounded-xl">
          {KINDS.map((k) => (
            <button key={k.value} onClick={() => setKind(k.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${kind === k.value ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>{k.label}</button>
          ))}
        </div>
      </div>
      <div className="bg-card border border-border rounded-2xl overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead><tr className="border-b border-border text-left text-xs text-muted-foreground">
            <th className="px-4 py-3 font-medium">Code</th><th className="px-4 py-3 font-medium">Offer</th>
            <th className="px-4 py-3 font-medium">Valid</th><th className="px-4 py-3 font-medium">Used</th>
            <th className="px-4 py-3 font-medium text-right">Discount given</th><th className="px-4 py-3 font-medium">Status</th><th></th>
          </tr></thead>
          <tbody>
            {isLoading && <tr><td colSpan={7} className="px-4 py-6 text-center text-muted-foreground">Loading…</td></tr>}
            {!isLoading && (data ?? []).length === 0 && <tr><td colSpan={7} className="px-4 py-6 text-center text-muted-foreground">No coupons yet</td></tr>}
            {(data ?? []).map((c) => (
              <tr key={c.id} className="border-b border-border last:border-0">
                <td className="px-4 py-2.5">
                  <p className="font-mono font-semibold">{c.code}</p>
                  <p className="text-xs text-muted-foreground">{c.name}{c.customer_name ? ` · for ${c.customer_name}` : ""}</p>
                </td>
                <td className="px-4 py-2.5">{couponText(c)}</td>
                <td className="px-4 py-2.5 text-xs">{c.start_date} → {c.expiry_date}</td>
                <td className="px-4 py-2.5">{c.times_used}{c.max_uses ? ` / ${c.max_uses}` : ""}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{rupees(c.total_discount)}</td>
                <td className="px-4 py-2.5"><StatusBadge status={STATE_BADGE[c.state]?.status ?? c.state} label={STATE_BADGE[c.state]?.label ?? c.state} /></td>
                <td className="px-4 py-2.5 text-right whitespace-nowrap">
                  <button onClick={() => setViewing(c)} className="text-xs font-semibold mr-3" style={{ color: RETAIL_ACCENT }}>History</button>
                  <Can perm="retail.manage"><button onClick={() => setEditing(c)} className="text-xs font-semibold" style={{ color: RETAIL_ACCENT }}>Edit</button></Can>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
