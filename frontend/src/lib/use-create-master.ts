"use client";
import { useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { usePermissions } from "@/lib/permissions";

// Master lists a SearchableSelect can add to in place. Each entry is the
// endpoint that creates a record from just a name, the cached list(s) to
// refresh afterwards, and the permission the endpoint checks.
const MASTERS = {
  colour: { endpoint: "/master/colours", queryKeys: [["master-colours"]], perm: "master_data.create" },
  stylePart: { endpoint: "/master/style-parts", queryKeys: [["master-style-parts"]], perm: "master_data.create" },
  brand: { endpoint: "/master/brands", queryKeys: [["master-brands"]], perm: "master_data.create" },
  category: { endpoint: "/master/categories", queryKeys: [["master-categories"]], perm: "master_data.create" },
  worker: { endpoint: "/production/workers", queryKeys: [["production-workers"]], perm: "production.create" },
} as const;

export type MasterKind = keyof typeof MASTERS;

/**
 * Returns an `onCreate` for SearchableSelect that saves a new master record
 * and resolves to its id, or undefined when the user may not create one (so
 * the "+ Add" row is hidden instead of failing on save).
 */
export function useCreateMaster(kind: MasterKind): ((name: string) => Promise<string>) | undefined {
  const qc = useQueryClient();
  const { can } = usePermissions();
  const master = MASTERS[kind];
  if (!can(master.perm)) return undefined;
  return async (name: string) => {
    const res = await api.post(master.endpoint, { name });
    await Promise.all(master.queryKeys.map((queryKey) => qc.invalidateQueries({ queryKey })));
    return res.data.data.id as string;
  };
}
