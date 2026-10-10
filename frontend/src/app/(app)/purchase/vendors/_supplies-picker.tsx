"use client";

export const SUPPLY_TYPES: { value: string; label: string }[] = [
  { value: "yarn", label: "Yarn" },
  { value: "fabric", label: "Fabric" },
  { value: "trim", label: "Trim" },
  { value: "packing", label: "Packing" },
  { value: "raw_material", label: "Raw Material" },
  { value: "finished_good", label: "Finished Good" },
];

export function SuppliesPicker({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div>
      <label className="text-xs font-medium text-muted-foreground">Supplies (optional)</label>
      <p className="text-[11px] text-muted-foreground mt-0.5 mb-1.5">
        Restricts the product dropdown to these types wherever this vendor is picked. Leave empty to allow any product.
      </p>
      <div className="flex gap-1 flex-wrap">
        {SUPPLY_TYPES.map((t) => (
          <button
            key={t.value}
            type="button"
            onClick={() => onChange(value.includes(t.value) ? value.filter((v) => v !== t.value) : [...value, t.value])}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
              value.includes(t.value)
                ? "bg-primary/10 text-primary border-primary/40"
                : "bg-background border-border text-muted-foreground hover:border-foreground/30"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
    </div>
  );
}
