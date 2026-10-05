"use client";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Copy, Pencil } from "lucide-react";
import api from "@/lib/api";
import { Can } from "@/lib/permissions";

const INDIGO = "#0049A7";

interface SizeOut { id: string; size_id: string; sort_order: number; quantity: string | null }
interface ColourOut { id: string; colour_id: string; sort_order: number }
interface YarnOut { id: string; yarn_name: string; lot_id: string | null; quantity: string | null; unit: string | null; notes: string | null }
interface FabricOut { id: string; fabric_name: string; lot_id: string | null; consumption: string | null; unit: string | null; excess_pct: string | null; gsm: string | null; dyeing_rate: string | null; printing_rate: string | null; notes: string | null }
interface SubProcessOut { id: string; seq: number; name: string; notes: string | null }
interface ProcessOut {
  id: string; seq: number; process_name: string; process_master_id: string | null; is_enabled: boolean;
  tolerance_pct: string | null; input_unit: string | null; output_unit: string | null; conversion_rule: string | null;
  min_rate: string | null; max_rate: string | null; planned_rate: string | null; notes: string | null;
  sub_processes: SubProcessOut[];
}
interface TrimOut { id: string; trim_name: string; lot_id: string | null; quantity: string | null; unit: string | null; category: string | null; excess_pct: string | null; notes: string | null }
interface PackingOut { id: string; material_name: string; quantity: string | null; unit: string | null; excess_pct: string | null; consumption_stage: string | null; notes: string | null }
interface AdditionalCostOut {
  id: string; cost_type: string; description: string; amount: string | null;
  basis: string | null; party_vendor_id: string | null; notes: string | null;
}
interface TargetPriceSuggestion {
  process_name: string; current_rate: string; suggested_rate: string; delta: string;
}
interface TargetPriceCheck {
  planned_process_cost: string; target_price: string; gap: string;
  message: string; suggestions: TargetPriceSuggestion[];
}

interface StyleDetail {
  id: string; name: string; code: string | null; description: string | null;
  garment_type: string | null; gender: string | null; season: string | null;
  final_output_unit: string | null; target_price: string | null; version: number; is_active: boolean;
  product_id: string | null; product_code: string | null; gst_rate: string | null;
  sizes: SizeOut[]; colours: ColourOut[]; yarns: YarnOut[]; fabrics: FabricOut[];
  processes: ProcessOut[]; trims: TrimOut[]; packing_materials: PackingOut[];
  additional_costs: AdditionalCostOut[];
  target_price_check: TargetPriceCheck | null;
}

