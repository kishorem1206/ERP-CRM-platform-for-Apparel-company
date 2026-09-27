import Link from "next/link";
import { TrendingUp, ShoppingBag, Factory, Calculator, BarChart3, ChevronRight } from "lucide-react";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";
const AMBER    = "#A096F7";

const CARDS = [
  {
    href: "/reports/sales",
    icon: TrendingUp,
    title: "Sales Summary",
    description: "Revenue by customer with GST breakdown and outstanding",
    accent: INDIGO,
  },
  {
    href: "/reports/purchases",
    icon: ShoppingBag,
    title: "Purchase Summary",
    description: "Spend by vendor with GST breakdown and payables",
    accent: TEAL,
  },
  {
    href: "/reports/production",
    icon: Factory,
    title: "Production Efficiency",
    description: "Planned vs actual quantity per production lot",
    accent: BLUE,
  },
  {
    href: "/reports/gst",
    icon: Calculator,
    title: "GST Summary",
    description: "Monthly CGST / SGST / IGST output and input tax",
    accent: LAVENDER,
  },
  {
    href: "/reports/stock-ageing",
    icon: BarChart3,
    title: "Stock Ageing",
    description: "How long inventory has been sitting per warehouse",
    accent: AMBER,
  },
];

export default function ReportsPage() {
  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          Module
        </p>
        <h1 className="text-2xl font-bold tracking-tight">Reports</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Analytics and summaries across all modules
        </p>
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
