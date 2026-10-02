// Central registry of every report in the Reports Hub, grouped by category.
// Adding a report in the future = one entry here + one page file — nothing
// else needs to change for it to show up in the hub and be searchable.

export interface ReportEntry {
  id: string;
  title: string;
  category: "CRM" | "Sales" | "Purchasing" | "Inventory" | "Production" | "Finance";
  description: string;
  href: string;
}

export const REPORT_REGISTRY: ReportEntry[] = [
  // ── CRM ──────────────────────────────────────────────────────────────────
  {
    id: "crm-analytics",
    title: "CRM Analytics",
    category: "CRM",
    description: "Pipeline funnel, lead sources, activities, and quote conversion",
    href: "/crm/reports",
  },
  {
    id: "lead-ageing",
    title: "Lead Conversion & Ageing",
    category: "CRM",
    description: "Every lead with current stage, source, value, and time-in-stage",
    href: "/reports/crm/lead-ageing",
  },
  {
    id: "task-performance",
    title: "Employee Task Performance",
    category: "CRM",
    description: "Pending, in-progress, overdue, and completed-this-week tasks per employee",
    href: "/reports/crm/task-performance",
  },
  {
    id: "platform-analytics",
    title: "Platform-Wise Lead Analytics",
    category: "CRM",
    description: "Leads, qualification, conversion, and revenue by source/platform",
    href: "/reports/crm/platform-analytics",
  },
  {
    id: "lead-acquisition-cost",
    title: "Lead Acquisition Cost",
    category: "CRM",
    description: "Cost per lead, per qualified lead, per conversion, and ROAS by platform",
    href: "/reports/crm/lead-acquisition-cost",
  },

  // ── Sales ────────────────────────────────────────────────────────────────
  {
    id: "sales-summary",
    title: "Sales Summary",
    category: "Sales",
    description: "Revenue by customer with GST breakdown and outstanding",
    href: "/reports/sales",
  },
  {
    id: "invoice-register",
    title: "Invoice Register & AR Ageing",
    category: "Sales",
    description: "Every invoice with due date, balance, and overdue ageing bucket",
    href: "/reports/sales/invoice-register",
  },
  {
    id: "quotation-register",
    title: "Quotation Register",
    category: "Sales",
    description: "Every quotation with status and the order it converted to",
    href: "/reports/sales/quotation-register",
  },
  {
    id: "sales-order-book",
    title: "Sales Order Book",
    category: "Sales",
    description: "Open and closed orders with delivery fulfilment percentage",
    href: "/reports/sales/order-book",
  },
  {
    id: "sales-by-product",
    title: "Sales by Product",
    category: "Sales",
    description: "Quantity ordered and revenue per product across sales orders",
    href: "/reports/sales/by-product",
  },

  // ── Purchasing ───────────────────────────────────────────────────────────
  {
    id: "purchase-summary",
    title: "Purchase Summary",
    category: "Purchasing",
    description: "Spend by vendor with GST breakdown and payables",
    href: "/reports/purchases",
  },
  {
    id: "po-register",
    title: "Purchase Order Register",
    category: "Purchasing",
    description: "Every PO with ordered vs received percentage",
    href: "/reports/purchasing/po-register",
  },
  {
    id: "grn-register",
    title: "GRN Register",
    category: "Purchasing",
    description: "Goods receipts with received, accepted, and rejected quantities",
    href: "/reports/purchasing/grn-register",
  },
  {
    id: "vendor-payable-ageing",
    title: "Vendor Payable Ageing",
    category: "Purchasing",
    description: "Outstanding GRN balances bucketed by age",
    href: "/reports/purchasing/vendor-payable-ageing",
  },

  // ── Inventory ────────────────────────────────────────────────────────────
  {
    id: "stock-ageing",
    title: "Stock Ageing",
    category: "Inventory",
    description: "How long inventory has been sitting per warehouse",
    href: "/reports/stock-ageing",
  },
  {
    id: "stock-summary",
    title: "Stock Summary",
    category: "Inventory",
    description: "Current stock balance and value by product and warehouse",
    href: "/reports/inventory/stock-summary",
  },
  {
    id: "stock-movement",
    title: "Stock Movement Ledger",
    category: "Inventory",
    description: "Every inventory transaction — receipts, issues, transfers, adjustments",
    href: "/reports/inventory/stock-movement",
  },
  {
    id: "material-lot-register",
    title: "Material Lot Register",
    category: "Inventory",
    description: "Yarn, fabric, and trim lots with supplier and cost",
    href: "/reports/inventory/material-lot-register",
  },

  // ── Production ───────────────────────────────────────────────────────────
  {
    id: "production-efficiency",
    title: "Production Efficiency",
    category: "Production",
    description: "Planned vs actual quantity per production lot",
    href: "/reports/production",
  },
  {
    id: "lot-costing-register",
    title: "Lot Costing Register",
    category: "Production",
    description: "Cost/piece, selling price, profit, and margin across all lots",
    href: "/reports/production/lot-costing-register",
  },
  {
    id: "job-work-outstanding",
    title: "Job-Work Outstanding",
    category: "Production",
    description: "Open vendor and worker challans with pending quantity and age",
    href: "/reports/production/job-work-outstanding",
  },
  {
    id: "material-consumption",
    title: "Material Consumption",
    category: "Production",
    description: "Materials issued to production lots by stage and product",
    href: "/reports/production/material-consumption",
  },

  // ── Finance ──────────────────────────────────────────────────────────────
  {
    id: "gst-summary",
    title: "GST Summary",
    category: "Finance",
    description: "Monthly CGST / SGST / IGST output and input tax",
    href: "/reports/gst",
  },
  {
    id: "receipt-register",
    title: "Receipt Register",
    category: "Finance",
    description: "Customer payments received, by mode and reference",
    href: "/reports/finance/receipt-register",
  },
  {
    id: "payment-register",
    title: "Payment Register",
    category: "Finance",
    description: "Payments made to vendors, by mode and reference",
    href: "/reports/finance/payment-register",
  },
  {
    id: "credit-note-register",
    title: "Credit Note Register",
    category: "Finance",
    description: "Credit notes issued to customers against invoices",
    href: "/reports/finance/credit-note-register",
  },
  {
    id: "debit-note-register",
    title: "Debit Note Register",
    category: "Finance",
    description: "Debit notes issued against vendors and GRNs",
    href: "/reports/finance/debit-note-register",
  },
];

export const REPORT_CATEGORIES = ["CRM", "Sales", "Purchasing", "Inventory", "Production", "Finance"] as const;
