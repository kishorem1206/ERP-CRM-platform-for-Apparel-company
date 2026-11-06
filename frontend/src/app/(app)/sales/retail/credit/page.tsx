"use client";
import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Search } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { Can } from "@/lib/permissions";
import { exportRowsToCsv } from "@/lib/csv-export";
import { StatusBadge } from "@/components/shared/status-badge";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { CollectModal } from "@/components/retail/collect-modal";
import { fmtDate } from "@/components/documents/pdf-document-page";
import {
  AGING_BUCKETS, RETAIL_ACCENT, collectionStatusLabel, rupees,
  type Collection, type CreditRow, type CreditSummary, type CustomerAging,
} from "@/lib/retail";

const TABS = ["Bills", "By customer", "Collections"] as const;
const OVERDUE = [
  { value: "", label: "Any due date" }, { value: "0-0", label: "Not yet due" }, { value: "1-30", label: "1–30 days overdue" },
  { value: "31-60", label: "31–60 days overdue" }, { value: "61-90", label: "61–90 days overdue" }, { value: "91-", label: "Over 90 days overdue" },
];
const badge = (s: string) => ({ overdue: "rejected", unpaid: "pending", partially_paid: "partial", paid: "completed" }[s] ?? s);
const csvButton = "inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-semibold hover:bg-muted";

