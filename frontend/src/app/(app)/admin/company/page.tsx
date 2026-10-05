"use client";
import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Save } from "lucide-react";
import api from "@/lib/api";
import { Can } from "@/lib/permissions";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

type CompanyData = {
  id: string;
  name: string;
  gstin: string | null;
  pan: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  state_code: number | null;
  pincode: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  currency: string;
  fabric_variance_pct: number | null;
  negative_stock_allowed: boolean;
  bill_alert_days: number;
};

type FormState = {
  name: string;
  gstin: string;
  pan: string;
  address: string;
  city: string;
  state: string;
  state_code: string;
  pincode: string;
  phone: string;
  email: string;
  website: string;
  fabric_variance_pct: string;
  negative_stock_allowed: boolean;
  bill_alert_days: string;
};

function toForm(d: CompanyData): FormState {
  return {
    name: d.name ?? "",
    gstin: d.gstin ?? "",
    pan: d.pan ?? "",
    address: d.address ?? "",
    city: d.city ?? "",
    state: d.state ?? "",
    state_code: d.state_code != null ? String(d.state_code) : "",
    pincode: d.pincode ?? "",
    phone: d.phone ?? "",
    email: d.email ?? "",
    website: d.website ?? "",
    fabric_variance_pct: d.fabric_variance_pct != null ? String(d.fabric_variance_pct) : "3",
    negative_stock_allowed: d.negative_stock_allowed,
    bill_alert_days: String(d.bill_alert_days ?? 7),
  };
}

type FieldDef = { key: keyof FormState; label: string; required?: boolean; multiline?: boolean; type?: string };
type Section = { title: string; subtitle: string; fields: FieldDef[] };

const SECTIONS: Section[] = [
  {
    title: "Identity",
    subtitle: "Legal name and tax registration",
    fields: [
      { key: "name", label: "Company Name", required: true },
      { key: "gstin", label: "GSTIN" },
      { key: "pan", label: "PAN" },
    ],
  },
  {
    title: "Address",
    subtitle: "Registered office address",
    fields: [
      { key: "address", label: "Address", multiline: true },
      { key: "city", label: "City" },
      { key: "state", label: "State" },
      { key: "state_code", label: "State Code (GST)", type: "number" },
      { key: "pincode", label: "Pincode" },
    ],
  },
  {
    title: "Contact",
    subtitle: "Phone, email and web presence",
    fields: [
      { key: "phone", label: "Phone" },
      { key: "email", label: "Email" },
      { key: "website", label: "Website" },
    ],
  },
];

export default function CompanySettingsPage() {
  const [form, setForm] = useState<FormState | null>(null);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const { data, isLoading } = useQuery<CompanyData>({
    queryKey: ["admin-company"],
    queryFn: async () => {
      const res = await api.get("/admin/company");
      return res.data.data;
    },
  });

  useEffect(() => {
    if (data && !form) setForm(toForm(data));
  }, [data, form]);

  const saveMut = useMutation({
    mutationFn: () =>
      api.put("/admin/company", {
        ...form,
        state_code: form?.state_code ? Number(form.state_code) : null,
        fabric_variance_pct: form?.fabric_variance_pct ? Number(form.fabric_variance_pct) : null,
        bill_alert_days: form?.bill_alert_days ? Number(form.bill_alert_days) : null,
      }),
    onSuccess: () => {
      setSuccess("Settings saved successfully.");
      setError("");
      setTimeout(() => setSuccess(""), 4000);
    },
    onError: () => setError("Failed to save settings."),
  });

  function set(key: keyof FormState, val: string | boolean) {
    setForm((f) => f && { ...f, [key]: val });
  }

  if (isLoading || !form) {
    return <div className="p-8 text-muted-foreground text-sm">Loading…</div>;
  }

  return (
    <div className="p-8 space-y-8 max-w-2xl">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            ADMIN / COMPANY
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Company Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Legal name, GSTIN, address, and branding.
          </p>
        </div>
      </div>

      {success && (
        <div className="rounded-2xl bg-blue-50 dark:bg-blue-950/30 border border-blue-200 text-blue-800 dark:text-blue-400 px-4 py-3 text-sm">
          {success}
        </div>
      )}
      {error && (
        <div className="rounded-2xl bg-violet-50 dark:bg-violet-950/30 border border-violet-200 text-violet-700 px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {SECTIONS.map(({ title, subtitle, fields }) => (
        <div key={title} className="bg-card border border-border rounded-2xl p-6 space-y-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">{title.toUpperCase()}</p>
            <p className="text-sm font-medium mt-0.5">{subtitle}</p>
          </div>
          {fields.map(({ key, label, required, multiline, type }) => (
            <div key={key}>
              <label className="block text-xs font-medium mb-1 text-muted-foreground">
                {label}{required && " *"}
              </label>
              {multiline ? (
                <textarea
                  value={String(form[key] ?? "")}
                  onChange={(e) => set(key, e.target.value)}
                  rows={3}
                  className="w-full border rounded-xl px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
                />
              ) : (
                <input
                  type={type ?? "text"}
                  value={String(form[key] ?? "")}
                  onChange={(e) => set(key, e.target.value)}
                  className="w-full border rounded-xl px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              )}
            </div>
          ))}
        </div>
      ))}

      <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">OPERATIONAL</p>
          <p className="text-sm font-medium mt-0.5">Inventory and variance controls</p>
        </div>
        <div>
          <label className="block text-xs font-medium mb-1 text-muted-foreground">Fabric Variance % (allowed wastage)</label>
          <input
            type="number" step="0.01" min="0" max="20"
            value={form.fabric_variance_pct}
            onChange={(e) => set("fabric_variance_pct", e.target.value)}
            className="w-40 border rounded-xl px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1 text-muted-foreground">Bill / invoice alert after (days)</label>
          <input
            type="number" step="1" min="1" max="365"
            value={form.bill_alert_days}
            onChange={(e) => set("bill_alert_days", e.target.value)}
            className="w-40 border rounded-xl px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
          <p className="text-xs text-muted-foreground mt-1">Alert when a job-work challan's vendor bill is still missing this many days after material was sent out.</p>
        </div>
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={form.negative_stock_allowed}
            onChange={(e) => set("negative_stock_allowed", e.target.checked)}
            className="h-4 w-4 rounded"
          />
          <div>
            <span className="text-sm font-medium">Allow Negative Stock</span>
            <p className="text-xs text-muted-foreground">Allow stock balance to go below zero</p>
          </div>
        </label>
      </div>

      <div className="flex justify-end">
        <Can perm="admin.settings"><button
          onClick={() => saveMut.mutate()}
          disabled={saveMut.isPending}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          <Save className="h-4 w-4" />
          {saveMut.isPending ? "Saving…" : "Save Settings"}
        </button></Can>
      </div>
    </div>
  );
}
