import Link from "next/link";
import { Users2, ChevronRight } from "lucide-react";

const INDIGO = "#5347CE";

export default function CRMPage() {
  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          Module
        </p>
        <h1 className="text-2xl font-bold tracking-tight">CRM</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage buyer relationships, addresses, and contacts
        </p>
      </div>

      {/* Nav cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Link
          href="/crm/customers"
          className="group flex flex-col gap-4 bg-card border border-border rounded-2xl p-6 hover:border-primary/30 hover:shadow-lg transition-all duration-200"
        >
          <div className="flex items-center justify-between">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: `${INDIGO}14`, border: `1.5px solid ${INDIGO}28` }}
            >
              <Users2 className="h-5 w-5" style={{ color: INDIGO }} />
            </div>
            <ChevronRight className="h-4 w-4 text-muted-foreground/40 group-hover:text-primary transition-colors" />
          </div>
          <div>
            <p className="font-semibold">Customers</p>
            <p className="text-sm text-muted-foreground mt-0.5">
              Manage customer master, addresses, contacts, and buyer relationships
            </p>
          </div>
        </Link>
      </div>
    </div>
  );
}
