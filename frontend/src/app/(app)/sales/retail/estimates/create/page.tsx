"use client";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { BillEditor } from "@/components/retail/bill-editor";
import { Can } from "@/lib/permissions";
import type { RetailEstimate } from "@/lib/retail";

function EstimateForm() {
  const from = useSearchParams()?.get("from");
  const existing = useQuery({
    queryKey: ["retail-estimate", from],
    queryFn: async () => (await api.get(`/retail/estimates/${from}`)).data.data as RetailEstimate,
    enabled: !!from,
  });
  if (from && !existing.data) return <p className="text-sm text-muted-foreground">Loading…</p>;
  return <BillEditor mode="estimate" estimate={existing.data ?? null} />;
}

export default function RetailEstimateCreatePage() {
  return (
    <div className="p-6 lg:p-8 space-y-5">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / RETAIL / ESTIMATES</p>
        <h1 className="text-2xl font-bold tracking-tight">Retail Estimate</h1>
        <p className="text-sm text-muted-foreground mt-1">MRP prices include GST. No stock is taken until it&apos;s billed.</p>
      </div>
      <Can perm="retail.create">
        <Suspense fallback={null}><EstimateForm /></Suspense>
      </Can>
    </div>
  );
}
