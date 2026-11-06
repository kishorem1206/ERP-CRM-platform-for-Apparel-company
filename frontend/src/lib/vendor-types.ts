"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { usePermissions } from "@/lib/permissions";

export interface VendorTypeOption { code: string; name: string; builtin: boolean }

/** Built-in vendor types plus the ones this company added. */
export function useVendorTypes() {
  return useQuery({
    queryKey: ["vendor-types"],
    queryFn: async () => (await api.get("/purchase/vendor-types")).data.data as VendorTypeOption[],
    staleTime: 5 * 60_000,
  });
}

/** Turns a type code ("job_worker") into its name ("Job Worker"). */
export function useVendorTypeLabel(): (code: string | null | undefined) => string {
  const { data } = useVendorTypes();
  return (code) => (code ? data?.find((t) => t.code === code)?.name ?? code.replace(/_/g, " ") : "");
}

/** `onCreate` for a vendor-type SearchableSelect: adds the type, resolves to its code. */
export function useCreateVendorType(): ((name: string) => Promise<string>) | undefined {
  const qc = useQueryClient();
  const { can } = usePermissions();
  if (!can("purchase.create")) return undefined;
  return async (name: string) => {
    const res = await api.post("/purchase/vendor-types", { name });
    await qc.invalidateQueries({ queryKey: ["vendor-types"] });
    return res.data.data.code as string;
  };
}
