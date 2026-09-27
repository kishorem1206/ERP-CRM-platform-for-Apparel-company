import Link from "next/link";
import { Wallet, CreditCard, Calculator, FileMinus, FilePlus, ChevronRight } from "lucide-react";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";
const ORANGE   = "#A096F7";

const CARDS = [
  {
    href: "/finance/payments",
    icon: Wallet,
    title: "Customer Payments",
    description: "Record receipts against sales invoices",
    accent: TEAL,
  },
  {
    href: "/finance/vendor-payments",
    icon: CreditCard,
    title: "Vendor Payments",
    description: "Record payments made to vendors",
    accent: LAVENDER,
  },
  {
    href: "/finance/gst",
    icon: Calculator,
    title: "GST Register",
    description: "GSTR-1 output and GSTR-2A input tax register",
    accent: BLUE,
  },
  {
    href: "/finance/credit-notes",
    icon: FileMinus,
    title: "Credit Notes",
    description: "Issue credit notes to customers",
    accent: INDIGO,
  },
  {
    href: "/finance/debit-notes",
    icon: FilePlus,
    title: "Debit Notes",
    description: "Issue debit notes against vendors",
    accent: ORANGE,
  },
];

export default function FinancePage() {
  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          Module
        </p>
        <h1 className="text-2xl font-bold tracking-tight">Finance</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Payments, credit/debit notes, and GST register
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
