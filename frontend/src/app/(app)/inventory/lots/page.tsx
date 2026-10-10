"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

// ── Palette ───────────────────────────────────────────────────────────────────
const BLUE     = "#0049A7";
const LAVENDER = "#0F78FF";

// ── Type badge using StatusDot pattern ───────────────────────────────────────
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
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap capitalize"
      style={{ background: `${color}18`, color }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {label}
    </span>
  );
}

// ── Types ─────────────────────────────────────────────────────────────────────
interface Lot {
  id: string;
  lot_number: string;
  material_type: string;
  product_id: string | null;
  product_name: string | null;
  blend_composition: string | null;
  fibre_type: string | null;
  yarn_count: string | null;
  construction: string | null;
  trim_type: string | null;
  trim_unit: string | null;
  colour: string | null;
  gsm: number | null;
  bags: number | null;
  kg_per_bag: number | null;
  unit_cost: number | null;
  invoice_number: string | null;
  invoice_date: string | null;
  supplier_id: string | null;
  stock_qty: number | null;
}

const TYPE_FILTERS = [
  { label: "All", value: "" },
  { label: "Yarn", value: "yarn" },
  { label: "Fabric", value: "fabric" },
  { label: "Trims", value: "trim" },
];

function lotSummary(lot: Lot): string {
  if (lot.material_type === "yarn") {
    const parts = [lot.yarn_count, lot.blend_composition || lot.fibre_type].filter(Boolean);
    return parts.join(" · ") || "—";
  }
  if (lot.material_type === "fabric") {
    const parts = [lot.construction, lot.gsm ? `${lot.gsm} GSM` : null, lot.blend_composition || lot.fibre_type].filter(Boolean);
    return parts.join(" · ") || "—";
  }
  if (lot.material_type === "trim") {
    return [lot.trim_type, lot.colour].filter(Boolean).join(" · ") || "—";
  }
  return "—";
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function LotsPage() {
  const router = useRouter();
  const [typeFilter, setTypeFilter] = useState("");
  const [trimType, setTrimType] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["material-lots", typeFilter, typeFilter === "trim" ? trimType : "", page],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      if (typeFilter) params.set("material_type", typeFilter);
      if (typeFilter === "trim" && trimType) params.set("trim_type", trimType);
      const r = await api.get(`/materials/lots?${params}`);
      return r.data;
    },
  });

  const { data: trimTypeCounts } = useQuery({
    queryKey: ["material-lots-trim-types"],
    queryFn: async () => (await api.get("/materials/lots/trim-types")).data.data as { trim_type: string; count: number }[],
    enabled: typeFilter === "trim",
  });

  const lots: Lot[] = data?.data ?? [];
  const total: number = data?.meta?.total ?? 0;
  const trimTotalCount = (trimTypeCounts ?? []).reduce((sum, t) => sum + t.count, 0);

  function selectTypeFilter(value: string) {
    setTypeFilter(value);
    setTrimType("");
    setPage(1);
  }

  const filtered = search
    ? lots.filter((l) =>
        l.lot_number.toLowerCase().includes(search.toLowerCase()) ||
        (l.blend_composition ?? "").toLowerCase().includes(search.toLowerCase()) ||
        (l.fibre_type ?? "").toLowerCase().includes(search.toLowerCase()) ||
        (l.yarn_count ?? "").toLowerCase().includes(search.toLowerCase()) ||
        (l.construction ?? "").toLowerCase().includes(search.toLowerCase()) ||
        (l.trim_type ?? "").toLowerCase().includes(search.toLowerCase())
      )
    : lots;

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: "lot_number",
      header: "Lot #",
      sortable: true,
      render: (row) => (
        <span className="font-mono text-xs font-medium">{row.lot_number as string}</span>
      ),
    },
    {
      key: "material_type",
      header: "Type",
      render: (row) => <TypeDot type={row.material_type as string} />,
    },
    {
      key: "summary",
      header: "Specification",
      render: (row) => (
        <span className="text-sm text-muted-foreground">{lotSummary(row as unknown as Lot)}</span>
      ),
    },
    {
      key: "product_name",
      header: "Product",
      render: (row) =>
        row.product_name ? (
          <span className="text-sm">{row.product_name as string}</span>
        ) : (
          <span className="text-xs text-muted-foreground italic">Not linked</span>
        ),
    },
    {
      key: "colour",
      header: "Colour",
      render: (row) => (row.colour as string) || "—",
    },
    {
      key: "quantity",
      header: "Qty",
      render: (row) => {
        const lot = row as unknown as Lot;
        if (lot.material_type === "yarn" && lot.bags && lot.kg_per_bag) {
          return `${(Number(lot.bags) * Number(lot.kg_per_bag)).toFixed(1)} kg`;
        }
        if (lot.stock_qty != null && lot.stock_qty !== 0) {
          const unit = lot.trim_unit || (lot.material_type === "fabric" ? "kg" : "");
          return `${Number(lot.stock_qty).toLocaleString("en-IN")}${unit ? " " + unit : ""}`;
        }
        return "—";
      },
    },
    {
      key: "unit_cost",
      header: "Rate",
      render: (row) => row.unit_cost ? `₹${Number(row.unit_cost).toFixed(2)}` : "—",
    },
    {
      key: "invoice_number",
      header: "Invoice",
      render: (row) => (row.invoice_number as string) || "—",
    },
  ];

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">INVENTORY / MATERIALS</p>
          <h1 className="text-2xl font-bold tracking-tight">Material Lots</h1>
          <p className="text-sm text-muted-foreground mt-1">Yarn, fabric, and trim stock — every inbound lot.</p>
        </div>
      </div>

      {/* Search + filter strip */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            className="rounded-xl border border-input bg-background pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Search lots…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit flex-wrap">
          {TYPE_FILTERS.map((t) => (
            <button
              key={t.value}
              onClick={() => selectTypeFilter(t.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                typeFilter === t.value
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Trim-type sub-filter — only shown on the Trims tab */}
      {typeFilter === "trim" && (
        <div className="flex flex-wrap gap-1.5 -mt-4">
          <button
            onClick={() => { setTrimType(""); setPage(1); }}
            className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
              trimType === ""
                ? "bg-primary/10 text-primary border-primary/40"
                : "bg-background border-border text-muted-foreground hover:border-foreground/30"
            }`}
          >
            All Types{trimTotalCount ? ` (${trimTotalCount})` : ""}
          </button>
          {(trimTypeCounts ?? []).map(({ trim_type: tt, count }) => (
            <button
              key={tt}
              onClick={() => { setTrimType(tt); setPage(1); }}
              className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                trimType === tt
                  ? "bg-primary/10 text-primary border-primary/40"
                  : "bg-background border-border text-muted-foreground hover:border-foreground/30"
              }`}
            >
              {tt} ({count})
            </button>
          ))}
        </div>
      )}

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">ALL LOTS</p>
            <p className="text-sm font-medium mt-0.5">{total} record{total !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <div className="p-6">
          <DataTable
            columns={columns}
            data={filtered as unknown as Record<string, unknown>[]}
            loading={isLoading}
            emptyMessage="No material lots found — add yarn, fabric, or trims to begin"
            onRowClick={(row) => router.push(`/inventory/lots/${row.id as string}`)}
          />
        </div>
      </div>

      {total > 50 && (
        <div className="flex justify-center gap-2">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
            className="px-3 py-1 rounded border border-input text-sm disabled:opacity-40">Prev</button>
          <span className="text-sm text-muted-foreground self-center">Page {page}</span>
          <button onClick={() => setPage((p) => p + 1)} disabled={lots.length < 50}
            className="px-3 py-1 rounded border border-input text-sm disabled:opacity-40">Next</button>
        </div>
      )}
    </div>
  );
}
