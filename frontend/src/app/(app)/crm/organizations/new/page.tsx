"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ChevronRight } from "lucide-react";
import api from "@/lib/api";

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

interface OrgForm {
  name: string;
  website: string;
  city: string;
  state: string;
  country: string;
}

export default function NewOrganizationPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<OrgForm>({ name: "", website: "", city: "", state: "", country: "India" });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post("/crm/organizations", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-organizations"] });
      queryClient.invalidateQueries({ queryKey: ["crm-orgs-all"] });
      router.push("/crm/organizations");
    },
    onError: () => setError("Failed to create organization. Please try again."),
  });

  function set<K extends keyof OrgForm>(k: K, v: OrgForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function handleSubmit() {
    if (!form.name.trim()) { setError("Name is required."); return; }
    setError("");
    mutation.mutate({
      name: form.name,
      website: form.website || undefined,
      address: (form.city || form.state || form.country)
        ? { city: form.city || undefined, state: form.state || undefined, country: form.country || undefined }
        : undefined,
    });
  }

  return (
    <div>
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.push("/crm/organizations")}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground leading-none">
              CRM / ORGANIZATIONS
            </p>
            <h1 className="text-base font-semibold leading-tight mt-0.5">New Organization</h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {error && <p className="text-xs text-destructive max-w-xs text-right">{error}</p>}
          <button
            type="button"
            onClick={() => router.push("/crm/organizations")}
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
            {mutation.isPending ? "Saving…" : <><ChevronRight className="h-4 w-4" /> Save Organization</>}
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="p-6">
        <div className="max-w-2xl space-y-4">
          <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
            <SectionLabel label="IDENTITY" />

            <Field label="Organization Name" required>
              <input
                className={inputCls}
                placeholder="Company Pvt Ltd"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                autoFocus
              />
            </Field>

            <Field label="Website">
              <input
                className={inputCls}
                placeholder="https://example.com"
                value={form.website}
                onChange={(e) => set("website", e.target.value)}
              />
            </Field>
          </div>

          <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
            <SectionLabel label="ADDRESS" />

            <div className="grid grid-cols-2 gap-4">
              <Field label="City">
                <input
                  className={inputCls}
                  placeholder="e.g. Tiruppur"
                  value={form.city}
                  onChange={(e) => set("city", e.target.value)}
                />
              </Field>
              <Field label="State / Province">
                <input
                  className={inputCls}
                  placeholder="e.g. Tamil Nadu"
                  value={form.state}
                  onChange={(e) => set("state", e.target.value)}
                />
              </Field>
            </div>

            <Field label="Country">
              <input
                className={inputCls}
                placeholder="India"
                value={form.country}
                onChange={(e) => set("country", e.target.value)}
              />
            </Field>
          </div>
        </div>
      </div>
    </div>
  );
}
