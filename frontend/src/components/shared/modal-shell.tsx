"use client";
import { ReactNode, useEffect, useState } from "react";
import { createPortal } from "react-dom";

export function ModalShell({
  children,
  maxWidth = "max-w-lg",
  onClose,
}: {
  children: ReactNode;
  maxWidth?: string;
  onClose?: () => void;
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  useEffect(() => {
    if (!onClose) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  if (!mounted) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] overflow-y-auto bg-black/40 backdrop-blur-[2px] px-4 py-8 sm:px-6 sm:py-12"
      onClick={(e) => {
        if (e.target === e.currentTarget && onClose) onClose();
      }}
    >
      <div
        className={`relative mx-auto w-full ${maxWidth} bg-card border border-border rounded-2xl shadow-2xl`}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>,
    document.body
  );
}
