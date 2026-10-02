"use client";

import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { ModalShell } from "@/components/shared/modal-shell";
import { useCustomerOptions } from "@/components/reports/filter-sources";

const INDIGO = "#0049A7";
const inputCls =
  "w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

interface ProductVariant {
  id: string;
  sku: string;
  colour_name: string | null;
  size_name: string | null;
}
interface ProductWithVariants {
  id: string;
  name: string;
  code: string;
  variants: ProductVariant[];
}

export interface PriceListItemEntry {
  id: string;
  product_id: string;
  variant_id: string | null;
  customer_id: string | null;
  min_quantity: string;
  max_quantity: string | null;
  unit_price: string;
  discount_pct: string;
  valid_from: string | null;
  valid_to: string | null;
}

export function PriceListItemModal({
  priceListId, initial, onClose,
}: {
  priceListId: string;
  initial?: PriceListItemEntry;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [productId, setProductId] = useState(initial?.product_id ?? "");
  const [variantId, setVariantId] = useState(initial?.variant_id ?? "");
  const [customerId, setCustomerId] = useState(initial?.customer_id ?? "");
  const [minQty, setMinQty] = useState(initial?.min_quantity ?? "0");
  const [maxQty, setMaxQty] = useState(initial?.max_quantity ?? "");
  const [unitPrice, setUnitPrice] = useState(initial?.unit_price ?? "");
  const [discountPct, setDiscountPct] = useState(initial?.discount_pct ?? "0");
  const [validFrom, setValidFrom] = useState(initial?.valid_from ?? "");
  const [validTo, setValidTo] = useState(initial?.valid_to ?? "");
  const [error, setError] = useState("");

  const { data: productsData } = useQuery({
    queryKey: ["products-for-pricelist"],
    queryFn: () => api.get("/products", { params: { page_size: 200 } }).then((r) => r.data),
  });
  const products: ProductWithVariants[] = productsData?.data ?? [];
  const selectedProduct = products.find((p) => p.id === productId);

  const customers = useCustomerOptions();

  const variantOptions = useMemo(
    () => (selectedProduct?.variants ?? []).map((v) => ({
      value: v.id,
      label: v.sku,
      meta: [v.colour_name, v.size_name].filter(Boolean).join(" / "),
    })),
    [selectedProduct],
  );

  const mutation = useMutation({
    mutationFn: async () => {
      const payload = {
        product_id: productId,
        variant_id: variantId || undefined,
        customer_id: customerId || undefined,
        min_quantity: minQty ? Number(minQty) : 0,
        max_quantity: maxQty ? Number(maxQty) : undefined,
        unit_price: Number(unitPrice),
        discount_pct: discountPct ? Number(discountPct) : 0,
        valid_from: validFrom || undefined,
        valid_to: validTo || undefined,
      };
      if (initial) {
        await api.patch(`/sales/price-lists/items/${initial.id}`, payload);
      } else {
        await api.post(`/sales/price-lists/${priceListId}/items`, payload);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["price-list-items", priceListId] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Failed to save");
    },
  });

  const canSave = productId && unitPrice && Number(unitPrice) > 0;

  return (
    <ModalShell maxWidth="max-w-md" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">{initial ? "Edit Price" : "Add Price"}</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Product <span className="text-destructive">*</span>
          </label>
          <SearchableSelect
            options={products.map((p) => ({ value: p.id, label: p.name, meta: p.code }))}
            value={productId}
            onChange={(v) => { setProductId(v); setVariantId(""); }}
            placeholder="Search product…"
            accent={INDIGO}
          />
        </div>
        {variantOptions.length > 0 && (
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Variant / SKU</label>
            <SearchableSelect
              options={variantOptions}
              value={variantId}
              onChange={setVariantId}
              placeholder="Any variant"
              accent={INDIGO}
            />
          </div>
        )}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Customer-Specific Override
          </label>
          <SearchableSelect
            options={customers}
            value={customerId}
            onChange={setCustomerId}
            placeholder="Generic — applies to all customers on this list"
            accent={INDIGO}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Min Qty</label>
            <input className={inputCls} type="number" min="0" value={minQty} onChange={(e) => setMinQty(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Max Qty</label>
            <input className={inputCls} type="number" min="0" placeholder="No limit" value={maxQty} onChange={(e) => setMaxQty(e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Unit Price (₹) <span className="text-destructive">*</span>
            </label>
            <input className={inputCls} type="number" min="0" step="0.01" value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Discount %</label>
            <input className={inputCls} type="number" min="0" max="100" step="0.01" value={discountPct} onChange={(e) => setDiscountPct(e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Valid From</label>
            <input className={inputCls} type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Valid To</label>
            <input className={inputCls} type="date" value={validTo} onChange={(e) => setValidTo(e.target.value)} />
          </div>
        </div>
        <p className="text-[11px] text-muted-foreground">
          Leave dates blank to use the price list&rsquo;s own validity window.
        </p>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => { setError(""); mutation.mutate(); }}
          disabled={!canSave || mutation.isPending}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </ModalShell>
  );
}