export default function RetailCreditPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<(typeof TABS)[number]>("Bills");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [overdue, setOverdue] = useState("");
  const [minOwed, setMinOwed] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [collecting, setCollecting] = useState<{ id: string; name: string } | null>(null);
  const [cancelError, setCancelError] = useState("");

  const summary = useQuery({ queryKey: ["retail-credit-summary"], queryFn: async () => (await api.get("/retail/credit/summary")).data.data as CreditSummary });
  const [lo, hi] = overdue ? overdue.split("-") : ["", ""];
  const register = useQuery({
    queryKey: ["retail-credit-register", search, status, overdue, minOwed, from, to],
    queryFn: async () => (await api.get("/retail/credit/register", { params: {
      search: search || undefined, status: status || undefined,
      min_days_overdue: overdue ? Number(lo) : undefined, max_days_overdue: overdue && hi ? Number(hi) : undefined,
      min_outstanding: minOwed || undefined, from_date: from || undefined, to_date: to || undefined,
    } })).data.data as CreditRow[],
    enabled: tab === "Bills",
  });
  const customers = useQuery({
    queryKey: ["retail-credit-customers"],
    queryFn: async () => (await api.get("/retail/credit/customers")).data.data as CustomerAging[],
    enabled: tab === "By customer",
  });
  const collections = useQuery({
    queryKey: ["retail-collections", from, to],
    queryFn: async () => (await api.get("/retail/credit/collections", { params: { from_date: from || undefined, to_date: to || undefined } })).data.data as Collection[],
    enabled: tab === "Collections",
  });
  const cancelPayment = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => api.post(`/retail/payments/${id}/cancel`, { reason }),
    onSuccess: () => {
      setCancelError("");
      ["retail-collections", "retail-credit-summary", "retail-credit-register", "retail-credit-customers"].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
    },
    onError: (e: unknown) => setCancelError(parseApiError(e, "Could not cancel this payment.")),
  });

  const s = summary.data;
  const agingTotal = s ? AGING_BUCKETS.reduce((t, b) => t + Number(s.aging[b.key] ?? 0), 0) : 0;
  const card = (label: string, value: string, tone?: string) => (
    <div className="rounded-2xl border border-border bg-card p-4">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className={`mt-1 text-lg font-semibold tabular-nums ${tone ?? ""}`}>{value}</p>
    </div>
  );

  return (
    <div className="p-8 space-y-6">
      {collecting && <CollectModal customerId={collecting.id} customerName={collecting.name} onClose={() => setCollecting(null)} />}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / RETAIL</p>
        <h1 className="text-2xl font-bold tracking-tight">Credit Register</h1>
        <p className="text-sm text-muted-foreground mt-1">What retail customers owe on credit bills, how old it is, and what&apos;s been collected. Collections are not counted as sales.</p>
      </div>

      {s && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
            {card("Outstanding", rupees(s.total_outstanding, 0))}
            {card("Overdue", rupees(s.total_overdue, 0), Number(s.total_overdue) > 0 ? "text-destructive" : "")}
            {card("Collected today", rupees(s.collections_today, 0))}
            {card("Credit sales", rupees(s.total_credit_sales, 0))}
            {card("Customers owing", String(s.customers_with_outstanding))}
            {card("Overdue bills", String(s.overdue_invoices))}
          </div>
          <div className="rounded-2xl border border-border bg-card p-4 space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Aging (by due date)</p>
            {agingTotal > 0 && (
              <div className="flex h-3 overflow-hidden rounded-full bg-muted">
                {AGING_BUCKETS.map((b, i) => {
                  const v = Number(s.aging[b.key] ?? 0);
                  return v > 0 ? <div key={b.key} style={{ width: `${(v / agingTotal) * 100}%`, background: ["#0F78FF", "#F5B400", "#F58A07", "#E5484D", "#9B1C1C"][i] }} title={`${b.label}: ${rupees(v, 0)}`} /> : null;
                })}
              </div>
            )}
            <div className="grid grid-cols-2 gap-2 md:grid-cols-5 text-sm">
              {AGING_BUCKETS.map((b) => (
                <div key={b.key}><span className="text-xs text-muted-foreground">{b.label}</span><p className="font-semibold tabular-nums">{rupees(s.aging[b.key] ?? 0, 0)}</p></div>
              ))}
            </div>
          </div>
        </>
      )}

      <div className="flex flex-wrap items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${tab === t ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>{t}</button>
        ))}
      </div>

      {tab === "Bills" && (
        <div className="space-y-3">
          <div className="grid gap-2 md:grid-cols-6">
            <div className="relative md:col-span-2">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <input className="w-full rounded-lg border border-input bg-background pl-8 pr-3 py-2 text-sm" placeholder="Bill #, customer or mobile…" value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            <SearchableSelect clearable value={status} onChange={setStatus} accent={RETAIL_ACCENT} placeholder="Any status"
              options={["unpaid", "partially_paid", "overdue"].map((x) => ({ value: x, label: collectionStatusLabel(x) }))} />
            <SearchableSelect value={overdue} onChange={setOverdue} accent={RETAIL_ACCENT} options={OVERDUE} />
            <input type="number" min="0" className="rounded-lg border border-input bg-background px-3 py-2 text-sm" placeholder="Owes at least ₹" value={minOwed} onChange={(e) => setMinOwed(e.target.value)} />
            <div className="flex gap-1">
              <input type="date" title="Billed from" className="w-full rounded-lg border border-input bg-background px-2 py-2 text-xs" value={from} onChange={(e) => setFrom(e.target.value)} />
              <input type="date" title="Billed to" className="w-full rounded-lg border border-input bg-background px-2 py-2 text-xs" value={to} onChange={(e) => setTo(e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end">
            <button className={csvButton} onClick={() => exportRowsToCsv("credit-register", [
              { key: "invoice_number", header: "Bill" }, { key: "invoice_date", header: "Date" }, { key: "customer_name", header: "Customer" },
              { key: "customer_mobile", header: "Mobile" }, { key: "invoice_amount", header: "Bill amount" }, { key: "amount_paid", header: "Paid" },
              { key: "outstanding", header: "Outstanding" }, { key: "due_date", header: "Due" }, { key: "days_overdue", header: "Days overdue" },
              { key: "status", header: "Status" },
            ], (register.data ?? []) as unknown as Record<string, unknown>[])}><Download className="h-3.5 w-3.5" /> Export CSV</button>
          </div>
          <div className="bg-card border border-border rounded-2xl overflow-x-auto">
            <table className="w-full min-w-[900px] text-sm">
              <thead><tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="px-4 py-3 font-medium">Bill</th><th className="px-4 py-3 font-medium">Customer</th>
                <th className="px-4 py-3 font-medium text-right">Bill amount</th><th className="px-4 py-3 font-medium text-right">Paid</th>
                <th className="px-4 py-3 font-medium text-right">Outstanding</th><th className="px-4 py-3 font-medium">Due</th>
                <th className="px-4 py-3 font-medium text-right">Overdue</th><th className="px-4 py-3 font-medium">Status</th><th></th>
              </tr></thead>
              <tbody>
                {register.isLoading && <tr><td colSpan={9} className="px-4 py-6 text-center text-muted-foreground">Loading…</td></tr>}
                {!register.isLoading && (register.data ?? []).length === 0 && <tr><td colSpan={9} className="px-4 py-6 text-center text-muted-foreground">Nothing outstanding</td></tr>}
                {(register.data ?? []).map((r) => (
                  <tr key={r.invoice_id} className="border-b border-border last:border-0">
                    <td className="px-4 py-2.5"><Link className="font-medium hover:underline" href={`/sales/retail/invoices/${r.invoice_id}`}>{r.invoice_number}</Link><p className="text-xs text-muted-foreground">{fmtDate(r.invoice_date)}</p></td>
                    <td className="px-4 py-2.5">{r.customer_name}<p className="text-xs text-muted-foreground">{r.customer_mobile}</p></td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{rupees(r.invoice_amount, 0)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{rupees(r.amount_paid, 0)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums font-semibold">{rupees(r.outstanding)}</td>
                    <td className="px-4 py-2.5">{fmtDate(r.due_date)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{r.days_overdue > 0 ? `${r.days_overdue} d` : "—"}</td>
                    <td className="px-4 py-2.5"><StatusBadge status={badge(r.status)} label={collectionStatusLabel(r.status)} /></td>
                    <td className="px-4 py-2.5 text-right">
                      {r.customer_id && (
                        <Can perm="retail.collect">
                          <button onClick={() => setCollecting({ id: r.customer_id!, name: r.customer_name ?? "customer" })} className="text-xs font-semibold" style={{ color: RETAIL_ACCENT }}>Collect</button>
                        </Can>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "By customer" && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <button className={csvButton} onClick={() => exportRowsToCsv("credit-aging-by-customer", [
              { key: "customer_name", header: "Customer" }, { key: "customer_mobile", header: "Mobile" }, { key: "bills", header: "Bills" },
              { key: "outstanding", header: "Outstanding" }, ...AGING_BUCKETS.map((b) => ({ key: b.key, header: b.label })),
              { key: "oldest_due", header: "Oldest due" },
            ], (customers.data ?? []) as unknown as Record<string, unknown>[])}><Download className="h-3.5 w-3.5" /> Export CSV</button>
          </div>
          <div className="bg-card border border-border rounded-2xl overflow-x-auto">
            <table className="w-full min-w-[900px] text-sm">
              <thead><tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="px-4 py-3 font-medium">Customer</th><th className="px-4 py-3 font-medium text-right">Bills</th>
                <th className="px-4 py-3 font-medium text-right">Outstanding</th>
                {AGING_BUCKETS.map((b) => <th key={b.key} className="px-4 py-3 font-medium text-right">{b.label}</th>)}<th></th>
              </tr></thead>
              <tbody>
                {(customers.data ?? []).length === 0 && <tr><td colSpan={9} className="px-4 py-6 text-center text-muted-foreground">Nobody owes anything</td></tr>}
                {(customers.data ?? []).map((c) => (
                  <tr key={c.customer_id} className="border-b border-border last:border-0">
                    <td className="px-4 py-2.5"><Link className="font-medium hover:underline" href={`/sales/retail/customers/${c.customer_id}`}>{c.customer_name}</Link><p className="text-xs text-muted-foreground">{c.customer_mobile}</p></td>
                    <td className="px-4 py-2.5 text-right">{c.bills}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums font-semibold">{rupees(c.outstanding, 0)}</td>
                    {AGING_BUCKETS.map((b) => <td key={b.key} className={`px-4 py-2.5 text-right tabular-nums ${Number(c[b.key]) > 0 && b.key !== "not_due" ? "text-destructive" : "text-muted-foreground"}`}>{Number(c[b.key]) > 0 ? rupees(c[b.key], 0) : "—"}</td>)}
                    <td className="px-4 py-2.5 text-right">
                      <Can perm="retail.collect">
                        <button onClick={() => setCollecting({ id: c.customer_id, name: c.customer_name ?? "customer" })} className="text-xs font-semibold" style={{ color: RETAIL_ACCENT }}>Collect</button>
                      </Can>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "Collections" && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <input type="date" className="rounded-lg border border-input bg-background px-2 py-2 text-xs" value={from} onChange={(e) => setFrom(e.target.value)} />
            <span className="text-xs text-muted-foreground">to</span>
            <input type="date" className="rounded-lg border border-input bg-background px-2 py-2 text-xs" value={to} onChange={(e) => setTo(e.target.value)} />
            <span className="text-sm text-muted-foreground ml-2">
              Total {rupees((collections.data ?? []).filter((c) => c.status === "active").reduce((t, c) => t + Number(c.amount), 0), 0)}
            </span>
            <button className={`${csvButton} ml-auto`} onClick={() => exportRowsToCsv("credit-collections", [
              { key: "receipt_number", header: "Receipt" }, { key: "payment_date", header: "Date" }, { key: "customer_name", header: "Customer" },
              { key: "invoice_number", header: "Bill" }, { key: "amount", header: "Amount" }, { key: "mode", header: "Mode" },
              { key: "reference", header: "Reference" }, { key: "status", header: "Status" },
            ], (collections.data ?? []) as unknown as Record<string, unknown>[])}><Download className="h-3.5 w-3.5" /> Export CSV</button>
          </div>
          {cancelError && <p className="text-sm text-destructive">{cancelError}</p>}
          <div className="bg-card border border-border rounded-2xl overflow-x-auto">
            <table className="w-full min-w-[800px] text-sm">
              <thead><tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="px-4 py-3 font-medium">Receipt</th><th className="px-4 py-3 font-medium">Date</th>
                <th className="px-4 py-3 font-medium">Customer</th><th className="px-4 py-3 font-medium">Bill</th>
                <th className="px-4 py-3 font-medium">Mode</th><th className="px-4 py-3 font-medium text-right">Amount</th><th></th>
              </tr></thead>
              <tbody>
                {(collections.data ?? []).length === 0 && <tr><td colSpan={7} className="px-4 py-6 text-center text-muted-foreground">No collections</td></tr>}
                {(collections.data ?? []).map((c) => (
                  <tr key={c.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-2.5"><Link className="font-mono text-xs hover:underline" href={`/sales/retail/receipts/${c.batch_ref}`}>{c.receipt_number}</Link></td>
                    <td className="px-4 py-2.5">{fmtDate(c.payment_date)}</td>
                    <td className="px-4 py-2.5">{c.customer_name}</td>
                    <td className="px-4 py-2.5"><Link className="hover:underline" href={`/sales/retail/invoices/${c.invoice_id}`}>{c.invoice_number}</Link></td>
                    <td className="px-4 py-2.5 capitalize">{c.mode}{c.reference ? ` · ${c.reference}` : ""}</td>
                    <td className={`px-4 py-2.5 text-right tabular-nums ${c.status !== "active" ? "line-through text-muted-foreground" : ""}`} title={c.cancel_reason ?? undefined}>{rupees(c.amount)}</td>
                    <td className="px-4 py-2.5 text-right">
                      {c.status === "active" ? (
                        <Can perm="retail.manage">
                          <button className="text-xs text-destructive font-semibold" onClick={() => {
                            const reason = prompt(`Cancel ${rupees(c.amount)} on ${c.invoice_number}? Give the reason:`);
                            if (reason && reason.trim().length >= 3) cancelPayment.mutate({ id: c.id, reason: reason.trim() });
                          }}>Cancel</button>
                        </Can>
                      ) : <span className="text-xs text-muted-foreground">Cancelled</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
