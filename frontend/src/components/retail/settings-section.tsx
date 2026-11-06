"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { RETAIL_ACCENT } from "@/lib/retail";

/** Save part of the retail settings, with a status line. */
export function useSaveRetailSettings() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const save = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.patch("/retail/settings", body),
    onSuccess: () => {
      setError(""); setMsg("Saved.");
      qc.invalidateQueries({ queryKey: ["retail-settings"] });
      qc.invalidateQueries({ queryKey: ["retail-settings-audit"] });
    },
    onError: (e: unknown) => { setMsg(""); setError(parseApiError(e, "Could not save.")); },
  });
  const status = (
    <>
      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
    </>
  );
  const button = (onClick: () => void) => (
    <button type="button" onClick={() => { setMsg(""); onClick(); }} disabled={save.isPending}
      className="px-4 py-2 rounded-xl text-sm font-semibold text-white disabled:opacity-50" style={{ background: RETAIL_ACCENT }}>
      {save.isPending ? "Saving…" : "Save"}
    </button>
  );
  return { save, status, button };
}

export const settingsInputCls = "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
