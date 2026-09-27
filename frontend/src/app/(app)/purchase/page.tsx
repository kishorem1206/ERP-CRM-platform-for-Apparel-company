import Link from "next/link";
import { Building2, ClipboardList, PackageCheck, ChevronRight } from "lucide-react";

const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

const CARDS = [
  {
    href: "/purchase/vendors",
    icon: Building2,
    title: "Vendors",
    description: "Manage suppliers, job workers, and transporters",
    accent: LAVENDER,
  },
  {
    href: "/purchase/orders",
    icon: ClipboardList,
    title: "Purchase Orders",
    description: "Create and approve POs with GST line items",
    accent: BLUE,
  },
  {
    href: "/purchase/grn",
    icon: PackageCheck,
    title: "Goods Receipt",
    description: "Record GRNs, quality check, and update inventory",
    accent: TEAL,
  },
];

const WORKFLOW = [
  { label: "PO", color: BLUE },
  { label: "GRN", color: TEAL },
  { label: "Stock", color: LAVENDER },
];

export default function PurchasePage() {
  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          Module
        </p>
        <h1 className="text-2xl font-bold tracking-tight">Purchase</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage vendors, purchase orders, and goods receipts
        </p>
      </div>

      {/* Workflow strip */}
      <div className="bg-card border border-border rounded-2xl px-6 py-4">
        <div className="flex items-center gap-2 flex-wrap text-xs font-medium text-muted-foreground">
          {WORKFLOW.map((step, i) => (
            <>
              <span
                key={step.label}
                className="px-2.5 py-1 rounded-full font-semibold text-[11px]"
                style={{ background: `${step.color}14`, color: step.color }}
              >
                {step.label}
              </span>
              {i < WORKFLOW.length - 1 && (
                <ChevronRight key={`arrow-${i}`} className="h-3 w-3" />
              )}
            </>
          ))}
        </div>
      </div>

      {/* Nav cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {CARDS.map(({ href, icon: Icon, title, description, accent }) => (
          <Link
            key={href}
            href={href}
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
              <p className="font-semibold">{title}</p>
              <p className="text-sm text-muted-foreground mt-0.5">{description}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
