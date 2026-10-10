"use client";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import api from "@/lib/api";

// ── Palette ───────────────────────────────────────────────────────────────────
const BLUE     = "#0049A7";
const LAVENDER = "#0F78FF";

// ── Type badge ────────────────────────────────────────────────────────────────
const TYPE_HEX: Record<string, string> = {
  yarn:   "#A096F7",
  fabric: BLUE,
  trim:   LAVENDER,
};

function TypeDot({ type }: { type: string }) {
  const color = TYPE_HEX[type?.toLowerCase()] ?? "#94A3B8";
  const label = type.replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-bold whitespace-nowrap capitalize"
      style={{ background: `${color}18`, color }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {label}
    </span>
  );
}

// ── Types ─────────────────────────────────────────────────────────────────────
interface CompositionItem {
  id: string;
  fibre_name: string;
  percentage: number;
}

interface FabricVariant {
  id: string;
  colour: string | null;
  dia_inches: number | null;
  notes: string | null;
}

interface TrimVariant {
  id: string;
  colour: string | null;
  notes: string | null;
}

interface Lot {
  id: string;
  lot_number: string;
  material_type: string;
  product_id: string | null;
  product_name: string | null;
  yarn_count: string | null;
  ply: string | null;
  mill: string | null;
  spinning_type: string | null;
  treatment: string | null;
  fibre_type: string | null;
  blend_composition: string | null;
  construction: string | null;
  gsm: number | null;
  diameter_inches: number | null;
  colour: string | null;
  finish: string | null;
  trim_type: string | null;
  trim_unit: string | null;
  bags: number | null;
  kg_per_bag: number | null;
  unit_cost: number | null;
  split_by_colour: boolean;
  split_by_dia: boolean;
  invoice_number: string | null;
  invoice_date: string | null;
  notes: string | null;
  compositions: CompositionItem[];
  fabric_variants: FabricVariant[];
  trim_variants: TrimVariant[];
}

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value == null || value === "") return null;
  return (
    <div>
      <dt className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium mt-0.5">{String(value)}</dd>
    </div>
  );
}

