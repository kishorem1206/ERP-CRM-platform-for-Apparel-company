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
  loyalty_points: number;
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
  reference: string | null; status: string; created_at: string; batch_ref: string | null; cancel_reason: string | null;
}

export interface RetailInvoice extends RetailTotals {
  id: string; invoice_number: string; customer_id: string | null; customer_name: string | null; customer_mobile: string | null;
  invoice_date: string; payment_mode: "cash" | "credit"; payment_status: string; amount_paid: string; outstanding: string;
  due_date: string | null; status: string; estimate_id: string | null; cancel_reason: string | null; created_at: string;
  discount_approved: boolean; items: RetailLine[]; payments: RetailPayment[];
  coupon_code: string | null; coupon_discount: string; points_redeemed: number; points_discount: string;
  points_earned: number; points_awarded: boolean;
  returned_amount: string; refunded_amount: string; points_returned: number; returned_qty: Record<string, string>;
}

export interface RetailEstimate extends RetailTotals {
  id: string; estimate_number: string; customer_id: string | null; customer_name: string | null; customer_mobile: string | null;
  estimate_date: string; valid_until: string | null; status: string; converted_invoice_id: string | null;
  converted_invoice_number: string | null; created_at: string; items: RetailLine[];
}

export interface RetailSettings {
  min_discount_pct: string; max_discount_pct: string; default_discount_pct: string; allow_approved_override: boolean;
  warehouse_id: string | null; warehouse_name: string | null; credit_days: number; estimate_validity_days: number;
  loyalty_enabled: boolean; amount_per_point: string; min_bill_for_points: string; min_redeem_points: number;
  point_value: string; max_redeem_pct: string; points_expiry_days: number; loyalty_excluded_category_ids: string[];
  birthday_enabled: boolean; birthday_discount_type: "percent" | "fixed"; birthday_discount_value: string;
  birthday_min_purchase: string; birthday_max_discount: string | null; birthday_window: "week" | "month"; birthday_lead_days: number;
}

export interface RetailCoupon {
  id: string; code: string; name: string; description: string | null; kind: string;
  discount_type: "percent" | "fixed"; discount_value: string; min_purchase: string; max_discount: string | null;
  start_date: string; expiry_date: string; max_uses: number | null; per_customer_limit: number | null;
  product_ids: string[]; category_ids: string[]; customer_id: string | null; customer_name: string | null;
  birthday_year: number | null; status: string; state: string; times_used: number; total_discount: string; created_at: string;
}

export interface BillPreview {
  gross_amount: string; discount_amount: string; coupon_code: string | null; coupon_discount: string;
  points_redeemed: number; points_discount: string; taxable_amount: string; cgst_amount: string; sgst_amount: string;
  round_off: string; total_amount: string; points_earned: number; points_balance: number | null; max_redeem_points: number | null;
}

export const couponText = (c: Pick<RetailCoupon, "discount_type" | "discount_value" | "max_discount" | "min_purchase">) =>
  (c.discount_type === "percent" ? `${Number(c.discount_value)}% off` : `${rupees(c.discount_value, 0)} off`)
  + (c.max_discount ? ` (max ${rupees(c.max_discount, 0)})` : "")
  + (Number(c.min_purchase) > 0 ? ` on ${rupees(c.min_purchase, 0)}+` : "");

/** Days until the next birthday (0 = today), or null without a date of birth. */
export function daysToBirthday(dob: string | null, today = new Date()): number | null {
  if (!dob) return null;
  const [, m, d] = dob.split("-").map(Number);
  const t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  let next = new Date(t.getFullYear(), m - 1, d);
  if (next < t) next = new Date(t.getFullYear() + 1, m - 1, d);
  return Math.round((next.getTime() - t.getTime()) / 86400000);
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


// ── Stage 3: credit collections and returns ─────────────────────────────────

export const AGING_BUCKETS: { key: "not_due" | "d1_30" | "d31_60" | "d61_90" | "d90_plus"; label: string }[] = [
  { key: "not_due", label: "Not yet due" }, { key: "d1_30", label: "1–30 days" }, { key: "d31_60", label: "31–60 days" },
  { key: "d61_90", label: "61–90 days" }, { key: "d90_plus", label: "Over 90 days" },
];

export interface CreditRow {
  invoice_id: string; invoice_number: string; invoice_date: string; customer_id: string | null; customer_name: string | null;
  customer_mobile: string | null; invoice_amount: string; amount_paid: string; outstanding: string; due_date: string | null;
  days_overdue: number; bucket: string | null; status: "unpaid" | "partially_paid" | "paid" | "overdue";
}

export interface CreditSummary {
  total_outstanding: string; total_credit_sales: string; credit_bills: number; collected_in_period: string;
  collections_today: string; total_overdue: string; customers_with_outstanding: number; overdue_invoices: number;
  aging: Record<string, string>;
}

export interface CustomerAging {
  customer_id: string; customer_name: string | null; customer_mobile: string | null; bills: number; outstanding: string;
  oldest_due: string | null; not_due: string; d1_30: string; d31_60: string; d61_90: string; d90_plus: string;
}

export interface Collection {
  id: string; receipt_number: string; batch_ref: string; payment_date: string; amount: string; mode: string;
  reference: string | null; status: string; cancel_reason: string | null; invoice_id: string; invoice_number: string;
  payment_mode: string; customer_name: string | null; customer_mobile: string | null;
}

export interface RetailReturn {
  id: string; return_number: string; invoice_id: string; invoice_number: string | null; customer_id: string | null;
  customer_name: string | null; return_date: string; reason: string; return_amount: string; taxable_amount: string;
  cgst_amount: string; sgst_amount: string; applied_to_balance: string; refund_amount: string; refund_mode: string | null;
  points_reversed: number; created_at: string;
  items: { id: string; invoice_item_id: string; description: string; quantity: string; amount: string }[];
}

export const collectionStatusLabel = (s: string) =>
  ({ unpaid: "Unpaid", partially_paid: "Partially paid", paid: "Paid", overdue: "Overdue" }[s] ?? s);
