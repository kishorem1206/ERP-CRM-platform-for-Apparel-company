"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, Check, X, Ruler, Boxes, Palette, Scale, Warehouse as WarehouseIcon, Receipt, Cog, Tag, Shirt } from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { Can } from "@/lib/permissions";

const INDIGO = "#0049A7";

type FieldType = "text" | "number" | "color";

interface FieldConfig {
  key: string;
  label: string;
  type: FieldType;
  placeholder?: string;
  options?: { value: string; label: string }[];
  width?: string;
  step?: string;
}

interface EntityConfig {
  key: string;
  endpoint: string;
  title: string;
  description: string;
  addLabel: string;
  fields: FieldConfig[];
  deactivateOnly?: boolean; // warehouses: PATCH is_active instead of hard delete
}

const ENTITIES: (EntityConfig & { icon: typeof Ruler })[] = [
  {
    key: "categories", endpoint: "/master/categories", title: "Categories",
    description: "Top-level product groupings (e.g. Fabric, Trims, Finished Garments).",
    addLabel: "Category", icon: Boxes,
    fields: [{ key: "name", label: "Name", type: "text", placeholder: "e.g. Knitwear" }],
  },
  {
    key: "brands", endpoint: "/master/brands", title: "Brands",
    description: "One brand list reused across products, styles, and material lots.",
    addLabel: "Brand", icon: Tag,
    fields: [{ key: "name", label: "Name", type: "text", placeholder: "e.g. Zenith" }],
  },
  {
    key: "style-parts", endpoint: "/master/style-parts", title: "Style Parts",
    description: "Garment parts (Front, Back, Collar, Sleeves, Waistband, ...) selectable from Style creation.",
    addLabel: "Style Part", icon: Shirt, deactivateOnly: true,
    fields: [{ key: "name", label: "Name", type: "text", placeholder: "e.g. Collar" }],
  },
  {
    key: "sizes", endpoint: "/master/sizes", title: "Sizes",
    description: "Garment sizes used across styles and products.",
    addLabel: "Size", icon: Ruler,
    fields: [
      { key: "name", label: "Name", type: "text", placeholder: "e.g. XL", width: "w-32" },
      { key: "sort_order", label: "Sort Order", type: "number", width: "w-28" },
    ],
  },
  {
    key: "colours", endpoint: "/master/colours", title: "Colours",
    description: "Colour options for styles and product variants.",
    addLabel: "Colour", icon: Palette,
    fields: [
      { key: "name", label: "Name", type: "text", placeholder: "e.g. Navy Blue" },
      { key: "hex_code", label: "Hex Code", type: "color", width: "w-32" },
    ],
  },
  {
    key: "units", endpoint: "/master/units", title: "Units",
    description: "Units of measure used for materials, products, and transactions.",
    addLabel: "Unit", icon: Scale,
    fields: [
      { key: "name", label: "Name", type: "text", placeholder: "e.g. Kilogram" },
      { key: "abbreviation", label: "Abbreviation", type: "text", placeholder: "e.g. kg", width: "w-28" },
      {
        key: "unit_type", label: "Type", type: "text", width: "w-32",
        options: [
          { value: "weight", label: "Weight" },
          { value: "length", label: "Length" },
          { value: "piece", label: "Piece" },
        ],
      },
    ],
  },
  {
    key: "processes", endpoint: "/master/processes", title: "Processes",
    description: "Reusable process definitions (Knitting, Cutting, Making, ...) with default rate/unit/tolerance, selectable from Style Creation.",
    addLabel: "Process", icon: Cog,
    fields: [
      { key: "name", label: "Name", type: "text", placeholder: "e.g. Embroidery" },
      { key: "default_unit", label: "Default Unit", type: "text", placeholder: "e.g. Pieces", width: "w-28" },
      { key: "default_tolerance_pct", label: "Tolerance %", type: "number", width: "w-24", step: "0.01" },
      { key: "default_min_rate", label: "Min Rate", type: "number", width: "w-24", step: "0.01" },
      { key: "default_max_rate", label: "Max Rate", type: "number", width: "w-24", step: "0.01" },
      { key: "default_planned_rate", label: "Planned Rate", type: "number", width: "w-28", step: "0.01" },
      { key: "sort_order", label: "Sort Order", type: "number", width: "w-24" },
    ],
  },
  {
    key: "warehouses", endpoint: "/master/warehouses", title: "Warehouses",
    description: "Storage locations tracked across inventory and production.",
    addLabel: "Warehouse", icon: WarehouseIcon, deactivateOnly: true,
    fields: [
      { key: "name", label: "Name", type: "text", placeholder: "e.g. Yarn Store" },
      { key: "code", label: "Code", type: "text", placeholder: "e.g. WH-YARN", width: "w-32" },
      { key: "address", label: "Address", type: "text", placeholder: "Optional" },
      {
        key: "material_type", label: "Material Type", type: "text", width: "w-36",
        options: [
          { value: "", label: "General (no restriction)" },
          { value: "yarn", label: "Yarn" },
          { value: "fabric", label: "Fabric" },
          { value: "trim", label: "Trim" },
          { value: "packing", label: "Packing" },
          { value: "raw_material", label: "Raw Material" },
          { value: "finished_good", label: "Finished Good" },
        ],
      },
    ],
  },
  {
    key: "hsn", endpoint: "/master/hsn", title: "HSN Codes",
    description: "Tax classification codes and GST rates, shared across all companies.",
    addLabel: "HSN Code", icon: Receipt,
    fields: [
      { key: "hsn", label: "HSN", type: "text", placeholder: "e.g. 6111", width: "w-28" },
      { key: "description", label: "Description", type: "text", placeholder: "Optional" },
      { key: "gst_rate", label: "GST %", type: "number", width: "w-24", step: "0.01" },
      { key: "cess_rate", label: "Cess %", type: "number", width: "w-24", step: "0.01" },
    ],
  },
];

