"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ChevronRight, Phone, Users, StickyNote, CheckSquare, Mail, Clock } from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";

const INDIGO = "#0049A7";
const inputCls =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

type ActivityType = string;

const ACTIVITY_META: Record<string, { icon: React.ElementType; color: string }> = {
  call:    { icon: Phone,       color: "#0F78FF" },
  meeting: { icon: Users,       color: "#8174F5" },
  task:    { icon: CheckSquare, color: "#A096F7" },
  email:   { icon: Mail,        color: "#0049A7" },
  note:    { icon: StickyNote,  color: "#6B7280" },
  "Phone Call": { icon: Phone, color: "#0F78FF" },
  Meeting:      { icon: Users, color: "#8174F5" },
  Task:         { icon: CheckSquare, color: "#A096F7" },
  Email:        { icon: Mail, color: "#0049A7" },
  Note:         { icon: StickyNote, color: "#6B7280" },
};
const DEFAULT_ACTIVITY_META = { icon: Clock, color: INDIGO };

interface ActivityForm {
  type: ActivityType;
  title: string;
  comment: string;
  lead_id: string;
  schedule_from: string;
  schedule_to: string;
}

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

export default function NewActivityPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ActivityForm>({
    type: "",
    title: "",
    comment: "",
    lead_id: "",
    schedule_from: "",
    schedule_to: "",
  });
  const [error, setError] = useState("");

  const { data: leadsData } = useQuery({
    queryKey: ["crm-leads-all"],
    queryFn: () => api.get("/crm/leads?page_size=200").then((r) => r.data),
  });
  const leads: { id: string; title: string }[] = leadsData?.data ?? [];

  const { data: followUpTypesData } = useQuery({
    queryKey: ["crm-follow-up-types"],
    queryFn: () => api.get("/crm/follow-up-types").then((r) => r.data),
  });
  const followUpTypes: { id: string; name: string }[] = followUpTypesData?.data ?? [];

  useEffect(() => {
    if (!form.type && followUpTypes.length > 0) {
      setForm((f) => ({ ...f, type: followUpTypes[0].name }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [followUpTypes]);

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post("/crm/activities", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-activities"] });
      router.push("/crm/activities");
    },
    onError: () => setError("Failed to create activity. Please try again."),
  });

  function set<K extends keyof ActivityForm>(k: K, v: ActivityForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function handleSubmit() {
    if (!form.title.trim()) { setError("Title is required."); return; }
    setError("");
    mutation.mutate({
      type: form.type,
      title: form.title,
      comment: form.comment || undefined,
      lead_id: form.lead_id || undefined,
      schedule_from: form.schedule_from || undefined,
      schedule_to: form.schedule_to || undefined,
    });
  }

  return (
    <div>
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.push("/crm/activities")}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground leading-none">
              CRM / ACTIVITIES
            </p>
            <h1 className="text-base font-semibold leading-tight mt-0.5">Log Activity</h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {error && <p className="text-xs text-destructive max-w-xs text-right">{error}</p>}
          <button
            type="button"
            onClick={() => router.push("/crm/activities")}
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
            {mutation.isPending ? "Saving…" : <><ChevronRight className="h-4 w-4" /> Log Activity</>}
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="p-6">
        <div className="max-w-2xl space-y-4">
          <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
            <SectionLabel label="ACTIVITY DETAILS" />

            <Field label="Type">
              <div className="flex flex-wrap gap-2 mt-1">
                {followUpTypes.map((ft) => {
                  const { icon: Icon, color } = ACTIVITY_META[ft.name] ?? DEFAULT_ACTIVITY_META;
                  const active = form.type === ft.name;
                  return (
                    <button
                      key={ft.id}
                      type="button"
                      onClick={() => set("type", ft.name)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all"
                      style={{
                        borderColor: active ? color : "hsl(var(--border))",
                        background: active ? `${color}18` : "transparent",
                        color: active ? color : "hsl(var(--muted-foreground))",
                      }}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      {ft.name}
                    </button>
                  );
                })}
              </div>
            </Field>

            <Field label="Title" required>
              <input
                className={inputCls}
                placeholder="e.g. Introductory call with Rajesh"
                value={form.title}
                onChange={(e) => set("title", e.target.value)}
                autoFocus
              />
            </Field>

            <Field label="Notes / Comment">
              <textarea
                className={`${inputCls} resize-none`}
                rows={3}
                placeholder="Add details or outcome…"
                value={form.comment}
                onChange={(e) => set("comment", e.target.value)}
              />
            </Field>
          </div>

          <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
            <SectionLabel label="LINK & SCHEDULE" />

            <Field label="Linked Lead">
              <SearchableSelect
                options={leads.map((l) => ({ value: l.id, label: l.title }))}
                value={form.lead_id}
                onChange={(v) => set("lead_id", v)}
                placeholder="Link to a lead…"
                accent={INDIGO}
              />
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Schedule From">
                <input
                  className={inputCls}
                  type="datetime-local"
                  value={form.schedule_from}
                  onChange={(e) => set("schedule_from", e.target.value)}
                />
              </Field>
              <Field label="Schedule To">
                <input
                  className={inputCls}
                  type="datetime-local"
                  value={form.schedule_to}
                  onChange={(e) => set("schedule_to", e.target.value)}
                />
              </Field>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
