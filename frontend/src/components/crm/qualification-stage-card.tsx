"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";

const INDIGO = "#0049A7";

interface PipelineStage {
  id: string;
  name: string;
}

interface Pipeline {
  id: string;
  name: string;
  qualified_stage_id: string | null;
  stages: PipelineStage[];
}

export function QualificationStageCard() {
  const queryClient = useQueryClient();
  const { data: pipelinesData, isLoading } = useQuery({
    queryKey: ["qual-pipelines"],
    queryFn: async () => (await api.get("/crm/pipelines")).data.data as Pipeline[],
  });

  const mutation = useMutation({
    mutationFn: ({ pipelineId, stageId }: { pipelineId: string; stageId: string | null }) =>
      api.put(`/crm/pipelines/${pipelineId}/qualification-stage`, { stage_id: stageId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["qual-pipelines"] });
      queryClient.invalidateQueries({ queryKey: ["crm-pipelines"] });
      queryClient.invalidateQueries({ queryKey: ["crm-sales-kpis"] });
    },
  });

  const pipelines = pipelinesData ?? [];

  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      <p className="font-semibold">Qualification Stage</p>
      <p className="text-xs text-muted-foreground mt-1 mb-4">
        A lead counts as qualified once it reaches this stage, or any later stage, at any point. This sets the
        Lead → Qualified KPI on the CRM dashboard. Leads in a pipeline with no stage chosen are not counted as qualified.
      </p>
      {isLoading && <p className="text-xs text-muted-foreground">Loading pipelines…</p>}
      {!isLoading && pipelines.length === 0 && (
        <p className="text-xs text-muted-foreground">No pipelines yet.</p>
      )}
      <div className="space-y-3">
        {pipelines.map((p) => (
          <div key={p.id} className="grid grid-cols-1 md:grid-cols-[1fr_1fr] gap-2 md:items-center">
            <p className="text-sm font-medium">{p.name}</p>
            <SearchableSelect
              options={[
                { value: "", label: "Not set" },
                ...p.stages.map((s) => ({ value: s.id, label: s.name })),
              ]}
              value={p.qualified_stage_id ?? ""}
              onChange={(v) => mutation.mutate({ pipelineId: p.id, stageId: v || null })}
              placeholder="Not set"
              accent={INDIGO}
              disabled={mutation.isPending}
            />
          </div>
        ))}
      </div>
      {mutation.isError && (
        <p className="text-xs text-red-600 mt-3">Could not save the qualification stage. Try again.</p>
      )}
    </div>
  );
}