function parseApiError(e: unknown, fallback: string): string {
  const data = (e as { response?: { data?: Record<string, unknown> } })?.response?.data;
  if (!data) return fallback;
  const err = data.error;
  if (typeof err === "string") return err;
  if (err && typeof (err as { message?: string }).message === "string") return (err as { message: string }).message;
  const detail = data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) return (detail as Array<{ msg: string }>)[0]?.msg ?? fallback;
  return fallback;
}

type Row = Record<string, unknown> & { id: string };

function emptyForm(fields: FieldConfig[]): Record<string, string> {
  const f: Record<string, string> = {};
  for (const field of fields) f[field.key] = field.key === "unit_type" ? "piece" : "";
  return f;
}

function FieldInput({ field, value, onChange }: { field: FieldConfig; value: string; onChange: (v: string) => void }) {
  if (field.options) {
    return (
      <div className={field.width ?? "flex-1"}>
        <SearchableSelect
          options={field.options}
          value={value}
          onChange={onChange}
          accent={INDIGO}
        />
      </div>
    );
  }
  if (field.type === "color") {
    return (
      <div className={`flex items-center gap-1.5 ${field.width ?? ""}`}>
        <input
          type="color"
          value={/^#[0-9a-fA-F]{6}$/.test(value) ? value : "#94A3B8"}
          onChange={(e) => onChange(e.target.value)}
          className="w-8 h-8 rounded border border-input cursor-pointer p-0.5 bg-background"
        />
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="#RRGGBB"
          className="w-24 rounded border border-input bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>
    );
  }
  return (
    <input
      type={field.type === "number" ? "number" : "text"}
      step={field.step}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={field.placeholder}
      className={`rounded border border-input bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring ${field.width ?? "flex-1"}`}
    />
  );
}

function MasterEntitySection({ config }: { config: EntityConfig }) {
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [addForm, setAddForm] = useState(() => emptyForm(config.fields));
  const [editId, setEditId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["master-data", config.key],
    queryFn: async () => {
      const params = config.key === "warehouses" ? "?include_inactive=true" : "";
      const res = await api.get(`${config.endpoint}${params}`);
      return (res.data?.data ?? []) as Row[];
    },
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["master-data", config.key] });

  const createMut = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post(config.endpoint, body),
    onSuccess: () => {
      invalidate();
      setAdding(false);
      setAddForm(emptyForm(config.fields));
      setError("");
    },
    onError: (e: unknown) => setError(parseApiError(e, `Failed to create ${config.addLabel.toLowerCase()}`)),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      api.patch(`${config.endpoint}/${id}`, body),
    onSuccess: () => {
      invalidate();
      setEditId(null);
      setError("");
    },
    onError: (e: unknown) => setError(parseApiError(e, `Failed to update ${config.addLabel.toLowerCase()}`)),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`${config.endpoint}/${id}`),
    onSuccess: () => {
      invalidate();
      setConfirmDeleteId(null);
      setError("");
    },
    onError: (e: unknown) => {
      setError(parseApiError(e, `Failed to delete ${config.addLabel.toLowerCase()}`));
      setConfirmDeleteId(null);
    },
  });

  const toggleActiveMut = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.patch(`${config.endpoint}/${id}`, { is_active }),
    onSuccess: () => invalidate(),
    onError: (e: unknown) => setError(parseApiError(e, "Failed to update status")),
  });

  function toBody(form: Record<string, string>): Record<string, unknown> {
    const body: Record<string, unknown> = {};
    for (const field of config.fields) {
      const v = form[field.key];
      body[field.key] = field.type === "number" ? (v === "" ? null : Number(v)) : v;
    }
    return body;
  }

  const rows = data ?? [];

  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div>
          <p className="font-semibold">{config.title}</p>
          <p className="text-sm text-muted-foreground mt-0.5">{config.description}</p>
        </div>
        {!adding && (
          <Can perm="master_data.create"><button
            onClick={() => { setAdding(true); setError(""); }}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-semibold text-white transition-all duration-200 hover:opacity-90 active:scale-95"
            style={{ background: INDIGO }}
          >
            <Plus className="h-4 w-4" /> Add {config.addLabel}
          </button></Can>
        )}
      </div>

      {error && <p className="px-6 pt-3 text-xs text-destructive">{error}</p>}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 border-b border-border">
            <tr>
              {config.fields.map((f) => (
                <th key={f.key} className="text-left px-4 py-2.5 font-medium text-xs text-muted-foreground uppercase tracking-wide">{f.label}</th>
              ))}
              {config.deactivateOnly && <th className="text-left px-4 py-2.5 font-medium text-xs text-muted-foreground uppercase tracking-wide">Status</th>}
              <th className="w-24" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {adding && (
              <tr className="bg-muted/20">
                {config.fields.map((f) => (
                  <td key={f.key} className="px-4 py-2">
                    <FieldInput field={f} value={addForm[f.key] ?? ""} onChange={(v) => setAddForm((s) => ({ ...s, [f.key]: v }))} />
                  </td>
                ))}
                {config.deactivateOnly && <td />}
                <td className="px-4 py-2">
                  <div className="flex items-center gap-1 justify-end">
                    <button
                      onClick={() => createMut.mutate(toBody(addForm))}
                      disabled={createMut.isPending}
                      className="p-1.5 rounded-lg text-white hover:opacity-90 disabled:opacity-50"
                      style={{ background: INDIGO }}
                      title="Save"
                    >
                      <Check className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => { setAdding(false); setAddForm(emptyForm(config.fields)); setError(""); }}
                      className="p-1.5 rounded-lg border border-input hover:bg-muted"
                      title="Cancel"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </td>
              </tr>
            )}

            {isLoading && (
              <tr><td colSpan={config.fields.length + (config.deactivateOnly ? 2 : 1)} className="px-4 py-8 text-center text-muted-foreground">Loading…</td></tr>
            )}
            {!isLoading && rows.length === 0 && !adding && (
              <tr><td colSpan={config.fields.length + (config.deactivateOnly ? 2 : 1)} className="px-4 py-8 text-center text-muted-foreground">No {config.title.toLowerCase()} yet.</td></tr>
            )}

            {rows.map((row) => {
              const isEditing = editId === row.id;
              return (
                <tr key={row.id} className={isEditing ? "bg-muted/20" : "hover:bg-muted/10"}>
                  {config.fields.map((f) => (
                    <td key={f.key} className="px-4 py-2">
                      {isEditing ? (
                        <FieldInput field={f} value={editForm[f.key] ?? ""} onChange={(v) => setEditForm((s) => ({ ...s, [f.key]: v }))} />
                      ) : f.type === "color" && row[f.key] ? (
                        <span className="flex items-center gap-2">
                          <span className="w-3.5 h-3.5 rounded-full border border-border flex-shrink-0" style={{ background: row[f.key] as string }} />
                          <span className="text-muted-foreground">{String(row[f.key])}</span>
                        </span>
                      ) : f.options ? (
                        <span className="text-muted-foreground capitalize">{f.options.find((o) => o.value === row[f.key])?.label ?? String(row[f.key] ?? "—")}</span>
                      ) : (
                        <span className={f.key === "name" || f.key === "hsn" ? "font-medium" : "text-muted-foreground"}>
                          {row[f.key] != null && row[f.key] !== "" ? String(row[f.key]) : "—"}
                        </span>
                      )}
                    </td>
                  ))}
                  {config.deactivateOnly && (
                    <td className="px-4 py-2">
                      <span
                        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold"
                        style={row.is_active
                          ? { background: "#0F78FF18", color: "#0F78FF" }
                          : { background: "#94A3B818", color: "#94A3B8" }}
                      >
                        <span className="w-1.5 h-1.5 rounded-full" style={{ background: row.is_active ? "#0F78FF" : "#94A3B8" }} />
                        {row.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                  )}
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-1 justify-end">
                      {isEditing ? (
                        <>
                          <button
                            onClick={() => updateMut.mutate({ id: row.id, body: toBody(editForm) })}
                            disabled={updateMut.isPending}
                            className="p-1.5 rounded-lg text-white hover:opacity-90 disabled:opacity-50"
                            style={{ background: INDIGO }}
                            title="Save"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={() => setEditId(null)} className="p-1.5 rounded-lg border border-input hover:bg-muted" title="Cancel">
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </>
                      ) : confirmDeleteId === row.id ? (
                        <>
                          <span className="text-xs text-muted-foreground mr-1">Delete?</span>
                          <button
                            onClick={() => deleteMut.mutate(row.id)}
                            disabled={deleteMut.isPending}
                            className="p-1.5 rounded-lg text-white bg-destructive hover:opacity-90 disabled:opacity-50"
                            title="Confirm delete"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={() => setConfirmDeleteId(null)} className="p-1.5 rounded-lg border border-input hover:bg-muted" title="Cancel">
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </>
                      ) : (
                        <>
                          <Can perm="master_data.edit"><button
                            onClick={() => {
                              setError("");
                              setEditId(row.id);
                              const f: Record<string, string> = {};
                              for (const field of config.fields) f[field.key] = row[field.key] != null ? String(row[field.key]) : "";
                              setEditForm(f);
                            }}
                            className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
                            title="Edit"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button></Can>
                          {config.deactivateOnly ? (
                            <Can perm="master_data.edit"><button
                              onClick={() => toggleActiveMut.mutate({ id: row.id, is_active: !row.is_active })}
                              className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
                              title={row.is_active ? "Deactivate" : "Activate"}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button></Can>
                          ) : (
                            <Can perm="master_data.delete"><button
                              onClick={() => setConfirmDeleteId(row.id)}
                              className="p-1.5 rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                              title="Delete"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button></Can>
                          )}
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function MasterDataPage() {
  const [active, setActive] = useState(ENTITIES[0].key);
  const activeConfig = ENTITIES.find((e) => e.key === active)!;

  return (
    <div className="p-8 space-y-6">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">ADMIN / MASTER DATA</p>
        <h1 className="text-2xl font-bold tracking-tight">Master Data</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Base reference data used across Inventory, Production, and Sales — units, categories, colours, sizes, warehouses, and HSN codes.
        </p>
      </div>

      <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit flex-wrap">
        {ENTITIES.map((e) => (
          <button
            key={e.key}
            onClick={() => setActive(e.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold transition-all duration-150 ${
              active === e.key ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <e.icon className="h-3.5 w-3.5" />
            {e.title}
          </button>
        ))}
      </div>

      <MasterEntitySection key={activeConfig.key} config={activeConfig} />
    </div>
  );
}
