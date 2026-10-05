"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Download } from "lucide-react";
import api from "@/lib/api";
import { formatIndianFull } from "@/lib/format";

const INDIGO = "#0049A7";

export interface Fact {
  label: string;
  value: string | null | undefined;
}

export function fmtDate(iso: string | null | undefined) {
  if (!iso) return null;
  return new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function money(v: unknown) {
  return v === null || v === undefined || v === "" ? null : formatIndianFull(Number(v));
}

export function PdfDocumentPage({
  title, number, status, backHref, pdfPath, downloadName, facts, loading, error,
}: {
  title: string;
  number?: string;
  status?: string | null;
  backHref: string;
  pdfPath: string;
  downloadName: string;
  facts: Fact[];
  loading: boolean;
  error: boolean;
}) {
  const [src, setSrc] = useState<string | null>(null);
  const [pdfFailed, setPdfFailed] = useState(false);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    setSrc(null);
    setPdfFailed(false);
    api
      .get(pdfPath, { responseType: "blob" })
      .then((res) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(res.data as Blob);
        setSrc(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setPdfFailed(true);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [pdfPath]);

  return (
    <div className="p-8 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <Link href={backHref} className="rounded-lg p-2 hover:bg-muted" aria-label="Back">
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">{title}</p>
            <h1 className="text-2xl font-bold tracking-tight truncate">{number ?? (loading ? "Loading…" : "—")}</h1>
          </div>
          {status && (
            <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-[11px] font-bold uppercase text-indigo-700">{status}</span>
          )}
        </div>
        <a
          href={src ?? undefined}
          download={downloadName}
          aria-disabled={!src}
          className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-sm ${src ? "" : "pointer-events-none opacity-50"}`}
          style={{ background: INDIGO }}
        >
          <Download className="h-4 w-4" /> Download PDF
        </a>
      </div>

      {error ? (
        <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
          This record could not be loaded. It may have been deleted, or you may not have access to it.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {facts.map((f) => (
              <div key={f.label} className="rounded-xl border border-border bg-card p-4 min-w-0">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{f.label}</p>
                <p className="mt-1 truncate font-semibold tabular-nums">{loading ? "…" : f.value || "—"}</p>
              </div>
            ))}
          </div>

          <div className="rounded-2xl border border-border bg-card p-3">
            {pdfFailed ? (
              <p className="p-8 text-center text-sm text-muted-foreground">The PDF could not be generated.</p>
            ) : src ? (
              <iframe src={src} title={`${title} ${number ?? ""}`} className="h-[85vh] w-full rounded-xl bg-white" />
            ) : (
              <div className="flex h-[60vh] items-center justify-center text-sm text-muted-foreground">Preparing document…</div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
