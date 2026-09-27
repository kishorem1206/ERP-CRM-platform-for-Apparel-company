"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ChevronRight, Plus, Trash2 } from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";

const INDIGO = "#0049A7";
const inputCls =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

interface ContactEntry { value: string; label: string }

interface PersonForm {
  name: string;
  job_title: string;
  city: string;
  org_id: string;
  whatsapp_number: string;
  emails: ContactEntry[];
  phone_numbers: ContactEntry[];
}

const EMAIL_LABELS = [
  { value: "work", label: "Work" },
  { value: "personal", label: "Personal" },
  { value: "other", label: "Other" },
];
const PHONE_LABELS = [
  { value: "mobile", label: "Mobile" },
  { value: "office", label: "Office" },
  { value: "home", label: "Home" },
  { value: "other", label: "Other" },
];

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

function ContactRow({
  entry,
  onChange,
  onRemove,
  canRemove,
  labelOpts,
  placeholder,
}: {
  entry: ContactEntry;
  onChange: (e: ContactEntry) => void;
  onRemove: () => void;
  canRemove: boolean;
  labelOpts: { value: string; label: string }[];
  placeholder: string;
}) {
  return (
    <div className="flex gap-2 items-center">
      <input
        className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        placeholder={placeholder}
        value={entry.value}
        onChange={(e) => onChange({ ...entry, value: e.target.value })}
      />
      <div className="w-28 flex-shrink-0">
        <SearchableSelect
          options={labelOpts}
          value={entry.label}
          onChange={(v) => onChange({ ...entry, label: v })}
          placeholder="Label"
          accent={INDIGO}
        />
      </div>
      {canRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

export default function NewPersonPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<PersonForm>({
    name: "", job_title: "", city: "", org_id: "", whatsapp_number: "",
    emails: [{ value: "", label: "work" }],
    phone_numbers: [{ value: "", label: "mobile" }],
  });
  const [error, setError] = useState("");

  const { data: orgsData } = useQuery({
    queryKey: ["crm-orgs-all"],
    queryFn: () => api.get("/crm/organizations?page_size=200").then((r) => r.data),
  });
  const orgs: { id: string; name: string }[] = orgsData?.data ?? [];

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post("/crm/persons", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-persons"] });
      router.push("/crm/persons");
    },
    onError: () => setError("Failed to create person. Please try again."),
  });

  function set<K extends keyof PersonForm>(k: K, v: PersonForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function handleSubmit() {
    if (!form.name.trim()) { setError("Name is required."); return; }
    setError("");
    mutation.mutate({
      name: form.name,
      job_title: form.job_title || undefined,
      city: form.city || undefined,
      organization_id: form.org_id || undefined,
      whatsapp_number: form.whatsapp_number || undefined,
      emails: form.emails.filter((e) => e.value.trim()),
      contact_numbers: form.phone_numbers.filter((p) => p.value.trim()),
    });
  }

  return (
    <div>
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.push("/crm/persons")}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground leading-none">
              CRM / PERSONS
            </p>
            <h1 className="text-base font-semibold leading-tight mt-0.5">New Person</h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {error && <p className="text-xs text-destructive max-w-xs text-right">{error}</p>}
          <button
            type="button"
            onClick={() => router.push("/crm/persons")}
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
            {mutation.isPending ? "Saving…" : <><ChevronRight className="h-4 w-4" /> Save Person</>}
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="p-6">
        <div className="max-w-2xl space-y-4">
          {/* Identity */}
          <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
            <SectionLabel label="IDENTITY" />

            <Field label="Full Name" required>
              <input
                className={inputCls}
                placeholder="e.g. Rajesh Kumar"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                autoFocus
              />
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Job Title">
                <input
                  className={inputCls}
                  placeholder="e.g. Buyer, Director…"
                  value={form.job_title}
                  onChange={(e) => set("job_title", e.target.value)}
                />
              </Field>
              <Field label="City">
                <input
                  className={inputCls}
                  placeholder="e.g. Tiruppur"
                  value={form.city}
                  onChange={(e) => set("city", e.target.value)}
                />
              </Field>
            </div>

            <Field label="Organization">
              <SearchableSelect
                options={orgs.map((o) => ({ value: o.id, label: o.name }))}
                value={form.org_id}
                onChange={(v) => set("org_id", v)}
                placeholder="Select organization…"
                accent={INDIGO}
              />
            </Field>
          </div>

          {/* Contact */}
          <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
            <SectionLabel label="CONTACT" />

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-medium text-muted-foreground">Emails</label>
                <button
                  type="button"
                  onClick={() => set("emails", [...form.emails, { value: "", label: "work" }])}
                  className="flex items-center gap-1 text-[11px] font-semibold hover:opacity-80 transition-opacity"
                  style={{ color: INDIGO }}
                >
                  <Plus className="h-3 w-3" /> Add
                </button>
              </div>
              <div className="space-y-2">
                {form.emails.map((entry, i) => (
                  <ContactRow
                    key={i}
                    entry={entry}
                    onChange={(e) => {
                      const emails = [...form.emails];
                      emails[i] = e;
                      set("emails", emails);
                    }}
                    onRemove={() => set("emails", form.emails.filter((_, idx) => idx !== i))}
                    canRemove={form.emails.length > 1}
                    labelOpts={EMAIL_LABELS}
                    placeholder="email@example.com"
                  />
                ))}
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-medium text-muted-foreground">Phone Numbers</label>
                <button
                  type="button"
                  onClick={() => set("phone_numbers", [...form.phone_numbers, { value: "", label: "mobile" }])}
                  className="flex items-center gap-1 text-[11px] font-semibold hover:opacity-80 transition-opacity"
                  style={{ color: INDIGO }}
                >
                  <Plus className="h-3 w-3" /> Add
                </button>
              </div>
              <div className="space-y-2">
                {form.phone_numbers.map((entry, i) => (
                  <ContactRow
                    key={i}
                    entry={entry}
                    onChange={(e) => {
                      const phone_numbers = [...form.phone_numbers];
                      phone_numbers[i] = e;
                      set("phone_numbers", phone_numbers);
                    }}
                    onRemove={() => set("phone_numbers", form.phone_numbers.filter((_, idx) => idx !== i))}
                    canRemove={form.phone_numbers.length > 1}
                    labelOpts={PHONE_LABELS}
                    placeholder="+91 98765 43210"
                  />
                ))}
              </div>
            </div>

            <Field label="WhatsApp Number">
              <input
                className={inputCls}
                placeholder="+91 98765 43210"
                value={form.whatsapp_number}
                onChange={(e) => set("whatsapp_number", e.target.value)}
              />
            </Field>
          </div>
        </div>
      </div>
    </div>
  );
}
