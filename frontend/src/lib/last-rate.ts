import api from "@/lib/api";

export interface LastRate {
  unit_price: string;
  source: string;
  date: string | null;
  same_vendor: boolean;
}

/** Latest rate for a product: from this vendor, else any vendor, else its cost price. */
export async function fetchLastRate(productId: string, vendorId?: string): Promise<LastRate | null> {
  try {
    const res = await api.get("/purchase/last-rate", { params: { product_id: productId, vendor_id: vendorId || undefined } });
    return (res.data.data as LastRate | null) ?? null;
  } catch {
    return null;
  }
}

/** e.g. "Rate ₹120 from PO00012 · 27 Aug 2026" or "… (another vendor)". */
export function lastRateNote(r: LastRate): string {
  const price = `₹${Number(r.unit_price).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
  const when = r.date
    ? ` · ${new Date(`${r.date}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}`
    : "";
  const whose = r.date && !r.same_vendor ? " (another vendor)" : "";
  return `Rate ${price} from ${r.source}${when}${whose}`;
}
