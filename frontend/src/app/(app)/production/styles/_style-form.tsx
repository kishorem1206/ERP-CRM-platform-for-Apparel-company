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
interface YarnRow { key: string; yarn_name: string; lot_id: string; quantity: string; unit: string; notes: string }
interface FabricRow { key: string; fabric_name: string; lot_id: string; consumption: string; unit: string; excess_pct: string; gsm: string; dyeing_rate: string; printing_rate: string; notes: string }
interface SubProcessRow { key: string; name: string }
interface ProcessRow {
  key: string; process_name: string; process_master_id: string; is_enabled: boolean;
  tolerance_pct: string; input_unit: string; output_unit: string; conversion_rule: string;
  min_rate: string; max_rate: string; planned_rate: string; notes: string;
  sub_processes: SubProcessRow[];
}
interface TrimRow { key: string; process_key: string; trim_name: string; lot_id: string; quantity: string; unit: string; category: string; excess_pct: string; notes: string; size_breakdown: Record<string, string> }
interface PackingRow { key: string; material_name: string; quantity: string; unit: string; excess_pct: string; consumption_stage: string; notes: string }
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
    final_output_unit: string | null;
    pieces_per_box: number | null; fabric_source: string;
    target_price: number | null;
    product_id: string | null; product_code: string | null; gst_rate: number | null;
    sizes: { size_id: string; sort_order: number; quantity: number | null; size_chart_id: string | null }[];
    colours: { colour_id: string; sort_order: number }[];
    yarns: { yarn_name: string; lot_id: string | null; quantity: number | null; unit: string | null; notes: string | null }[];
    fabrics: { fabric_name: string; lot_id: string | null; consumption: number | null; unit: string | null; excess_pct: number | null; gsm: number | null; dyeing_rate: number | null; printing_rate: number | null; notes: string | null }[];
    processes: {
      seq: number; process_name: string; process_master_id: string | null; is_enabled: boolean; tolerance_pct: number | null;
      input_unit: string | null; output_unit: string | null; conversion_rule: string | null;
      min_rate: number | null; max_rate: number | null; planned_rate: number | null; notes: string | null;
      sub_processes: { seq: number; name: string }[];
    }[];
    trims: { process_seq: number | null; trim_name: string; lot_id: string | null; quantity: number | null; unit: string | null; category: string | null; excess_pct: number | null; notes: string | null; size_breakdown: { size_id: string; quantity: number }[] }[];
    packing_materials: { material_name: string; quantity: number | null; unit: string | null; excess_pct: number | null; consumption_stage: string | null; notes: string | null }[];
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
    setYarns(d.yarns.map((y) => ({
      key: newId(), yarn_name: y.yarn_name, lot_id: y.lot_id ?? "",
      quantity: y.quantity != null ? String(y.quantity) : "", unit: y.unit ?? "", notes: y.notes ?? "",
    })));
    setFabrics(d.fabrics.map((f) => ({
      key: newId(), fabric_name: f.fabric_name, lot_id: f.lot_id ?? "",
      consumption: f.consumption != null ? String(f.consumption) : "", unit: f.unit ?? "",
      excess_pct: f.excess_pct != null ? String(f.excess_pct) : "",
      gsm: f.gsm != null ? String(f.gsm) : "",
      dyeing_rate: f.dyeing_rate != null ? String(f.dyeing_rate) : "",
      printing_rate: f.printing_rate != null ? String(f.printing_rate) : "",
      notes: f.notes ?? "",
    })));
    const loadedProcesses = [...d.processes].sort((a, b) => a.seq - b.seq).map((p) => ({
      seq: p.seq, row: {
      key: newId(), process_name: p.process_name, process_master_id: p.process_master_id ?? "", is_enabled: p.is_enabled,
      tolerance_pct: p.tolerance_pct != null ? String(p.tolerance_pct) : "",
      input_unit: p.input_unit ?? "", output_unit: p.output_unit ?? "", conversion_rule: p.conversion_rule ?? "",
      min_rate: p.min_rate != null ? String(p.min_rate) : "", max_rate: p.max_rate != null ? String(p.max_rate) : "",
      planned_rate: p.planned_rate != null ? String(p.planned_rate) : "", notes: p.notes ?? "",
      sub_processes: [...p.sub_processes].sort((a, b) => a.seq - b.seq).map((sp) => ({ key: newId(), name: sp.name })),
    } as ProcessRow }));
    setProcesses(loadedProcesses.map((lp) => lp.row));
    setTrims(d.trims.map((t) => ({
      key: newId(), process_key: loadedProcesses.find((lp) => lp.seq === t.process_seq)?.row.key ?? "", trim_name: t.trim_name, lot_id: t.lot_id ?? "",
      quantity: t.quantity != null ? String(t.quantity) : "", unit: t.unit ?? "",
      category: t.category ?? "Sizable", excess_pct: t.excess_pct != null ? String(t.excess_pct) : "", notes: t.notes ?? "",
      size_breakdown: Object.fromEntries(t.size_breakdown.map((sb) => [sb.size_id, String(sb.quantity)])),
    })));
    setPackingMaterials(d.packing_materials.map((p) => ({
      key: newId(), material_name: p.material_name,
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
    const from = parseFloat(rangeFrom);
    if (isNaN(from)) return;
    const to = rangeTo.trim() ? parseFloat(rangeTo) : from;
    const step = parseFloat(rangeStep) || 1;
    const values: string[] = [];
    if (!isNaN(to) && to >= from && step > 0) {
      for (let v = from; v <= to + 1e-9; v += step) values.push(String(Math.round(v * 100) / 100));
    } else {
      values.push(String(from));
    }
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
    setYarns((r) => [...r, { key: newId(), yarn_name: "", lot_id: "", quantity: "", unit: "kg", notes: "" }]);
  }
  function updateYarn(key: string, patch: Partial<YarnRow>) {
    setYarns((r) => r.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }
  function removeYarn(key: string) {
    setYarns((r) => r.filter((row) => row.key !== key));
  }

  // ── Fabric rows ──────────────────────────────────────────────────────────
  function addFabric() {
    setFabrics((r) => [...r, { key: newId(), fabric_name: "", lot_id: "", consumption: "", unit: "kg", excess_pct: "", gsm: "", dyeing_rate: "", printing_rate: "", notes: "" }]);
  }
  function updateFabric(key: string, patch: Partial<FabricRow>) {
    setFabrics((r) => r.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }
  function removeFabric(key: string) {
    setFabrics((r) => r.filter((row) => row.key !== key));
  }

  // ── Process rows ─────────────────────────────────────────────────────────
  function addProcess() {
    setProcesses((r) => [...r, {
      key: newId(), process_name: "", process_master_id: "", is_enabled: true,
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
      ? { ...row, sub_processes: [...row.sub_processes, { key: newId(), name: "" }] }
      : row));
  }
  function updateSubProcess(processKey: string, subKey: string, name: string) {
    setProcesses((r) => r.map((row) => row.key === processKey
      ? { ...row, sub_processes: row.sub_processes.map((sp) => (sp.key === subKey ? { ...sp, name } : sp)) }
      : row));
  }
  function removeSubProcess(processKey: string, subKey: string) {
    setProcesses((r) => r.map((row) => row.key === processKey
      ? { ...row, sub_processes: row.sub_processes.filter((sp) => sp.key !== subKey) }
      : row));
  }

  // ── Trim rows ────────────────────────────────────────────────────────────
  function addTrim(processKey = "") {
    setTrims((r) => [...r, { key: newId(), process_key: processKey, trim_name: "", lot_id: "", quantity: "", unit: "Nos", category: "Sizable", excess_pct: "", notes: "", size_breakdown: {} }]);
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
    setPackingMaterials((r) => [...r, { key: newId(), material_name: "", quantity: "", unit: "Nos", excess_pct: "", consumption_stage: "", notes: "" }]);
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
      const payload = {
        name: name.trim(),
        code: code.trim() || undefined,
        description: description.trim() || undefined,
        garment_type: garmentType.trim() || undefined,
        gender: gender.trim() || undefined,
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
        yarns: (fabricSource === "yarn" ? yarns : []).filter((y) => y.yarn_name.trim()).map((y) => ({
          yarn_name: y.yarn_name.trim(),
          lot_id: y.lot_id || undefined,
          quantity: y.quantity ? Number(y.quantity) : undefined,
          unit: y.unit || undefined,
          notes: y.notes || undefined,
        })),
        fabrics: fabrics.filter((f) => f.fabric_name.trim()).map((f) => ({
          fabric_name: f.fabric_name.trim(),
          lot_id: f.lot_id || undefined,
          consumption: f.consumption ? Number(f.consumption) : undefined,
          unit: f.unit || undefined,
          excess_pct: f.excess_pct ? Number(f.excess_pct) : undefined,
          gsm: f.gsm ? Number(f.gsm) : undefined,
          dyeing_rate: f.dyeing_rate ? Number(f.dyeing_rate) : undefined,
          printing_rate: f.printing_rate ? Number(f.printing_rate) : undefined,
          notes: f.notes || undefined,
        })),
        processes: processes.filter((p) => p.process_name.trim()).map((p, i) => ({
          seq: i,
          process_name: p.process_name.trim(),
          process_master_id: p.process_master_id || undefined,
          is_enabled: p.is_enabled,
          tolerance_pct: p.tolerance_pct ? Number(p.tolerance_pct) : undefined,
          input_unit: p.input_unit || undefined,
          output_unit: p.output_unit || undefined,
          conversion_rule: p.conversion_rule || undefined,
          min_rate: p.min_rate ? Number(p.min_rate) : undefined,
          max_rate: p.max_rate ? Number(p.max_rate) : undefined,
          planned_rate: p.planned_rate ? Number(p.planned_rate) : undefined,
          notes: p.notes || undefined,
          sub_processes: p.sub_processes.filter((sp) => sp.name.trim()).map((sp, si) => ({ seq: si, name: sp.name.trim() })),
        })),
        trims: trims.filter((t) => t.trim_name.trim()).map((t) => ({
          trim_name: t.trim_name.trim(),
          lot_id: t.lot_id || undefined,
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
      <div className="grid grid-cols-5 gap-2">
        <SearchableSelect
          value={t.lot_id}
          onChange={(v) => updateTrim(t.key, { lot_id: v })}
          placeholder="Link trim lot (optional)"
          accent={INDIGO}
          options={(trimLots.data ?? []).map((l) => ({ value: l.id, label: l.lot_number, meta: [l.trim_type, l.colour].filter(Boolean).join(" · ") || undefined }))}
        />
        <Input type="number" step="0.0001" value={t.quantity} onChange={(e) => updateTrim(t.key, { quantity: e.target.value })} placeholder="Qty" />
        {unitOptionsInput(t.unit, (v) => updateTrim(t.key, { unit: v }), "Unit")}
        <SegControl options={TRIM_CATEGORIES} value={t.category} onChange={(v) => updateTrim(t.key, { category: v })} />
        <Input type="number" step="0.01" value={t.excess_pct} onChange={(e) => updateTrim(t.key, { excess_pct: e.target.value })} placeholder="Excess %" />
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
            <Field label="Gender (optional)">
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
                placeholder="From, e.g. 75"
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
              For a numeric size run (e.g. kidswear in cm): enter "75" to "100" with step "5" → generates 75, 80, 85, 90, 95, 100. Leave "To" blank to add a single custom size.
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
        <Section n={3} title="Yarn Requirements" subtitle="References the Yarn Master — quantities and consumption for this style">
          <div className="space-y-3">
            {yarns.map((y) => (
              <div key={y.key} className="flex items-start gap-2 p-3 rounded-xl border border-border bg-background">
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
            ))}
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
                  <Input type="number" step="0.01" value={f.excess_pct} onChange={(e) => updateFabric(f.key, { excess_pct: e.target.value })} placeholder="Excess %" />
                  <Input type="number" step="0.01" value={f.gsm} onChange={(e) => updateFabric(f.key, { gsm: e.target.value })} placeholder="GSM" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Input type="number" step="0.01" value={f.dyeing_rate} onChange={(e) => updateFabric(f.key, { dyeing_rate: e.target.value })} placeholder="Dyeing Rate (₹/kg)" />
                  <Input type="number" step="0.01" value={f.printing_rate} onChange={(e) => updateFabric(f.key, { printing_rate: e.target.value })} placeholder="Printing Rate (₹/kg)" />
                </div>
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
                  <Field label="Process (from master)" hint="Optional — select to auto-fill the name and blank fields below from a reusable default; your own entries are never overwritten">
                    <SearchableSelect
                      value={p.process_master_id}
                      onChange={(v) => selectProcessMaster(p.key, v)}
                      placeholder="— Custom / no master —"
                      accent={INDIGO}
                      options={(processMasters.data ?? []).map((m) => ({ value: m.id, label: m.name }))}
                    />
                  </Field>
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
                          <Input value={sp.name} onChange={(e) => updateSubProcess(p.key, sp.key, e.target.value)} placeholder="e.g. Power Table" className="flex-1 !py-1.5" />
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
            <AddRowButton onClick={addProcess} label="Add Process" />
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
        <Section n={fabricSource === "yarn" ? 7 : 6} title="Packing Material Planning" subtitle="Required packing materials, consumption, and the stage at which each is used">
          <div className="space-y-3">
            {packingMaterials.map((p) => (
              <div key={p.key} className="p-3 rounded-xl border border-border bg-background space-y-2">
                <div className="flex items-start gap-2">
                  <Input value={p.material_name} onChange={(e) => updatePacking(p.key, { material_name: e.target.value })} placeholder="e.g. Carton-24x18x14" className="flex-1" />
                  <RemoveRowButton onClick={() => removePacking(p.key)} />
                </div>
                <div className="grid grid-cols-4 gap-2">
                  <Input type="number" step="0.0001" value={p.quantity} onChange={(e) => updatePacking(p.key, { quantity: e.target.value })} placeholder="Qty" />
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