function Card({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="bg-card border border-border rounded-2xl overflow-hidden">
      <div className="px-6 py-4 border-b border-border">
        <h2 className="text-sm font-semibold">{title}</h2>
        {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
      </div>
      <div className="p-6">{children}</div>
    </section>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="text-sm text-muted-foreground">{text}</p>;
}

export default function StyleDetailPage() {
  const params = useParams();
  const router = useRouter();
  const qc = useQueryClient();
  const id = params.id as string;

  const { data: style, isLoading } = useQuery({
    queryKey: ["style-detail", id],
    queryFn: async () => (await api.get(`/production/styles/${id}`)).data.data as StyleDetail,
    enabled: !!id,
  });

  const sizes = useQuery({
    queryKey: ["master-sizes"],
    queryFn: async () => (await api.get("/master/sizes")).data.data as { id: string; name: string }[],
  });
  const colours = useQuery({
    queryKey: ["master-colours"],
    queryFn: async () => (await api.get("/master/colours")).data.data as { id: string; name: string; hex_code: string | null }[],
  });
  const vendors = useQuery({
    queryKey: ["vendors", "ref"],
    queryFn: async () => (await api.get("/purchase/vendors", { params: { page_size: 200 } })).data.data as { id: string; name: string }[],
  });

  const cloneMut = useMutation({
    mutationFn: async () => (await api.post(`/production/styles/${id}/clone`)).data.data as StyleDetail,
    onSuccess: (cloned) => {
      qc.invalidateQueries({ queryKey: ["styles-list"] });
      router.push(`/production/styles/${cloned.id}/edit`);
    },
  });

  if (isLoading || !style) {
    return <div className="p-8"><p className="text-sm text-muted-foreground">Loading style…</p></div>;
  }

  const sizeById = new Map((sizes.data ?? []).map((s) => [s.id, s.name]));
  const colourById = new Map((colours.data ?? []).map((c) => [c.id, c]));
  const vendorById = new Map((vendors.data ?? []).map((v) => [v.id, v.name]));

  const sortedSizes = [...style.sizes].sort((a, b) => a.sort_order - b.sort_order);
  const sortedColours = [...style.colours].sort((a, b) => a.sort_order - b.sort_order);
  const sortedProcesses = [...style.processes].sort((a, b) => a.seq - b.seq);

  return (
    <div className="p-8 space-y-8 max-w-5xl">
      <div className="flex items-start gap-4">
        <button onClick={() => router.push("/production/styles")} className="mt-1 p-2 rounded-lg hover:bg-muted text-muted-foreground transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div className="flex-1 flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">PRODUCTION / STYLES</p>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold tracking-tight">{style.name}</h1>
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">v{style.version}</span>
              <span
                className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold"
                style={{ background: style.is_active ? "#0F78FF18" : "#94A3B818", color: style.is_active ? "#0F78FF" : "#94A3B8" }}
              >
                {style.is_active ? "Active" : "Inactive"}
              </span>
            </div>
            {style.code && style.code !== style.name && <p className="text-sm text-muted-foreground mt-1 font-mono">{style.code}</p>}
            {style.description && <p className="text-sm text-muted-foreground mt-1">{style.description}</p>}
            <div className="flex gap-2 flex-wrap mt-3">
              {style.garment_type && <span className="text-xs px-2.5 py-1 rounded bg-muted">{style.garment_type}</span>}
              {style.gender && <span className="text-xs px-2.5 py-1 rounded bg-muted">{style.gender}</span>}
              {style.season && <span className="text-xs px-2.5 py-1 rounded bg-muted">{style.season}</span>}
              {style.final_output_unit && (
                <span className="text-xs px-2.5 py-1 rounded" style={{ background: `${INDIGO}18`, color: INDIGO }}>
                  Final Output: {style.final_output_unit}
                </span>
              )}
              {style.target_price && (
                <span className="text-xs px-2.5 py-1 rounded bg-muted">
                  Target Price: ₹{Number(style.target_price).toLocaleString("en-IN")}
                </span>
              )}
              <span className="text-xs px-2.5 py-1 rounded bg-muted font-mono">
                Product: {style.product_code ?? "—"}
                {style.gst_rate != null && ` · GST ${Number(style.gst_rate)}%`}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Can perm="production.create"><button
              onClick={() => cloneMut.mutate()}
              disabled={cloneMut.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border border-input hover:bg-muted transition-colors disabled:opacity-50"
            >
              <Copy className="h-4 w-4" /> {cloneMut.isPending ? "Cloning…" : "Clone"}
            </button></Can>
            <Can perm="production.edit"><button
              onClick={() => router.push(`/production/styles/${id}/edit`)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
              style={{ background: INDIGO }}
            >
              <Pencil className="h-4 w-4" /> Edit Style
            </button></Can>
          </div>
        </div>
      </div>

      <Card title="Sizes & Colours" subtitle="Applicable size chart and colour variants">
        {sortedSizes.length === 0 && sortedColours.length === 0 ? (
          <Empty text="No sizes or colours configured." />
        ) : (
          <div className="grid grid-cols-2 gap-6">
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Sizes</p>
              <div className="flex gap-1.5 flex-wrap">
                {sortedSizes.map((s) => (
                  <span key={s.id} className="px-2.5 py-1 rounded-lg text-xs font-medium bg-muted">
                    {sizeById.get(s.size_id) ?? "—"}{s.quantity ? `: ${Number(s.quantity)}` : ""}
                  </span>
                ))}
                {sortedSizes.length === 0 && <Empty text="None" />}
              </div>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Colours</p>
              <div className="flex gap-1.5 flex-wrap">
                {sortedColours.map((c) => {
                  const colour = colourById.get(c.colour_id);
                  return (
                    <span key={c.id} className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-muted">
                      {colour?.hex_code && <span className="w-2 h-2 rounded-full border border-black/10" style={{ background: colour.hex_code }} />}
                      {colour?.name ?? "—"}
                    </span>
                  );
                })}
                {sortedColours.length === 0 && <Empty text="None" />}
              </div>
            </div>
          </div>
        )}
      </Card>

      <Card title="Yarn Requirements">
        {style.yarns.length === 0 ? <Empty text="No yarn requirements configured." /> : (
          <div className="space-y-2">
            {style.yarns.map((y) => (
              <div key={y.id} className="flex items-center justify-between px-4 py-2.5 rounded-xl border border-border text-sm">
                <span className="font-medium">{y.yarn_name}</span>
                <span className="text-muted-foreground">{y.quantity ? `${Number(y.quantity)} ${y.unit ?? ""}` : "—"}</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Fabric Requirements">
        {style.fabrics.length === 0 ? <Empty text="No fabric requirements configured." /> : (
          <div className="space-y-2">
            {style.fabrics.map((f) => (
              <div key={f.id} className="flex items-center justify-between px-4 py-2.5 rounded-xl border border-border text-sm">
                <span className="font-medium">{f.fabric_name}</span>
                <span className="text-muted-foreground">
                  {f.consumption ? `${Number(f.consumption)} ${f.unit ?? ""}` : "—"}
                  {f.excess_pct ? ` · +${Number(f.excess_pct)}% excess` : ""}
                  {f.gsm ? ` · ${Number(f.gsm)} GSM` : ""}
                  {f.dyeing_rate ? ` · Dyeing ₹${Number(f.dyeing_rate)}/kg` : ""}
                  {f.printing_rate ? ` · Printing ₹${Number(f.printing_rate)}/kg` : ""}
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>

      {style.target_price_check && (
        <Card
          title="Target Price Check"
          subtitle="Deterministic comparison of planned process rates against your target price"
        >
          {(() => {
            const tpc = style.target_price_check;
            const gap = Number(tpc.gap);
            const over = gap > 0;
            return (
              <>
                <div className="grid grid-cols-3 gap-4 text-sm mb-4">
                  <div>
                    <p className="text-muted-foreground text-xs">Planned Process Cost</p>
                    <p className="font-semibold mt-0.5">₹{Number(tpc.planned_process_cost).toLocaleString("en-IN")}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Target Price</p>
                    <p className="font-semibold mt-0.5">₹{Number(tpc.target_price).toLocaleString("en-IN")}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">{over ? "Over Budget" : "Cushion"}</p>
                    <p className="font-semibold mt-0.5" style={{ color: over ? "#1D0DB0" : "#0F78FF" }}>
                      ₹{Math.abs(gap).toLocaleString("en-IN")}
                    </p>
                  </div>
                </div>
                <p className={`text-sm px-4 py-2.5 rounded-xl ${over ? "bg-[#1D0DB0]/10 text-[#1D0DB0]" : "bg-[#0F78FF]/10 text-[#0049A7]"}`}>
                  {tpc.message}
                </p>
                {tpc.suggestions.length > 0 && (
                  <div className="mt-4 overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                          <th className="py-2 pr-4">Process</th>
                          <th className="py-2 pr-4">Current Rate</th>
                          <th className="py-2 pr-4">Suggested Rate</th>
                          <th className="py-2 pr-4">Change</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {tpc.suggestions.map((s) => (
                          <tr key={s.process_name}>
                            <td className="py-2 pr-4 font-medium">{s.process_name}</td>
                            <td className="py-2 pr-4">₹{Number(s.current_rate).toFixed(2)}</td>
                            <td className="py-2 pr-4">₹{Number(s.suggested_rate).toFixed(2)}</td>
                            <td className="py-2 pr-4 text-[#1D0DB0]">₹{Number(s.delta).toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            );
          })()}
        </Card>
      )}

      <Card title="Production Workflow" subtitle="Configurable process sequence with tolerance %, units, conversion, and rate band">
        {sortedProcesses.length === 0 ? <Empty text="No processes configured." /> : (
          <div className="space-y-3">
            {sortedProcesses.map((p, idx) => (
              <div key={p.id} className={`rounded-xl border overflow-hidden ${p.is_enabled ? "border-border" : "border-border opacity-50"}`}>
                <div className="flex items-center gap-3 px-4 py-2.5 bg-muted/30 border-b border-border">
                  <span className="text-xs font-mono text-muted-foreground">{idx + 1}</span>
                  <span className="text-sm font-semibold flex-1">{p.process_name}</span>
                  {!p.is_enabled && <span className="text-[11px] text-muted-foreground">Disabled</span>}
                </div>
                <div className="px-4 py-3 grid grid-cols-4 gap-3 text-xs">
                  <div><p className="text-muted-foreground">Tolerance</p><p className="font-medium mt-0.5">{p.tolerance_pct ? `${Number(p.tolerance_pct)}%` : "—"}</p></div>
                  <div><p className="text-muted-foreground">Input Unit</p><p className="font-medium mt-0.5">{p.input_unit ?? "—"}</p></div>
                  <div><p className="text-muted-foreground">Output Unit</p><p className="font-medium mt-0.5">{p.output_unit ?? "—"}</p></div>
                  <div><p className="text-muted-foreground">Conversion</p><p className="font-medium mt-0.5">{p.conversion_rule ?? "—"}</p></div>
                  <div><p className="text-muted-foreground">Min Rate</p><p className="font-medium mt-0.5">{p.min_rate ? `₹${Number(p.min_rate).toFixed(2)}` : "—"}</p></div>
                  <div><p className="text-muted-foreground">Max Rate</p><p className="font-medium mt-0.5">{p.max_rate ? `₹${Number(p.max_rate).toFixed(2)}` : "—"}</p></div>
                  <div><p className="text-muted-foreground">Planned Rate</p><p className="font-medium mt-0.5">{p.planned_rate ? `₹${Number(p.planned_rate).toFixed(2)}` : "—"}</p></div>
                </div>
                {p.sub_processes.length > 0 && (
                  <div className="px-4 pb-3 flex gap-1.5 flex-wrap">
                    {p.sub_processes.map((sp) => (
                      <span key={sp.id} className="text-[11px] px-2 py-0.5 rounded bg-muted text-muted-foreground">{sp.name}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Trim Planning">
        {style.trims.length === 0 ? <Empty text="No trim requirements configured." /> : (
          <div className="space-y-2">
            {style.trims.map((t) => (
              <div key={t.id} className="flex items-center justify-between px-4 py-2.5 rounded-xl border border-border text-sm">
                <span className="font-medium">{t.trim_name}</span>
                <div className="flex items-center gap-2 text-muted-foreground">
                  {t.category && <span className="text-[11px] px-2 py-0.5 rounded bg-muted">{t.category}</span>}
                  <span>{t.quantity ? `${Number(t.quantity)} ${t.unit ?? ""}` : "—"}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Packing Material Planning">
        {style.packing_materials.length === 0 ? <Empty text="No packing materials configured." /> : (
          <div className="space-y-2">
            {style.packing_materials.map((p) => (
              <div key={p.id} className="flex items-center justify-between px-4 py-2.5 rounded-xl border border-border text-sm">
                <span className="font-medium">{p.material_name}</span>
                <div className="flex items-center gap-2 text-muted-foreground">
                  {p.consumption_stage && <span className="text-[11px] px-2 py-0.5 rounded bg-muted">{p.consumption_stage}</span>}
                  <span>{p.quantity ? `${Number(p.quantity)} ${p.unit ?? ""}` : "—"}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Additional Costs & Agent Commission" subtitle="Named cost components outside Fabric/Cutting/Making/Trims — flows into every LOT as a planned value">
        {style.additional_costs.length === 0 ? <Empty text="No additional costs configured." /> : (
          <div className="space-y-2">
            {style.additional_costs.map((a) => (
              <div key={a.id} className="flex items-center justify-between px-4 py-2.5 rounded-xl border border-border text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] px-2 py-0.5 rounded bg-muted">
                    {a.cost_type === "agent_commission" ? "Agent Commission" : "Additional"}
                  </span>
                  <span className="font-medium">{a.description}</span>
                  {a.party_vendor_id && vendorById.get(a.party_vendor_id) && (
                    <span className="text-xs text-muted-foreground">({vendorById.get(a.party_vendor_id)})</span>
                  )}
                </div>
                <span className="text-muted-foreground">
                  {a.amount ? `₹${Number(a.amount).toLocaleString("en-IN")}` : "—"}
                  {a.basis ? ` / ${a.basis}` : ""}
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
