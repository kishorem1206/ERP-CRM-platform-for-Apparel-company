"use client";
import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Pencil, Receipt } from "lucide-react";
import api from "@/lib/api";
import { Can } from "@/lib/permissions";
import { CustomerFormModal } from "@/components/retail/customer-form";
import { StatusBadge } from "@/components/shared/status-badge";
import { fmtDate } from "@/components/documents/pdf-document-page";
import { RETAIL_ACCENT, payStatusLabel, rupees, type RetailCustomer } from "@/lib/retail";

interface InvoiceRow { id: string; invoice_number: string; invoice_date: string; payment_mode: string; payment_status: string; total_amount: string; outstanding: string; status: string }
interface EstimateRow { id: string; estimate_number: string; estimate_date: string; status: string; total_amount: string }

export default function RetailCustomerPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
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
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            {[
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
