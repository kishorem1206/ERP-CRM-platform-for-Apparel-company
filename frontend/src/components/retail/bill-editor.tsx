"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, Trash2 } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { usePermissions } from "@/lib/permissions";
import { CustomerPicker } from "@/components/retail/customer-picker";
import { SearchableSelect } from "@/components/shared/searchable-select";
import {
  RETAIL_ACCENT, newClientRef, previewBill, previewLine, productLabel, rupees,
  couponText, daysToBirthday,
  type BillPreview, type DraftLine, type RetailCoupon, type RetailCustomer, type RetailEstimate, type RetailProduct, type RetailSettings,
} from "@/lib/retail";

const inputCls =
  "rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
export const COLLECTION_MODES = [
  { value: "cash", label: "Cash" }, { value: "upi", label: "UPI" },
  { value: "card", label: "Card" }, { value: "bank", label: "Bank transfer" },
];
const lineKey = (p: RetailProduct) => `${p.product_id}:${p.variant_id ?? ""}`;

/** Counter bill (mode "invoice") or estimate (mode "estimate"), GST-inclusive. */
export function BillEditor({ mode, estimate }: { mode: "invoice" | "estimate"; estimate?: RetailEstimate | null }) {
  const router = useRouter();
  const qc = useQueryClient();
  const { can } = usePermissions();
  const clientRef = useRef(newClientRef());
  const searchRef = useRef<HTMLInputElement>(null);

  const settings = useQuery({
    queryKey: ["retail-settings"],
    queryFn: async () => (await api.get("/retail/settings")).data.data as RetailSettings,
  });
  const [lines, setLines] = useState<DraftLine[]>([]);
  const [billPct, setBillPct] = useState("");
  const [customer, setCustomer] = useState<RetailCustomer | null>(null);
  const [paymentMode, setPaymentMode] = useState<"cash" | "credit">("cash");
  const [paidNow, setPaidNow] = useState("");
  const [collectionMode, setCollectionMode] = useState("cash");
  const [validUntil, setValidUntil] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");

  // Defaults: bill discount from settings; an estimate being edited loads its own lines.
  useEffect(() => {
    if (settings.data && billPct === "" && !estimate) setBillPct(String(Number(settings.data.default_discount_pct) || ""));
  }, [settings.data, billPct, estimate]);
  useEffect(() => {
    if (!estimate) return;
    setBillPct(String(Number(estimate.bill_discount_pct) || ""));
    setValidUntil(estimate.valid_until ?? "");
    setNotes(estimate.notes ?? "");
    setLines(estimate.items.map((i) => ({
      key: `${i.product_id}:${i.variant_id ?? ""}`,
      product: {
        product_id: i.product_id, variant_id: i.variant_id, name: i.description, sku: null, barcode: null,
        size: null, colour: null, mrp: i.unit_price, gst_rate: i.gst_rate, hsn_code: i.hsn_code, in_stock: "0",
      },
      quantity: String(Number(i.quantity)), discount: String(Number(i.item_discount_pct) || ""), price: i.unit_price,
    })));
    if (estimate.customer_id) {
      api.get(`/retail/customers/${estimate.customer_id}`).then((r) => setCustomer(r.data.data)).catch(() => undefined);
    }
  }, [estimate]);

  // Product search (name, SKU or a scanned barcode).
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(search.trim()), 200);
    return () => clearTimeout(t);
  }, [search]);
  const products = useQuery({
    queryKey: ["retail-products", debounced],
    queryFn: async () => (await api.get("/retail/products", { params: { search: debounced, limit: 20 } })).data.data as RetailProduct[],
    enabled: debounced.length >= 2,
  });

  function addProduct(p: RetailProduct) {
    setLines((prev) => {
      const existing = prev.find((l) => l.key === lineKey(p));
      if (existing) return prev.map((l) => (l === existing ? { ...l, quantity: String((Number(l.quantity) || 0) + 1) } : l));
      return [...prev, { key: lineKey(p), product: p, quantity: "1", discount: "", price: p.mrp ?? "" }];
    });
    setSearch("");
    setError("");
    searchRef.current?.focus();
  }
  const setLine = (key: string, patch: Partial<DraftLine>) => setLines((prev) => prev.map((l) => (l.key === key ? { ...l, ...patch } : l)));

  const bill = Number(billPct) || 0;
  const local = useMemo(() => previewBill(lines, bill), [lines, bill]);

  // Coupon and loyalty points (bills only). Applied values go to the server
  // preview, which works the bill out exactly as it will be saved.
  const [couponInput, setCouponInput] = useState("");
  const [couponCode, setCouponCode] = useState("");
  const [pointsInput, setPointsInput] = useState("");
  const [redeemPoints, setRedeemPoints] = useState(0);
  useEffect(() => { setCouponCode(""); setCouponInput(""); setRedeemPoints(0); setPointsInput(""); }, [customer?.id]);
  const coupons = useQuery({
    queryKey: ["retail-customer-coupons", customer?.id],
    queryFn: async () => (await api.get(`/retail/customers/${customer!.id}/coupons`)).data.data as RetailCoupon[],
    enabled: mode === "invoice" && !!customer,
  });
  const previewBody = JSON.stringify({
    customer_id: customer?.id ?? null, bill_discount_pct: bill, coupon_code: couponCode || null, redeem_points: redeemPoints,
    items: lines.filter((l) => Number(l.quantity) > 0).map((l) => ({
      product_id: l.product.product_id, variant_id: l.product.variant_id, quantity: Number(l.quantity),
      item_discount_pct: Number(l.discount) || 0, unit_price: l.product.mrp ? undefined : Number(l.price) || undefined,
    })),
  });
  const [debouncedPreview, setDebouncedPreview] = useState(previewBody);
  useEffect(() => { const t = setTimeout(() => setDebouncedPreview(previewBody), 300); return () => clearTimeout(t); }, [previewBody]);
  const wantPreview = mode === "invoice" && lines.length > 0 && (!!customer || !!couponCode);
  const preview = useQuery({
    queryKey: ["retail-bill-preview", debouncedPreview],
    queryFn: async () => (await api.post("/retail/invoices/preview", JSON.parse(debouncedPreview))).data.data as BillPreview,
    enabled: wantPreview && JSON.parse(debouncedPreview).items.length > 0,
    retry: false,
  });
  const previewError = wantPreview && preview.isError ? parseApiError(preview.error, "Could not work out this bill.") : "";
  const p = wantPreview && preview.data && !preview.isError ? preview.data : null;
  const totals = p ? {
    gross: Number(p.gross_amount), discount: Number(p.discount_amount), coupon: Number(p.coupon_discount),
    points: Number(p.points_discount), taxable: Number(p.taxable_amount),
    gst: Number(p.cgst_amount) + Number(p.sgst_amount), roundOff: Number(p.round_off), total: Number(p.total_amount),
  } : { ...local, coupon: 0, points: 0 };
  const bdayIn = daysToBirthday(customer?.date_of_birth ?? null);
  const lo = Number(settings.data?.min_discount_pct ?? 0);
  const hi = Number(settings.data?.max_discount_pct ?? 100);
  const canApprove = can("retail.discount_approve") && !!settings.data?.allow_approved_override;
  const discountProblem = (pct: number) =>
    pct > 0 && pct < lo ? `min ${lo}%` : pct > hi ? (canApprove ? "above max — you're approving it" : `max ${hi}%`) : "";

  const payload = () => ({
    customer_id: customer?.id ?? null,
    bill_discount_pct: bill,
    notes: notes || null,
    ...(mode === "invoice" ? { coupon_code: couponCode || null, redeem_points: redeemPoints } : {}),
    items: lines.map((l) => ({
      product_id: l.product.product_id, variant_id: l.product.variant_id,
      quantity: Number(l.quantity), item_discount_pct: Number(l.discount) || 0,
      unit_price: l.product.mrp ? undefined : Number(l.price) || undefined,
    })),
  });

  const save = useMutation({
    mutationFn: async () => {
      if (mode === "invoice") {
        return (await api.post("/retail/invoices", {
          ...payload(), client_ref: clientRef.current, payment_mode: paymentMode,
          amount_paid_now: paymentMode === "credit" && paidNow ? Number(paidNow) : null, collection_mode: collectionMode,
        })).data.data;
      }
      const body = { ...payload(), valid_until: validUntil || null };
      return estimate
        ? (await api.put(`/retail/estimates/${estimate.id}`, body)).data.data
        : (await api.post("/retail/estimates", body)).data.data;
    },
    onSuccess: (doc: { id: string }) => {
      qc.invalidateQueries({ queryKey: ["retail-invoices"] });
      qc.invalidateQueries({ queryKey: ["retail-estimates"] });
      qc.invalidateQueries({ queryKey: ["retail-products"] });
      router.push(mode === "invoice" ? `/sales/retail/invoices/${doc.id}` : `/sales/retail/estimates/${doc.id}`);
    },
    onError: (e: unknown) => setError(parseApiError(e, "Could not save.")),
  });

  function submit() {
    setError("");
    if (!lines.length) return setError("Add at least one item.");
    const bad = lines.find((l) => !(Number(l.quantity) > 0));
    if (bad) return setError(`Enter a quantity for ${productLabel(bad.product)}.`);
    const noPrice = lines.find((l) => !l.product.mrp && !(Number(l.price) > 0));
    if (noPrice) return setError(`${productLabel(noPrice.product)} has no MRP — enter its price.`);
    if (mode === "invoice" && paymentMode === "credit" && !customer) return setError("A credit bill needs a customer.");
    if (mode === "invoice" && paymentMode === "credit" && Number(paidNow) > totals.total) return setError("Paid now can't be more than the total.");
    if (previewError) return setError(previewError);
    save.mutate();
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
      {/* Items */}
      <div className="space-y-3 min-w-0">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input ref={searchRef} autoFocus value={search} onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                const first = products.data?.[0];
                if (first && (debounced === search.trim())) addProduct(first);
              }
            }}
            placeholder="Search product, SKU or scan barcode…"
            className="w-full rounded-xl border border-input bg-background pl-9 pr-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          {debounced.length >= 2 && search && (
            <div className="absolute z-20 mt-1 w-full max-h-72 overflow-y-auto rounded-xl border border-border bg-background shadow-xl">
              {products.isLoading && <p className="px-3 py-2 text-sm text-muted-foreground">Searching…</p>}
              {products.data?.length === 0 && <p className="px-3 py-2 text-sm text-muted-foreground">No finished goods match “{debounced}”.</p>}
              {(products.data ?? []).map((p) => (
                <button key={lineKey(p)} type="button" onClick={() => addProduct(p)}
                  className="w-full flex items-center justify-between gap-3 px-3 py-2 text-left hover:bg-muted/60">
                  <span className="min-w-0">
                    <span className="block text-sm font-medium truncate">{productLabel(p)}</span>
                    <span className="block text-[11px] text-muted-foreground">{[p.sku, p.barcode].filter(Boolean).join(" · ") || "—"}</span>
                  </span>
                  <span className="text-right shrink-0">
                    <span className="block text-sm tabular-nums">{p.mrp ? rupees(p.mrp, 0) : "No MRP"}</span>
                    <span className={`block text-[11px] ${Number(p.in_stock) > 0 ? "text-muted-foreground" : "text-destructive"}`}>
                      {Number(p.in_stock) > 0 ? `${Number(p.in_stock)} in stock` : "Out of stock"}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-border bg-card overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="px-3 py-2 font-medium">Item</th>
                <th className="px-3 py-2 font-medium text-right">MRP</th>
                <th className="px-3 py-2 font-medium text-right">Qty</th>
                <th className="px-3 py-2 font-medium text-right">Disc %</th>
                <th className="px-3 py-2 font-medium text-right">Amount</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {lines.length === 0 && (
                <tr><td colSpan={6} className="px-3 py-8 text-center text-sm text-muted-foreground">Search above to add items.</td></tr>
              )}
              {lines.map((l) => {
                const p = previewLine(l, bill);
                const warn = discountProblem(Number(l.discount) || 0);
                const stock = Number(l.product.in_stock);
                return (
                  <tr key={l.key} className="border-b border-border last:border-0 align-top">
                    <td className="px-3 py-2">
                      <p className="font-medium">{productLabel(l.product)}</p>
                      <p className="text-[11px] text-muted-foreground">
                        GST {Number(l.product.gst_rate)}%{mode === "invoice" && l.product.in_stock !== "0" ? ` · ${stock} in stock` : ""}
                      </p>
                      {mode === "invoice" && stock > 0 && Number(l.quantity) > stock && (
                        <p className="text-[11px] text-destructive">Only {stock} in stock</p>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {l.product.mrp ? rupees(l.product.mrp) : (
                        <input type="number" min="0" step="0.01" value={l.price} placeholder="Price"
                          onChange={(e) => setLine(l.key, { price: e.target.value })} className={`${inputCls} w-24 text-right`} />
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <input type="number" min="1" step="1" value={l.quantity}
                        onChange={(e) => setLine(l.key, { quantity: e.target.value })} className={`${inputCls} w-20 text-right`} />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <input type="number" min="0" max="100" step="0.5" value={l.discount} placeholder="0"
                        onChange={(e) => setLine(l.key, { discount: e.target.value })} className={`${inputCls} w-20 text-right`} />
                      {warn && <p className={`text-[11px] mt-0.5 ${warn.startsWith("above") ? "text-amber-600" : "text-destructive"}`}>{warn}</p>}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums font-medium">{rupees(p.net)}</td>
                    <td className="px-1 py-2">
                      <button type="button" onClick={() => setLines((prev) => prev.filter((x) => x.key !== l.key))}
                        className="p-1 text-muted-foreground hover:text-destructive" aria-label="Remove">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} placeholder="Notes (optional)"
          className="w-full rounded-xl border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none" />
      </div>

      {/* Customer, payment and totals */}
      <div className="space-y-4">
        <div className="rounded-2xl border border-border bg-card p-4 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Customer</p>
          <CustomerPicker value={customer} onChange={setCustomer} />
          {customer && bdayIn != null && bdayIn <= 7 && (
            <p className="text-xs font-semibold text-pink-600 dark:text-pink-400">
              {bdayIn === 0 ? "🎂 Birthday today!" : `🎂 Birthday in ${bdayIn} day${bdayIn === 1 ? "" : "s"}`}
            </p>
          )}
        </div>

        {mode === "invoice" && (
          <div className="rounded-2xl border border-border bg-card p-4 space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Coupon & points</p>
            <div className="flex gap-2">
              <input value={couponInput} onChange={(e) => setCouponInput(e.target.value.toUpperCase())} placeholder="Coupon code"
                className={`${inputCls} flex-1 uppercase`} />
              {couponCode ? (
                <button type="button" onClick={() => { setCouponCode(""); setCouponInput(""); }} className="px-3 rounded-lg border text-xs">Remove</button>
              ) : (
                <button type="button" disabled={!couponInput.trim()} onClick={() => setCouponCode(couponInput.trim())}
                  className="px-3 rounded-lg text-xs font-semibold text-white disabled:opacity-40" style={{ background: RETAIL_ACCENT }}>Apply</button>
              )}
            </div>
            {!couponCode && (coupons.data ?? []).length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {(coupons.data ?? []).slice(0, 6).map((c) => (
                  <button key={c.id} type="button" onClick={() => { setCouponInput(c.code); setCouponCode(c.code); }}
                    title={`${c.name} — ${couponText(c)}`}
                    className="rounded-full border border-dashed px-2.5 py-0.5 text-[11px] font-semibold hover:bg-muted"
                    style={{ borderColor: RETAIL_ACCENT, color: RETAIL_ACCENT }}>
                    {c.kind === "birthday" ? "🎂 " : ""}{c.code} · {couponText(c)}
                  </button>
                ))}
              </div>
            )}
            {customer && settings.data?.loyalty_enabled && (
              <div className="space-y-1.5 border-t border-border pt-3">
                <p className="text-xs text-muted-foreground">
                  Points balance <b className="text-foreground">{p?.points_balance ?? customer.loyalty_points}</b>
                  {p?.max_redeem_points != null && ` · can use up to ${p.max_redeem_points}`}
                  {` · 1 point = ${rupees(settings.data.point_value)}`}
                </p>
                <div className="flex gap-2">
                  <input type="number" min="0" step="1" value={pointsInput} onChange={(e) => setPointsInput(e.target.value)}
                    placeholder="Points to redeem" className={`${inputCls} flex-1`} />
                  {redeemPoints ? (
                    <button type="button" onClick={() => { setRedeemPoints(0); setPointsInput(""); }} className="px-3 rounded-lg border text-xs">Remove</button>
                  ) : (
                    <button type="button" disabled={!(Number(pointsInput) > 0)} onClick={() => setRedeemPoints(Math.floor(Number(pointsInput)))}
                      className="px-3 rounded-lg text-xs font-semibold text-white disabled:opacity-40" style={{ background: RETAIL_ACCENT }}>Redeem</button>
                  )}
                </div>
              </div>
            )}
            {previewError && <p className="text-xs text-destructive">{previewError}</p>}
          </div>
        )}

        <div className="rounded-2xl border border-border bg-card p-4 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <label className="text-sm">Bill discount %</label>
            <input type="number" min="0" max="100" step="0.5" value={billPct} placeholder="0"
              onChange={(e) => setBillPct(e.target.value)} className={`${inputCls} w-24 text-right`} />
          </div>
          {discountProblem(bill) && <p className="text-[11px] text-amber-600 -mt-2 text-right">{discountProblem(bill)}</p>}
          {settings.data && (
            <p className="text-[11px] text-muted-foreground">Discount allowed: {lo > 0 ? `${lo}–` : "up to "}{hi}%</p>
          )}
          <dl className="space-y-1 text-sm border-t border-border pt-3">
            <Row label="MRP value" value={rupees(totals.gross)} />
            {totals.discount > 0 && <Row label="Discount" value={`− ${rupees(totals.discount)}`} />}
            {totals.coupon > 0 && <Row label={`Coupon ${p?.coupon_code ?? ""}`} value={`− ${rupees(totals.coupon)}`} />}
            {totals.points > 0 && <Row label={`Points (${p?.points_redeemed ?? redeemPoints})`} value={`− ${rupees(totals.points)}`} />}
            <Row label="Taxable value" value={rupees(totals.taxable)} muted />
            <Row label="GST (incl.)" value={rupees(totals.gst)} muted />
            {totals.roundOff !== 0 && <Row label="Round off" value={rupees(totals.roundOff)} muted />}
          </dl>
          <div className="flex items-baseline justify-between border-t border-border pt-3">
            <span className="text-sm font-semibold">Total</span>
            <span className="text-2xl font-bold tabular-nums">{rupees(totals.total, 0)}</span>
          </div>
          {p && p.points_earned > 0 && (
            <p className="text-[11px] text-muted-foreground text-right">
              Earns {p.points_earned} point{p.points_earned === 1 ? "" : "s"}{paymentMode === "credit" ? " once fully paid" : ""}
            </p>
          )}
        </div>

        {mode === "invoice" ? (
          <div className="rounded-2xl border border-border bg-card p-4 space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Payment</p>
            <div className="grid grid-cols-2 gap-1 rounded-xl bg-muted/50 p-1">
              {(["cash", "credit"] as const).map((m) => (
                <button key={m} type="button" onClick={() => setPaymentMode(m)}
                  className="rounded-lg py-1.5 text-sm font-semibold"
                  style={paymentMode === m ? { background: RETAIL_ACCENT, color: "#fff" } : { color: "hsl(var(--muted-foreground))" }}>
                  {m === "cash" ? "Cash" : "Credit"}
                </button>
              ))}
            </div>
            {paymentMode === "credit" && (
              <div className="flex items-center justify-between gap-3">
                <label className="text-sm">Paid now (₹)</label>
                <input type="number" min="0" step="1" value={paidNow} placeholder="0"
                  onChange={(e) => setPaidNow(e.target.value)} className={`${inputCls} w-28 text-right`} />
              </div>
            )}
            {(paymentMode === "cash" || Number(paidNow) > 0) && (
              <div className="flex items-center justify-between gap-3">
                <label className="text-sm">Received by</label>
                <div className="w-40">
                  <SearchableSelect value={collectionMode} onChange={(v) => setCollectionMode(v || "cash")} accent={RETAIL_ACCENT}
                    options={COLLECTION_MODES} />
                </div>
              </div>
            )}
            {paymentMode === "credit" && (
              <p className="text-[11px] text-muted-foreground">
                Balance {rupees(Math.max(totals.total - (Number(paidNow) || 0), 0), 0)} due in {settings.data?.credit_days ?? 30} days.
              </p>
            )}
          </div>
        ) : (
          <div className="rounded-2xl border border-border bg-card p-4 space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Valid until</label>
            <input type="date" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} className={`${inputCls} w-full`} />
            <p className="text-[11px] text-muted-foreground">Leave blank for {settings.data?.estimate_validity_days ?? 7} days.</p>
          </div>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}
        <button type="button" onClick={submit} disabled={save.isPending}
          className="w-full rounded-xl py-3 text-sm font-semibold text-white disabled:opacity-60" style={{ background: RETAIL_ACCENT }}>
          {save.isPending ? "Saving…" : mode === "invoice" ? `Save bill · ${rupees(totals.total, 0)}` : estimate ? "Save estimate" : "Create estimate"}
        </button>
      </div>
    </div>
  );
}

function Row({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <div className={`flex justify-between ${muted ? "text-muted-foreground text-xs" : ""}`}>
      <dt>{label}</dt>
      <dd className="tabular-nums">{value}</dd>
    </div>
  );
}
