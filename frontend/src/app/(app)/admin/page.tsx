import Link from "next/link";
import { Building2, Users, Shield, Database, ChevronRight } from "lucide-react";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

const CARDS = [
  {
    href: "/admin/company",
    icon: Building2,
    title: "Company Settings",
    description: "Update GSTIN, address, state code, and operational defaults",
    accent: INDIGO,
  },
  {
    href: "/admin/master-data",
    icon: Database,
    title: "Master Data",
    description: "Manage units, categories, colours, sizes, warehouses, and HSN codes",
    accent: TEAL,
  },
  {
    href: "/admin/users",
    icon: Users,
    title: "User Management",
    description: "Invite and manage user accounts, activate or deactivate access",
    accent: BLUE,
  },
  {
    href: "/admin/roles",
    icon: Shield,
    title: "Roles & Permissions",
    description: "Create roles and control which actions each role can perform",
    accent: LAVENDER,
  },
];

export default function AdminPage() {
  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          Module
        </p>
        <h1 className="text-2xl font-bold tracking-tight">Administration</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage users, access control, and company configuration
        </p>
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
