"use client";

import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X, Upload, FileText } from "lucide-react";
import api from "@/lib/api";
import { ModalShell } from "@/components/shared/modal-shell";

const INDIGO = "#0049A7";
const RED = "#1D0DB0";

interface ImportResult {
  total_rows: number;
  imported: number;
  failed: number;
  errors: { row: number; error: string }[];
}

export function AdSpendImportModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      fd.append("file", file!);
      const res = await api.post("/crm/ad-spend/import", fd);
      return res.data;
    },
    onSuccess: (data) => {
      setResult(data?.data ?? null);
      queryClient.invalidateQueries({ queryKey: ["crm-ad-spend"] });
      queryClient.invalidateQueries({ queryKey: ["crm-lead-sources"] });
    },
  });

  return (
    <ModalShell maxWidth="max-w-lg" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Import Ad Spend</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="p-6 space-y-4">
        {!result && (
          <>
            <p className="text-xs text-muted-foreground">
              CSV columns: <code className="text-[11px]">platform, campaign, campaign_id, ad_set,
              period_start, period_end, amount, impressions, clicks, notes</code>. Dates as
              YYYY-MM-DD. A platform name not already in Lead Sources gets created automatically.
            </p>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border p-8 cursor-pointer hover:border-muted-foreground/40 transition-colors"
            >
              {file ? (
                <>
                  <FileText className="h-6 w-6" style={{ color: INDIGO }} />
                  <p className="text-sm font-medium">{file.name}</p>
                </>
              ) : (
                <>
                  <Upload className="h-6 w-6 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">Click to choose a CSV file</p>
                </>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>
          </>
        )}

        {result && (
          <div className="space-y-3">
            <div className="flex gap-4">
              <div>
                <p className="text-[11px] uppercase tracking-widest text-muted-foreground font-semibold">Imported</p>
                <p className="text-xl font-bold" style={{ color: INDIGO }}>{result.imported}</p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-widest text-muted-foreground font-semibold">Failed</p>
                <p className="text-xl font-bold" style={{ color: result.failed > 0 ? RED : undefined }}>{result.failed}</p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-widest text-muted-foreground font-semibold">Total Rows</p>
                <p className="text-xl font-bold">{result.total_rows}</p>
              </div>
            </div>
            {result.errors.length > 0 && (
              <div className="rounded-xl border border-border divide-y divide-border max-h-48 overflow-y-auto">
                {result.errors.map((e, i) => (
                  <div key={i} className="px-3 py-2 text-xs">
                    <span className="font-semibold">Row {e.row}:</span> {e.error}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          {result ? "Close" : "Cancel"}
        </button>
        {!result && (
          <button
            onClick={() => mutation.mutate()}
            disabled={!file || mutation.isPending}
            className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
            style={{ background: INDIGO }}
          >
            {mutation.isPending ? "Importing…" : "Import"}
          </button>
        )}
      </div>
    </ModalShell>
  );
}
