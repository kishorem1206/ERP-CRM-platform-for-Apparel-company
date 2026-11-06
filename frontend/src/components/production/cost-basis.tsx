"use client";
/** How an additional cost / agent commission is charged, shared by the style
 *  form, the new-lot form and a lot's Add Cost. "percent" is % of the lot's
 *  selling value: target price x pieces. */

export type CostBasis = "lumpsum" | "per_piece" | "percent";

export const COST_BASIS_OPTIONS: { value: CostBasis; label: string }[] = [
  { value: "lumpsum", label: "₹ Lump sum" },
  { value: "per_piece", label: "₹ per piece" },
  { value: "percent", label: "% of selling value (before GST)" },
];

export const asBasis = (b: string | null | undefined): CostBasis =>
  b === "per_piece" || b === "percent" ? b : "lumpsum";

const inr = (n: number) => `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

/** The planned ₹ for a lot, or null when it can't be worked out yet. */
export function plannedFor(basis: CostBasis, rate: number, pieces: number, sellingPrice: number | null): number | null {
  if (!Number.isFinite(rate) || rate <= 0) return null;
  if (basis === "lumpsum") return rate;
  if (!pieces) return null;
  if (basis === "per_piece") return rate * pieces;
  return sellingPrice ? (rate / 100) * sellingPrice * pieces : null;
}

/** e.g. "₹20 per piece", "2% of selling value", "Lump sum". */
export function basisText(basis: string | null | undefined, rate: number | string | null | undefined): string {
  const r = rate == null || rate === "" ? null : Number(rate);
  const b = asBasis(basis);
  if (b === "per_piece") return r != null ? `${inr(r)} per piece` : "Per piece";
  if (b === "percent") return r != null ? `${r}% of selling value (before GST)` : "% of selling value (before GST)";
  return "Lump sum";
}

/** One-line explanation of what the entered value comes to. */
export function basisPreview(basis: CostBasis, rate: string, pieces: number | null, sellingPrice: number | null): string {
  const r = parseFloat(rate);
  if (!Number.isFinite(r) || r <= 0) return "";
  if (basis === "lumpsum") return "Charged once for the whole lot.";
  if (basis === "per_piece") {
    return pieces ? `${inr(r)} × ${pieces.toLocaleString("en-IN")} pcs = ${inr(r * pieces)} for the lot` : "Multiplied by the lot's pieces.";
  }
  if (!sellingPrice) return "Needs a target price — worked out once the lot has one.";
  const perPiece = (r / 100) * sellingPrice;
  return pieces
    ? `${r}% of ${inr(sellingPrice)} = ${inr(perPiece)} per piece → ${inr(perPiece * pieces)} for ${pieces.toLocaleString("en-IN")} pcs`
    : `${r}% of target price ${inr(sellingPrice)} = ${inr(perPiece)} per piece`;
}

export function CostBasisPicker({ value, onChange, accent }: { value: CostBasis; onChange: (b: CostBasis) => void; accent: string }) {
  return (
    <div className="inline-flex flex-wrap gap-1 rounded-xl bg-muted/50 p-1">
      {COST_BASIS_OPTIONS.map((o) => (
        <button key={o.value} type="button" onClick={() => onChange(o.value)}
          className="rounded-lg px-2.5 py-1 text-xs font-semibold transition-colors"
          style={value === o.value ? { background: accent, color: "#fff" } : { color: "hsl(var(--muted-foreground))" }}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** "Pay ₹9,900 · TDS ₹100" — what goes to the party and what's held back for the Govt. */
export function tdsSplit(amount: number | null | undefined, tdsPct: number | string | null | undefined): string {
  const pct = Number(tdsPct);
  if (amount == null || !Number.isFinite(pct) || pct <= 0) return "";
  const tds = Math.round(amount * pct) / 100;
  return `Pay ${inr(amount - tds)} · TDS ${inr(tds)} (${pct}%)`;
}

export const rateLabel = (b: CostBasis) => (b === "percent" ? "Percent (%)" : b === "per_piece" ? "₹ per piece" : "Amount (₹)");
