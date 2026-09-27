"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Pencil, Trash2, X } from "lucide-react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { ModalShell } from "@/components/shared/modal-shell";
import { SearchableSelect } from "@/components/shared/searchable-select";

const INDIGO = "#0049A7";
const inputCls =
  "w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

interface ContactEntry {
  value: string;
  label: string;
}

interface Person {
  id: string;
  name: string;
  job_title: string | null;
  city: string | null;
  organization_id: string | null;
  org_name: string | null;
  emails: ContactEntry[];
  phone_numbers: ContactEntry[];
  whatsapp_number: string | null;
  assigned_to_name: string | null;
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

function ContactRow({
  entry, onChange, onRemove, canRemove, labelOpts, placeholder,
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
        className="flex-1 rounded-xl border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
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

function EditPersonModal({
  person, onClose,
}: {
  person: Person;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    name: person.name,
    job_title: person.job_title ?? "",
    city: person.city ?? "",
    org_id: person.organization_id ?? "",
    whatsapp_number: person.whatsapp_number ?? "",
    emails: person.emails.length ? person.emails : [{ value: "", label: "work" }],
    phone_numbers: person.phone_numbers.length ? person.phone_numbers : [{ value: "", label: "mobile" }],
  });
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: orgsData } = useQuery({
    queryKey: ["crm-orgs-all"],
    queryFn: () => api.get("/crm/organizations?page_size=200").then((r) => r.data),
  });
  const orgs: { id: string; name: string }[] = orgsData?.data ?? [];

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["crm-persons"] });
  }

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.patch(`/crm/persons/${person.id}`, data),
    onSuccess: () => {
      invalidate();
      onClose();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/crm/persons/${person.id}`),
    onSuccess: () => {
      invalidate();
      onClose();
    },
  });

  function set<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function handleSubmit() {
    if (!form.name.trim()) return;
    mutation.mutate({
      name: form.name,
      job_title: form.job_title || null,
      city: form.city || null,
      organization_id: form.org_id || null,
      whatsapp_number: form.whatsapp_number || null,
      emails: form.emails.filter((e) => e.value.trim()),
      contact_numbers: form.phone_numbers.filter((p) => p.value.trim()),
    });
  }

  return (
    <ModalShell maxWidth="max-w-md" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Edit Person</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Full Name <span className="text-destructive">*</span>
          </label>
          <input
            className={inputCls}
            placeholder="e.g. Rajesh Kumar"
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Job Title</label>
            <input
              className={inputCls}
              placeholder="e.g. Buyer, Director…"
              value={form.job_title}
              onChange={(e) => set("job_title", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">City</label>
            <input
              className={inputCls}
              placeholder="e.g. Tiruppur"
              value={form.city}
              onChange={(e) => set("city", e.target.value)}
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Organization</label>
          <SearchableSelect
            options={orgs.map((o) => ({ value: o.id, label: o.name }))}
            value={form.org_id}
            onChange={(v) => set("org_id", v)}
            placeholder="Select organization…"
            accent={INDIGO}
          />
        </div>

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

        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">WhatsApp Number</label>
          <input
            className={inputCls}
            placeholder="+91 98765 43210"
            value={form.whatsapp_number}
            onChange={(e) => set("whatsapp_number", e.target.value)}
          />
        </div>
      </div>
      <div className="flex items-center justify-between gap-3 p-6 border-t">
        <button
          onClick={() => setConfirmDelete(true)}
          className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-xl text-violet-500 hover:bg-violet-50 transition-colors"
        >
          <Trash2 className="h-3.5 w-3.5" /> Delete
        </button>
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!form.name.trim() || mutation.isPending}
            className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
            style={{ background: INDIGO }}
          >
            {mutation.isPending ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </div>

      {confirmDelete && (
        <ModalShell maxWidth="max-w-xs" onClose={() => setConfirmDelete(false)}>
          <div className="p-6">
            <p className="text-sm font-medium mb-1">Delete this person?</p>
            <p className="text-xs text-muted-foreground mb-5">This action cannot be undone.</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDelete(false)}
                className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 text-sm rounded-xl text-white font-semibold bg-violet-500 hover:bg-violet-600 transition-colors disabled:opacity-50"
              >
                {deleteMutation.isPending ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </ModalShell>
      )}
    </ModalShell>
  );
}

export default function PersonsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [editingPerson, setEditingPerson] = useState<Person | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["crm-persons", page, search],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      if (search) params.set("search", search);
      const res = await api.get(`/crm/persons?${params}`);
      return res.data;
    },
  });

  const persons: Person[] = data?.data ?? [];
  const total: number = data?.meta?.total ?? 0;

  const filtered = search.trim()
    ? persons.filter(
        (p) =>
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          (p.job_title ?? "").toLowerCase().includes(search.toLowerCase()) ||
          (p.org_name ?? "").toLowerCase().includes(search.toLowerCase())
      )
    : persons;

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: "name",
      header: "Name",
      sortable: true,
      render: (row) => (
        <button
          onClick={() => router.push(`/crm/persons/${row.id as string}`)}
          className="font-medium hover:underline text-left transition-colors"
          style={{ color: INDIGO }}
        >
          {row.name as string}
        </button>
      ),
    },
    { key: "job_title", header: "Job Title", render: (row) => (row.job_title as string) || "—" },
    { key: "org_name", header: "Organization", render: (row) => (row.org_name as string) || "—" },
    {
      key: "emails",
      header: "Emails",
      render: (row) => {
        const emails = row.emails as ContactEntry[];
        if (!emails || emails.length === 0) return "—";
        return (
          <div className="flex flex-col gap-0.5">
            {emails.slice(0, 2).map((e, i) => (
              <span key={i} className="text-xs">{e.value}</span>
            ))}
          </div>
        );
      },
    },
    {
      key: "phone_numbers",
      header: "Phone",
      render: (row) => {
        const phones = row.phone_numbers as ContactEntry[];
        if (!phones || phones.length === 0) return "—";
        return phones[0].value;
      },
    },
    {
      key: "whatsapp_number",
      header: "WhatsApp",
      render: (row) => (row.whatsapp_number as string) || "—",
    },
    {
      key: "assigned_to_name",
      header: "Assigned To",
      render: (row) => (row.assigned_to_name as string) || "—",
    },
    {
      key: "edit",
      header: "",
      render: (row) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            setEditingPerson(row as unknown as Person);
          }}
          className="p-1 rounded transition-colors hover:bg-muted text-muted-foreground"
          title="Edit person"
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
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            CRM / PERSONS
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Persons</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Individual contacts linked to organizations and leads.
          </p>
        </div>
        <button
          onClick={() => router.push("/crm/persons/new")}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: INDIGO }}
        >
          <Plus className="h-4 w-4" /> New Person
        </button>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            className="rounded-xl border border-input bg-background pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Search persons…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
      </div>

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              ALL PERSONS
            </p>
            <p className="text-sm font-medium mt-0.5">{total} record{total !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <div className="p-6">
          <DataTable
            columns={columns}
            data={filtered as unknown as Record<string, unknown>[]}
            loading={isLoading}
            emptyMessage="No persons found — click New Person to add one"
          />
        </div>
      </div>

      {total > 50 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 rounded border border-input text-sm disabled:opacity-40"
          >
            Prev
          </button>
          <span className="text-sm text-muted-foreground self-center">Page {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={persons.length < 50}
            className="px-3 py-1 rounded border border-input text-sm disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}

      {editingPerson && <EditPersonModal person={editingPerson} onClose={() => setEditingPerson(null)} />}
    </div>
  );
}
