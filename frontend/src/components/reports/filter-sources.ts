"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { SelectOption } from "@/components/shared/searchable-select";

function useOptions(
  key: string,
  url: string,
  mapFn: (row: Record<string, unknown>) => SelectOption,
  params?: Record<string, unknown>,
): SelectOption[] {
  const { data } = useQuery({
    queryKey: [key],
    queryFn: async () => {
      const res = await api.get(url, { params: { page_size: 500, ...params } });
      return (res.data.data ?? []) as Record<string, unknown>[];
    },
    staleTime: 5 * 60 * 1000,
  });
  return (data ?? []).map(mapFn);
}

export const useCustomerOptions = () =>
  useOptions("filter-customers", "/sales/customers", (c) => ({ value: String(c.id), label: String(c.legal_name) }), { active_only: false });

export const useVendorOptions = () =>
  useOptions("filter-vendors", "/purchase/vendors", (v) => ({ value: String(v.id), label: String(v.name) }), { active_only: false });

export const useProductOptions = () =>
  useOptions("filter-products", "/products", (p) => ({ value: String(p.id), label: String(p.name) }));

export const useWarehouseOptions = () =>
  useOptions("filter-warehouses", "/master/warehouses", (w) => ({ value: String(w.id), label: String(w.name) }));

export const useUnitOptions = () =>
  useOptions("filter-units", "/master/units", (u) => ({
    value: String(u.id),
    label: `${String(u.name)} (${String(u.abbreviation ?? u.symbol ?? "")})`,
  }));

export const useCategoryOptions = () =>
  useOptions("filter-categories", "/master/categories", (c) => ({ value: String(c.id), label: String(c.name) }));

export const useStyleOptions = () =>
  useOptions("filter-styles", "/production/styles", (s) => ({ value: String(s.id), label: String(s.name) }));

export const useWorkerOptions = () =>
  useOptions("filter-workers", "/production/workers", (w) => ({ value: String(w.id), label: String(w.name) }));

export const usePipelineOptions = () =>
  useOptions("filter-pipelines", "/crm/pipelines", (p) => ({ value: String(p.id), label: String(p.name) }));

export const useLeadSourceOptions = () =>
  useOptions("filter-lead-sources", "/crm/lead-sources", (s) => ({ value: String(s.id), label: String(s.name) }));

export const useEmployeeOptions = () =>
  useOptions("filter-employees", "/crm/assignable-users", (u) => ({ value: String(u.id), label: String(u.name) }));
