/** Receipt tolerance on PO lines — internal only, never on the PDFs. */

export const PO_STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  approved: "Approved",
  partial: "Part received",
  received: "Received",
  close_requested: "Awaiting close approval",
  closed: "Closed",
  cancelled: "Cancelled",
};

export const fmtQty = (n: number) => n.toLocaleString("en-IN", { maximumFractionDigits: 3 });

/** Lowest and highest quantity a receipt may total without admin approval. */
export function toleranceRange(ordered: number, tolerancePct: number | string | null | undefined): [number, number] {
  const tol = (Number(tolerancePct) || 0) / 100;
  return [ordered * (1 - tol), ordered * (1 + tol)];
}

/** e.g. "450 – 550 kg", or "exactly 500 kg" with no tolerance. */
export function rangeText(ordered: number, tolerancePct: number | string | null | undefined, unit?: string): string {
  const [low, high] = toleranceRange(ordered, tolerancePct);
  const u = unit ? ` ${unit}` : "";
  return low === high ? `exactly ${fmtQty(ordered)}${u}` : `${fmtQty(low)} – ${fmtQty(high)}${u}`;
}

export type LineState = "short" | "within" | "over";

export function lineState(ordered: number, received: number, tolerancePct: number | string | null | undefined): LineState {
  const [low, high] = toleranceRange(ordered, tolerancePct);
  return received > high ? "over" : received < low ? "short" : "within";
}
