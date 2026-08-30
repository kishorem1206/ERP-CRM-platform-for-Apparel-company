"use client";
import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Save } from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";

const INDIGO   = "#5347CE";
const LAVENDER = "#887CFD";
const BLUE     = "#4896FE";
const TEAL     = "#16C8C7";

type Permission = { id: string; code: string; description: string | null };

function groupPermissions(perms: Permission[]): Record<string, Permission[]> {
  return perms.reduce<Record<string, Permission[]>>((acc, p) => {
    const module = p.code.split(".")[0];
    (acc[module] ??= []).push(p);
    return acc;
  }, {});
}

export default function RoleDetailPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const qc = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [success, setSuccess] = useState("");

  const { data: allPerms } = useQuery<Permission[]>({
    queryKey: ["admin-permissions"],
    queryFn: async () => {
      const res = await api.get("/admin/permissions");
      return res.data.data ?? [];
    },
  });

  const { data: rolePerms } = useQuery<Permission[]>({
    queryKey: ["admin-role-perms", id],
    queryFn: async () => {
      const res = await api.get(`/admin/roles/${id}/permissions`);
      return res.data.data ?? [];
    },
  });

  const { data: roles } = useQuery({
    queryKey: ["admin-roles"],
    queryFn: async () => {
      const res = await api.get("/admin/roles");
      return res.data.data ?? [];
    },
  });

  useEffect(() => {
    if (rolePerms) {
      setSelected(new Set(rolePerms.map((p) => p.id)));
    }
  }, [rolePerms]);

  const saveMut = useMutation({
    mutationFn: () =>
      api.put(`/admin/roles/${id}/permissions`, {
        permission_ids: Array.from(selected),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-roles"] });
      qc.invalidateQueries({ queryKey: ["admin-role-perms", id] });
      setSuccess("Permissions saved.");
      setTimeout(() => setSuccess(""), 3000);
    },
  });

  const role = (roles as { id: string; name: string; is_system: boolean }[] | undefined)?.find(
    (r) => r.id === id
  );
  const grouped = allPerms ? groupPermissions(allPerms) : {};

  function toggleModule(module: string, perms: Permission[], checked: boolean) {
    setSelected((prev) => {
      const next = new Set(prev);
      perms.forEach((p) => (checked ? next.add(p.id) : next.delete(p.id)));
      return next;
    });
  }

  return (
    <div className="p-8 space-y-8 max-w-3xl">
      {/* Page header */}
      <div className="flex items-start gap-3">
        <Link href="/admin/roles" className="p-1.5 rounded-xl hover:bg-muted transition-colors mt-0.5">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            ADMIN / ROLES
          </p>
          <h1 className="text-2xl font-bold tracking-tight">{role?.name ?? "Role"}</h1>
          {role?.is_system && (
            <p className="text-xs font-medium mt-0.5" style={{ color: "#F59E0B" }}>
              System role — permissions locked
            </p>
          )}
        </div>
      </div>

      {success && (
        <div className="rounded-2xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 text-emerald-800 dark:text-emerald-400 px-4 py-3 text-sm">
          {success}
        </div>
      )}

      {/* Permission group cards */}
      <div className="space-y-4">
        {Object.entries(grouped).sort().map(([module, perms]) => {
          const moduleSelected = perms.every((p) => selected.has(p.id));
          const modulePartial = !moduleSelected && perms.some((p) => selected.has(p.id));
          return (
            <div key={module} className="bg-card border border-border rounded-2xl overflow-hidden">
              <div className="flex items-center gap-3 bg-muted/40 px-6 py-3 border-b border-border">
                <input
                  type="checkbox"
                  checked={moduleSelected}
                  ref={(el) => { if (el) el.indeterminate = modulePartial; }}
                  disabled={role?.is_system}
                  onChange={(e) => toggleModule(module, perms, e.target.checked)}
                  className="h-4 w-4 rounded"
                />
                <span className="font-semibold text-sm capitalize">{module.replace(/_/g, " ")}</span>
                <span className="text-xs text-muted-foreground ml-auto">
                  {perms.filter((p) => selected.has(p.id)).length} / {perms.length}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-0 divide-y divide-border">
                {perms.map((p) => (
                  <label
                    key={p.id}
                    className="flex items-start gap-3 px-6 py-3 hover:bg-muted/20 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(p.id)}
                      disabled={role?.is_system}
                      onChange={(e) =>
                        setSelected((prev) => {
                          const next = new Set(prev);
                          e.target.checked ? next.add(p.id) : next.delete(p.id);
                          return next;
                        })
                      }
                      className="h-4 w-4 rounded mt-0.5 shrink-0"
                    />
                    <div>
                      <p className="text-xs font-mono text-foreground">{p.code}</p>
                      {p.description && (
                        <p className="text-xs text-muted-foreground">{p.description}</p>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {!role?.is_system && (
        <div className="flex justify-end pt-2">
          <button
            onClick={() => saveMut.mutate()}
            disabled={saveMut.isPending}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
            style={{ background: LAVENDER }}
          >
            <Save className="h-4 w-4" />
            {saveMut.isPending ? "Saving…" : "Save Permissions"}
          </button>
        </div>
      )}
    </div>
  );
}
