"use client";
import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, ChevronUp, Check } from "lucide-react";

export interface SelectOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
  meta?: string;
}

interface Props {
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  accent?: string;
  disabled?: boolean;
}

const DEFAULT_ACCENT = "#0049A7";
const SELECTED_COLOR = "#0F78FF"; // vivid blue for confirmed selection

export function SearchableSelect({
  options,
  value,
  onChange,
  placeholder = "Select…",
  accent = DEFAULT_ACCENT,
  disabled = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [hovered, setHovered] = useState<string | null>(null);
  const [coords, setCoords] = useState<{ top: number; left: number; width: number } | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selected = options.find((o) => o.value === value) ?? null;

  // Filtered list
  const filtered = query.trim()
    ? options.filter((o) =>
        o.label.toLowerCase().includes(query.toLowerCase()) ||
        (o.meta ?? "").toLowerCase().includes(query.toLowerCase())
      )
    : options;

  // Close on outside click (trigger or portaled dropdown)
  useEffect(() => {
    function handle(e: MouseEvent) {
      const target = e.target as Node;
      if (ref.current?.contains(target)) return;
      if (dropdownRef.current?.contains(target)) return;
      close();
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  // Escape key — closes just the dropdown, and must not also close a parent
  // modal (ModalShell listens for Escape too, at the window level).
  useEffect(() => {
    function handle(e: KeyboardEvent) {
      if (e.key === "Escape" && open) {
        e.stopPropagation();
        close();
      }
    }
    document.addEventListener("keydown", handle);
    return () => document.removeEventListener("keydown", handle);
  }, [open]);

  // Keep the portaled dropdown anchored to the trigger; close on scroll/resize
  // so it never drifts or gets clipped by an ancestor's overflow-hidden.
  useEffect(() => {
    if (!open) return;
    function updateCoords() {
      const rect = ref.current?.getBoundingClientRect();
      if (rect) setCoords({ top: rect.bottom + 6, left: rect.left, width: rect.width });
    }
    updateCoords();
    function handleScroll(e: Event) {
      if (dropdownRef.current?.contains(e.target as Node)) return;
      close();
    }
    window.addEventListener("resize", updateCoords);
    window.addEventListener("scroll", handleScroll, true);
    return () => {
      window.removeEventListener("resize", updateCoords);
      window.removeEventListener("scroll", handleScroll, true);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function openDropdown() {
    if (disabled) return;
    const rect = ref.current?.getBoundingClientRect();
    if (rect) setCoords({ top: rect.bottom + 6, left: rect.left, width: rect.width });
    setOpen(true);
    setQuery("");
    setTimeout(() => inputRef.current?.focus(), 20);
  }

  function close() {
    setOpen(false);
    setQuery("");
    setHovered(null);
  }

  function select(opt: SelectOption) {
    onChange(opt.value);
    close();
  }

  // Highlight matched text
  function highlight(text: string, q: string) {
    if (!q.trim()) return <span>{text}</span>;
    const idx = text.toLowerCase().indexOf(q.toLowerCase());
    if (idx === -1) return <span>{text}</span>;
    return (
      <>
        <span>{text.slice(0, idx)}</span>
        <span className="font-bold">{text.slice(idx, idx + q.length)}</span>
        <span className="text-muted-foreground font-normal">{text.slice(idx + q.length)}</span>
      </>
    );
  }

  const isSelected = !!selected && !!value;

  return (
    <div ref={ref} className="relative w-full">
      {/* ── Trigger ─────────────────────────────────────── */}
      <div
        onClick={openDropdown}
        className={[
          "flex items-center w-full rounded-xl border bg-background cursor-text transition-all duration-150",
          disabled ? "opacity-50 cursor-not-allowed" : "",
        ].join(" ")}
        style={{
          borderColor: open
            ? accent
            : isSelected
            ? `${SELECTED_COLOR}80`
            : "hsl(var(--border))",
          boxShadow: open ? `0 0 0 3px ${accent}20` : undefined,
        }}
      >
        {/* Icon from selected option */}
        {selected?.icon && !open && (
          <span className="pl-3 text-lg flex-shrink-0">{selected.icon}</span>
        )}

        {/* Input (always rendered — shows value when closed, accepts query when open) */}
        <input
          ref={inputRef}
          type="text"
          value={open ? query : (selected?.label ?? "")}
          placeholder={open ? "Type to search…" : placeholder}
          readOnly={!open}
          disabled={disabled}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={openDropdown}
          className={[
            "flex-1 bg-transparent px-3 py-2.5 text-sm outline-none min-w-0",
            !open && !selected ? "text-muted-foreground" : "text-foreground",
            !open ? "cursor-pointer select-none" : "cursor-text",
          ].join(" ")}
          style={open ? { color: "hsl(var(--foreground))" } : undefined}
          autoComplete="off"
        />

        {/* Right icon */}
        <span className="pr-3 flex-shrink-0 flex items-center">
          {isSelected && !open ? (
            <Check className="h-4 w-4" style={{ color: SELECTED_COLOR }} />
          ) : open ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </span>
      </div>

      {/* ── Dropdown panel — portaled so ancestor overflow-hidden can't clip it ── */}
      {open && coords && createPortal(
        <div
          ref={dropdownRef}
          className="fixed z-[10000] bg-background border border-border rounded-xl shadow-2xl overflow-hidden"
          style={{ top: coords.top, left: coords.left, width: coords.width, minWidth: "200px" }}
        >
          <div className="max-h-60 overflow-y-auto py-1.5">
            {filtered.length === 0 ? (
              <p className="px-4 py-3 text-sm text-muted-foreground text-center">
                No results for &ldquo;{query}&rdquo;
              </p>
            ) : (
              filtered.map((opt) => {
                const isActive = opt.value === value;
                const isHov = hovered === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onMouseEnter={() => setHovered(opt.value)}
                    onMouseLeave={() => setHovered(null)}
                    onClick={() => select(opt)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-left transition-colors duration-75"
                    style={{
                      background: isActive
                        ? `${accent}12`
                        : isHov
                        ? "hsl(var(--muted) / 0.6)"
                        : "transparent",
                      color: isActive ? accent : "hsl(var(--foreground))",
                    }}
                  >
                    {opt.icon && (
                      <span className="flex-shrink-0 text-base">{opt.icon}</span>
                    )}
                    <span className="flex-1 min-w-0">
                      <span className={`block truncate ${isActive ? "font-semibold" : ""}`}>
                        {highlight(opt.label, query)}
                      </span>
                      {opt.meta && (
                        <span
                          className="block text-[11px] truncate"
                          style={{ color: isActive ? `${accent}99` : "hsl(var(--muted-foreground))" }}
                        >
                          {opt.meta}
                        </span>
                      )}
                    </span>
                    {isActive && (
                      <Check className="h-4 w-4 flex-shrink-0" style={{ color: accent }} />
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
