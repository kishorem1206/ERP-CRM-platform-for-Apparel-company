"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard, Users, ShoppingCart, Package, Factory,
  BarChart3, Settings, Bot, Wallet, ShoppingBag, Scissors, Shield, LogOut, Plus,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import { CreateMenu } from "@/components/create/CreateMenu";

const nav = [
  { label: "Dashboard",    href: "/dashboard",        icon: LayoutDashboard },
  { label: "CRM",          href: "/crm",              icon: Users },
  { label: "Sales",        href: "/sales",            icon: ShoppingCart },
  { label: "Purchasing",   href: "/purchase",         icon: ShoppingBag },
  { label: "Inventory",    href: "/inventory",        icon: Package },
  { label: "Production",   href: "/production",       icon: Scissors },
  { label: "Finance",      href: "/finance",          icon: Wallet },
  { label: "Reports",      href: "/reports",          icon: BarChart3 },
  { label: "AI Assistant", href: "/ai-assistant",     icon: Bot },
  { label: "Security",     href: "/settings/security",icon: Shield },
  { label: "Admin",        href: "/admin",            icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [createOpen, setCreateOpen] = useState(false);

  async function handleLogout() {
    try { await api.post("/auth/logout"); } catch { /* ignore */ }
    localStorage.removeItem("access_token");
    router.push("/login");
  }

  return (
    <>
      <aside className="w-60 border-r bg-card flex flex-col shrink-0">
        {/* Logo */}
        <div className="h-14 flex items-center px-4 border-b">
          <span className="font-semibold text-base tracking-tight">Apparel ERP</span>
        </div>

        {/* Create button */}
        <div className="px-3 pt-3 pb-1">
          <button
            onClick={() => setCreateOpen(true)}
            className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-2 overflow-y-auto">
          {nav.map(({ label, href, icon: Icon }) => {
            const active = pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 mx-2 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                  active
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* User info + logout */}
        <div className="p-3 border-t">
          <div className="flex items-center justify-between gap-2">
            <div className="text-xs text-muted-foreground min-w-0">
              <p className="truncate">admin@company.com</p>
              <p className="mt-0.5 text-[10px] opacity-60">Administrator</p>
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="shrink-0 p-1.5 rounded-md text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </aside>

      <CreateMenu open={createOpen} onClose={() => setCreateOpen(false)} />
    </>
  );
}
