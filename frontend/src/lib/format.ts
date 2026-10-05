// ── Indian currency formatting ──────────────────────────────────────────────
// Raw monetary values from the API are plain numbers (often with decimal
// cruft from NUMERIC columns, e.g. 10400000.0000). Never render that
// directly — always go through one of these.

/** Compact form for dense UI: ₹1.04 Cr, ₹60.50 L, ₹12,000, ₹0. */
export function formatIndianCompact(value: number): string {
  const n = Number(value) || 0;
  if (n === 0) return "₹0";
  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (abs >= 1_00_00_000) return `${sign}₹${(abs / 1_00_00_000).toFixed(2)} Cr`;
  if (abs >= 1_00_000) return `${sign}₹${(abs / 1_00_000).toFixed(2)} L`;
  return `${sign}₹${Math.round(abs).toLocaleString("en-IN")}`;
}

/** Full precise value with Indian digit grouping, for tooltips/detail views. */
export function formatIndianFull(value: number): string {
  const n = Number(value) || 0;
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}
