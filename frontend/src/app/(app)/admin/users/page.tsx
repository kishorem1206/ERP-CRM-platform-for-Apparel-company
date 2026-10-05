"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { UserPlus, X, Check, Ban, ShieldCheck } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { ModalPortal } from "@/components/shared/modal-portal";
import { Can } from "@/lib/permissions";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

function StatusDot({ active }: { active: boolean }) {
  const color = active ? "#0F78FF" : "#94A3B8";
  const label = active ? "Active" : "Inactive";
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"
      style={{ background: `${color}18`, color }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {label}
    </span>
  );
}

type UserRow = Record<string, unknown> & {
  id: string;
  email: string;
  full_name: string | null;
  phone: string | null;
  is_active: boolean;
  is_owner: boolean;
  last_login_at: string | null;
  roles: string[];
};

type Role = { id: string; name: string };

const columns: Column<UserRow>[] = [
  { key: "full_name", header: "Name", render: (r) => r.full_name || <span className="text-muted-foreground italic">—</span> },
  { key: "email", header: "Email" },
  {
    key: "roles",
    header: "Roles",
    render: (r) =>
      r.roles.length ? (
        <div className="flex flex-wrap gap-1">
          {r.roles.map((role) => (
            <span
              key={role}
              className="px-2 py-0.5 rounded-full text-[11px] font-semibold"
              style={{ background: `${LAVENDER}18`, color: LAVENDER }}
            >
              {role}
            </span>
          ))}
        </div>
      ) : <span className="text-muted-foreground text-xs">No role</span>,
  },
  {
    key: "is_active",
    header: "Status",
    render: (r) => <StatusDot active={r.is_active} />,
  },
  {
    key: "last_login_at",
    header: "Last Login",
    render: (r) => r.last_login_at ? new Date(r.last_login_at).toLocaleDateString("en-IN") : "Never",
  },
];

const INIT = { email: "", full_name: "", phone: "", password: "", role_ids: [] as string[] };

