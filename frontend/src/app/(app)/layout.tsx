"use client";
import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { Topbar } from "@/components/layout/topbar";
import { findActiveModule, requiredPathPermission } from "@/components/layout/module-nav-config";
import { usePermissions } from "@/lib/permissions";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname() ?? "";
  const { ready, can } = usePermissions();
  const activeModule = findActiveModule(pathname);
  const blocked = ready && (!can(activeModule.permission) || !can(requiredPathPermission(pathname)));

  // A module the user cannot use is not shown: send them to the dashboard.
  useEffect(() => {
    if (blocked) router.replace("/dashboard");
  }, [blocked, router]);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div className="flex h-screen bg-background">
      <AppSidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto">
          {ready && !blocked ? children : null}
        </main>
      </div>
    </div>
  );
}
