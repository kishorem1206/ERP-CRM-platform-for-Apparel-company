"use client";
import { useState, useEffect } from "react";
import { X, Layers, Package2, Scissors, Wind } from "lucide-react";
import { NewLotModal } from "./NewLotModal";
import { NewFabricRunModal } from "./NewFabricRunModal";
import { AddYarnModal } from "./AddYarnModal";
import { AddFabricModal } from "./AddFabricModal";
import { AddTrimsModal } from "./AddTrimsModal";
import { usePermissions } from "@/lib/permissions";

type ModalKey = "lot" | "fabric_run" | "yarn" | "fabric" | "trim" | null;

const SECTIONS = [
  {
    label: "Production",
    items: [
      { key: "lot" as ModalKey,        icon: Layers,    label: "New Lot",         desc: "Start a production lot linked to a style", permission: "production.create" },
      { key: "fabric_run" as ModalKey, icon: Scissors,  label: "New Fabric Run",  desc: "Track a knitting or weaving run", permission: "materials.create" },
    ],
  },
  {
    label: "Stock",
    items: [
      { key: "yarn" as ModalKey,   icon: Wind,     label: "Add Yarn",    desc: "Receive a yarn lot into inventory", permission: "materials.create" },
      { key: "fabric" as ModalKey, icon: Package2, label: "Add Fabric",  desc: "Receive a fabric lot", permission: "materials.create" },
      { key: "trim" as ModalKey,   icon: Package2, label: "Add Trims",   desc: "Receive buttons, labels, or other trims", permission: "materials.create" },
    ],
  },
];

/** Any one of these lets the user open Quick Create at all. */
export const QUICK_CREATE_PERMISSIONS = ["production.create", "materials.create"];

interface Props {
  open: boolean;
  onClose: () => void;
}

export function CreateMenu({ open, onClose }: Props) {
  const [active, setActive] = useState<ModalKey>(null);
  const { can } = usePermissions();

  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  function pick(key: ModalKey) {
    setActive(key);
    onClose();
  }

  return (
    <>
      {/* Menu panel — only visible when open */}
      {open && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[1px]"
            onClick={onClose}
          />
          {/* Panel */}
          <div className="fixed z-50 left-4 top-28 w-72 bg-card border border-border rounded-2xl shadow-xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <p className="text-sm font-semibold">Quick Create</p>
              <button onClick={onClose} className="p-1 rounded-md hover:bg-muted text-muted-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="p-2">
              {SECTIONS.map((section) => {
                const items = section.items.filter((item) => can(item.permission));
                if (items.length === 0) return null;
                return (
                <div key={section.label} className="mb-1">
                  <p className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                    {section.label}
                  </p>
                  {items.map(({ key, icon: Icon, label, desc }) => (
                    <button
                      key={key}
                      onClick={() => pick(key)}
                      className="w-full flex items-start gap-3 px-3 py-2.5 rounded-lg hover:bg-muted text-left transition-colors"
                    >
                      <span className="mt-0.5 flex-none p-1.5 rounded-md bg-primary/10">
                        <Icon className="h-3.5 w-3.5 text-primary" />
                      </span>
                      <span>
                        <span className="block text-sm font-medium">{label}</span>
                        <span className="block text-xs text-muted-foreground">{desc}</span>
                      </span>
                    </button>
                  ))}
                </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* Modals always rendered — independent of menu open state */}
      <NewLotModal       open={active === "lot"}        onClose={() => setActive(null)} />
      <NewFabricRunModal open={active === "fabric_run"} onClose={() => setActive(null)} />
      <AddYarnModal      open={active === "yarn"}       onClose={() => setActive(null)} />
      <AddFabricModal    open={active === "fabric"}     onClose={() => setActive(null)} />
      <AddTrimsModal     open={active === "trim"}       onClose={() => setActive(null)} />
    </>
  );
}
