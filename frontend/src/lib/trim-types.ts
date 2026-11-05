/** Garment trim types, as used across style trims, lot trims and trim stock. */
export const TRIM_TYPES = [
  "Elastic", "Thread / Cone", "Button", "Zipper", "Label", "Tag", "Tape", "Drawcord",
  "Lace", "Interlining", "Velcro", "Snap / Rivet / Eyelet", "Patch / Badge", "Piping", "Other",
] as const;

const KEYWORDS: [RegExp, string][] = [
  [/elastic/i, "Elastic"],
  [/thread|cone/i, "Thread / Cone"],
  [/zip/i, "Zipper"],
  [/button/i, "Button"],
  [/label/i, "Label"],
  [/\btag/i, "Tag"],
  [/tape/i, "Tape"],
  [/lace/i, "Lace"],
  [/draw ?cord|string/i, "Drawcord"],
  [/interlin|fusing/i, "Interlining"],
  [/velcro|hook.?(and|&).?loop/i, "Velcro"],
  [/rivet|snap|eyelet/i, "Snap / Rivet / Eyelet"],
  [/patch|badge/i, "Patch / Badge"],
  [/piping/i, "Piping"],
];

/** Best guess of a trim's type from its name, or "" when nothing fits. */
export function guessTrimType(name: string): string {
  return KEYWORDS.find(([re]) => re.test(name))?.[1] ?? "";
}
