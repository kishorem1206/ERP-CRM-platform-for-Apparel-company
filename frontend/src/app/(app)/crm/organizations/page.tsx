"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, X } from "lucide-react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { ModalShell } from "@/components/shared/modal-shell";
import { Can } from "@/lib/permissions";

const INDIGO = "#0049A7";
const inputCls =
  "w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

interface Organization {
  id: string;
  name: string;
  website: string | null;
  address: {
    city?: string;
    state?: string;
    country?: string;
  } | null;
  assigned_to_name: string | null;
}

interface OrgEditForm {
  name: string;
  website: string;
  city: string;
  state: string;
  country: string;
}

function EditOrgModal({
  org, onClose,
}: {
  org: Organization;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<OrgEditForm>({
    name: org.name,
    website: org.website ?? "",
    city: org.address?.city ?? "",
    state: org.address?.state ?? "",
    country: org.address?.country ?? "",
  });
  const [confirmDelete, setConfirmDelete] = useState(false);

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["crm-organizations"] });
    queryClient.invalidateQueries({ queryKey: ["crm-orgs-all"] });
  }

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.patch(`/crm/organizations/${org.id}`, data),
    onSuccess: () => {
      invalidate();
      onClose();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/crm/organizations/${org.id}`),
    onSuccess: () => {
      invalidate();
      onClose();
    },
  });

  function set<K extends keyof OrgEditForm>(k: K, v: OrgEditForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function handleSubmit() {
    if (!form.name.trim()) return;
    mutation.mutate({
      name: form.name,
      website: form.website || null,
      address: (form.city || form.state || form.country)
        ? { city: form.city || undefined, state: form.state || undefined, country: form.country || undefined }
        : null,
    });
  }

  return (
    <ModalShell maxWidth="max-w-md" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Edit Organization</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Organization Name <span className="text-destructive">*</span>
          </label>
          <input
            className={inputCls}
            placeholder="Company Pvt Ltd"
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Website</label>
          <input
            className={inputCls}
            placeholder="https://example.com"
            value={form.website}
            onChange={(e) => set("website", e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">City</label>
            <input
              className={inputCls}
              placeholder="e.g. Tiruppur"
              value={form.city}
              onChange={(e) => set("city", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">State / Province</label>
            <input
              className={inputCls}
              placeholder="e.g. Tamil Nadu"
              value={form.state}
              onChange={(e) => set("state", e.target.value)}
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Country</label>
          <input
            className={inputCls}
            placeholder="India"
            value={form.country}
            onChange={(e) => set("country", e.target.value)}
          />
        </div>
      </div>
      <div className="flex items-center justify-between gap-3 p-6 border-t">
        <Can perm="crm.delete"><button
          onClick={() => setConfirmDelete(true)}
          className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-xl text-violet-500 hover:bg-violet-50 transition-colors"
        >
          <Trash2 className="h-3.5 w-3.5" /> Delete
        </button></Can>
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
            <p className="text-sm font-medium mb-1">Delete this organization?</p>
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

export default function OrganizationsPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [editingOrg, setEditingOrg] = useState<Organization | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["crm-organizations", page],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      const res = await api.get(`/crm/organizations?${params}`);
      return res.data;
    },
  });

  const organizations: Organization[] = data?.data ?? [];
  const total: number = data?.meta?.total ?? 0;

  const columns: Column<Record<string, unknown>>[] = [
    { key: "name", header: "Name", sortable: true },
    {
      key: "website",
      header: "Website",
      render: (row) =>
        row.website ? (
          <a
            href={row.website as string}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-xs underline underline-offset-2 hover:opacity-80 transition-opacity"
            style={{ color: INDIGO }}
          >
            {(row.website as string).replace(/^https?:\/\//, "")}
          </a>
        ) : (
          "—"
        ),
    },
    {
      key: "address",
      header: "City",
      render: (row) => {
        const addr = row.address as Organization["address"];
        return addr?.city ?? "—";
      },
    },
    {
      key: "address_country",
      header: "Country",
      render: (row) => {
        const addr = row.address as Organization["address"];
        return addr?.country ?? "—";
      },
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
            setEditingOrg(row as unknown as Organization);
          }}
          className="p-1 rounded transition-colors hover:bg-muted text-muted-foreground"
          title="Edit organization"
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
            CRM / ORGANIZATIONS
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Organizations</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Company accounts, websites, and address details.
          </p>
        </div>
        <Can perm="crm.create"><button
          onClick={() => router.push("/crm/organizations/new")}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: INDIGO }}
        >
          <Plus className="h-4 w-4" /> New Organization
        </button></Can>
      </div>

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              ALL ORGANIZATIONS
            </p>
            <p className="text-sm font-medium mt-0.5">{total} record{total !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <div className="p-6">
          <DataTable
            columns={columns}
            data={organizations as unknown as Record<string, unknown>[]}
            loading={isLoading}
            emptyMessage="No organizations found — click New Organization to add one"
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
            disabled={organizations.length < 50}
            className="px-3 py-1 rounded border border-input text-sm disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}

      {editingOrg && <EditOrgModal org={editingOrg} onClose={() => setEditingOrg(null)} />}
    </div>
  );
}
