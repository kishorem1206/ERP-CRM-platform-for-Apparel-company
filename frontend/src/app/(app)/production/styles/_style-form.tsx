"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, GripVertical } from "lucide-react";
import api from "@/lib/api";
import { Field, Input, Textarea, SegControl } from "@/components/create/ModalShell";
import { SearchableSelect } from "@/components/shared/searchable-select";

const INDIGO = "#0049A7";
const FINAL_OUTPUT_UNITS = ["Pieces", "Dozen", "Sets", "Boxes"];
const TRIM_CATEGORIES = ["Sizable", "Non-Sizable"];

let rowSeq = 0;
function newId() {
  rowSeq += 1;
  return `row-${Date.now()}-${rowSeq}`;
}

// ── Row shapes ──────────────────────────────────────────────────────────────
interface YarnRow { key: string; yarn_name: string; lot_id: string; fabricKey: string; colour_id: string; counts: string; consumption_pct: string; quantity: string; unit: string; notes: string }
interface FabricRow {
  key: string; fabric_name: string; lot_id: string; style_part_id: string; colour_id: string; source_type: string;
  knit_dia: string; finish_dia: string; consumption: string; unit: string; excess_pct: string; gsm: string;
  dyeing_rate: string; printing_rate: string; notes: string; size_breakdown: Record<string, string>;
}
interface SubProcessRow { key: string; name: string; min_rate: string; max_rate: string; planned_rate: string }
interface ProcessRow {
  key: string; process_name: string; process_master_id: string; style_part_id: string; is_enabled: boolean;
  tolerance_pct: string; input_unit: string; output_unit: string; conversion_rule: string;
  min_rate: string; max_rate: string; planned_rate: string; notes: string;
  sub_processes: SubProcessRow[];
}
interface TrimRow { key: string; process_key: string; trim_name: string; lot_id: string; style_part_id: string; colour_id: string; quantity: string; unit: string; category: string; excess_pct: string; notes: string; size_breakdown: Record<string, string> }
interface PartColourRow { key: string; style_part_id: string; colour_id: string; sizeQty: Record<string, string> }
interface PackingRow { key: string; material_name: string; product_id: string; quantity: string; unit: string; excess_pct: string; consumption_stage: string; notes: string }
interface AdditionalCostRow { key: string; cost_type: "additional" | "agent_commission"; description: string; amount: string; basis: string; party_vendor_id: string; notes: string }
const GENDER_OPTIONS = ["Men's", "Women's", "Kids", "Newborn Baby"];

// ── Section shell ────────────────────────────────────────────────────────────
function Section({ n, title, subtitle, children }: { n: number; title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <section className="bg-card border border-border rounded-2xl overflow-hidden">
      <div className="px-6 py-4 border-b border-border flex items-start gap-3">
        <span
          className="flex-shrink-0 w-6 h-6 rounded-full text-[11px] font-bold flex items-center justify-center"
          style={{ background: `${INDIGO}18`, color: INDIGO }}
        >
          {n}
        </span>
        <div>
          <h2 className="text-sm font-semibold">{title}</h2>
          <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
        </div>
      </div>
      <div className="p-6 space-y-4">{children}</div>
    </section>
  );
}

function AddRowButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border border-dashed border-border text-muted-foreground hover:text-foreground hover:border-foreground/40 transition-colors"
    >
      <Plus className="h-3.5 w-3.5" /> {label}
    </button>
  );
}

function FactorCalcModal({ onApply, onClose }: { onApply: (qty: number) => void; onClose: () => void }) {
  const [perPack, setPerPack] = useState("");
  const [perPc, setPerPc] = useState("");
  const [result, setResult] = useState<number | null>(null);

  function calculate() {
    const pack = Number(perPack), pc = Number(perPc);
    if (!pack || !pc) return;
    setResult(pack / pc);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/40 backdrop-blur-[2px]" onClick={onClose}>
      <div className="bg-card border rounded-2xl shadow-2xl w-full max-w-sm p-5 space-y-4" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-semibold text-base">Factor Calculation</h3>
        <Field label="Per Pack Qty" hint="Number or fraction, e.g. 1/40">
          <Input value={perPack} onChange={(e) => { setPerPack(e.target.value); setResult(null); }} placeholder="e.g. 5000" />
        </Field>
        <Field label="Per Pc Qty">
          <Input value={perPc} onChange={(e) => { setPerPc(e.target.value); setResult(null); }} placeholder="e.g. 25" />
        </Field>
        <Field label="Factor Qty (result)">
          <div className="flex gap-2">
            <Input value={result != null ? String(result) : ""} readOnly className="bg-muted" />
            <button type="button" onClick={calculate} className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold border border-border hover:bg-muted transition-colors">
              Calculate
            </button>
          </div>
        </Field>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onClose} className="px-4 py-1.5 rounded-lg border border-border text-sm hover:bg-muted">Cancel</button>
          <button
            type="button"
            disabled={result == null}
            onClick={() => { if (result != null) onApply(result); onClose(); }}
            className="px-4 py-1.5 rounded-lg text-sm font-semibold text-white disabled:opacity-50"
            style={{ background: INDIGO }}
          >
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}

function RemoveRowButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="p-1.5 rounded-md text-muted-foreground hover:text-[#1D0DB0] hover:bg-[#1D0DB0]/10 transition-colors flex-shrink-0"
    >
      <Trash2 className="h-3.5 w-3.5" />
    </button>
  );
}

