import Link from "next/link";
import { WarehouseSummary } from "@/components/inventory/warehouse-summary";
import { ComponentType, CSSProperties } from "react";
import {
  Layers,
  BarChart2,
  Package,
  ArrowLeftRight,
  Warehouse,
  ChevronRight,
} from "lucide-react";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

const MATERIALS = [
  {
    href: "/inventory/lots",
    icon: Layers,
    title: "Material Lots",
    description: "Browse yarn, fabric, and trim lot records",
    accent: TEAL,
  },
  {
    href: "/inventory/balance",
    icon: BarChart2,
    title: "Stock Balance",
    description: "Current stock per product per warehouse",
    accent: BLUE,
  },
];

const OPERATIONS = [
  {
    href: "/inventory/stock-movement",
    icon: ArrowLeftRight,
    title: "Stock Movement",
    description: "In, out, transfer, or adjust — one form, pick the type",
    accent: TEAL,
  },
  {
    href: "/inventory/products",
    icon: Package,
    title: "Products",
    description: "Styles, yarns, fabrics, trims, packing",
    accent: LAVENDER,
  },
  {
    href: "/inventory/transactions",
    icon: Warehouse,
    title: "Transaction Log",
    description: "All inventory movements",
    accent: INDIGO,
  },
];


function NavCard({
  href,
  icon: Icon,
  title,
  description,
  accent,
}: {
  href: string;
  icon: ComponentType<{ className?: string; style?: CSSProperties }>;
  title: string;
  description: string;
  accent: string;
}) {
  return (
    <Link
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
  );
}

export default function InventoryPage() {
  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          Module
        </p>
        <h1 className="text-2xl font-bold tracking-tight">Inventory</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Ledger-based stock — every movement is recorded, nothing is ever overwritten
        </p>
      </div>

      {/* Materials section */}
      <div className="space-y-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
            Materials
          </p>
          <p className="text-sm font-medium mt-0.5">Lots and stock visibility</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {MATERIALS.map((card) => (
            <NavCard key={card.href} {...card} />
          ))}
        </div>
      </div>

      {/* Operations section */}
      <div className="space-y-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
            Operations
          </p>
          <p className="text-sm font-medium mt-0.5">Stock movements and product master</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {OPERATIONS.map((card) => (
            <NavCard key={card.href} {...card} />
          ))}
        </div>
      </div>

      {/* Warehouse stock summary */}
      <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
            Warehouses
          </p>
          <p className="text-sm font-medium mt-0.5">Stock by location</p>
        </div>
        <WarehouseSummary />
      </div>
    </div>
  );
}
