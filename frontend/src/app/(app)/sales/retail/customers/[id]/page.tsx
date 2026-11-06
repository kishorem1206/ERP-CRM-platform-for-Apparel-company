"use client";
import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Pencil, Receipt } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { Can } from "@/lib/permissions";
import { CustomerFormModal } from "@/components/retail/customer-form";
import { CollectModal } from "@/components/retail/collect-modal";
import { StatusBadge } from "@/components/shared/status-badge";
import { fmtDate } from "@/components/documents/pdf-document-page";
import { RETAIL_ACCENT, payStatusLabel, rupees, type RetailCustomer } from "@/lib/retail";

interface InvoiceRow { id: string; invoice_number: string; invoice_date: string; payment_mode: string; payment_status: string; total_amount: string; outstanding: string; status: string }
interface EstimateRow { id: string; estimate_number: string; estimate_date: string; status: string; total_amount: string }

const ENTRY_LABEL: Record<string, string> = { earned: "Earned", redeemed: "Redeemed", expired: "Expired", adjusted: "Adjusted", reversed: "Reversed" };

function PointsCard({ customerId }: { customerId: string }) {
  const qc = useQueryClient();
  const [adjusting, setAdjusting] = useState(false);
  const [points, setPoints] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const { data } = useQuery({
    queryKey: ["retail-points", customerId],
    queryFn: async () => (await api.get(`/retail/customers/${customerId}/points`)).data.data as {
      balance: number; entries: { id: string; entry_type: string; points: number; balance_after: number; invoice_id: string | null;
        invoice_number: string | null; reason: string | null; expires_on: string | null; created_at: string }[];
    },
  });
  const adjust = useMutation({
    mutationFn: () => api.post(`/retail/customers/${customerId}/points/adjust`, { points: Number(points), reason }),
    onSuccess: () => {
      setAdjusting(false); setPoints(""); setReason(""); setError("");
      qc.invalidateQueries({ queryKey: ["retail-points", customerId] });
      qc.invalidateQueries({ queryKey: ["retail-customer", customerId] });
    },
    onError: (e: unknown) => setError(parseApiError(e, "Could not adjust the points.")),
  });
  return (
    <div className="rounded-2xl border border-border bg-card p-5">
      <div className="flex items-center justify-between gap-3 mb-3">
        <p className="text-sm font-semibold" style={{ color: RETAIL_ACCENT }}>Loyalty points · <span className="text-foreground">{data?.balance ?? "…"}</span></p>
        <Can perm="retail.manage">
          <button onClick={() => setAdjusting((v) => !v)} className="text-xs font-semibold" style={{ color: RETAIL_ACCENT }}>Adjust points</button>
        </Can>
      </div>
      {adjusting && (
        <div className="mb-3 flex flex-wrap items-end gap-2 rounded-xl border border-border p-3">
          <div><label className="block text-[11px] text-muted-foreground">Points (+ add, − remove)</label>
            <input type="number" step="1" value={points} onChange={(e) => setPoints(e.target.value)} className="w-32 rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm" /></div>
          <div className="flex-1 min-w-[200px]"><label className="block text-[11px] text-muted-foreground">Reason (required)</label>
            <input value={reason} onChange={(e) => setReason(e.target.value)} className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm" /></div>
          <button onClick={() => adjust.mutate()} disabled={adjust.isPending || !Number(points) || reason.trim().length < 3}
            className="px-3 py-1.5 rounded-lg text-sm font-semibold text-white disabled:opacity-50" style={{ background: RETAIL_ACCENT }}>Save</button>
          {error && <p className="w-full text-xs text-destructive">{error}</p>}
        </div>
      )}
      {(data?.entries ?? []).length === 0 ? <p className="text-sm text-muted-foreground">No points yet.</p> : (
        <table className="w-full text-sm">
          <tbody>
            {(data?.entries ?? []).slice(0, 30).map((e) => (
              <tr key={e.id} className="border-t border-border first:border-0">
                <td className="py-1.5 pr-3 text-xs text-muted-foreground whitespace-nowrap">{fmtDate(e.created_at)}</td>
                <td className="py-1.5 pr-3">{ENTRY_LABEL[e.entry_type] ?? e.entry_type}</td>
                <td className="py-1.5 pr-3 text-xs">
                  {e.invoice_id ? <Link className="hover:underline" href={`/sales/retail/invoices/${e.invoice_id}`}>{e.invoice_number}</Link> : e.reason}
                  {e.expires_on && e.points > 0 && <span className="text-muted-foreground"> · expires {fmtDate(e.expires_on)}</span>}
                </td>
                <td className={`py-1.5 pr-3 text-right tabular-nums ${e.points < 0 ? "text-destructive" : ""}`}>{e.points > 0 ? `+${e.points}` : e.points}</td>
                <td className="py-1.5 text-right tabular-nums text-muted-foreground">{e.balance_after}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function RetailCustomerPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [collecting, setCollecting] = useState(false);
  const customer = useQuery({
    queryKey: ["retail-customer", id],
    queryFn: async () => (await api.get(`/retail/customers/${id}`)).data.data as RetailCustomer,
  });
  const invoices = useQuery({
    queryKey: ["retail-invoices", "customer", id],
    queryFn: async () => (await api.get("/retail/invoices", { params: { customer_id: id, page_size: 200 } })).data.data as InvoiceRow[],
  });
  const estimates = useQuery({
    queryKey: ["retail-estimates", "customer", id],
    queryFn: async () => (await api.get("/retail/estimates", { params: { customer_id: id, page_size: 100 } })).data.data as EstimateRow[],
  });
  const c = customer.data;
  const card = "rounded-2xl border border-border bg-card p-5";
  const label = "text-[11px] font-semibold uppercase tracking-wider text-muted-foreground";
  const avg = c && c.purchase_count ? Number(c.total_spent) / c.purchase_count : 0;

  return (
    <div className="p-8 space-y-6">
      {collecting && c && <CollectModal customerId={c.id} customerName={c.name} onClose={() => { setCollecting(false); qc.invalidateQueries({ queryKey: ["retail-customer", id] }); }} />}
      {editing && c && (
        <CustomerFormModal initial={{ ...c, id: c.id } as unknown as Record<string, string | null> & { id: string }}
          onClose={() => setEditing(false)}
          onSaved={() => { setEditing(false); qc.invalidateQueries({ queryKey: ["retail-customer", id] }); }} />
      )}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <Link href="/sales/retail/customers" className="rounded-lg p-2 hover:bg-muted" aria-label="Back"><ArrowLeft className="h-4 w-4" /></Link>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Retail customer</p>
            <h1 className="text-2xl font-bold tracking-tight">{c?.name ?? (customer.isLoading ? "Loading…" : "—")}</h1>
            {c && <p className="text-sm text-muted-foreground">{c.mobile}{c.status === "inactive" ? " · Inactive" : ""}</p>}
          </div>
        </div>
        <Can perm="retail.create">
          <div className="flex gap-2">
            {c && Number(c.outstanding) > 0 && (
              <Can perm="retail.collect">
                <button onClick={() => setCollecting(true)} className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2 text-sm font-semibold hover:bg-muted" style={{ color: RETAIL_ACCENT }}>
                  Collect payment
                </button>
              </Can>
            )}
            <button onClick={() => setEditing(true)} className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2 text-sm font-semibold hover:bg-muted">
              <Pencil className="h-4 w-4" /> Edit
            </button>
            <Link href="/sales/retail/bill" className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-white" style={{ background: RETAIL_ACCENT }}>
              <Receipt className="h-4 w-4" /> New bill
            </Link>
          </div>
        </Can>
      </div>

      {c && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
            {[
              ["Loyalty points", String(c.loyalty_points)],
              ["Bills", String(c.purchase_count)],
              ["Total spent", rupees(c.total_spent, 0)],
              ["Average bill", c.purchase_count ? rupees(avg, 0) : "—"],
              ["Items bought", String(Number(c.products_purchased))],
              ["Outstanding", Number(c.outstanding) > 0 ? rupees(c.outstanding) : "—"],
            ].map(([k, v]) => (
              <div key={k} className={card}><p className={label}>{k}</p><p className="mt-1 text-lg font-semibold tabular-nums">{v}</p></div>
            ))}
          </div>

          <div className={card}>
            <p className="text-sm font-semibold mb-3" style={{ color: RETAIL_ACCENT }}>Details</p>
            <dl className="grid gap-x-6 gap-y-2 text-sm md:grid-cols-3">
              {[
                ["Email", c.email], ["Date of birth", fmtDate(c.date_of_birth)], ["Gender", c.gender],
                ["Billing address", [c.billing_address, c.city, c.state, c.pincode].filter(Boolean).join(", ")],
                ["Shipping address", c.shipping_address], ["Registered", fmtDate(c.created_at)],
                ["Last purchase", fmtDate(c.last_purchase_date)], ["Notes", c.notes],
              ].map(([k, v]) => (
                <div key={k as string}><dt className="text-xs text-muted-foreground">{k}</dt><dd>{(v as string) || "—"}</dd></div>
              ))}
            </dl>
          </div>

          <PointsCard customerId={id} />

          <div className={card}>
            <p className="text-sm font-semibold mb-3" style={{ color: RETAIL_ACCENT }}>Purchase history</p>
            {(invoices.data ?? []).length === 0 ? <p className="text-sm text-muted-foreground">No bills yet.</p> : (
              <table className="w-full text-sm">
                <thead><tr className="text-left text-xs text-muted-foreground border-b border-border">
                  <th className="py-2 pr-3 font-medium">Bill</th><th className="py-2 pr-3 font-medium">Date</th>
                  <th className="py-2 pr-3 font-medium">Mode</th><th className="py-2 pr-3 font-medium">Status</th>
                  <th className="py-2 pr-3 font-medium text-right">Total</th><th className="py-2 font-medium text-right">Outstanding</th>
                </tr></thead>
                <tbody>
                  {(invoices.data ?? []).map((i) => (
                    <tr key={i.id} className="border-b border-border last:border-0">
                      <td className="py-2 pr-3"><Link className="font-medium hover:underline" href={`/sales/retail/invoices/${i.id}`}>{i.invoice_number}</Link></td>
                      <td className="py-2 pr-3">{fmtDate(i.invoice_date)}</td>
                      <td className="py-2 pr-3 capitalize">{i.payment_mode}</td>
                      <td className="py-2 pr-3">{i.status === "cancelled" ? <StatusBadge status="cancelled" /> : payStatusLabel(i.payment_status)}</td>
                      <td className="py-2 pr-3 text-right tabular-nums">{rupees(i.total_amount, 0)}</td>
                      <td className="py-2 text-right tabular-nums">{Number(i.outstanding) > 0 ? rupees(i.outstanding) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className={card}>
            <p className="text-sm font-semibold mb-3" style={{ color: RETAIL_ACCENT }}>Estimates</p>
            {(estimates.data ?? []).length === 0 ? <p className="text-sm text-muted-foreground">No estimates.</p> : (
              <div className="space-y-1.5">
                {(estimates.data ?? []).map((e) => (
                  <Link key={e.id} href={`/sales/retail/estimates/${e.id}`} className="flex justify-between text-sm hover:underline">
                    <span>{e.estimate_number} · {fmtDate(e.estimate_date)} · <span className="capitalize">{e.status}</span></span>
                    <span className="tabular-nums">{rupees(e.total_amount, 0)}</span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