export function StyleForm({ styleId }: { styleId?: string }) {
  const isEdit = !!styleId;
  const router = useRouter();
  const qc = useQueryClient();
  const hydrated = useRef(false);

  // ── Section 1: Basic Information ──────────────────────────────────────────
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [garmentType, setGarmentType] = useState("");
  const [gender, setGender] = useState("");
  const [brandId, setBrandId] = useState("");
  const [piecesPerBox, setPiecesPerBox] = useState("");
  const [fabricSource, setFabricSource] = useState<"yarn" | "purchased">("yarn");
  const [season, setSeason] = useState("");
  const [finalOutputUnit, setFinalOutputUnit] = useState("Pieces");
  const [targetPrice, setTargetPrice] = useState("");
  const [productId, setProductId] = useState("");
  const [linkedProduct, setLinkedProduct] = useState<{ code: string | null; gst_rate: number | null } | null>(null);

  // ── Section 2 & 3: Sizes / Colours / SKU ──────────────────────────────────
  const [sizeIds, setSizeIds] = useState<string[]>([]);
  const [colourIds, setColourIds] = useState<string[]>([]);
  const [rangeFrom, setRangeFrom] = useState("");
  const [rangeTo, setRangeTo] = useState("");
  const [rangeStep, setRangeStep] = useState("1");
  const [addingSizes, setAddingSizes] = useState(false);
  const [sizeQuantities, setSizeQuantities] = useState<Record<string, string>>({});
  const [sizeChartBySize, setSizeChartBySize] = useState<Record<string, string>>({});
  const [loadChartId, setLoadChartId] = useState("");
  const [partColours, setPartColours] = useState<PartColourRow[]>([]);
  const [showAddPart, setShowAddPart] = useState(false);
  const [factorCalcKey, setFactorCalcKey] = useState<string | null>(null);
  const [newPartName, setNewPartName] = useState("");

  // ── Section 4 & 5: Yarn / Fabric ───────────────────────────────────────────
  const [yarns, setYarns] = useState<YarnRow[]>([]);
  const [fabrics, setFabrics] = useState<FabricRow[]>([]);

  // ── Section 6 & 7: Workflow / Process configuration ───────────────────────
  const [processes, setProcesses] = useState<ProcessRow[]>([]);

  // ── Section 8: Trim Planning ────────────────────────────────────────────
  const [trims, setTrims] = useState<TrimRow[]>([]);

  // ── Section 9: Packing Material Planning ──────────────────────────────────
  const [packingMaterials, setPackingMaterials] = useState<PackingRow[]>([]);

  // ── Section 10: Additional Costs & Agent Commission ────────────────────────
  const [additionalCosts, setAdditionalCosts] = useState<AdditionalCostRow[]>([]);

  const [err, setErr] = useState<string | null>(null);

  // ── Reference data ─────────────────────────────────────────────────────────
  const sizes = useQuery({
    queryKey: ["master-sizes"],
    queryFn: async () => (await api.get("/master/sizes")).data.data as { id: string; name: string }[],
  });
  const styleParts = useQuery({
    queryKey: ["master-style-parts"],
    queryFn: async () => (await api.get("/master/style-parts")).data.data as { id: string; name: string }[],
  });
  const createPartMut = useMutation({
    mutationFn: (name: string) => api.post("/master/style-parts", { name }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["master-style-parts"] }),
  });
  const brands = useQuery({
    queryKey: ["master-brands"],
    queryFn: async () => (await api.get("/master/brands")).data.data as { id: string; name: string }[],
  });
  const colours = useQuery({
    queryKey: ["master-colours"],
    queryFn: async () => (await api.get("/master/colours")).data.data as { id: string; name: string; hex_code: string | null }[],
  });
  const yarnLots = useQuery({
    queryKey: ["material-lots", "yarn", "ref"],
    queryFn: async () => (await api.get("/materials/lots", { params: { material_type: "yarn", page_size: 200 } })).data.data as { id: string; lot_number: string; yarn_count: string | null }[],
  });
  const fabricLots = useQuery({
    queryKey: ["material-lots", "fabric", "ref"],
    queryFn: async () => (await api.get("/materials/lots", { params: { material_type: "fabric", page_size: 200 } })).data.data as { id: string; lot_number: string; construction: string | null; colour: string | null }[],
  });
  const trimLots = useQuery({
    queryKey: ["material-lots", "trim", "ref"],
    queryFn: async () => (await api.get("/materials/lots", { params: { material_type: "trim", page_size: 200 } })).data.data as { id: string; lot_number: string; trim_type: string | null; colour: string | null }[],
  });
  const vendors = useQuery({
    queryKey: ["vendors", "ref"],
    queryFn: async () => (await api.get("/purchase/vendors", { params: { page_size: 200 } })).data.data as { id: string; name: string; vendor_type: string }[],
  });
  const products = useQuery({
    queryKey: ["products", "ref"],
    queryFn: async () => (await api.get("/products", { params: { page_size: 200 } })).data.data as { id: string; name: string; code: string }[],
  });
  const packingProducts = useQuery({
    queryKey: ["products", "packing", "ref"],
    queryFn: async () => (await api.get("/products", { params: { page_size: 200, product_type: "packing" } })).data.data as { id: string; name: string; code: string }[],
  });
  const processMasters = useQuery({
    queryKey: ["master-processes"],
    queryFn: async () => (await api.get("/master/processes")).data.data as {
      id: string; name: string; default_unit: string | null; default_tolerance_pct: number | null;
      default_min_rate: number | null; default_max_rate: number | null; default_planned_rate: number | null;
    }[],
  });
  const sizeCharts = useQuery({
    queryKey: ["size-charts"],
    queryFn: async () => (await api.get("/production/size-charts")).data.data as {
      id: string; name: string; items: { size_id: string; quantity: number | null }[];
    }[],
  });

  // ── Existing style (edit mode only) ─────────────────────────────────────────
  interface StyleDetail {
    name: string; code: string | null; description: string | null;
    garment_type: string | null; gender: string | null; season: string | null;
    brand_id: string | null;
    final_output_unit: string | null;
    pieces_per_box: number | null; fabric_source: string;
    target_price: number | null;
    product_id: string | null; product_code: string | null; gst_rate: number | null;
    sizes: { size_id: string; sort_order: number; quantity: number | null; size_chart_id: string | null }[];
    colours: { colour_id: string; sort_order: number }[];
    part_colours: { style_part_id: string; colour_id: string | null; sort_order: number; sizes: { size_id: string; quantity: number | null }[] }[];
    yarns: {
      yarn_name: string; lot_id: string | null; style_fabric_id: string | null; colour_id: string | null;
      counts: string | null; consumption_pct: number | null; quantity: number | null; unit: string | null; notes: string | null;
    }[];
    fabrics: {
      id: string; fabric_name: string; lot_id: string | null; style_part_id: string | null; colour_id: string | null; source_type: string | null;
      knit_dia: number | null; finish_dia: number | null; consumption: number | null; unit: string | null; excess_pct: number | null;
      gsm: number | null; dyeing_rate: number | null; printing_rate: number | null; notes: string | null;
      size_breakdown: { size_id: string; quantity: number }[];
    }[];
    processes: {
      seq: number; process_name: string; process_master_id: string | null; style_part_id: string | null; is_enabled: boolean; tolerance_pct: number | null;
      input_unit: string | null; output_unit: string | null; conversion_rule: string | null;
      min_rate: number | null; max_rate: number | null; planned_rate: number | null; notes: string | null;
      sub_processes: { seq: number; name: string; min_rate: number | null; max_rate: number | null; planned_rate: number | null }[];
    }[];
    trims: { process_seq: number | null; trim_name: string; lot_id: string | null; style_part_id: string | null; colour_id: string | null; quantity: number | null; unit: string | null; category: string | null; excess_pct: number | null; notes: string | null; size_breakdown: { size_id: string; quantity: number }[] }[];
    packing_materials: { material_name: string; product_id: string | null; quantity: number | null; unit: string | null; excess_pct: number | null; consumption_stage: string | null; notes: string | null }[];
    additional_costs: { cost_type: string; description: string; amount: number | null; basis: string | null; party_vendor_id: string | null; notes: string | null }[];
  }
  const styleQuery = useQuery({
    queryKey: ["style-detail", styleId],
    queryFn: async () => (await api.get(`/production/styles/${styleId}`)).data.data as StyleDetail,
    enabled: isEdit,
  });

  useEffect(() => {
    const d = styleQuery.data;
    if (!d || hydrated.current) return;
    hydrated.current = true;
    setName(d.name);
    setCode(d.code ?? "");
    setDescription(d.description ?? "");
    setGarmentType(d.garment_type ?? "");
    setGender(d.gender ?? "");
    setBrandId(d.brand_id ?? "");
    setPiecesPerBox(d.pieces_per_box != null ? String(d.pieces_per_box) : "");
    setFabricSource(d.fabric_source === "purchased" ? "purchased" : "yarn");
    setSeason(d.season ?? "");
    setFinalOutputUnit(d.final_output_unit ?? "Pieces");
    setTargetPrice(d.target_price != null ? String(d.target_price) : "");
    setProductId(d.product_id ?? "");
    setLinkedProduct(d.product_id ? { code: d.product_code, gst_rate: d.gst_rate } : null);
    setSizeIds([...d.sizes].sort((a, b) => a.sort_order - b.sort_order).map((s) => s.size_id));
    setSizeQuantities(Object.fromEntries(d.sizes.map((s) => [s.size_id, s.quantity != null ? String(s.quantity) : ""])));
    setSizeChartBySize(Object.fromEntries(d.sizes.filter((s) => s.size_chart_id).map((s) => [s.size_id, s.size_chart_id as string])));
    setColourIds([...d.colours].sort((a, b) => a.sort_order - b.sort_order).map((c) => c.colour_id));
    setPartColours([...d.part_colours].sort((a, b) => a.sort_order - b.sort_order).map((pc) => ({
      key: newId(), style_part_id: pc.style_part_id, colour_id: pc.colour_id ?? "",
      sizeQty: Object.fromEntries(pc.sizes.map((s) => [s.size_id, s.quantity != null ? String(s.quantity) : ""])),
    })));
    const fabricKeyById = new Map(d.fabrics.map((f) => [f.id, newId()]));
    setFabrics(d.fabrics.map((f) => ({
      key: fabricKeyById.get(f.id)!, fabric_name: f.fabric_name, lot_id: f.lot_id ?? "",
      style_part_id: f.style_part_id ?? "", colour_id: f.colour_id ?? "", source_type: f.source_type ?? "",
      knit_dia: f.knit_dia != null ? String(f.knit_dia) : "", finish_dia: f.finish_dia != null ? String(f.finish_dia) : "",
      consumption: f.consumption != null ? String(f.consumption) : "", unit: f.unit ?? "",
      excess_pct: f.excess_pct != null ? String(f.excess_pct) : "",
      gsm: f.gsm != null ? String(f.gsm) : "",
      dyeing_rate: f.dyeing_rate != null ? String(f.dyeing_rate) : "",
      printing_rate: f.printing_rate != null ? String(f.printing_rate) : "",
      notes: f.notes ?? "",
      size_breakdown: Object.fromEntries(f.size_breakdown.map((s) => [s.size_id, String(s.quantity)])),
    })));
    setYarns(d.yarns.map((y) => ({
      key: newId(), yarn_name: y.yarn_name, lot_id: y.lot_id ?? "",
      fabricKey: (y.style_fabric_id && fabricKeyById.get(y.style_fabric_id)) || "",
      colour_id: y.colour_id ?? "", counts: y.counts ?? "", consumption_pct: y.consumption_pct != null ? String(y.consumption_pct) : "",
      quantity: y.quantity != null ? String(y.quantity) : "", unit: y.unit ?? "", notes: y.notes ?? "",
    })));
    const loadedProcesses = [...d.processes].sort((a, b) => a.seq - b.seq).map((p) => ({
      seq: p.seq, row: {
      key: newId(), process_name: p.process_name, process_master_id: p.process_master_id ?? "", style_part_id: p.style_part_id ?? "", is_enabled: p.is_enabled,
      tolerance_pct: p.tolerance_pct != null ? String(p.tolerance_pct) : "",
      input_unit: p.input_unit ?? "", output_unit: p.output_unit ?? "", conversion_rule: p.conversion_rule ?? "",
      min_rate: p.min_rate != null ? String(p.min_rate) : "", max_rate: p.max_rate != null ? String(p.max_rate) : "",
      planned_rate: p.planned_rate != null ? String(p.planned_rate) : "", notes: p.notes ?? "",
      sub_processes: [...p.sub_processes].sort((a, b) => a.seq - b.seq).map((sp) => ({
        key: newId(), name: sp.name,
        min_rate: sp.min_rate != null ? String(sp.min_rate) : "",
        max_rate: sp.max_rate != null ? String(sp.max_rate) : "",
        planned_rate: sp.planned_rate != null ? String(sp.planned_rate) : "",
      })),
    } as ProcessRow }));
    setProcesses(loadedProcesses.map((lp) => lp.row));
    setTrims(d.trims.map((t) => ({
      key: newId(), process_key: loadedProcesses.find((lp) => lp.seq === t.process_seq)?.row.key ?? "", trim_name: t.trim_name, lot_id: t.lot_id ?? "",
      style_part_id: t.style_part_id ?? "", colour_id: t.colour_id ?? "",
      quantity: t.quantity != null ? String(t.quantity) : "", unit: t.unit ?? "",
      category: t.category ?? "Sizable", excess_pct: t.excess_pct != null ? String(t.excess_pct) : "", notes: t.notes ?? "",
      size_breakdown: Object.fromEntries(t.size_breakdown.map((sb) => [sb.size_id, String(sb.quantity)])),
    })));
    setPackingMaterials(d.packing_materials.map((p) => ({
      key: newId(), material_name: p.material_name, product_id: p.product_id ?? "",
      quantity: p.quantity != null ? String(p.quantity) : "", unit: p.unit ?? "",
      excess_pct: p.excess_pct != null ? String(p.excess_pct) : "", consumption_stage: p.consumption_stage ?? "", notes: p.notes ?? "",
    })));
    setAdditionalCosts(d.additional_costs.map((a) => ({
      key: newId(), cost_type: a.cost_type === "agent_commission" ? "agent_commission" : "additional",
      description: a.description, amount: a.amount != null ? String(a.amount) : "",
      basis: a.basis ?? "", party_vendor_id: a.party_vendor_id ?? "", notes: a.notes ?? "",
    })));
  }, [styleQuery.data]);

  const sizeById = useMemo(() => new Map((sizes.data ?? []).map((s) => [s.id, s.name])), [sizes.data]);
  const colourById = useMemo(() => new Map((colours.data ?? []).map((c) => [c.id, c.name])), [colours.data]);
  const totalTolerancePct = useMemo(
    () => processes.filter((p) => p.is_enabled && p.tolerance_pct).reduce((sum, p) => sum + Number(p.tolerance_pct), 0),
    [processes]
  );
  const yarnCompositionByFabric = useMemo(() => {
    const totals = new Map<string, number>();
    for (const y of yarns) {
      if (!y.fabricKey || !y.consumption_pct) continue;
      totals.set(y.fabricKey, (totals.get(y.fabricKey) ?? 0) + Number(y.consumption_pct));
    }
    return totals;
  }, [yarns]);
  const agentVendors = useMemo(() => (vendors.data ?? []).filter((v) => v.vendor_type === "agent"), [vendors.data]);

  function toggleSize(id: string) {
    setSizeIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }
  function toggleColour(id: string) {
    setColourIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }
  function updateSizeQuantity(sizeId: string, qty: string) {
    setSizeQuantities((prev) => ({ ...prev, [sizeId]: qty }));
  }
  function addPartColour() {
    setPartColours((r) => [...r, { key: newId(), style_part_id: "", colour_id: "", sizeQty: {} }]);
  }
  function updatePartColour(key: string, patch: Partial<PartColourRow>) {
    setPartColours((r) => r.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }
  function removePartColour(key: string) {
    setPartColours((r) => r.filter((row) => row.key !== key));
  }
  function updatePartSizeQty(key: string, sizeId: string, qty: string) {
    setPartColours((r) => r.map((row) => (row.key === key ? { ...row, sizeQty: { ...row.sizeQty, [sizeId]: qty } } : row)));
  }
  function loadSizeChart(chartId: string) {
    setLoadChartId(chartId);
    const chart = (sizeCharts.data ?? []).find((c) => c.id === chartId);
    if (!chart) return;
    const newIds = chart.items.map((i) => i.size_id);
    setSizeIds((prev) => Array.from(new Set([...prev, ...newIds])));
    setSizeQuantities((prev) => {
      const next = { ...prev };
      for (const i of chart.items) next[i.size_id] = i.quantity != null ? String(i.quantity) : "";
      return next;
    });
    setSizeChartBySize((prev) => {
      const next = { ...prev };
      for (const i of chart.items) next[i.size_id] = chartId;
      return next;
    });
  }

  async function addSizeRange() {
    const fromStr = rangeFrom.trim();
    if (!fromStr) return;
    const toStr = rangeTo.trim();
    const isPlainNumber = (s: string) => /^-?\d+(\.\d+)?$/.test(s);

    let values: string[];
    if (toStr) {
      // A "To" bound only makes sense as a numeric run (e.g. 75 to 100 step 5).
      if (!isPlainNumber(fromStr) || !isPlainNumber(toStr)) {
        setErr('A size range needs plain numbers in "From" and "To", e.g. 75 to 100. For a text size like "0-3M" or "XL", leave "To" blank.');
        return;
      }
      const from = parseFloat(fromStr);
      const to = parseFloat(toStr);
      const step = parseFloat(rangeStep) || 1;
      if (to < from || step <= 0) {
        setErr('"To" must be greater than or equal to "From", and step must be positive.');
        return;
      }
      values = [];
      for (let v = from; v <= to + 1e-9; v += step) values.push(String(Math.round(v * 100) / 100));
    } else {
      // No range end — add "From" as a single literal size name, numeric or
      // text alike (e.g. "0-3M", "XL", "Free Size").
      values = [fromStr];
    }
    setErr("");
    setAddingSizes(true);
    try {
      const newIds: string[] = [];
      for (const v of values) {
        const res = await api.post("/master/sizes", { name: v });
        newIds.push(res.data.data.id);
      }
      await qc.invalidateQueries({ queryKey: ["master-sizes"] });
      setSizeIds((prev) => Array.from(new Set([...prev, ...newIds])));
      setRangeFrom("");
      setRangeTo("");
      setRangeStep("1");
    } catch {
      setErr("Failed to add size(s). Please try again.");
    } finally {
      setAddingSizes(false);
    }
  }

  const skuPreview = useMemo(() => {
    if (!sizeIds.length) return [];
    const base = code.trim() || name.trim() || "STYLE";
    const rows: { sku: string; size: string; colour: string }[] = [];
    if (!colourIds.length) {
      for (const sId of sizeIds) {
        const sizeName = sizeById.get(sId) ?? "";
        rows.push({ sku: `${base}-${sizeName}`, size: sizeName, colour: "" });
      }
    } else {
      for (const cId of colourIds) {
        for (const sId of sizeIds) {
          const colourName = (colourById.get(cId) ?? "").toUpperCase().replace(/\s+/g, "-");
          const sizeName = sizeById.get(sId) ?? "";
          rows.push({ sku: `${base}-${sizeName}-${colourName}`, size: sizeName, colour: colourById.get(cId) ?? "" });
        }
      }
    }
    return rows;
  }, [sizeIds, colourIds, sizeById, colourById, code, name]);

  // ── Yarn rows ────────────────────────────────────────────────────────────
  function addYarn() {
    setYarns((r) => [...r, {
      key: newId(), yarn_name: "", lot_id: "", fabricKey: "", colour_id: "", counts: "", consumption_pct: "",
      quantity: "", unit: "kg", notes: "",
    }]);
  }
  function updateYarn(key: string, patch: Partial<YarnRow>) {
    setYarns((r) => r.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }
  function removeYarn(key: string) {
    setYarns((r) => r.filter((row) => row.key !== key));
  }

  // ── Fabric rows ──────────────────────────────────────────────────────────
  function addFabric() {
    setFabrics((r) => [...r, {
      key: newId(), fabric_name: "", lot_id: "", style_part_id: "", colour_id: "", source_type: "",
      knit_dia: "", finish_dia: "", consumption: "", unit: "kg", excess_pct: "", gsm: "",
      dyeing_rate: "", printing_rate: "", notes: "", size_breakdown: {},
    }]);
  }
  function updateFabric(key: string, patch: Partial<FabricRow>) {
    setFabrics((r) => r.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }
  function removeFabric(key: string) {
    setFabrics((r) => r.filter((row) => row.key !== key));
  }
  function updateFabricSizeQty(key: string, sizeId: string, qty: string) {
    setFabrics((r) => r.map((row) => (row.key === key ? { ...row, size_breakdown: { ...row.size_breakdown, [sizeId]: qty } } : row)));
  }

  // ── Process rows ─────────────────────────────────────────────────────────
  function addProcess() {
    setProcesses((r) => [...r, {
      key: newId(), process_name: "", process_master_id: "", style_part_id: "", is_enabled: true,
      tolerance_pct: "", input_unit: "", output_unit: "", conversion_rule: "",
      min_rate: "", max_rate: "", planned_rate: "", notes: "", sub_processes: [],
    }]);
  }
  function updateProcess(key: string, patch: Partial<ProcessRow>) {
    setProcesses((r) => r.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }
  function selectProcessMaster(key: string, masterId: string) {
    const master = (processMasters.data ?? []).find((m) => m.id === masterId);
    setProcesses((r) => r.map((row) => {
      if (row.key !== key) return row;
      if (!master) return { ...row, process_master_id: "" };
      return {
        ...row,
        process_master_id: masterId,
        process_name: row.process_name.trim() ? row.process_name : master.name,
        tolerance_pct: row.tolerance_pct || (master.default_tolerance_pct != null ? String(master.default_tolerance_pct) : ""),
        input_unit: row.input_unit || master.default_unit || "",
        output_unit: row.output_unit || master.default_unit || "",
        min_rate: row.min_rate || (master.default_min_rate != null ? String(master.default_min_rate) : ""),
        max_rate: row.max_rate || (master.default_max_rate != null ? String(master.default_max_rate) : ""),
        planned_rate: row.planned_rate || (master.default_planned_rate != null ? String(master.default_planned_rate) : ""),
      };
    }));
  }
  function removeProcess(key: string) {
    setProcesses((r) => r.filter((row) => row.key !== key));
    setTrims((r) => r.map((t) => (t.process_key === key ? { ...t, process_key: "" } : t)));
  }
  function moveProcess(key: string, dir: -1 | 1) {
    setProcesses((r) => {
      const idx = r.findIndex((row) => row.key === key);
      const swapWith = idx + dir;
      if (idx === -1 || swapWith < 0 || swapWith >= r.length) return r;
      const copy = [...r];
      [copy[idx], copy[swapWith]] = [copy[swapWith], copy[idx]];
      return copy;
    });
  }
  function addSubProcess(processKey: string) {
    setProcesses((r) => r.map((row) => row.key === processKey
      ? { ...row, sub_processes: [...row.sub_processes, { key: newId(), name: "", min_rate: "", max_rate: "", planned_rate: "" }] }
      : row));
  }
  function updateSubProcess(processKey: string, subKey: string, patch: Partial<SubProcessRow>) {
    setProcesses((r) => r.map((row) => row.key === processKey
      ? { ...row, sub_processes: row.sub_processes.map((sp) => (sp.key === subKey ? { ...sp, ...patch } : sp)) }
      : row));
  }
  function removeSubProcess(processKey: string, subKey: string) {
    setProcesses((r) => r.map((row) => row.key === processKey
      ? { ...row, sub_processes: row.sub_processes.filter((sp) => sp.key !== subKey) }
      : row));
  }

  // ── Trim rows ────────────────────────────────────────────────────────────
  function addTrim(processKey = "") {
    setTrims((r) => [...r, { key: newId(), process_key: processKey, trim_name: "", lot_id: "", style_part_id: "", colour_id: "", quantity: "", unit: "Nos", category: "Sizable", excess_pct: "", notes: "", size_breakdown: {} }]);
  }
  function updateTrim(key: string, patch: Partial<TrimRow>) {
    setTrims((r) => r.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }
  function updateTrimSizeQty(key: string, sizeId: string, qty: string) {
    setTrims((r) => r.map((row) => (row.key === key ? { ...row, size_breakdown: { ...row.size_breakdown, [sizeId]: qty } } : row)));
  }
  function removeTrim(key: string) {
    setTrims((r) => r.filter((row) => row.key !== key));
  }

  // ── Packing material rows ──────────────────────────────────────────────────
  function addPacking() {
    setPackingMaterials((r) => [...r, { key: newId(), material_name: "", product_id: "", quantity: "", unit: "Nos", excess_pct: "", consumption_stage: "", notes: "" }]);
  }
  function updatePacking(key: string, patch: Partial<PackingRow>) {
    setPackingMaterials((r) => r.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }
  function removePacking(key: string) {
    setPackingMaterials((r) => r.filter((row) => row.key !== key));
  }

  // ── Additional cost rows ─────────────────────────────────────────────────
  function addAdditionalCost() {
    setAdditionalCosts((r) => [...r, { key: newId(), cost_type: "additional", description: "", amount: "", basis: "", party_vendor_id: "", notes: "" }]);
  }
  function updateAdditionalCost(key: string, patch: Partial<AdditionalCostRow>) {
    setAdditionalCosts((r) => r.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }
  function removeAdditionalCost(key: string) {
    setAdditionalCosts((r) => r.filter((row) => row.key !== key));
  }

  const mut = useMutation({
    mutationFn: async () => {
      const submittedFabricIndexByKey = new Map(
        fabrics.filter((f) => f.fabric_name.trim()).map((f, i) => [f.key, i])
      );
      const payload = {
        name: name.trim(),
        code: code.trim() || undefined,
        description: description.trim() || undefined,
        garment_type: garmentType.trim() || undefined,
        gender: gender.trim() || undefined,
        brand_id: brandId || undefined,
        pieces_per_box: piecesPerBox ? Number(piecesPerBox) : undefined,
        fabric_source: fabricSource,
        season: season.trim() || undefined,
        final_output_unit: finalOutputUnit || undefined,
        target_price: targetPrice ? Number(targetPrice) : undefined,
        product_id: productId || undefined,
        sizes: sizeIds.map((size_id, i) => ({
          size_id, sort_order: i,
          quantity: sizeQuantities[size_id] ? Number(sizeQuantities[size_id]) : undefined,
          size_chart_id: sizeChartBySize[size_id] || undefined,
        })),
        colours: colourIds.map((colour_id, i) => ({ colour_id, sort_order: i })),
        part_colours: partColours.filter((p) => p.style_part_id).map((p, i) => ({
          style_part_id: p.style_part_id,
          colour_id: p.colour_id || undefined,
          sort_order: i,
          sizes: Object.entries(p.sizeQty)
            .filter(([, v]) => v)
            .map(([size_id, qty], j) => ({ size_id, quantity: Number(qty), sort_order: j })),
        })),
        yarns: (fabricSource === "yarn" ? yarns : []).filter((y) => y.yarn_name.trim()).map((y) => ({
          yarn_name: y.yarn_name.trim(),
          lot_id: y.lot_id || undefined,
          fabric_index: y.fabricKey ? submittedFabricIndexByKey.get(y.fabricKey) : undefined,
          colour_id: y.colour_id || undefined,
          counts: y.counts.trim() || undefined,
          consumption_pct: y.consumption_pct ? Number(y.consumption_pct) : undefined,
          quantity: y.quantity ? Number(y.quantity) : undefined,
          unit: y.unit || undefined,
          notes: y.notes || undefined,
        })),
        fabrics: fabrics.filter((f) => f.fabric_name.trim()).map((f) => ({
          fabric_name: f.fabric_name.trim(),
          lot_id: f.lot_id || undefined,
          style_part_id: f.style_part_id || undefined,
          colour_id: f.colour_id || undefined,
          source_type: f.source_type || undefined,
          knit_dia: f.knit_dia ? Number(f.knit_dia) : undefined,
          finish_dia: f.finish_dia ? Number(f.finish_dia) : undefined,
          consumption: f.consumption ? Number(f.consumption) : undefined,
          unit: f.unit || undefined,
          excess_pct: f.excess_pct ? Number(f.excess_pct) : undefined,
          gsm: f.gsm ? Number(f.gsm) : undefined,
          dyeing_rate: f.dyeing_rate ? Number(f.dyeing_rate) : undefined,
          printing_rate: f.printing_rate ? Number(f.printing_rate) : undefined,
          notes: f.notes || undefined,
          size_breakdown: Object.entries(f.size_breakdown).filter(([, v]) => v).map(([size_id, qty]) => ({ size_id, quantity: Number(qty) })),
        })),
        processes: processes.filter((p) => p.process_name.trim()).map((p, i) => ({
          seq: i,
          process_name: p.process_name.trim(),
          process_master_id: p.process_master_id || undefined,
          style_part_id: p.style_part_id || undefined,
          is_enabled: p.is_enabled,
          tolerance_pct: p.tolerance_pct ? Number(p.tolerance_pct) : undefined,
          input_unit: p.input_unit || undefined,
          output_unit: p.output_unit || undefined,
          conversion_rule: p.conversion_rule || undefined,
          min_rate: p.min_rate ? Number(p.min_rate) : undefined,
          max_rate: p.max_rate ? Number(p.max_rate) : undefined,
          planned_rate: p.planned_rate ? Number(p.planned_rate) : undefined,
          notes: p.notes || undefined,
          sub_processes: p.sub_processes.filter((sp) => sp.name.trim()).map((sp, si) => ({
            seq: si, name: sp.name.trim(),
            min_rate: sp.min_rate ? Number(sp.min_rate) : undefined,
            max_rate: sp.max_rate ? Number(sp.max_rate) : undefined,
            planned_rate: sp.planned_rate ? Number(sp.planned_rate) : undefined,
          })),
        })),
        trims: trims.filter((t) => t.trim_name.trim()).map((t) => ({
          trim_name: t.trim_name.trim(),
          lot_id: t.lot_id || undefined,
          style_part_id: t.style_part_id || undefined,
          colour_id: t.colour_id || undefined,
          quantity: t.quantity ? Number(t.quantity) : undefined,
          unit: t.unit || undefined,
          category: t.category || undefined,
          process_seq: (() => {
            const named = processes.filter((p) => p.process_name.trim());
            const idx = named.findIndex((p) => p.key === t.process_key);
            return idx >= 0 ? idx : undefined;
          })(),
          excess_pct: t.excess_pct ? Number(t.excess_pct) : undefined,
          notes: t.notes || undefined,
          size_breakdown: t.category === "Sizable"
            ? Object.entries(t.size_breakdown).filter(([, v]) => v).map(([size_id, qty]) => ({ size_id, quantity: Number(qty) }))
            : [],
        })),
        packing_materials: packingMaterials.filter((p) => p.material_name.trim()).map((p) => ({
          material_name: p.material_name.trim(),
          product_id: p.product_id || undefined,
          quantity: p.quantity ? Number(p.quantity) : undefined,
          unit: p.unit || undefined,
          excess_pct: p.excess_pct ? Number(p.excess_pct) : undefined,
          consumption_stage: p.consumption_stage || undefined,
          notes: p.notes || undefined,
        })),
        additional_costs: additionalCosts.filter((a) => a.description.trim()).map((a) => ({
          cost_type: a.cost_type,
          description: a.description.trim(),
          amount: a.amount ? Number(a.amount) : undefined,
          basis: a.basis || undefined,
          party_vendor_id: a.cost_type === "agent_commission" && a.party_vendor_id ? a.party_vendor_id : undefined,
          notes: a.notes || undefined,
        })),
      };
      return isEdit
        ? api.patch(`/production/styles/${styleId}`, payload)
        : api.post("/production/styles", payload);
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["styles-list"] });
      if (isEdit) qc.invalidateQueries({ queryKey: ["style-detail", styleId] });
      router.push(`/production/styles/${res.data.data.id}`);
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: { message?: string }; detail?: string } } })
        ?.response?.data?.error?.message
        ?? (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErr(typeof msg === "string" ? msg : `Failed to ${isEdit ? "update" : "create"} style`);
    },
  });

  const unitOptionsInput = (value: string, onChange: (v: string) => void, placeholder: string) => (
    <Input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
  );

  const renderTrim = (t: TrimRow) => (
    <div key={t.key} className="p-3 rounded-xl border border-border bg-card space-y-2">
      <div className="flex items-start gap-2">
        <Input value={t.trim_name} onChange={(e) => updateTrim(t.key, { trim_name: e.target.value })} placeholder="Trim name, e.g. Elastic-25mm-White" className="flex-1" />
        <RemoveRowButton onClick={() => removeTrim(t.key)} />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <SearchableSelect
          value={t.style_part_id}
          onChange={(v) => updateTrim(t.key, { style_part_id: v })}
          placeholder="— Part (optional) —"
          accent={INDIGO}
          options={[
            { value: "", label: "— Part (optional) —" },
            ...(styleParts.data ?? []).map((sp) => ({ value: sp.id, label: sp.name })),
          ]}
        />
        <SearchableSelect
          value={t.colour_id}
          onChange={(v) => updateTrim(t.key, { colour_id: v })}
          placeholder="— Trim Colour (optional) —"
          accent={INDIGO}
          options={[
            { value: "", label: "— Trim Colour (optional) —" },
            ...(colours.data ?? []).map((c) => ({ value: c.id, label: c.name })),
          ]}
        />
        <SearchableSelect
          value={t.lot_id}
          onChange={(v) => updateTrim(t.key, { lot_id: v })}
          placeholder="Link trim lot (optional)"
          accent={INDIGO}
          options={(trimLots.data ?? []).map((l) => ({ value: l.id, label: l.lot_number, meta: [l.trim_type, l.colour].filter(Boolean).join(" · ") || undefined }))}
        />
      </div>
      <div className="grid grid-cols-5 gap-2">
        <div className="flex gap-1">
          <Input type="number" step="0.0001" value={t.quantity} onChange={(e) => updateTrim(t.key, { quantity: e.target.value })} placeholder="Qty/Pcs" />
          <button
            type="button"
            onClick={() => setFactorCalcKey(t.key)}
            title="Calculate Qty/Pcs from a pack ratio"
            className="shrink-0 px-2 rounded-lg border border-border text-xs text-muted-foreground hover:text-foreground hover:border-foreground/40 transition-colors"
          >
            ƒ
          </button>
        </div>
        {unitOptionsInput(t.unit, (v) => updateTrim(t.key, { unit: v }), "Unit")}
        <SegControl options={TRIM_CATEGORIES} value={t.category} onChange={(v) => updateTrim(t.key, { category: v })} />
        <Input type="number" step="0.01" value={t.excess_pct} onChange={(e) => updateTrim(t.key, { excess_pct: e.target.value })} placeholder="Wastage %" />
      </div>
      {t.category === "Sizable" && sizeIds.length > 0 && (
        <div className="pt-1">
          <p className="text-[11px] text-muted-foreground mb-1.5">
            Qty per size (§21) — overrides the flat Qty above when filled in; fetched automatically into every Lot created from this Style.
          </p>
          <div className="flex gap-2 flex-wrap">
            {sizeIds.map((sId) => (
              <div key={sId} className="flex items-center gap-1.5">
                <span className="text-xs font-medium">{sizeById.get(sId) ?? "—"}</span>
                <input
                  type="number" step="0.0001"
                  value={t.size_breakdown[sId] ?? ""}
                  onChange={(e) => updateTrimSizeQty(t.key, sId, e.target.value)}
                  placeholder="Qty"
                  className="w-20 rounded border border-input bg-background px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  if (isEdit && styleQuery.isLoading) {
    return <div className="p-8 text-sm text-muted-foreground">Loading style…</div>;
  }

  return (
    <div className="p-8 pb-32 space-y-8 max-w-5xl">
      {factorCalcKey && (
        <FactorCalcModal
          onApply={(qty) => updateTrim(factorCalcKey, { quantity: String(qty) })}
          onClose={() => setFactorCalcKey(null)}
        />
      )}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          PRODUCTION / STYLES / {isEdit ? "EDIT" : "NEW"}
        </p>
        <h1 className="text-2xl font-bold tracking-tight">{isEdit ? "Edit Style Master" : "New Style Master"}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Define the complete production blueprint — variants, materials, workflow, and rates. A LOT created from this
          Style will snapshot this configuration; later edits will not retroactively change existing LOTs.
        </p>
      </div>

      <form onSubmit={(e) => { e.preventDefault(); setErr(null); mut.mutate(); }} className="space-y-6">
        {/* 1. Basic Information */}
        <Section n={1} title="Basic Information" subtitle="Style identity">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Style Name" required>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. SK-203-50" required />
            </Field>
            <Field label="Style Code" hint="Used as the SKU prefix">
              <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. SK-203-50" />
            </Field>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Field label="Garment Type">
              <Input value={garmentType} onChange={(e) => setGarmentType(e.target.value)} placeholder="e.g. T-Shirt" />
            </Field>
            <Field label="Product Category (optional)">
              <SearchableSelect
                value={gender}
                onChange={setGender}
                placeholder="— Not specified —"
                accent={INDIGO}
                options={[
                  { value: "", label: "— Not specified —" },
                  ...[...GENDER_OPTIONS, ...(gender && !GENDER_OPTIONS.includes(gender) ? [gender] : [])].map((g) => ({ value: g, label: g })),
                ]}
              />
            </Field>
            <Field label="Season">
              <Input value={season} onChange={(e) => setSeason(e.target.value)} placeholder="e.g. SS26" />
            </Field>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Field label="Brand (optional)">
              <SearchableSelect
                value={brandId}
                onChange={setBrandId}
                placeholder="— Not specified —"
                accent={INDIGO}
                options={[
                  { value: "", label: "— Not specified —" },
                  ...(brands.data ?? []).map((b) => ({ value: b.id, label: b.name })),
                ]}
              />
            </Field>
          </div>
          <Field label="Description">
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Additional details…" />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Final Output Unit" hint="The unit the finished, packed output is measured in for this style">
              <SegControl options={FINAL_OUTPUT_UNITS} value={finalOutputUnit} onChange={setFinalOutputUnit} />
            </Field>
            <Field label="Pieces per Box" hint="Used to show box counts alongside piece quantities in production">
              <Input type="number" min="1" step="1" value={piecesPerBox} onChange={(e) => setPiecesPerBox(e.target.value)} placeholder="e.g. 12" />
            </Field>
            <Field label="Fabric Source" hint="Purchased fabric skips the yarn process entirely">
              <SegControl options={["Made from yarn", "Purchased directly"]} value={fabricSource === "yarn" ? "Made from yarn" : "Purchased directly"} onChange={(v) => setFabricSource(v === "Made from yarn" ? "yarn" : "purchased")} />
            </Field>
            <Field label="Target Price (₹)" hint="Baseline selling price for this style — distinct from actual production cost">
              <Input type="number" step="0.01" value={targetPrice} onChange={(e) => setTargetPrice(e.target.value)} placeholder="0.00" />
            </Field>
          </div>
          <Field label="Link to Product" hint="Leave blank to auto-create a new sellable Product for this Style. Linking carries over GST/HSN from the Product master.">
            <SearchableSelect
              value={productId}
              onChange={setProductId}
              placeholder="— Auto-create a new Product —"
              accent={INDIGO}
              options={(products.data ?? []).map((p) => ({ value: p.id, label: p.name, meta: p.code }))}
            />
            {isEdit && linkedProduct && (
              <p className="text-[11px] text-muted-foreground mt-1.5">
                Linked Product: <span className="font-mono">{linkedProduct.code ?? "—"}</span>
                {linkedProduct.gst_rate != null && <> · GST {linkedProduct.gst_rate}%</>}
              </p>
            )}
          </Field>
        </Section>

        {/* 2 & 3. Sizes / Colours / SKU */}
        <Section n={2} title="Sizes, Colours & SKU" subtitle="Applicable size chart and colour variants — Style + variant dimensions form the SKU">
          <Field label="Load from Size Chart" hint="Optional — merges a reusable chart's sizes and default quantities in; edit any value below afterward without affecting the saved chart">
            <SearchableSelect
              value={loadChartId}
              onChange={loadSizeChart}
              placeholder="— None —"
              accent={INDIGO}
              options={(sizeCharts.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
            />
          </Field>
          <Field label="Applicable Sizes">
            <div className="flex gap-1.5 flex-wrap">
              {(sizes.data ?? []).map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => toggleSize(s.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    sizeIds.includes(s.id)
                      ? "bg-primary/10 text-primary border-primary/40"
                      : "bg-background border-border text-muted-foreground hover:border-foreground/30"
                  }`}
                >
                  {s.name}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 mt-2.5 p-2.5 rounded-lg border border-dashed border-border">
              <span className="text-[11px] text-muted-foreground whitespace-nowrap">Add size(s):</span>
              <Input
                value={rangeFrom}
                onChange={(e) => setRangeFrom(e.target.value)}
                placeholder="e.g. 75 or 0-3M"
                className="!py-1.5 w-28"
              />
              <span className="text-[11px] text-muted-foreground">to</span>
              <Input
                value={rangeTo}
                onChange={(e) => setRangeTo(e.target.value)}
                placeholder="To (optional)"
                className="!py-1.5 w-28"
              />
              <span className="text-[11px] text-muted-foreground">step</span>
              <Input
                value={rangeStep}
                onChange={(e) => setRangeStep(e.target.value)}
                placeholder="1"
                className="!py-1.5 w-16"
              />
              <button
                type="button"
                onClick={addSizeRange}
                disabled={!rangeFrom.trim() || addingSizes}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold border border-dashed border-border text-muted-foreground hover:text-foreground hover:border-foreground/40 transition-colors disabled:opacity-50 whitespace-nowrap"
              >
                <Plus className="h-3.5 w-3.5" /> {addingSizes ? "Adding…" : "Add"}
              </button>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">
              Leave &ldquo;To&rdquo; blank to add exactly what you type in &ldquo;From&rdquo; as one size — numeric or text, e.g. &ldquo;0-3M&rdquo;, &ldquo;XL&rdquo;, &ldquo;Free Size&rdquo;. Fill in &ldquo;To&rdquo; for a numeric run instead, e.g. &ldquo;75&rdquo; to &ldquo;100&rdquo; step &ldquo;5&rdquo; → 75, 80, 85, 90, 95, 100.
            </p>
          </Field>
          {sizeIds.length > 0 && (
            <Field label="Quantity per Size" hint="Quantity/configuration applicable for each size — from the loaded chart, or entered directly">
              <div className="space-y-1.5">
                {sizeIds.map((sId) => (
                  <div key={sId} className="flex items-center gap-2">
                    <span className="text-xs font-medium w-20 flex-shrink-0">{sizeById.get(sId) ?? "—"}</span>
                    <Input
                      type="number" step="0.001"
                      value={sizeQuantities[sId] ?? ""}
                      onChange={(e) => updateSizeQuantity(sId, e.target.value)}
                      placeholder="Quantity"
                      className="!py-1.5 w-32"
                    />
                    {sizeChartBySize[sId] && (
                      <span className="text-[11px] text-muted-foreground">
                        from {(sizeCharts.data ?? []).find((c) => c.id === sizeChartBySize[sId])?.name ?? "chart"}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </Field>
          )}
          <Field label="Applicable Colours">
            <div className="flex gap-1.5 flex-wrap">
              {(colours.data ?? []).map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => toggleColour(c.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    colourIds.includes(c.id)
                      ? "bg-primary/10 text-primary border-primary/40"
                      : "bg-background border-border text-muted-foreground hover:border-foreground/30"
                  }`}
                >
                  {c.hex_code && <span className="w-2.5 h-2.5 rounded-full border border-black/10" style={{ background: c.hex_code }} />}
                  {c.name}
                </button>
              ))}
            </div>
          </Field>
          <Field
            label="Style Parts (optional)"
            hint="For garments made of multiple parts (e.g. Front, Back, Collar) that need their own colour and size-wise quantities — e.g. a contrast-colour collar. Leave empty for a single-piece style."
          >
            <div className="space-y-3">
              {partColours.map((p) => (
                <div key={p.key} className="p-3 rounded-xl border border-border bg-background space-y-2">
                  <div className="flex items-start gap-2">
                    <div className="flex-1">
                      <SearchableSelect
                        value={p.style_part_id}
                        onChange={(v) => updatePartColour(p.key, { style_part_id: v })}
                        placeholder="Select Style Part"
                        accent={INDIGO}
                        options={(styleParts.data ?? []).map((sp) => ({ value: sp.id, label: sp.name }))}
                      />
                    </div>
                    <div className="flex-1">
                      <SearchableSelect
                        value={p.colour_id}
                        onChange={(v) => updatePartColour(p.key, { colour_id: v })}
                        placeholder="— Colour (optional) —"
                        accent={INDIGO}
                        options={[
                          { value: "", label: "— Colour (optional) —" },
                          ...(colours.data ?? []).map((c) => ({ value: c.id, label: c.name })),
                        ]}
                      />
                    </div>
                    <RemoveRowButton onClick={() => removePartColour(p.key)} />
                  </div>
                  {sizeIds.length > 0 && (
                    <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${Math.min(sizeIds.length, 6)}, minmax(0, 1fr))` }}>
                      {sizeIds.map((sId) => (
                        <div key={sId}>
                          <label className="block text-[10px] text-muted-foreground mb-0.5">
                            {(sizes.data ?? []).find((s) => s.id === sId)?.name ?? "—"}
                          </label>
                          <Input
                            type="number" step="1" placeholder="Qty"
                            value={p.sizeQty[sId] ?? ""}
                            onChange={(e) => updatePartSizeQty(p.key, sId, e.target.value)}
                          />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              <div className="flex items-center gap-3">
                <AddRowButton onClick={addPartColour} label="Add Style Part" />
                {!showAddPart ? (
                  <button type="button" onClick={() => setShowAddPart(true)} className="text-xs font-semibold" style={{ color: INDIGO }}>
                    + New Style Part
                  </button>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <Input
                      value={newPartName}
                      onChange={(e) => setNewPartName(e.target.value)}
                      placeholder="e.g. Collar"
                      className="w-40"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        if (!newPartName.trim()) return;
                        createPartMut.mutate(newPartName.trim());
                        setNewPartName("");
                        setShowAddPart(false);
                      }}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white"
                      style={{ background: INDIGO }}
                    >
                      Add
                    </button>
                    <button type="button" onClick={() => { setShowAddPart(false); setNewPartName(""); }} className="text-xs text-muted-foreground px-2">
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            </div>
          </Field>
          {skuPreview.length > 0 && (
            <div className="rounded-xl border border-border overflow-hidden">
              <p className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground bg-muted/40">
                SKU Preview ({skuPreview.length})
              </p>
              <div className="max-h-40 overflow-y-auto divide-y divide-border">
                {skuPreview.map((row) => (
                  <div key={row.sku} className="flex items-center justify-between px-4 py-1.5 text-xs">
                    <span className="font-mono">{row.sku}</span>
                    <span className="text-muted-foreground">{row.colour ? `${row.colour} · ${row.size}` : row.size}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Section>

        {/* 4. Yarn */}
        {fabricSource === "yarn" && (
        <Section n={3} title="Yarn Requirements" subtitle="References the Yarn Master — quantities and consumption for this style. Assign a yarn to a Fabric below to plan its blend composition (e.g. 65% Cotton + 35% Polyester).">
          <div className="space-y-3">
            {yarns.map((y) => {
              const total = y.fabricKey ? yarnCompositionByFabric.get(y.fabricKey) : undefined;
              return (
              <div key={y.key} className="p-3 rounded-xl border border-border bg-background space-y-2">
                <div className="flex items-start gap-2">
                  <div className="grid grid-cols-4 gap-2 flex-1">
                    <Input value={y.yarn_name} onChange={(e) => updateYarn(y.key, { yarn_name: e.target.value })} placeholder="Yarn name, e.g. 30s VL" className="col-span-2" />
                    <SearchableSelect
                      value={y.lot_id}
                      onChange={(v) => updateYarn(y.key, { lot_id: v })}
                      placeholder="Link yarn lot (optional)"
                      accent={INDIGO}
                      options={(yarnLots.data ?? []).map((l) => ({ value: l.id, label: l.lot_number, meta: l.yarn_count ?? undefined }))}
                    />
                    <div className="flex gap-2">
                      <Input type="number" step="0.0001" value={y.quantity} onChange={(e) => updateYarn(y.key, { quantity: e.target.value })} placeholder="Qty" />
                      {unitOptionsInput(y.unit, (v) => updateYarn(y.key, { unit: v }), "Unit")}
                    </div>
                  </div>
                  <RemoveRowButton onClick={() => removeYarn(y.key)} />
                </div>
                <div className="grid grid-cols-4 gap-2">
                  <SearchableSelect
                    value={y.fabricKey}
                    onChange={(v) => updateYarn(y.key, { fabricKey: v })}
                    placeholder="— Composes which fabric? (optional) —"
                    accent={INDIGO}
                    options={[
                      { value: "", label: "— Not assigned to a fabric —" },
                      ...fabrics.filter((f) => f.fabric_name.trim()).map((f) => ({ value: f.key, label: f.fabric_name })),
                    ]}
                  />
                  <SearchableSelect
                    value={y.colour_id}
                    onChange={(v) => updateYarn(y.key, { colour_id: v })}
                    placeholder="— Colour (optional) —"
                    accent={INDIGO}
                    options={[
                      { value: "", label: "— Colour (optional) —" },
                      ...(colours.data ?? []).map((c) => ({ value: c.id, label: c.name })),
                    ]}
                  />
                  <Input value={y.counts} onChange={(e) => updateYarn(y.key, { counts: e.target.value })} placeholder="Counts, e.g. 30S" />
                  <Input type="number" step="0.01" value={y.consumption_pct} onChange={(e) => updateYarn(y.key, { consumption_pct: e.target.value })} placeholder="Consumption %" />
                </div>
                {y.fabricKey && total !== undefined && (
                  <p className={`text-[11px] font-medium ${Math.abs(total - 100) < 1 ? "text-emerald-600" : "text-amber-600"}`}>
                    This fabric&apos;s yarn composition totals {total}% {Math.abs(total - 100) < 1 ? "✓" : "— must total 100%"}
                  </p>
                )}
              </div>
              );
            })}
            <AddRowButton onClick={addYarn} label="Add Yarn" />
          </div>
        </Section>
        )}

        {/* 5. Fabric */}
        <Section n={fabricSource === "yarn" ? 4 : 3} title="Fabric Requirements" subtitle={fabricSource === "yarn" ? "References the Fabric Master — consumption, unit, excess % per style" : "Fabric is purchased directly (no yarn process) — link the purchased fabric lot, consumption and excess % per style"}>
          <div className="space-y-3">
            {fabrics.map((f) => (
              <div key={f.key} className="p-3 rounded-xl border border-border bg-background space-y-2">
                <div className="flex items-start gap-2">
                  <Input value={f.fabric_name} onChange={(e) => updateFabric(f.key, { fabric_name: e.target.value })} placeholder="Fabric name, e.g. 30sVL-S/J-Pink-30" className="flex-1" />
                  <RemoveRowButton onClick={() => removeFabric(f.key)} />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <SearchableSelect
                    value={f.style_part_id}
                    onChange={(v) => updateFabric(f.key, { style_part_id: v })}
                    placeholder="— Part / Body Part (optional) —"
                    accent={INDIGO}
                    options={[
                      { value: "", label: "— Part / Body Part (optional) —" },
                      ...(styleParts.data ?? []).map((sp) => ({ value: sp.id, label: sp.name })),
                    ]}
                  />
                  <SearchableSelect
                    value={f.colour_id}
                    onChange={(v) => updateFabric(f.key, { colour_id: v })}
                    placeholder="— Fabric Colour (optional) —"
                    accent={INDIGO}
                    options={[
                      { value: "", label: "— Fabric Colour (optional) —" },
                      ...(colours.data ?? []).map((c) => ({ value: c.id, label: c.name })),
                    ]}
                  />
                  <SearchableSelect
                    value={f.source_type}
                    onChange={(v) => updateFabric(f.key, { source_type: v })}
                    placeholder="Source: inherit from Style"
                    accent={INDIGO}
                    options={[
                      { value: "", label: "Source: inherit from Style" },
                      { value: "yarn", label: "From Yarn" },
                      { value: "purchased", label: "Purchased" },
                    ]}
                  />
                </div>
                <div className="grid grid-cols-5 gap-2">
                  <SearchableSelect
                    value={f.lot_id}
                    onChange={(v) => updateFabric(f.key, { lot_id: v })}
                    placeholder="Link fabric lot (optional)"
                    accent={INDIGO}
                    options={(fabricLots.data ?? []).map((l) => ({ value: l.id, label: l.lot_number, meta: [l.construction, l.colour].filter(Boolean).join(" · ") || undefined }))}
                  />
                  <Input type="number" step="0.0001" value={f.consumption} onChange={(e) => updateFabric(f.key, { consumption: e.target.value })} placeholder="Consumption" />
                  {unitOptionsInput(f.unit, (v) => updateFabric(f.key, { unit: v }), "Unit")}
                  <Input type="number" step="0.01" value={f.excess_pct} onChange={(e) => updateFabric(f.key, { excess_pct: e.target.value })} placeholder="Wastage %" />
                  <Input type="number" step="0.01" value={f.gsm} onChange={(e) => updateFabric(f.key, { gsm: e.target.value })} placeholder="GSM" />
                </div>
                <div className="grid grid-cols-4 gap-2">
                  <Input type="number" step="0.01" value={f.dyeing_rate} onChange={(e) => updateFabric(f.key, { dyeing_rate: e.target.value })} placeholder="Dyeing Rate (₹/kg)" />
                  <Input type="number" step="0.01" value={f.printing_rate} onChange={(e) => updateFabric(f.key, { printing_rate: e.target.value })} placeholder="Printing Rate (₹/kg)" />
                  <Input type="number" step="0.01" value={f.knit_dia} onChange={(e) => updateFabric(f.key, { knit_dia: e.target.value })} placeholder="Knit Dia" />
                  <Input type="number" step="0.01" value={f.finish_dia} onChange={(e) => updateFabric(f.key, { finish_dia: e.target.value })} placeholder="Finish Dia" />
                </div>
                {sizeIds.length > 0 && (
                  <div className="pt-1">
                    <p className="text-[11px] text-muted-foreground mb-1.5">
                      Consumption per size — overrides the flat Consumption above when filled in.
                    </p>
                    <div className="flex gap-2 flex-wrap">
                      {sizeIds.map((sId) => (
                        <div key={sId} className="flex items-center gap-1.5">
                          <span className="text-xs font-medium">{sizeById.get(sId) ?? "—"}</span>
                          <input
                            type="number" step="0.0001"
                            value={f.size_breakdown[sId] ?? ""}
                            onChange={(e) => updateFabricSizeQty(f.key, sId, e.target.value)}
                            placeholder="Qty"
                            className="w-20 rounded border border-input bg-background px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
            <AddRowButton onClick={addFabric} label="Add Fabric" />
          </div>
        </Section>

        {/* 6 & 7. Production Workflow / Process Configuration */}
        <Section n={fabricSource === "yarn" ? 5 : 4} title="Production Workflow" subtitle="Configurable process list — add, remove, and reorder processes; each has its own tolerance %, units, conversion, and rate band">
          <div className="space-y-4">
            {processes.map((p, idx) => (
              <div key={p.key} className="rounded-xl border border-border bg-background overflow-hidden">
                <div className="flex items-center gap-2 px-3 py-2 bg-muted/30 border-b border-border">
                  <GripVertical className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                  <span className="text-xs font-mono text-muted-foreground w-5">{idx + 1}</span>
                  <Input
                    value={p.process_name}
                    onChange={(e) => updateProcess(p.key, { process_name: e.target.value })}
                    placeholder="Process name, e.g. Cutting"
                    className="flex-1 !py-1.5"
                  />
                  <label className="flex items-center gap-1.5 text-xs text-muted-foreground px-2 whitespace-nowrap">
                    <input type="checkbox" checked={p.is_enabled} onChange={(e) => updateProcess(p.key, { is_enabled: e.target.checked })} className="h-3.5 w-3.5 rounded border-border accent-primary" />
                    Enabled
                  </label>
                  <button type="button" onClick={() => moveProcess(p.key, -1)} disabled={idx === 0} className="p-1 rounded hover:bg-muted disabled:opacity-30 text-muted-foreground text-xs">↑</button>
                  <button type="button" onClick={() => moveProcess(p.key, 1)} disabled={idx === processes.length - 1} className="p-1 rounded hover:bg-muted disabled:opacity-30 text-muted-foreground text-xs">↓</button>
                  <RemoveRowButton onClick={() => removeProcess(p.key)} />
                </div>
                <div className="p-3 space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Process (from master)" hint="Optional — select to auto-fill the name and blank fields below from a reusable default; your own entries are never overwritten">
                      <SearchableSelect
                        value={p.process_master_id}
                        onChange={(v) => selectProcessMaster(p.key, v)}
                        placeholder="— Custom / no master —"
                        accent={INDIGO}
                        options={(processMasters.data ?? []).map((m) => ({ value: m.id, label: m.name }))}
                      />
                    </Field>
                    <Field label="Applies to Part (optional)" hint="Leave blank if this process applies to the whole style — e.g. a collar may skip a process the front goes through">
                      <SearchableSelect
                        value={p.style_part_id}
                        onChange={(v) => updateProcess(p.key, { style_part_id: v })}
                        placeholder="— Whole style —"
                        accent={INDIGO}
                        options={[
                          { value: "", label: "— Whole style —" },
                          ...(styleParts.data ?? []).map((sp) => ({ value: sp.id, label: sp.name })),
                        ]}
                      />
                    </Field>
                  </div>
                  <div className="grid grid-cols-4 gap-2">
                    <Field label="Tolerance %">
                      <Input type="number" step="0.01" value={p.tolerance_pct} onChange={(e) => updateProcess(p.key, { tolerance_pct: e.target.value })} placeholder="0" />
                    </Field>
                    <Field label="Input Unit">
                      <Input value={p.input_unit} onChange={(e) => updateProcess(p.key, { input_unit: e.target.value })} placeholder="e.g. Kg" />
                    </Field>
                    <Field label="Output Unit">
                      <Input value={p.output_unit} onChange={(e) => updateProcess(p.key, { output_unit: e.target.value })} placeholder="e.g. Pieces" />
                    </Field>
                    <Field label="Conversion Rule">
                      <Input value={p.conversion_rule} onChange={(e) => updateProcess(p.key, { conversion_rule: e.target.value })} placeholder="e.g. 12 Pcs = 1 Dozen" />
                    </Field>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <Field label="Min Rate (₹)">
                      <Input type="number" step="0.01" value={p.min_rate} onChange={(e) => updateProcess(p.key, { min_rate: e.target.value })} placeholder="0.00" />
                    </Field>
                    <Field label="Max Rate (₹)">
                      <Input type="number" step="0.01" value={p.max_rate} onChange={(e) => updateProcess(p.key, { max_rate: e.target.value })} placeholder="0.00" />
                    </Field>
                    <Field label="Planned Rate (₹)">
                      <Input type="number" step="0.01" value={p.planned_rate} onChange={(e) => updateProcess(p.key, { planned_rate: e.target.value })} placeholder="0.00" />
                    </Field>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-foreground mb-1.5">Sub-processes</p>
                    <div className="space-y-1.5">
                      {p.sub_processes.map((sp) => (
                        <div key={sp.key} className="flex items-center gap-2">
                          <Input value={sp.name} onChange={(e) => updateSubProcess(p.key, sp.key, { name: e.target.value })} placeholder="e.g. Power Table" className="flex-1 !py-1.5" />
                          <Input type="number" step="0.01" value={sp.min_rate} onChange={(e) => updateSubProcess(p.key, sp.key, { min_rate: e.target.value })} placeholder="Min ₹" className="w-24 !py-1.5" />
                          <Input type="number" step="0.01" value={sp.max_rate} onChange={(e) => updateSubProcess(p.key, sp.key, { max_rate: e.target.value })} placeholder="Max ₹" className="w-24 !py-1.5" />
                          <Input type="number" step="0.01" value={sp.planned_rate} onChange={(e) => updateSubProcess(p.key, sp.key, { planned_rate: e.target.value })} placeholder="Planned ₹" className="w-28 !py-1.5" />
                          <RemoveRowButton onClick={() => removeSubProcess(p.key, sp.key)} />
                        </div>
                      ))}
                      <AddRowButton onClick={() => addSubProcess(p.key)} label="Add Sub-process" />
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-foreground mb-1.5">Trims used in this process</p>
                    <div className="space-y-2">
                      {trims.filter((t) => t.process_key === p.key).map((t) => renderTrim(t))}
                      <AddRowButton onClick={() => addTrim(p.key)} label="Add Trim (e.g. Elastic)" />
                    </div>
                  </div>
                </div>
              </div>
            ))}
            <div className="flex items-center justify-between">
              <AddRowButton onClick={addProcess} label="Add Process" />
              {processes.length > 0 && (
                <p className="text-xs font-medium text-muted-foreground">
                  Total Tolerance: <span className="text-foreground">{totalTolerancePct}%</span>
                </p>
              )}
            </div>
          </div>
        </Section>

        {trims.some((t) => !t.process_key) && (
          <Section n={fabricSource === "yarn" ? 6 : 5} title="General Trims" subtitle="Trims not tied to a specific process — assign them to a process above by re-adding there, or keep as general requirements">
            <div className="space-y-2">
              {trims.filter((t) => !t.process_key).map((t) => renderTrim(t))}
            </div>
          </Section>
        )}

        {/* 9. Packing Material Planning */}
        <Section n={fabricSource === "yarn" ? 7 : 6} title="Packing Material Planning" subtitle="Required packing materials and the per-piece quantity needed — the total required for a Production Lot is computed automatically from the Lot's planned quantity">
          <div className="space-y-3">
            {packingMaterials.map((p) => (
              <div key={p.key} className="p-3 rounded-xl border border-border bg-background space-y-2">
                <div className="flex items-start gap-2">
                  <div className="flex-1">
                    <SearchableSelect
                      value={p.product_id}
                      onChange={(v) => {
                        const picked = (packingProducts.data ?? []).find((pp) => pp.id === v);
                        updatePacking(p.key, { product_id: v, material_name: picked?.name ?? p.material_name });
                      }}
                      placeholder="Select packing material"
                      accent={INDIGO}
                      options={(packingProducts.data ?? []).map((pp) => ({ value: pp.id, label: pp.name, meta: pp.code }))}
                    />
                  </div>
                  <RemoveRowButton onClick={() => removePacking(p.key)} />
                </div>
                <div className="grid grid-cols-4 gap-2">
                  <Input type="number" step="0.0001" value={p.quantity} onChange={(e) => updatePacking(p.key, { quantity: e.target.value })} placeholder="Per Piece Qty" />
                  {unitOptionsInput(p.unit, (v) => updatePacking(p.key, { unit: v }), "Unit")}
                  <Input type="number" step="0.01" value={p.excess_pct} onChange={(e) => updatePacking(p.key, { excess_pct: e.target.value })} placeholder="Excess %" />
                  <Input value={p.consumption_stage} onChange={(e) => updatePacking(p.key, { consumption_stage: e.target.value })} placeholder="Stage, e.g. After Ironing" />
                </div>
              </div>
            ))}
            <AddRowButton onClick={addPacking} label="Add Packing Material" />
          </div>
        </Section>

        {/* 10. Additional Costs & Agent Commission */}
        <Section n={fabricSource === "yarn" ? 8 : 7} title="Additional Costs & Agent Commission" subtitle="Named cost components outside Fabric/Cutting/Making/Trims — flows into every LOT created from this Style">
          <div className="space-y-3">
            {additionalCosts.map((a) => (
              <div key={a.key} className="p-3 rounded-xl border border-border bg-background space-y-2">
                <div className="flex items-start gap-2">
                  <SegControl
                    options={["Additional", "Agent Commission"]}
                    value={a.cost_type === "agent_commission" ? "Agent Commission" : "Additional"}
                    onChange={(v) => updateAdditionalCost(a.key, { cost_type: v === "Agent Commission" ? "agent_commission" : "additional" })}
                  />
                  <Input value={a.description} onChange={(e) => updateAdditionalCost(a.key, { description: e.target.value })} placeholder="Description, e.g. Freight / Agent commission for Order #123" className="flex-1" />
                  <RemoveRowButton onClick={() => removeAdditionalCost(a.key)} />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <Input type="number" step="0.01" value={a.amount} onChange={(e) => updateAdditionalCost(a.key, { amount: e.target.value })} placeholder="Amount (₹)" />
                  <Input value={a.basis} onChange={(e) => updateAdditionalCost(a.key, { basis: e.target.value })} placeholder="Basis, e.g. per_piece, lumpsum" />
                  {a.cost_type === "agent_commission" && (
                    <SearchableSelect
                      value={a.party_vendor_id}
                      onChange={(v) => updateAdditionalCost(a.key, { party_vendor_id: v })}
                      placeholder="Select Agent"
                      accent={INDIGO}
                      options={agentVendors.map((v) => ({ value: v.id, label: v.name }))}
                    />
                  )}
                </div>
              </div>
            ))}
            <AddRowButton onClick={addAdditionalCost} label="Add Cost" />
          </div>
        </Section>

        {err && (
          <p className="text-sm text-[#1D0DB0] bg-[#1D0DB0]/10 border border-[#1D0DB0]/20 rounded-xl px-4 py-3">{err}</p>
        )}
      </form>

      {/* Sticky review / save bar */}
      <div className="fixed bottom-0 left-0 right-0 lg:left-64 bg-card border-t border-border px-8 py-4 flex items-center justify-between gap-4 z-40">
        <p className="text-xs text-muted-foreground">
          {sizeIds.length} size{sizeIds.length !== 1 ? "s" : ""} · {colourIds.length} colour{colourIds.length !== 1 ? "s" : ""} ·{" "}
          {processes.filter((p) => p.process_name.trim()).length} process{processes.filter((p) => p.process_name.trim()).length !== 1 ? "es" : ""} ·{" "}
          {trims.filter((t) => t.trim_name.trim()).length} trim{trims.filter((t) => t.trim_name.trim()).length !== 1 ? "s" : ""}
        </p>
        <div className="flex gap-3">
          <button type="button" onClick={() => router.back()} className="px-4 py-2 rounded-lg border border-border text-sm font-medium hover:bg-muted transition-colors">
            Cancel
          </button>
          <button
            type="button"
            disabled={!name.trim() || mut.isPending}
            onClick={() => { setErr(null); mut.mutate(); }}
            className="px-5 py-2 rounded-lg text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50 transition-all"
            style={{ background: INDIGO }}
          >
            {mut.isPending ? "Saving…" : isEdit ? "Save Changes" : "Save Style"}
          </button>
        </div>
      </div>
    </div>
  );
}
