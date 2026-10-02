"use client";

import { useState } from "react";
import Link from "next/link";
import {
  TrendingUp, ShoppingBag, Factory, Calculator, BarChart3, ChevronRight, Search, Users,
} from "lucide-react";
import { REPORT_REGISTRY, REPORT_CATEGORIES, ReportEntry } from "./_registry";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const TEAL     = "#8174F5";
const AMBER    = "#A096F7";

const CATEGORY_META: Record<ReportEntry["category"], { icon: typeof TrendingUp; accent: string }> = {
  CRM:        { icon: Users,       accent: TEAL },
  Sales:      { icon: TrendingUp,  accent: INDIGO },
  Purchasing: { icon: ShoppingBag, accent: TEAL },
  Inventory:  { icon: BarChart3,   accent: AMBER },
  Production: { icon: Factory,     accent: INDIGO },
  Finance:    { icon: Calculator,  accent: LAVENDER },
};

export default function ReportsPage() {
  const [query, setQuery] = useState("");

  const q = query.trim().toLowerCase();
  const filtered = q
    ? REPORT_REGISTRY.filter(
        (r) => r.title.toLowerCase().includes(q) || r.description.toLowerCase().includes(q),
      )
    : REPORT_REGISTRY;

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            Module
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Reports</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {REPORT_REGISTRY.length} reports across every module — filter, search, and export any of them
          </p>
        </div>

        <div className="flex items-center gap-2 bg-card border border-border rounded-xl px-3 py-2.5 w-full sm:w-80">
          <Search className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search reports…"
            className="text-sm bg-transparent border-none outline-none w-full"
          />
        </div>
      </div>

      {q ? (
        filtered.length === 0 ? (
          <p className="text-sm text-muted-foreground py-12 text-center">
            No reports match &ldquo;{query}&rdquo;.
          </p>
        ) : (
          <ReportGrid entries={filtered} />
        )
      ) : (
        REPORT_CATEGORIES.map((category) => {
          const entries = REPORT_REGISTRY.filter((r) => r.category === category);
          if (entries.length === 0) return null;
          return (
            <div key={category} className="space-y-3">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                {category}
              </p>
              <ReportGrid entries={entries} />
            </div>
          );
        })
      )}
    </div>
  );
}

function ReportGrid({ entries }: { entries: ReportEntry[] }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {entries.map((entry) => {
        const { icon: Icon, accent } = CATEGORY_META[entry.category];
        return (
          <Link
            key={entry.id}
            href={entry.href}
            className="group flex flex-col gap-4 bg-card border border-border rounded-2xl p-6 hover:border-primary/30 hover:shadow-lg transition-all duration-200"
          >
            <div className="flex items-center justify-between">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: `${accent}14`, border: `1.5px solid ${accent}28` }}
              >
                <Icon className="h-5 w-5" style={{ color: accent }} />
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground/40 group-hover:text-primary transition-colors" />
            </div>
            <div>
              <p className="font-semibold">{entry.title}</p>
              <p className="text-sm text-muted-foreground mt-0.5">{entry.description}</p>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
