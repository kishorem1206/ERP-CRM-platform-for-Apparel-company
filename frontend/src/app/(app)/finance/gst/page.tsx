"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

type GSTOutputEntry = Record<string, unknown> & {
  invoice_date: string;
  invoice_number: string;
  customer_name: string;
  gstin: string | null;
  taxable_amount: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  total_amount: string;
};

type GSTInputEntry = Record<string, unknown> & {
  entry_date: string;
  entry_number: string;
  vendor_name: string;
  gstin: string | null;
  invoice_number: string | null;
  taxable_amount: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  total_amount: string;
};

const fmt = (v: string | number) =>
  `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const outputColumns: Column<GSTOutputEntry>[] = [
  { key: "invoice_date", header: "Date" },
  { key: "invoice_number", header: "Invoice No." },
  { key: "customer_name", header: "Customer" },
  { key: "gstin", header: "GSTIN" },
  { key: "taxable_amount", header: "Taxable", render: (r) => fmt(r.taxable_amount) },
  { key: "cgst_amount", header: "CGST", render: (r) => fmt(r.cgst_amount) },
  { key: "sgst_amount", header: "SGST", render: (r) => fmt(r.sgst_amount) },
  { key: "igst_amount", header: "IGST", render: (r) => fmt(r.igst_amount) },
  { key: "total_amount", header: "Total", render: (r) => fmt(r.total_amount) },
];

const inputColumns: Column<GSTInputEntry>[] = [
  { key: "entry_date", header: "Date" },
  { key: "entry_number", header: "GRN No." },
  { key: "vendor_name", header: "Vendor" },
  { key: "gstin", header: "GSTIN" },
  { key: "invoice_number", header: "Vendor Inv." },
  { key: "taxable_amount", header: "Taxable", render: (r) => fmt(r.taxable_amount) },
  { key: "cgst_amount", header: "CGST", render: (r) => fmt(r.cgst_amount) },
  { key: "sgst_amount", header: "SGST", render: (r) => fmt(r.sgst_amount) },
  { key: "igst_amount", header: "IGST", render: (r) => fmt(r.igst_amount) },
  { key: "total_amount", header: "Total", render: (r) => fmt(r.total_amount) },
];

const GST_TABS = [
  { value: "output", label: "GSTR-1 (Output Tax)" },
  { value: "input",  label: "GSTR-2A (Input Tax)" },
] as const;

export default function GSTRegisterPage() {
  const [tab, setTab] = useState<"output" | "input">("output");

  const { data: outputData, isLoading: outputLoading } = useQuery({
    queryKey: ["gst-output"],
    queryFn: async () => {
      const res = await api.get("/finance/gst/output");
      return (res.data.data ?? []) as GSTOutputEntry[];
    },
  });

  const { data: inputData, isLoading: inputLoading } = useQuery({
    queryKey: ["gst-input"],
    queryFn: async () => {
      const res = await api.get("/finance/gst/input");
      return (res.data.data ?? []) as GSTInputEntry[];
    },
  });

  const outputTotal = (outputData ?? []).reduce((s, r) => s + Number(r.total_amount), 0);
  const inputTotal  = (inputData  ?? []).reduce((s, r) => s + Number(r.total_amount), 0);
  const netGST      = outputTotal - inputTotal;

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            FINANCE / GST
          </p>
          <h1 className="text-2xl font-bold tracking-tight">GST Summary</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Output and input tax — monthly breakdown.
          </p>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-card border border-border rounded-2xl p-6">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">OUTPUT TAX</p>
          <p className="text-2xl font-bold tracking-tight tabular-nums mt-1" style={{ color: BLUE }}>
            {fmt(outputTotal)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">GSTR-1 total invoiced</p>
        </div>
        <div className="bg-card border border-border rounded-2xl p-6">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">INPUT ITC</p>
          <p className="text-2xl font-bold tracking-tight tabular-nums mt-1" style={{ color: TEAL }}>
            {fmt(inputTotal)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">GSTR-2A credit available</p>
        </div>
        <div className="bg-card border border-border rounded-2xl p-6">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">NET GST PAYABLE</p>
          <p
            className="text-2xl font-bold tracking-tight tabular-nums mt-1"
            style={{ color: netGST >= 0 ? "#1D0DB0" : "#0F78FF" }}
          >
            {fmt(Math.abs(netGST))}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            {netGST >= 0 ? "Payable to govt." : "Credit surplus"}
          </p>
        </div>
      </div>

      {/* Tab strip */}
      <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit flex-wrap">
        {GST_TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
              tab === t.value
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Table card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              {tab === "output" ? "OUTPUT REGISTER" : "INPUT REGISTER"}
            </p>
            <p className="text-sm font-medium mt-0.5">
              {tab === "output"
                ? `${(outputData ?? []).length} invoice${(outputData ?? []).length !== 1 ? "s" : ""}`
                : `${(inputData ?? []).length} entry${(inputData ?? []).length !== 1 ? "ies" : "y"}`}
            </p>
          </div>
        </div>
        <div className="p-0">
          {tab === "output" ? (
            <DataTable columns={outputColumns} data={outputData ?? []} loading={outputLoading} />
          ) : (
            <DataTable columns={inputColumns} data={inputData ?? []} loading={inputLoading} />
          )}
        </div>
      </div>
    </div>
  );
}
