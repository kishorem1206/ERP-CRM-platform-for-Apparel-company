"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ChevronRight, Flame, Thermometer, Snowflake } from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { DatePicker } from "@/components/shared/date-picker";

const INDIGO = "#0049A7";
const inputCls =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-muted-foreground mb-1">
        {label}{required && <span className="text-destructive ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

function SectionLabel({ label }: { label: string }) {
  return (
    <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground border-b pb-2 mb-4">
      {label}
    </p>
  );
}

const TEMPS = [
  { value: "hot",  label: "Hot",  Icon: Flame,       color: "#1D0DB0" },
  { value: "warm", label: "Warm", Icon: Thermometer,  color: "#A096F7" },
  { value: "cold", label: "Cold", Icon: Snowflake,    color: "#8FC0FF" },
] as const;

interface LeadForm {
  title: string;
  pipeline_id: string;
  stage_id: string;
  lead_value: string;
  temperature: "hot" | "warm" | "cold";
  person_id: string;
  org_id: string;
  source_id: string;
  type_id: string;
  expected_close_date: string;
  notes: string;
}

export default function NewLeadPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<LeadForm>({
    title: "", pipeline_id: "", stage_id: "", lead_value: "",
    temperature: "cold", person_id: "", org_id: "", source_id: "",
    type_id: "", expected_close_date: "", notes: "",
  });
  const [error, setError] = useState("");

  const { data: pipelinesData } = useQuery({
    queryKey: ["crm-pipelines"],
    queryFn: () => api.get("/crm/pipelines?page_size=200").then((r) => r.data),
  });
  const { data: personsData } = useQuery({
    queryKey: ["crm-persons-all"],
    queryFn: () => api.get("/crm/persons?page_size=200").then((r) => r.data),
  });
  const { data: orgsData } = useQuery({
    queryKey: ["crm-orgs-all"],
    queryFn: () => api.get("/crm/organizations?page_size=200").then((r) => r.data),
  });
  const { data: sourcesData } = useQuery({
    queryKey: ["crm-lead-sources"],
    queryFn: () => api.get("/crm/lead-sources?page_size=200").then((r) => r.data),
  });
  const { data: typesData } = useQuery({
    queryKey: ["crm-lead-types"],
    queryFn: () => api.get("/crm/lead-types?page_size=200").then((r) => r.data),
  });

  const pipelines: { id: string; name: string; stages: { id: string; name: string }[] }[] = pipelinesData?.data ?? [];
  const persons: { id: string; name: string; organization_id: string | null }[] = personsData?.data ?? [];
  const orgs: { id: string; name: string }[] = orgsData?.data ?? [];
  const sources: { id: string; name: string }[] = sourcesData?.data ?? [];
  const types: { id: string; name: string }[] = typesData?.data ?? [];

  const selectedPipeline = pipelines.find((p) => p.id === form.pipeline_id);
  const stageOptions = selectedPipeline?.stages?.map((s) => ({ value: s.id, label: s.name })) ?? [];

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post("/crm/leads", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-leads"] });
      queryClient.invalidateQueries({ queryKey: ["crm-leads-kanban"] });
      router.push("/crm/leads");
    },
    onError: () => setError("Failed to create lead. Please try again."),
  });

  function set<K extends keyof LeadForm>(k: K, v: LeadForm[K]) {
    if (k === "pipeline_id") {
      setForm((f) => ({ ...f, pipeline_id: v as string, stage_id: "" }));
    } else {
      setForm((f) => ({ ...f, [k]: v }));
    }
  }

  function handleSubmit() {
    if (!form.title.trim()) { setError("Title is required."); return; }
    setError("");
    mutation.mutate({
      title: form.title,
      pipeline_id: form.pipeline_id || undefined,
      stage_id: form.stage_id || undefined,
      lead_value: form.lead_value ? parseFloat(form.lead_value) : undefined,
      temperature: form.temperature,
      person_id: form.person_id || undefined,
      org_id: form.org_id || undefined,
      source_id: form.source_id || undefined,
      type_id: form.type_id || undefined,
      expected_close_date: form.expected_close_date || undefined,
      notes: form.notes || undefined,
    });
  }

  return (
    <div>
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.push("/crm/leads")}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground leading-none">
              CRM / LEADS
            </p>
            <h1 className="text-base font-semibold leading-tight mt-0.5">New Lead</h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {error && <p className="text-xs text-destructive max-w-xs text-right">{error}</p>}
          <button
            type="button"
            onClick={() => router.push("/crm/leads")}
            className="px-4 py-1.5 rounded-md border border-input text-sm hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={mutation.isPending}
            className="px-4 py-1.5 rounded-xl text-sm font-semibold text-white disabled:opacity-60 flex items-center gap-1.5 transition-all hover:opacity-90 active:scale-95"
            style={{ background: INDIGO }}
          >
            {mutation.isPending ? "Saving…" : <><ChevronRight className="h-4 w-4" /> Save Lead</>}
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="p-6">
        <div className="max-w-2xl space-y-4">
          {/* Basic info */}
          <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
            <SectionLabel label="BASIC INFO" />

            <Field label="Lead Title" required>
              <input
                className={inputCls}
                placeholder="e.g. Summer 2026 T-shirt Bulk Order"
                value={form.title}
                onChange={(e) => set("title", e.target.value)}
                autoFocus
              />
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Pipeline">
                <SearchableSelect
                  options={pipelines.map((p) => ({ value: p.id, label: p.name }))}
                  value={form.pipeline_id}
                  onChange={(v) => setForm((f) => ({ ...f, pipeline_id: v, stage_id: "" }))}
                  placeholder="Select pipeline…"
                  accent={INDIGO}
                />
              </Field>
              <Field label="Stage">
                <SearchableSelect
                  options={stageOptions}
                  value={form.stage_id}
                  onChange={(v) => set("stage_id", v)}
                  placeholder="Select stage…"
                  accent={INDIGO}
                  disabled={!form.pipeline_id}
                />
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Lead Value (₹)">
                <input
                  className={inputCls}
                  type="number"
                  min="0"
                  placeholder="0"
                  value={form.lead_value}
                  onChange={(e) => set("lead_value", e.target.value)}
                />
              </Field>
              <Field label="Expected Close Date">
                <DatePicker value={form.expected_close_date} onChange={(v) => set("expected_close_date", v)} />
              </Field>
            </div>

            <Field label="Temperature">
              <div className="flex gap-2 mt-1">
                {TEMPS.map(({ value, label, Icon, color }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => set("temperature", value)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all"
                    style={{
                      borderColor: form.temperature === value ? color : "hsl(var(--border))",
                      background: form.temperature === value ? `${color}18` : "transparent",
                      color: form.temperature === value ? color : "hsl(var(--muted-foreground))",
                    }}
                  >
                    <Icon className="h-3.5 w-3.5" /> {label}
                  </button>
                ))}
              </div>
            </Field>
          </div>

          {/* Contacts & Source */}
          <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
            <SectionLabel label="CONTACTS & SOURCE" />

            <Field label="Person">
              <SearchableSelect
                options={persons.map((p) => ({ value: p.id, label: p.name }))}
                value={form.person_id}
                onChange={(v) => {
                  const person = persons.find((p) => p.id === v);
                  setForm((f) => ({ ...f, person_id: v, org_id: person?.organization_id ?? "" }));
                }}
                placeholder="Select person…"
                accent={INDIGO}
              />
            </Field>

            <Field label="Organization">
              <SearchableSelect
                options={orgs.map((o) => ({ value: o.id, label: o.name }))}
                value={form.org_id}
                onChange={(v) => set("org_id", v)}
                placeholder="Select organization…"
                accent={INDIGO}
              />
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Source">
                <SearchableSelect
                  options={sources.map((s) => ({ value: s.id, label: s.name }))}
                  value={form.source_id}
                  onChange={(v) => set("source_id", v)}
                  placeholder="Select source…"
                  accent={INDIGO}
                />
              </Field>
              <Field label="Type">
                <SearchableSelect
                  options={types.map((t) => ({ value: t.id, label: t.name }))}
                  value={form.type_id}
                  onChange={(v) => set("type_id", v)}
                  placeholder="Select type…"
                  accent={INDIGO}
                />
              </Field>
            </div>
          </div>

          {/* Notes */}
          <div className="bg-card border border-border rounded-2xl p-5">
            <SectionLabel label="NOTES" />
            <textarea
              className={`${inputCls} resize-none`}
              rows={4}
              placeholder="Add any notes about this lead…"
              value={form.notes}
              onChange={(e) => set("notes", e.target.value)}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
