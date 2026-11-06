/** Retail Sales — shared types, formatting and the live bill preview.
 *  The server works the bill out again on save; these numbers are only for
 *  what the counter sees while building it. */

export interface RetailProduct {
  product_id: string; variant_id: string | null; name: string; sku: string | null; barcode: string | null;
  size: string | null; colour: string | null; mrp: string | null; gst_rate: string; hsn_code: string | null;
  in_stock: string;
}

export interface RetailCustomer {
  id: string; name: string; mobile: string; email: string | null; date_of_birth: string | null; gender: string | null;
  billing_address: string | null; shipping_address: string | null; city: string | null; state: string | null;
  pincode: string | null; status: string; notes: string | null; created_at: string;
  purchase_count: number; total_spent: string; products_purchased: string; last_purchase_date: string | null; outstanding: string;
}

export interface RetailLine {
  id: string; product_id: string; variant_id: string | null; description: string; hsn_code: string | null;
  quantity: string; unit_price: string; gross_amount: string; item_discount_pct: string; discount_amount: string;
  gst_rate: string; taxable_amount: string; cgst_amount: string; sgst_amount: string; net_amount: string;
}

export interface RetailTotals {
  bill_discount_pct: string; gross_amount: string; discount_amount: string; taxable_amount: string;
  cgst_amount: string; sgst_amount: string; round_off: string; total_amount: string; notes: string | null;
}

export interface RetailPayment {
  id: string; receipt_number: string; payment_date: string; amount: string; mode: string;
  reference: string | null; status: string; created_at: string;
}

export interface RetailInvoice extends RetailTotals {
  id: string; invoice_number: string; customer_id: string | null; customer_name: string | null; customer_mobile: string | null;
  invoice_date: string; payment_mode: "cash" | "credit"; payment_status: string; amount_paid: string; outstanding: string;
  due_date: string | null; status: string; estimate_id: string | null; cancel_reason: string | null; created_at: string;
  discount_approved: boolean; items: RetailLine[]; payments: RetailPayment[];
}

export interface RetailEstimate extends RetailTotals {
  id: string; estimate_number: string; customer_id: string | null; customer_name: string | null; customer_mobile: string | null;
  estimate_date: string; valid_until: string | null; status: string; converted_invoice_id: string | null;
  converted_invoice_number: string | null; created_at: string; items: RetailLine[];
}

export interface RetailSettings {
  min_discount_pct: string; max_discount_pct: string; default_discount_pct: string; allow_approved_override: boolean;
  warehouse_id: string | null; warehouse_name: string | null; credit_days: number; estimate_validity_days: number;
}

export const RETAIL_ACCENT = "#0049A7";

export const rupees = (v: number | string | null | undefined, digits = 2) =>
  v == null || v === "" ? "—"
    : new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: digits, minimumFractionDigits: digits }).format(Number(v));

export const payStatusLabel = (s: string) => ({ paid: "Paid", partially_paid: "Partially paid", unpaid: "Unpaid" }[s] ?? s);

export const newClientRef = () =>
  (typeof crypto !== "undefined" && "randomUUID" in crypto) ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;

const r2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;

export interface DraftLine {
  key: string; product: RetailProduct; quantity: string; discount: string; price: string;   // price used only without MRP
}

/** GST-inclusive line maths, same order as the server: item discount, then bill discount, then GST backed out. */
export function previewLine(line: DraftLine, billPct: number) {
  const price = line.product.mrp ? Number(line.product.mrp) : Number(line.price) || 0;
  const qty = Number(line.quantity) || 0;
  const gross = r2(price * qty);
  const afterItem = r2(gross * (100 - (Number(line.discount) || 0)) / 100);
  const net = r2(afterItem * (100 - billPct) / 100);
  const rate = Number(line.product.gst_rate) || 0;
  const taxable = r2(net * 100 / (100 + rate));
  return { price, gross, net, taxable, gst: r2(net - taxable) };
}

export function previewBill(lines: DraftLine[], billPct: number) {
  const rows = lines.map((l) => previewLine(l, billPct));
  const exact = r2(rows.reduce((s, r) => s + r.net, 0));
  const total = Math.round(exact);
  return {
    gross: r2(rows.reduce((s, r) => s + r.gross, 0)),
    discount: r2(rows.reduce((s, r) => s + (r.gross - r.net), 0)),
    taxable: r2(rows.reduce((s, r) => s + r.taxable, 0)),
    gst: r2(rows.reduce((s, r) => s + r.gst, 0)),
    roundOff: r2(total - exact),
    total,
  };
}

export const productLabel = (p: RetailProduct) => {
  const bits = [p.size, p.colour].filter(Boolean).join(" / ");
  return bits ? `${p.name} (${bits})` : p.name;
};
