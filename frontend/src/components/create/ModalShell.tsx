"use client";
import { X } from "lucide-react";
import { ReactNode, useEffect } from "react";
export { SearchableSelect } from "@/components/shared/searchable-select";
export type { SelectOption } from "@/components/shared/searchable-select";

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function ModalShell({ open, onClose, title, subtitle, children, footer }: Props) {
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" onClick={onClose} />
      <div className="fixed z-50 inset-0 flex items-center justify-center p-4 pointer-events-none">
        <div
          className="relative w-full max-w-lg bg-card border border-border rounded-2xl shadow-2xl flex flex-col max-h-[90vh] pointer-events-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-start justify-between px-5 py-4 border-b shrink-0">
            <div>
              <h2 className="text-base font-semibold">{title}</h2>
              {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-md hover:bg-muted text-muted-foreground transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Scrollable body */}
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            {children}
          </div>

          {/* Footer */}
          {footer && (
            <div className="px-5 py-3 border-t flex justify-end gap-3 shrink-0 bg-card">
              {footer}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

// Field + label wrapper
export function Field({ label, required, children, hint }: { label: string; required?: boolean; children: ReactNode; hint?: string }) {
  return (
    <div>
      <label className="block text-xs font-medium text-foreground mb-1">
        {label}{required && <span className="text-violet-500 ml-0.5">*</span>}
      </label>
      {children}
      {hint && <p className="text-[11px] text-muted-foreground mt-0.5">{hint}</p>}
    </div>
  );
}

// Reusable text input
export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-xl border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 ${props.className ?? ""}`}
    />
  );
}

// Reusable textarea
export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      rows={props.rows ?? 2}
      className={`w-full rounded-xl border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none ${props.className ?? ""}`}
    />
  );
}

// Pill segmented control
export function SegControl({ options, value, onChange }: { options: string[]; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex gap-1 flex-wrap">
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(opt)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
            value === opt
              ? "bg-primary text-primary-foreground border-primary"
              : "bg-background border-border text-muted-foreground hover:text-foreground hover:border-foreground/30"
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

// Submit / cancel buttons
export function ModalActions({ onClose, loading, label = "Save", disabled = false }: { onClose: () => void; loading: boolean; label?: string; disabled?: boolean }) {
  return (
    <>
      <button
        type="button"
        onClick={onClose}
        className="px-4 py-2 rounded-lg border border-border text-sm font-medium hover:bg-muted transition-colors"
      >
        Cancel
      </button>
      <button
        type="submit"
        disabled={loading || disabled}
        className="px-5 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 disabled:opacity-50 transition-colors"
      >
        {loading ? "Saving…" : label}
      </button>
    </>
  );
}
