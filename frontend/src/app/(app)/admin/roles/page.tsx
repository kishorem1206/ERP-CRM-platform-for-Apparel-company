"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, ChevronRight, Trash2, X } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { ModalPortal } from "@/components/shared/modal-portal";
import { Can } from "@/lib/permissions";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

type RoleRow = Record<string, unknown> & {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permission_count: number;
};

export default function RolesPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [error, setError] = useState("");

  const { data: roles, isLoading } = useQuery<RoleRow[]>({
    queryKey: ["admin-roles"],
    queryFn: async () => {
      const res = await api.get("/admin/roles");
      return res.data.data ?? [];
    },
  });

  const createMut = useMutation({
    mutationFn: () => api.post("/admin/roles", { name, description: desc || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-roles"] });
      qc.invalidateQueries({ queryKey: ["admin-roles-list"] });
      setShowCreate(false);
      setName(""); setDesc(""); setError("");
    },
    onError: (e: unknown) => {
      const data = (e as { response?: { data?: Record<string, unknown> } })?.response?.data;
      const msg = data?.error instanceof Object
        ? (data.error as { message?: string }).message
        : (data?.error as string) ?? (data?.detail as string) ?? "Failed to create role.";
      setError(String(msg ?? "Failed to create role."));
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/admin/roles/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-roles"] });
      qc.invalidateQueries({ queryKey: ["admin-roles-list"] });
    },
  });

  const columns: Column<RoleRow>[] = [
    { key: "name", header: "Role Name" },
    {
      key: "description",
      header: "Description",
      render: (r) => r.description || <span className="text-muted-foreground italic text-xs">—</span>,
    },
    {
      key: "is_system",
      header: "Type",
      render: (r) => {
        const color = r.is_system ? BLUE : "#94A3B8";
        return (
          <span
            className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"
            style={{ background: `${color}18`, color }}
          >
            {r.is_system ? "System" : "Custom"}
          </span>
        );
      },
    },
    { key: "permission_count", header: "Permissions" },
    {
      key: "id",
      header: "",
      render: (r) => (
        <div className="flex items-center gap-2">
          <Link
            href={`/admin/roles/${r.id}`}
            className="flex items-center gap-1 text-xs font-medium hover:underline"
            style={{ color: LAVENDER }}
          >
            Edit permissions <ChevronRight className="h-3 w-3" />
          </Link>
          {!r.is_system && (
            <Can perm="admin.roles"><button
              onClick={() => deleteMut.mutate(r.id)}
              className="p-1 rounded-lg hover:bg-violet-50 dark:hover:bg-violet-950/30 text-violet-500 transition-colors"
              title="Delete"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button></Can>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            ADMIN / ROLES
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Roles & Permissions</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Define what each role can access.
          </p>
        </div>
        <Can perm="admin.roles"><button
          onClick={() => { setShowCreate(true); setError(""); }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: LAVENDER }}
        >
          <Plus className="h-4 w-4" /> New Role
        </button></Can>
      </div>

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">ROLES</p>
            <p className="text-sm font-medium mt-0.5">
              {roles ? `${roles.length} role${roles.length !== 1 ? "s" : ""}` : "Loading…"}
            </p>
          </div>
        </div>
        <div className="p-0">
          <DataTable columns={columns} data={roles ?? []} loading={isLoading} />
        </div>
      </div>

      {showCreate && (
        <ModalPortal>
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
          <div className="bg-card border border-border rounded-2xl shadow-xl w-full max-w-sm mx-auto p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-lg">New Role</h2>
              <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground">
                <X className="h-5 w-5" />
              </button>
            </div>
            {error && <div className="rounded-xl bg-violet-50 border border-violet-200 text-violet-700 px-3 py-2 text-sm">{error}</div>}
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Role Name *</label>
              <input value={name} onChange={(e) => setName(e.target.value)}
                className="w-full border rounded-xl px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                placeholder="e.g. Warehouse Manager" />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">Description</label>
              <input value={desc} onChange={(e) => setDesc(e.target.value)}
                className="w-full border rounded-xl px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                placeholder="Optional description" />
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => setShowCreate(false)}
                className="flex-1 border rounded-xl py-2 text-sm hover:bg-muted transition-colors">Cancel</button>
              <button
                onClick={() => createMut.mutate()}
                disabled={createMut.isPending || !name.trim()}
                className="flex-1 rounded-xl py-2 text-sm font-semibold text-white transition-all hover:opacity-90 disabled:opacity-50"
                style={{ background: LAVENDER }}
              >
                {createMut.isPending ? "Creating…" : "Create"}
              </button>
            </div>
          </div>
        </div>
        </ModalPortal>
      )}
    </div>
  );
}
