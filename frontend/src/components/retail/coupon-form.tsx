"use client";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { ModalShell } from "@/components/shared/modal-shell";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { RETAIL_ACCENT, type RetailCoupon } from "@/lib/retail";

const inputCls = "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
const iso = (d: Date) => d.toISOString().slice(0, 10);

/** Create or edit a coupon. Leaving products and categories empty = whole bill. */
export function CouponFormModal({ coupon, onClose, onSaved }: { coupon?: RetailCoupon | null; onClose: () => void; onSaved: () => void }) {
  const today = new Date();
  const [f, setF] = useState({
    code: coupon?.code ?? "", name: coupon?.name ?? "", description: coupon?.description ?? "",
    kind: (coupon?.kind === "promo" ? "promo" : "manual") as "manual" | "promo",
    discount_type: coupon?.discount_type ?? "percent", discount_value: coupon ? String(Number(coupon.discount_value)) : "",
    min_purchase: coupon ? String(Number(coupon.min_purchase)) : "", max_discount: coupon?.max_discount ? String(Number(coupon.max_discount)) : "",
    start_date: coupon?.start_date ?? iso(today), expiry_date: coupon?.expiry_date ?? iso(new Date(today.getTime() + 30 * 86400000)),
    max_uses: coupon?.max_uses ? String(coupon.max_uses) : "", per_customer_limit: coupon?.per_customer_limit ? String(coupon.per_customer_limit) : "",
    status: coupon?.status ?? "active",
  });
  const [productIds, setProductIds] = useState<string[]>(coupon?.product_ids ?? []);
  const [categoryIds, setCategoryIds] = useState<string[]>(coupon?.category_ids ?? []);
  const [error, setError] = useState("");
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF((x) => ({ ...x, [k]: e.target.value }));

  const products = useQuery({
    queryKey: ["products", "finished"],
    queryFn: async () => (await api.get("/products", { params: { page_size: 200, product_type: "finished_good" } })).data.data as { id: string; name: string }[],
  });
  const categories = useQuery({
    queryKey: ["master-categories"],
    queryFn: async () => (await api.get("/master/categories")).data.data as { id: string; name: string }[],
  });

  const save = useMutation({
    mutationFn: async () => {
      const body = {
        ...f, code: f.code.trim(), description: f.description || null,
        discount_value: Number(f.discount_value), min_purchase: Number(f.min_purchase) || 0,
        max_discount: f.max_discount ? Number(f.max_discount) : null,
        max_uses: f.max_uses ? Number(f.max_uses) : null, per_customer_limit: f.per_customer_limit ? Number(f.per_customer_limit) : null,
        product_ids: productIds, category_ids: categoryIds, customer_id: coupon?.customer_id ?? null,
      };
      return coupon ? api.put(`/retail/coupons/${coupon.id}`, body) : api.post("/retail/coupons", body);
    },
    onSuccess: onSaved,
    onError: (e: unknown) => setError(parseApiError(e, "Could not save this coupon.")),
  });

  const chips = (ids: string[], list: { id: string; name: string }[] | undefined, remove: (id: string) => void) => (
    <div className="flex flex-wrap gap-1 mt-1">
      {ids.map((id) => (
        <span key={id} className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[11px]">
          {(list ?? []).find((x) => x.id === id)?.name ?? "…"}
          <button type="button" onClick={() => remove(id)} aria-label="Remove"><X className="h-3 w-3" /></button>
        </span>
      ))}
    </div>
  );

  return (
    <ModalShell maxWidth="max-w-2xl" onClose={onClose}>
      <div className="flex items-center justify-between px-5 py-4 border-b">
        <h2 className="font-semibold">{coupon ? `Edit coupon ${coupon.code}` : "New coupon"}</h2>
        <button onClick={onClose} aria-label="Close"><X className="h-4 w-4" /></button>
      </div>
      <form className="p-5 space-y-3" onSubmit={(e) => { e.preventDefault(); setError(""); save.mutate(); }}>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="text-xs text-muted-foreground">Code *</label>
            <input required className={`${inputCls} uppercase`} value={f.code} onChange={(e) => setF((x) => ({ ...x, code: e.target.value.toUpperCase() }))} placeholder="DIWALI10" /></div>
          <div><label className="text-xs text-muted-foreground">Name *</label><input required className={inputCls} value={f.name} onChange={set("name")} placeholder="Diwali offer" /></div>
        </div>
        <div><label className="text-xs text-muted-foreground">Description</label><input className={inputCls} value={f.description} onChange={set("description")} /></div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-muted-foreground">Discount type</label>
            <SearchableSelect value={f.discount_type} onChange={(v) => setF((x) => ({ ...x, discount_type: (v || "percent") as "percent" | "fixed" }))} accent={RETAIL_ACCENT}
              options={[{ value: "percent", label: "Percentage" }, { value: "fixed", label: "Fixed amount (₹)" }]} />
          </div>
          <div><label className="text-xs text-muted-foreground">{f.discount_type === "percent" ? "Discount % *" : "Discount ₹ *"}</label>
            <input required type="number" min="0.01" step="0.01" className={inputCls} value={f.discount_value} onChange={set("discount_value")} /></div>
          <div><label className="text-xs text-muted-foreground">Max discount ₹</label>
            <input type="number" min="0" step="1" className={inputCls} value={f.max_discount} onChange={set("max_discount")} placeholder="No cap" /></div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div><label className="text-xs text-muted-foreground">Minimum purchase ₹</label><input type="number" min="0" className={inputCls} value={f.min_purchase} onChange={set("min_purchase")} placeholder="0" /></div>
          <div><label className="text-xs text-muted-foreground">Starts *</label><input required type="date" className={inputCls} value={f.start_date} onChange={set("start_date")} /></div>
          <div><label className="text-xs text-muted-foreground">Expires *</label><input required type="date" className={inputCls} value={f.expiry_date} onChange={set("expiry_date")} /></div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div><label className="text-xs text-muted-foreground">Total uses allowed</label><input type="number" min="1" className={inputCls} value={f.max_uses} onChange={set("max_uses")} placeholder="Unlimited" /></div>
          <div><label className="text-xs text-muted-foreground">Uses per customer</label><input type="number" min="1" className={inputCls} value={f.per_customer_limit} onChange={set("per_customer_limit")} placeholder="Unlimited" /></div>
          <div>
            <label className="text-xs text-muted-foreground">Status</label>
            <SearchableSelect value={f.status} onChange={(v) => setF((x) => ({ ...x, status: v || "active" }))} accent={RETAIL_ACCENT}
              options={[{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }]} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-muted-foreground">Only these products</label>
            <SearchableSelect value="" onChange={(v) => v && setProductIds((x) => (x.includes(v) ? x : [...x, v]))} accent={RETAIL_ACCENT}
              placeholder="Any product" options={(products.data ?? []).filter((p) => !productIds.includes(p.id)).map((p) => ({ value: p.id, label: p.name }))} />
            {chips(productIds, products.data, (id) => setProductIds((x) => x.filter((y) => y !== id)))}
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Only these categories</label>
            <SearchableSelect value="" onChange={(v) => v && setCategoryIds((x) => (x.includes(v) ? x : [...x, v]))} accent={RETAIL_ACCENT}
              placeholder="Any category" options={(categories.data ?? []).filter((c) => !categoryIds.includes(c.id)).map((c) => ({ value: c.id, label: c.name }))} />
            {chips(categoryIds, categories.data, (id) => setCategoryIds((x) => x.filter((y) => y !== id)))}
          </div>
        </div>
        <p className="text-[11px] text-muted-foreground">With no products or categories picked, the coupon applies to the whole bill. The minimum purchase is checked on the items it applies to.</p>
        {coupon?.customer_name && <p className="text-xs">Assigned to <b>{coupon.customer_name}</b> only.</p>}
        {error && <p className="text-xs text-destructive">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-xl border text-sm">Cancel</button>
          <button type="submit" disabled={save.isPending} className="px-4 py-2 rounded-xl text-sm font-semibold text-white disabled:opacity-50" style={{ background: RETAIL_ACCENT }}>
            {save.isPending ? "Saving…" : "Save coupon"}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}