function AssignRolesModal({
  user,
  roles,
  onClose,
}: {
  user: UserRow;
  roles: Role[];
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const { data: allRoles } = useQuery<Role[]>({
    queryKey: ["admin-roles-list"],
    queryFn: async () => {
      const res = await api.get("/admin/roles");
      return res.data.data ?? [];
    },
    initialData: roles,
  });

  const currentRoleNames = new Set(user.roles);
  const initialIds = (allRoles ?? [])
    .filter((r) => currentRoleNames.has(r.name))
    .map((r) => r.id);

  const [selected, setSelected] = useState<string[]>(initialIds);
  const [error, setError] = useState("");

  const mut = useMutation({
    mutationFn: () => api.post(`/admin/users/${user.id}/roles`, { role_ids: selected }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Failed to update roles.");
    },
  });

  return (
    <ModalPortal>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
        <div className="bg-card border border-border rounded-2xl shadow-xl w-full max-w-sm mx-auto">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <div>
              <h2 className="font-semibold text-base">Assign Roles</h2>
              <p className="text-xs text-muted-foreground mt-0.5">{user.email}</p>
            </div>
            <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="p-5 space-y-4">
            {error && <div className="rounded-xl bg-violet-50 border border-violet-200 text-violet-700 px-3 py-2 text-sm">{error}</div>}
            <div className="space-y-1 max-h-60 overflow-y-auto border rounded-xl p-2">
              {(allRoles ?? []).map((r) => (
                <label key={r.id} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-muted px-2 py-1 rounded-lg">
                  <input
                    type="checkbox"
                    checked={selected.includes(r.id)}
                    onChange={(e) =>
                      setSelected((prev) =>
                        e.target.checked ? [...prev, r.id] : prev.filter((x) => x !== r.id)
                      )
                    }
                  />
                  {r.name}
                </label>
              ))}
            </div>
            <div className="flex gap-3">
              <button onClick={onClose} className="flex-1 border rounded-xl py-2 text-sm hover:bg-muted transition-colors">
                Cancel
              </button>
              <button
                onClick={() => mut.mutate()}
                disabled={mut.isPending}
                className="flex-1 rounded-xl py-2 text-sm font-semibold text-white transition-all hover:opacity-90 disabled:opacity-50"
                style={{ background: BLUE }}
              >
                {mut.isPending ? "Saving…" : "Save Roles"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </ModalPortal>
  );
}

export default function UsersPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [assignTarget, setAssignTarget] = useState<UserRow | null>(null);
  const [form, setForm] = useState(INIT);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [toggling, setToggling] = useState<string | null>(null);

  const { data: users, isLoading } = useQuery<UserRow[]>({
    queryKey: ["admin-users"],
    queryFn: async () => {
      const res = await api.get("/admin/users");
      return res.data.data ?? [];
    },
  });

  const { data: roles } = useQuery<Role[]>({
    queryKey: ["admin-roles-list"],
    queryFn: async () => {
      const res = await api.get("/admin/roles");
      return res.data.data ?? [];
    },
  });

  const createMut = useMutation({
    mutationFn: (body: typeof form) => api.post("/admin/users", { ...body, role_ids: body.role_ids }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      setShowCreate(false);
      setForm(INIT);
      setSuccess("User created successfully.");
      setError("");
      setTimeout(() => setSuccess(""), 4000);
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Failed to create user.");
    },
  });

  async function toggleActive(u: UserRow) {
    if (u.is_owner) return;
    setToggling(u.id);
    try {
      await api.patch(`/admin/users/${u.id}`, { is_active: !u.is_active });
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    } finally {
      setToggling(null);
    }
  }

  const colsWithAction: Column<UserRow>[] = [
    ...columns,
    {
      key: "id",
      header: "",
      render: (r) =>
        r.is_owner ? null : (
          <div className="flex items-center gap-1">
            <Can perm="admin.users"><button
              onClick={() => setAssignTarget(r)}
              title="Assign Roles"
              className="p-1.5 rounded-lg hover:bg-purple-50 dark:hover:bg-purple-950/30 transition-colors"
              style={{ color: LAVENDER }}
            >
              <ShieldCheck className="h-4 w-4" />
            </button></Can>
            <Can perm="admin.users"><button
              onClick={() => toggleActive(r)}
              disabled={toggling === r.id}
              title={r.is_active ? "Deactivate" : "Activate"}
              className={`p-1.5 rounded-lg transition-colors ${r.is_active ? "hover:bg-violet-50 dark:hover:bg-violet-950/30 text-violet-500" : "hover:bg-blue-50 dark:hover:bg-blue-950/30 text-blue-600"}`}
            >
              {r.is_active ? <Ban className="h-4 w-4" /> : <Check className="h-4 w-4" />}
            </button></Can>
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
            ADMIN / USERS
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Users</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage team access and role assignments.
          </p>
        </div>
        <Can perm="admin.users"><button
          onClick={() => { setShowCreate(true); setError(""); }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: BLUE }}
        >
          <UserPlus className="h-4 w-4" /> Invite User
        </button></Can>
      </div>

      {success && (
        <div className="rounded-2xl bg-blue-50 dark:bg-blue-950/30 border border-blue-200 text-blue-800 dark:text-blue-400 px-4 py-3 text-sm">
          {success}
        </div>
      )}

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">TEAM MEMBERS</p>
            <p className="text-sm font-medium mt-0.5">
              {users ? `${users.length} user${users.length !== 1 ? "s" : ""}` : "Loading…"}
            </p>
          </div>
        </div>
        <div className="p-0">
          <DataTable columns={colsWithAction} data={users ?? []} loading={isLoading} />
        </div>
      </div>

      {assignTarget && (
        <AssignRolesModal
          user={assignTarget}
          roles={roles ?? []}
          onClose={() => setAssignTarget(null)}
        />
      )}

      {/* Create modal */}
      {showCreate && (
        <ModalPortal>
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
          <div className="bg-card border border-border rounded-2xl shadow-xl w-full max-w-md mx-auto">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <h2 className="font-semibold text-base">Invite User</h2>
              <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              {error && <div className="rounded-xl bg-violet-50 border border-violet-200 text-violet-700 px-3 py-2 text-sm">{error}</div>}

              {[
                { label: "Email *", key: "email", type: "email" },
                { label: "Full Name", key: "full_name", type: "text" },
                { label: "Phone", key: "phone", type: "tel" },
                { label: "Password *", key: "password", type: "password" },
              ].map(({ label, key, type }) => (
                <div key={key}>
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">{label}</label>
                  <input
                    type={type}
                    value={String((form as Record<string, unknown>)[key] ?? "")}
                    onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                    className="w-full border rounded-xl px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                </div>
              ))}

              {roles && roles.length > 0 && (
                <div>
                  <label className="block text-xs font-medium mb-2 text-muted-foreground">Assign Roles</label>
                  <div className="space-y-1 max-h-40 overflow-y-auto border rounded-xl p-2">
                    {roles.map((r) => (
                      <label key={r.id} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-muted px-1 py-0.5 rounded-lg">
                        <input
                          type="checkbox"
                          checked={form.role_ids.includes(r.id)}
                          onChange={(e) => setForm((f) => ({
                            ...f,
                            role_ids: e.target.checked
                              ? [...f.role_ids, r.id]
                              : f.role_ids.filter((x) => x !== r.id),
                          }))}
                        />
                        {r.name}
                      </label>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button onClick={() => setShowCreate(false)}
                  className="flex-1 border rounded-xl py-2 text-sm hover:bg-muted transition-colors">
                  Cancel
                </button>
                <button
                  onClick={() => createMut.mutate(form)}
                  disabled={createMut.isPending || !form.email || !form.password}
                  className="flex-1 rounded-xl py-2 text-sm font-semibold text-white transition-all hover:opacity-90 disabled:opacity-50"
                  style={{ background: BLUE }}
                >
                  {createMut.isPending ? "Creating…" : "Create User"}
                </button>
              </div>
            </div>
          </div>
        </div>
        </ModalPortal>
      )}
    </div>
  );
}