function SectionCard({ eyebrow, title, children }: { eyebrow: string; title: string; children: React.ReactNode }) {
  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden">
      <div className="px-6 py-4 border-b border-border">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">{eyebrow}</p>
        <p className="text-sm font-medium mt-0.5">{title}</p>
      </div>
      <div className="p-6">
        {children}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function LotDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { id } = params;

  const { data, isLoading, error } = useQuery({
    queryKey: ["material-lot", id],
    queryFn: async () => {
      const r = await api.get(`/materials/lots/${id}`);
      return r.data.data as Lot;
    },
  });

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[200px] text-muted-foreground text-sm">
        Loading lot…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 space-y-4">
        <button onClick={() => router.back()} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to lots
        </button>
        <p className="text-[#1D0DB0] text-sm">Lot not found.</p>
      </div>
    );
  }

  const lot = data;
  const totalKg = lot.bags && lot.kg_per_bag ? (Number(lot.bags) * Number(lot.kg_per_bag)).toFixed(3) : null;
  const totalValue = totalKg && lot.unit_cost ? (Number(totalKg) * Number(lot.unit_cost)).toFixed(2) : null;

  return (
    <div className="p-8 space-y-8 max-w-3xl">
      {/* Back link */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" /> back to lots
      </button>

      {/* Page header */}
      <div className="flex items-start gap-4 flex-wrap">
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">INVENTORY / MATERIALS</p>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold tracking-tight font-mono">{lot.lot_number}</h1>
            <TypeDot type={lot.material_type} />
            {lot.product_name ? (
              <span className="text-xs font-medium px-2 py-0.5 rounded bg-muted text-foreground">
                Product: {lot.product_name}
              </span>
            ) : (
              <span className="text-xs text-muted-foreground italic">Not linked to a catalog product</span>
            )}
          </div>
          {lot.blend_composition && (
            <p className="text-sm text-muted-foreground mt-1">{lot.blend_composition}</p>
          )}
        </div>
      </div>

      {/* Yarn details */}
      {lot.material_type === "yarn" && (
        <SectionCard eyebrow="SPECIFICATION" title="Yarn Specification">
          <div className="space-y-4">
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <Field label="Yarn Count" value={lot.yarn_count} />
              <Field label="Ply" value={lot.ply} />
              <Field label="Mill" value={lot.mill} />
              <Field label="Spinning" value={lot.spinning_type} />
              <Field label="Treatment" value={lot.treatment} />
              <Field label="Colour / State" value={lot.colour} />
            </dl>

            {lot.compositions.length > 0 && (
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">Fibre Composition</p>
                <div className="flex gap-2 flex-wrap">
                  {lot.compositions.map((c) => (
                    <span key={c.id} className="bg-muted px-2.5 py-1 rounded text-xs">
                      {c.fibre_name} {c.percentage}%
                    </span>
                  ))}
                </div>
              </div>
            )}

            <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-border">
              <Field label="Bags" value={lot.bags} />
              <Field label="Kg / Bag" value={lot.kg_per_bag} />
              <Field label="Total Kg" value={totalKg} />
              <Field label="Rate / Kg (₹)" value={lot.unit_cost} />
              {totalValue && <Field label="Total Value (₹)" value={totalValue} />}
            </dl>
          </div>
        </SectionCard>
      )}

      {/* Fabric details */}
      {lot.material_type === "fabric" && (
        <SectionCard eyebrow="SPECIFICATION" title="Fabric Specification">
          <div className="space-y-4">
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <Field label="Construction" value={lot.construction} />
              <Field label="GSM" value={lot.gsm} />
              <Field label="Dia (inches)" value={lot.diameter_inches} />
              <Field label="Colour" value={lot.colour} />
              <Field label="Finish" value={lot.finish} />
            </dl>

            {lot.compositions.length > 0 && (
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">Fibre Composition</p>
                <div className="flex gap-2 flex-wrap">
                  {lot.compositions.map((c) => (
                    <span key={c.id} className="bg-muted px-2.5 py-1 rounded text-xs">
                      {c.fibre_name} {c.percentage}%
                    </span>
                  ))}
                </div>
              </div>
            )}

            {(lot.split_by_colour || lot.split_by_dia) && (
              <div className="flex gap-2">
                {lot.split_by_colour && (
                  <span
                    className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold"
                    style={{ background: `${BLUE}18`, color: BLUE }}
                  >
                    Split by Colour
                  </span>
                )}
                {lot.split_by_dia && (
                  <span
                    className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold"
                    style={{ background: `${BLUE}18`, color: BLUE }}
                  >
                    Split by Dia
                  </span>
                )}
              </div>
            )}

            {lot.fabric_variants.length > 0 && (
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-3">Fabric Variants</p>
                <div className="rounded-xl border border-border overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-4 py-2.5 text-left font-semibold text-muted-foreground">Colour</th>
                        <th className="px-4 py-2.5 text-left font-semibold text-muted-foreground">Dia (in)</th>
                        <th className="px-4 py-2.5 text-left font-semibold text-muted-foreground">Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lot.fabric_variants.map((fv) => (
                        <tr key={fv.id} className="border-t border-border">
                          <td className="px-4 py-2.5">{fv.colour || "—"}</td>
                          <td className="px-4 py-2.5">{fv.dia_inches ?? "—"}</td>
                          <td className="px-4 py-2.5 text-muted-foreground">{fv.notes || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <dl className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
              <Field label="Rate / Meter (₹)" value={lot.unit_cost} />
            </dl>
          </div>
        </SectionCard>
      )}

      {/* Trim details */}
      {lot.material_type === "trim" && (
        <SectionCard eyebrow="SPECIFICATION" title="Trim Specification">
          <div className="space-y-4">
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <Field label="Trim Type" value={lot.trim_type} />
              <Field label="Unit" value={lot.trim_unit} />
              <Field label="Colour" value={lot.colour} />
              <Field label="Rate / Unit (₹)" value={lot.unit_cost} />
            </dl>

            {lot.split_by_colour && (
              <span
                className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold"
                style={{ background: `${LAVENDER}18`, color: LAVENDER }}
              >
                Split by Colour
              </span>
            )}

            {lot.trim_variants.length > 0 && (
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-3">Trim Variants</p>
                <div className="rounded-xl border border-border overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-4 py-2.5 text-left font-semibold text-muted-foreground">Colour</th>
                        <th className="px-4 py-2.5 text-left font-semibold text-muted-foreground">Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lot.trim_variants.map((tv) => (
                        <tr key={tv.id} className="border-t border-border">
                          <td className="px-4 py-2.5">{tv.colour || "—"}</td>
                          <td className="px-4 py-2.5 text-muted-foreground">{tv.notes || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </SectionCard>
      )}

      {/* Invoice / supplier info */}
      {(lot.invoice_number || lot.invoice_date) && (
        <SectionCard eyebrow="PROCUREMENT" title="Purchase Details">
          <dl className="grid grid-cols-2 gap-4">
            <Field label="Invoice No." value={lot.invoice_number} />
            <Field label="Invoice Date" value={lot.invoice_date} />
          </dl>
        </SectionCard>
      )}

      {/* Notes */}
      {lot.notes && (
        <SectionCard eyebrow="NOTES" title="Additional Notes">
          <p className="text-sm text-muted-foreground whitespace-pre-line">{lot.notes}</p>
        </SectionCard>
      )}
    </div>
  );
}
