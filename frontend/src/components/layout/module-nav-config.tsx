import {
  LayoutDashboard, Users, ShoppingCart, Package, Factory,
  BarChart3, Settings, Bot, Wallet, ShoppingBag, Scissors, Shield,
  FileText, Truck, Receipt, Building2, ClipboardList, PackageCheck,
  Layers, BarChart2, ArrowDownToLine, ArrowUpFromLine, ArrowLeftRight,
  SlidersHorizontal, Warehouse, CreditCard, Calculator, FileMinus, FilePlus,
  TrendingUp, Ruler, PackageOpen, CheckSquare, Database, User,
  Target, ListChecks, MessageCircle, Mail, Star, ListTodo, Tag, Zap,
} from "lucide-react";
import type { ComponentType } from "react";

export interface ModuleNavItem {
  label: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
  group?: string;
}

export interface ModuleNavEntry {
  key: string;
  label: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
  items: ModuleNavItem[];
}

export const MODULE_NAV: ModuleNavEntry[] = [
  {
    key: "dashboard", label: "Dashboard", href: "/dashboard", icon: LayoutDashboard,
    items: [{ label: "Overview", href: "/dashboard", icon: LayoutDashboard }],
  },
  {
    key: "crm", label: "CRM", href: "/crm", icon: Users,
    items: [
      { label: "Dashboard", href: "/crm/dashboard", icon: LayoutDashboard, group: "Overview" },
      { label: "Tasks", href: "/crm/tasks", icon: ListTodo, group: "Overview" },
      { label: "Reports", href: "/crm/reports", icon: BarChart3, group: "Overview" },
      { label: "Leads", href: "/crm/leads", icon: Target, group: "Pipeline" },
      { label: "Customers", href: "/crm/customers", icon: Users, group: "Contacts" },
      { label: "Persons", href: "/crm/persons", icon: User, group: "Contacts" },
      { label: "Organizations", href: "/crm/organizations", icon: Building2, group: "Contacts" },
      { label: "Products", href: "/crm/products", icon: Package, group: "Sales" },
      { label: "Quotes", href: "/crm/quotes", icon: FileText, group: "Sales" },
      { label: "Activities", href: "/crm/activities", icon: ListChecks, group: "Activity" },
      { label: "WhatsApp", href: "/crm/whatsapp", icon: MessageCircle, group: "Activity" },
      { label: "Automation", href: "/crm/whatsapp-automation", icon: Zap, group: "Activity" },
      { label: "Emails", href: "/crm/email", icon: Mail, group: "Activity" },
      { label: "Ad Spend", href: "/crm/ad-spend", icon: Wallet, group: "Marketing" },
      { label: "Settings", href: "/crm/settings", icon: Settings, group: "Settings" },
    ],
  },
  {
    key: "sales", label: "Sales", href: "/sales", icon: ShoppingCart,
    items: [
      { label: "Quotations", href: "/sales/quotations", icon: FileText },
      { label: "Sales Orders", href: "/sales/orders", icon: ShoppingCart },
      { label: "Delivery Challans", href: "/sales/deliveries", icon: Truck },
      { label: "Invoices", href: "/sales/invoices", icon: Receipt },
      { label: "Price Lists", href: "/sales/price-lists", icon: Tag },
    ],
  },
  {
    key: "purchase", label: "Purchasing", href: "/purchase", icon: ShoppingBag,
    items: [
      { label: "Vendors", href: "/purchase/vendors", icon: Building2 },
      { label: "Purchase Orders", href: "/purchase/orders", icon: ClipboardList },
      { label: "Goods Receipt", href: "/purchase/grn", icon: PackageCheck },
    ],
  },
  {
    key: "inventory", label: "Inventory", href: "/inventory", icon: Package,
    items: [
      { label: "Material Lots", href: "/inventory/lots", icon: Layers },
      { label: "Stock Balance", href: "/inventory/balance", icon: BarChart2 },
      { label: "Stock In", href: "/inventory/stock-in", icon: ArrowDownToLine },
      { label: "Stock Out", href: "/inventory/stock-out", icon: ArrowUpFromLine },
      { label: "Stock Transfer", href: "/inventory/transfer", icon: ArrowLeftRight },
      { label: "Adjustment", href: "/inventory/adjust", icon: SlidersHorizontal },
      { label: "Products", href: "/inventory/products", icon: Package },
      { label: "Transaction Log", href: "/inventory/transactions", icon: Warehouse },
    ],
  },
  {
    key: "production", label: "Production", href: "/production", icon: Scissors,
    items: [
      { label: "Styles", href: "/production/styles", icon: Ruler },
      { label: "Production Lots", href: "/production/lots", icon: Scissors },
      { label: "Material Issue Slips", href: "/production/mis", icon: PackageOpen },
      { label: "Production Output", href: "/production/outputs", icon: CheckSquare },
    ],
  },
  {
    key: "finance", label: "Finance", href: "/finance", icon: Wallet,
    items: [
      { label: "Customer Payments", href: "/finance/payments", icon: Wallet },
      { label: "Vendor Payments", href: "/finance/vendor-payments", icon: CreditCard },
      { label: "GST Register", href: "/finance/gst", icon: Calculator },
      { label: "Credit Notes", href: "/finance/credit-notes", icon: FileMinus },
      { label: "Debit Notes", href: "/finance/debit-notes", icon: FilePlus },
    ],
  },
  {
    key: "reports", label: "Reports", href: "/reports", icon: BarChart3,
    items: [
      { label: "Sales Summary", href: "/reports/sales", icon: TrendingUp },
      { label: "Purchase Summary", href: "/reports/purchases", icon: ShoppingBag },
      { label: "Production Efficiency", href: "/reports/production", icon: Factory },
      { label: "GST Summary", href: "/reports/gst", icon: Calculator },
      { label: "Stock Ageing", href: "/reports/stock-ageing", icon: BarChart3 },
    ],
  },
  {
    key: "ai-assistant", label: "AI Assistant", href: "/ai-assistant", icon: Bot,
    items: [{ label: "Assistant", href: "/ai-assistant", icon: Bot }],
  },
  {
    key: "security", label: "Security", href: "/settings/security", icon: Shield,
    items: [{ label: "Security Settings", href: "/settings/security", icon: Shield }],
  },
  {
    key: "admin", label: "Admin", href: "/admin", icon: Settings,
    items: [
      { label: "Company Settings", href: "/admin/company", icon: Building2 },
      { label: "Master Data", href: "/admin/master-data", icon: Database },
      { label: "User Management", href: "/admin/users", icon: Users },
      { label: "Roles & Permissions", href: "/admin/roles", icon: Shield },
    ],
  },
];

export function findActiveModule(pathname: string): ModuleNavEntry {
  const sorted = [...MODULE_NAV].sort((a, b) => b.href.length - a.href.length);
  return sorted.find((m) => pathname === m.href || pathname.startsWith(m.href + "/")) ?? MODULE_NAV[0];
}

export { Star as SavedFilterIcon };
