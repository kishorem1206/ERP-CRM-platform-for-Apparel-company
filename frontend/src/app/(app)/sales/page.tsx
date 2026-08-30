import Link from "next/link";
import { FileText, ShoppingCart, Truck, Receipt, ChevronRight } from "lucide-react";

const INDIGO   = "#5347CE";
const LAVENDER = "#887CFD";
const BLUE     = "#4896FE";
const TEAL     = "#16C8C7";

const CARDS = [
  {
    href: "/sales/quotations",
    icon: FileText,
    title: "Quotations",
    description: "Create and manage price quotations for customers",
    accent: LAVENDER,
  },
  {
    href: "/sales/orders",
    icon: ShoppingCart,
    title: "Sales Orders",
    description: "Confirmed orders — track status and delivery progress",
    accent: BLUE,
  },
  {
    href: "/sales/deliveries",
    icon: Truck,
    title: "Delivery Challans",
    description: "Dispatch goods and record inventory outflow",
    accent: TEAL,
  },
  {
    href: "/sales/invoices",
    icon: Receipt,
    title: "Invoices",
    description: "Generate GST invoices and track outstanding payments",
    accent: INDIGO,
  },
];

const WORKFLOW = [
  { label: "Quotation", color: LAVENDER },
  { label: "Sales Order", color: BLUE },
  { label: "Delivery", color: TEAL },
  { label: "Invoice", color: INDIGO },
];

export default function SalesPage() {
  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          Module
        </p>
        <h1 className="text-2xl font-bold tracking-tight">Sales</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage the full sales cycle from quotation through to invoicing
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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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
