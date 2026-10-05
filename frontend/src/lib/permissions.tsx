"use client";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

/** A permission code, or a list where any one of them grants access. */
export type RequiredPermission = string | string[];

export const AUTH_ME_QUERY_KEY = ["auth-me"] as const;

/**
 * The signed-in user's permissions, from /auth/me. Matches the backend's exact
 * permission check, so a module hidden here is also blocked by the API.
 */
export function usePermissions() {
  const { data, isSuccess } = useQuery({
    queryKey: AUTH_ME_QUERY_KEY,
    queryFn: async () => {
      const res = await api.get("/auth/me");
      return res.data.data as { permissions: string[] };
    },
    staleTime: 5 * 60_000,
  });

  const granted = new Set<string>(data?.permissions ?? []);

  return {
    /** False until the permissions have loaded; avoids flashing items the user cannot use. */
    ready: isSuccess,
    can: (required?: RequiredPermission) => {
      if (!required) return true;
      return Array.isArray(required)
        ? required.some((p) => granted.has(p))
        : granted.has(required);
    },
  };
}

/**
 * Renders its children only when the user holds the permission. Nothing is
 * rendered otherwise, so the action is not shown at all (no disabled state).
 */
export function Can({ perm, children }: { perm: RequiredPermission; children: ReactNode }) {
  const { ready, can } = usePermissions();
  return ready && can(perm) ? <>{children}</> : null;
}
