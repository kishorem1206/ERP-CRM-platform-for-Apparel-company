"use client";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Plus, Pencil } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

const INDIGO = "#0049A7";

type Style = Record<string, unknown> & {
  id: string;
  name: string;
  code: string | null;
  garment_type: string | null;
  gender: string | null;
  season: string | null;
  final_output_unit: string | null;
  version: number;
  is_active: boolean;
};

export default function StylesPage() {
  const router = useRouter();

  const { data, isLoading } = useQuery({
    queryKey: ["styles-list"],
    queryFn: async () => (await api.get("/production/styles")).data.data as Style[],
  });

  const columns: Column<Style>[] = [
    {
      key: "name",
      header: "Style",
      render: (row) => (
        <div>
          <p className="font-medium">{row.name}</p>
          {row.code && row.code !== row.name && (
            <p className="text-xs text-muted-foreground font-mono">{row.code}</p>
          )}
        </div>
      ),
    },
    { key: "garment_type", header: "Garment Type", render: (row) => row.garment_type || "—" },
    { key: "gender", header: "Product Category", render: (row) => row.gender || "—" },
    { key: "season", header: "Season", render: (row) => row.season || "—" },
    { key: "final_output_unit", header: "Final Output", render: (row) => row.final_output_unit || "—" },
    {
      key: "version",
      header: "Version",
      render: (row) => <span className="font-mono text-xs">v{row.version}</span>,
    },
    {
      key: "is_active",
      header: "Status",
      render: (row) => (
        <span
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap"
          style={{
            background: row.is_active ? "#0F78FF18" : "#94A3B818",
            color: row.is_active ? "#0F78FF" : "#94A3B8",
          }}
        >
          <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: row.is_active ? "#0F78FF" : "#94A3B8" }} />
          {row.is_active ? "Active" : "Inactive"}
        </span>
      ),
    },
    {
      key: "edit",
      header: "",
      render: (row) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            router.push(`/production/styles/${row.id}/edit`);
          }}
          className="p-1 rounded transition-colors hover:bg-muted text-muted-foreground"
          title="Edit style"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
      ),
    },
  ];

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">PRODUCTION / STYLES</p>
          <h1 className="text-2xl font-bold tracking-tight">Style Master</h1>
          <p className="text-sm text-muted-foreground mt-1">
            The production blueprint for every garment — variants, materials, workflow, and rates.
          </p>
        </div>
        <button
          onClick={() => router.push("/production/styles/new")}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all duration-200 hover:opacity-90 active:scale-95"
          style={{ background: INDIGO }}
        >
          <Plus className="h-4 w-4" /> New Style
        </button>
      </div>

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">ALL STYLES</p>
            <p className="text-sm font-medium mt-0.5">{(data ?? []).length} record{(data ?? []).length !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <div className="p-6">
          <DataTable
            columns={columns}
            data={data ?? []}
            loading={isLoading}
            emptyMessage="No styles yet — create your first Style Master to begin."
            onRowClick={(row) => router.push(`/production/styles/${row.id}`)}
          />
        </div>
      </div>
    </div>
  );
}
