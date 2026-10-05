"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ChevronDown, LogOut, Plus, Scissors } from "lucide-react";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { AUTH_ME_QUERY_KEY, usePermissions } from "@/lib/permissions";
import { CreateMenu, QUICK_CREATE_PERMISSIONS } from "@/components/create/CreateMenu";
import { MODULE_NAV, findActiveModule, SavedFilterIcon } from "./module-nav-config";

const SIDEBAR_BLUE = "#0049A7";
const ICON_ACCENT = "#8174F5";

export function AppSidebar() {
  const pathname = usePathname() ?? "";
  const router = useRouter();
  const [createOpen, setCreateOpen] = useState(false);
  const activeModule = findActiveModule(pathname);
  const queryClient = useQueryClient();
  const { ready, can } = usePermissions();
  // Modules the user cannot access are not shown at all.
  const visibleModules = ready ? MODULE_NAV.filter((m) => can(m.permission)) : [];
  const canQuickCreate = ready && can(QUICK_CREATE_PERMISSIONS);

  // Which module's sub-nav is expanded. Follows the active module as you
  // navigate, but the chevron can toggle it independently of navigation.
  const [expandedKey, setExpandedKey] = useState(activeModule.key);
  useEffect(() => setExpandedKey(activeModule.key), [activeModule.key]);

  async function handleLogout() {
    try { await api.post("/auth/logout"); } catch { /* ignore */ }
    localStorage.removeItem("access_token");
    queryClient.removeQueries({ queryKey: AUTH_ME_QUERY_KEY });
    router.push("/login");
  }

  // Group a module's items in declaration order, preserving each item's
  // `group` label (falls back to a single ungrouped list).
  function groupItems(items: typeof activeModule.items) {
    const groups: { label: string | null; items: typeof items }[] = [];
    for (const item of items) {
      const label = item.group ?? null;
      const last = groups[groups.length - 1];
      if (last && last.label === label) last.items.push(item);
      else groups.push({ label, items: [item] });
    }
    return groups;
  }

  return (
    <>
      <aside
        className="w-[268px] flex flex-col shrink-0 h-full text-white"
        style={{ background: SIDEBAR_BLUE }}
      >
        {/* Logo */}
        <div className="h-14 flex items-center gap-2.5 px-4 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-white/15 flex items-center justify-center shrink-0">
            <Scissors className="h-4 w-4 text-white" />
          </div>
          <span className="font-semibold text-[15px] tracking-tight truncate">Apparel ERP</span>
        </div>

        {/* Create button */}
        {canQuickCreate && (
          <div className="px-4 pb-3 shrink-0">
            <button
              onClick={() => setCreateOpen(true)}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-white/15 hover:bg-white/25 px-3 py-2 text-sm font-semibold transition-colors"
            >
              <Plus className="h-4 w-4" />
              Create
            </button>
          </div>
        )}

        <div className="mx-4 h-px bg-white/12 shrink-0" />

        {/* Modules — collapsed rows, active module expands with its own sub-nav */}
        <nav className="flex-1 overflow-y-auto py-2">
          {visibleModules.map((mod) => {
            const isActive = mod.key === activeModule.key;
            const isExpanded = mod.key === expandedKey && mod.items.length > 1;
            return (
              <div key={mod.key} className={isActive ? "mb-1" : ""}>
                <div
                  className="flex items-center mx-2.5 rounded-lg transition-colors"
                  style={{ background: isActive ? "rgba(255,255,255,0.10)" : "transparent" }}
                >
                  <Link
                    href={mod.href}
                    className="flex-1 flex items-center gap-3 px-3 py-2 text-[13px] font-medium min-w-0"
                    style={{ color: "#FFFFFF" }}
                  >
                    <span
                      className="w-6 h-6 rounded-md flex items-center justify-center shrink-0"
                      style={isActive ? { background: ICON_ACCENT } : undefined}
                    >
                      <mod.icon className="h-4 w-4" />
                    </span>
                    <span className="flex-1 truncate">{mod.label}</span>
                  </Link>
                  {mod.items.length > 1 && (
                    <button
                      type="button"
                      onClick={() => setExpandedKey((prev) => (prev === mod.key ? "" : mod.key))}
                      title={isExpanded ? "Collapse" : "Expand"}
                      className="shrink-0 p-2 mr-1 rounded-md hover:bg-white/10 transition-colors"
                    >
                      <ChevronDown
                        className="h-3.5 w-3.5 transition-transform"
                        style={{ transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)", opacity: 0.6 }}
                      />
                    </button>
                  )}
                </div>

                {/* Expanded sub-navigation */}
                {isExpanded && (
                  <div className="mt-0.5 mb-1">
                    {groupItems(mod.items).map((g, gi) => (
                      <div key={gi} className={gi > 0 ? "mt-2.5" : "mt-0.5"}>
                        {g.label && (
                          <p className="px-6 mb-1 text-[10px] font-semibold uppercase tracking-widest text-white/45">
                            {g.label}
                          </p>
                        )}
                        {g.items.map((item) => {
                          const itemActive = pathname === item.href || pathname.startsWith(item.href + "/");
                          return (
                            <Link
                              key={item.href}
                              href={item.href}
                              className="flex items-center gap-3 mx-2.5 ml-6 px-3 py-1.5 rounded-lg text-[13px] font-medium transition-colors"
                              style={{
                                background: itemActive ? "rgba(0,0,0,0.18)" : "transparent",
                                color: itemActive ? "#FFFFFF" : "rgba(255,255,255,0.72)",
                              }}
                            >
                              <item.icon className="h-3.5 w-3.5 shrink-0" />
                              <span className="truncate">{item.label}</span>
                            </Link>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* Saved filters — scoped to the active module */}
        <div className="mx-4 h-px bg-white/12 shrink-0" />
        <div className="px-4 py-3 shrink-0">
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-white/45">
            Saved Filters
          </p>
          <p className="flex items-center gap-2 text-[12px] text-white/45">
            <SavedFilterIcon className="h-3.5 w-3.5" />
            No saved filters yet
          </p>
        </div>

        {/* Avatar + logout */}
        <div className="flex items-center justify-between gap-2 px-4 py-3 border-t border-white/12 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-full bg-white/15 flex items-center justify-center text-xs font-semibold shrink-0">
              A
            </div>
            <div className="text-xs min-w-0">
              <p className="truncate">admin@company.com</p>
              <p className="text-[10px] text-white/55">Administrator</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            title="Sign out"
            className="shrink-0 p-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors"
          >
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      </aside>

      <CreateMenu open={createOpen} onClose={() => setCreateOpen(false)} />
    </>
  );
}
