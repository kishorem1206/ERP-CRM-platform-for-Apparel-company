"use client";
import { BillEditor } from "@/components/retail/bill-editor";
import { Can } from "@/lib/permissions";

export default function RetailBillingPage() {
  return (
    <div className="p-6 lg:p-8 space-y-5">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / RETAIL</p>
        <h1 className="text-2xl font-bold tracking-tight">Retail Billing</h1>
        <p className="text-sm text-muted-foreground mt-1">Counter bill — MRP prices include GST. Stock comes out of the retail warehouse.</p>
      </div>
      <Can perm="retail.create">
        <BillEditor mode="invoice" />
      </Can>
    </div>
  );
}
