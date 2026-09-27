"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, Plus, Trash2, Star, Building2,
  Phone, MapPin, CreditCard, Users, FileText, ChevronRight, Edit2,
} from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";

// ── Palette ───────────────────────────────────────────────────────────────────
const INDIGO = "#0049A7";

interface NatureOfBusiness { id: string; name: string }
interface UserOption { id: string; full_name: string }
interface AddressForm {
  id?: string; address_type: string; line1: string; line2: string;
  city: string; state: string; state_code: string; pincode: string;
  country: string; is_default: boolean;
}
interface ContactForm { id?: string; name: string; designation: string; phone: string; email: string; is_primary: boolean }
interface DetailRow { id?: string; label: string; value: string; sort_order: number }

const emptyAddress = (type: string): AddressForm => ({
  address_type: type, line1: "", line2: "", city: "",
  state: "", state_code: "", pincode: "", country: "India", is_default: type === "billing",
});

function SectionTitle({ icon: Icon, label, eyebrow }: { icon: React.ElementType; label: string; eyebrow?: string }) {
  return (
    <div className="mb-4">
      {eyebrow && (
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">{eyebrow}</p>
      )}
      <div className="flex items-center gap-2 border-b pb-2">
        <Icon className="h-4 w-4" style={{ color: INDIGO }} />
        <h3 className="text-sm font-semibold">{label}</h3>
      </div>
    </div>
  );
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-muted-foreground mb-1">
        {label}{required && <span className="text-destructive ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

const inputCls = "w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
const GSTIN_RE = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;

const TABS = [
  { id: "company", label: "Company", icon: Building2 },
  { id: "address", label: "Addresses", icon: MapPin },
  { id: "contact", label: "Contacts", icon: Phone },
  { id: "accounting", label: "Accounting", icon: CreditCard },
  { id: "team", label: "Team", icon: Users },
  { id: "extra", label: "Other", icon: FileText },
];

function AddressBlock({ title, value, onChange }: { title: string; value: AddressForm; onChange: (a: AddressForm) => void }) {
  const set = (k: keyof AddressForm) => (e: React.ChangeEvent<HTMLInputElement>) => onChange({ ...value, [k]: e.target.value });
  return (
    <div className="rounded-2xl border border-border bg-card p-4 space-y-3">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">{title}</p>
      <div className="grid grid-cols-1 gap-3">
        <Field label="Line 1"><input className={inputCls} value={value.line1} onChange={set("line1")} /></Field>
        <Field label="Line 2"><input className={inputCls} value={value.line2} onChange={set("line2")} /></Field>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="City"><input className={inputCls} value={value.city} onChange={set("city")} /></Field>
        <Field label="State"><input className={inputCls} value={value.state} onChange={set("state")} /></Field>
        <Field label="State Code"><input className={inputCls} value={value.state_code} onChange={set("state_code")} /></Field>
        <Field label="Pincode"><input className={inputCls} value={value.pincode} onChange={set("pincode")} /></Field>
      </div>
      <Field label="Country"><input className={inputCls} value={value.country} onChange={set("country")} /></Field>
    </div>
  );
}

export default function EditCustomerPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const router = useRouter();
  const qc = useQueryClient();
  const [tab, setTab] = useState("company");
  const [error, setError] = useState("");
  const [gstinError, setGstinError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  const [form, setForm] = useState({
    code: "", legal_name: "", trade_name: "", print_name: "", internal_id: "",
    location: "", customer_type: "domestic", gstin: "", pan: "", mobile: "",
    whatsapp_no: "", landline_no: "", email: "", contact_person_name: "",
    nature_of_business_id: "", contact_type: "",
    credit_limit: "0", credit_days: "30", payable_opening_balance: "0",
    receivable_opening_balance: "0", discount_percent: "0", tds_percent: "0",
    enable_tcs: false, due_days: "0", price_list_id: "", sales_person_id: "",
    accounts_manager_id: "", agent_id: "", agent_commission_percent: "0",
    customer_rating: 0, customer_portal_enabled: false, other_details: "", remarks: "",
    is_active: true,
  });
  const [billing, setBilling] = useState<AddressForm>(emptyAddress("billing"));
  const [shipping, setShipping] = useState<AddressForm>(emptyAddress("shipping"));
  const [contacts, setContacts] = useState<ContactForm[]>([]);
  const [details, setDetails] = useState<DetailRow[]>([]);

  const { data: customer, isLoading } = useQuery({
    queryKey: ["customer", id],
    queryFn: () => api.get(`/sales/customers/${id}`).then((r) => r.data.data),
  });

  const { data: nobData } = useQuery({
    queryKey: ["nature-of-business"],
    queryFn: () => api.get("/sales/nature-of-business").then((r) => r.data.data as NatureOfBusiness[]),
  });

  const { data: usersData } = useQuery({
    queryKey: ["users-list"],
    queryFn: () => api.get("/admin/users?page_size=200").then((r) => r.data.data as UserOption[]),
  });

  useEffect(() => {
    if (!customer || ready) return;
    setForm({
      code: customer.code ?? "",
      legal_name: customer.legal_name ?? "",
      trade_name: customer.trade_name ?? "",
      print_name: customer.print_name ?? "",
      internal_id: customer.internal_id ?? "",
      location: customer.location ?? "",
      customer_type: customer.customer_type ?? "domestic",
      gstin: customer.gstin ?? "",
      pan: customer.pan ?? "",
      mobile: customer.mobile ?? "",
      whatsapp_no: customer.whatsapp_no ?? "",
      landline_no: customer.landline_no ?? "",
      email: customer.email ?? "",
      contact_person_name: customer.contact_person_name ?? "",
      nature_of_business_id: customer.nature_of_business_id ?? "",
      contact_type: customer.contact_type ?? "",
      credit_limit: String(customer.credit_limit ?? 0),
      credit_days: String(customer.credit_days ?? 30),
      payable_opening_balance: String(customer.payable_opening_balance ?? 0),
      receivable_opening_balance: String(customer.receivable_opening_balance ?? 0),
      discount_percent: String(customer.discount_percent ?? 0),
      tds_percent: String(customer.tds_percent ?? 0),
      enable_tcs: customer.enable_tcs ?? false,
      due_days: String(customer.due_days ?? 0),
      price_list_id: customer.price_list_id ?? "",
      sales_person_id: customer.sales_person_id ?? "",
      accounts_manager_id: customer.accounts_manager_id ?? "",
      agent_id: customer.agent_id ?? "",
      agent_commission_percent: String(customer.agent_commission_percent ?? 0),
      customer_rating: customer.customer_rating ?? 0,
      customer_portal_enabled: customer.customer_portal_enabled ?? false,
      other_details: customer.other_details ?? "",
      remarks: customer.remarks ?? "",
      is_active: customer.is_active ?? true,
    });
    const bill = customer.addresses?.find((a: { address_type: string }) => a.address_type === "billing") ?? emptyAddress("billing");
    const ship = customer.addresses?.find((a: { address_type: string }) => a.address_type === "shipping") ?? emptyAddress("shipping");
    setBilling({ ...emptyAddress("billing"), ...bill, state_code: String(bill.state_code ?? "") });
    setShipping({ ...emptyAddress("shipping"), ...ship, state_code: String(ship.state_code ?? "") });
    setContacts(customer.contacts?.length ? customer.contacts : []);
    setDetails(customer.details?.length ? customer.details : []);
    setReady(true);
  }, [customer, ready]);

  const mut = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.patch(`/sales/customers/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["customers"] });
      qc.invalidateQueries({ queryKey: ["customer", id] });
      router.push("/crm/customers");
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      if (Array.isArray(detail)) setError(detail.map((d: { msg?: string }) => d.msg).join(", "));
      else setError(typeof detail === "string" ? detail : "Failed to save customer");
    },
  });

  function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    setError("");
    if (form.gstin && !GSTIN_RE.test(form.gstin.toUpperCase())) {
      setGstinError("Invalid GSTIN format"); setTab("company"); return;
    }
    mut.mutate({
      ...form,
      gstin: form.gstin.toUpperCase() || null,
      pan: form.pan.toUpperCase() || null,
      trade_name: form.trade_name || null, print_name: form.print_name || null,
      internal_id: form.internal_id || null, location: form.location || null,
      mobile: form.mobile || null, whatsapp_no: form.whatsapp_no || null,
      landline_no: form.landline_no || null, email: form.email || null,
      contact_person_name: form.contact_person_name || null,
      nature_of_business_id: form.nature_of_business_id || null,
      contact_type: form.contact_type || null,
      price_list_id: form.price_list_id || null, sales_person_id: form.sales_person_id || null,
      accounts_manager_id: form.accounts_manager_id || null, agent_id: form.agent_id || null,
      other_details: form.other_details || null, remarks: form.remarks || null,
      credit_limit: parseFloat(form.credit_limit) || 0,
      credit_days: parseInt(form.credit_days) || 30,
      payable_opening_balance: parseFloat(form.payable_opening_balance) || 0,
      receivable_opening_balance: parseFloat(form.receivable_opening_balance) || 0,
      discount_percent: parseFloat(form.discount_percent) || 0,
      tds_percent: parseFloat(form.tds_percent) || 0,
      due_days: parseInt(form.due_days) || 0,
      agent_commission_percent: parseFloat(form.agent_commission_percent) || 0,
      addresses: [billing, shipping].filter((a) => a.line1 || a.city || a.pincode).map((a) => ({
        ...a, state_code: parseInt(a.state_code) || null,
      })),
      contacts: contacts.filter((c) => c.name.trim()),
      details,
    });
  }

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const setContact = (i: number, k: keyof ContactForm) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setContacts((cs) => cs.map((c, idx) => idx === i ? { ...c, [k]: e.target.value } : c));

  const nobList: NatureOfBusiness[] = nobData ?? [];
  const userList: UserOption[] = usersData ?? [];

  if (isLoading) return <div className="p-8 text-muted-foreground text-sm">Loading…</div>;
  if (!customer) return <div className="p-8 text-destructive text-sm">Customer not found</div>;

  const panels: Record<string, React.ReactNode> = {
    company: (
      <div className="space-y-6">
        <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <SectionTitle icon={Building2} label="Company Information" eyebrow="IDENTITY" />
          <div className="grid grid-cols-2 gap-4">
            <Field label="Code" required>
              <input className={inputCls} required value={form.code} onChange={set("code")} />
            </Field>
            <Field label="Type">
              <SearchableSelect
                value={form.customer_type}
                onChange={(v) => setForm((f) => ({ ...f, customer_type: v }))}
                placeholder="Select type"
                accent="#0049A7"
                options={[
                  { value: "domestic", label: "Domestic" },
                  { value: "export", label: "Export" },
                  { value: "sez", label: "SEZ" },
                ]}
              />
            </Field>
          </div>
          <Field label="Legal Name" required>
            <input className={inputCls} required value={form.legal_name} onChange={set("legal_name")} />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Trade Name"><input className={inputCls} value={form.trade_name} onChange={set("trade_name")} /></Field>
            <Field label="Print Name"><input className={inputCls} value={form.print_name} onChange={set("print_name")} /></Field>
            <Field label="Internal ID"><input className={inputCls} value={form.internal_id} onChange={set("internal_id")} /></Field>
            <Field label="Location"><input className={inputCls} value={form.location} onChange={set("location")} /></Field>
            <Field label="Nature of Business">
              <SearchableSelect
                value={form.nature_of_business_id}
                onChange={(v) => setForm((f) => ({ ...f, nature_of_business_id: v }))}
                placeholder="— Select —"
                accent="#0049A7"
                options={[
                  { value: "", label: "— Select —" },
                  ...nobList.map((n) => ({ value: n.id, label: n.name })),
                ]}
              />
            </Field>
            <Field label="Contact Type">
              <SearchableSelect
                value={form.contact_type}
                onChange={(v) => setForm((f) => ({ ...f, contact_type: v }))}
                placeholder="— Select —"
                accent="#0049A7"
                options={[
                  { value: "", label: "— Select —" },
                  { value: "buyer", label: "Buyer" },
                  { value: "agent", label: "Agent" },
                  { value: "distributor", label: "Distributor" },
                  { value: "retailer", label: "Retailer" },
                  { value: "other", label: "Other" },
                ]}
              />
            </Field>
          </div>
        </div>

        <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <SectionTitle icon={FileText} label="Tax" eyebrow="COMPLIANCE" />
          <div className="grid grid-cols-2 gap-4">
            <Field label="GSTIN">
              <input className={`${inputCls} ${gstinError ? "border-destructive" : ""}`} value={form.gstin}
                onChange={(e) => { setForm((f) => ({ ...f, gstin: e.target.value })); setGstinError(null); }} maxLength={15} />
              {gstinError && <p className="text-xs text-destructive mt-1">{gstinError}</p>}
            </Field>
            <Field label="PAN"><input className={inputCls} value={form.pan} onChange={set("pan")} maxLength={10} /></Field>
          </div>
        </div>

        <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <SectionTitle icon={Phone} label="Contact" eyebrow="COMMUNICATION" />
          <div className="grid grid-cols-2 gap-4">
            <Field label="Mobile"><input className={inputCls} value={form.mobile} onChange={set("mobile")} /></Field>
            <Field label="WhatsApp"><input className={inputCls} value={form.whatsapp_no} onChange={set("whatsapp_no")} /></Field>
            <Field label="Landline"><input className={inputCls} value={form.landline_no} onChange={set("landline_no")} /></Field>
            <Field label="Email"><input type="email" className={inputCls} value={form.email} onChange={set("email")} /></Field>
            <Field label="Contact Person"><input className={inputCls} value={form.contact_person_name} onChange={set("contact_person_name")} /></Field>
            <Field label="Status">
              <SearchableSelect
                value={form.is_active ? "true" : "false"}
                onChange={(v) => setForm((f) => ({ ...f, is_active: v === "true" }))}
                placeholder="Select status"
                accent="#0049A7"
                options={[
                  { value: "true", label: "Active" },
                  { value: "false", label: "Inactive" },
                ]}
              />
            </Field>
          </div>
        </div>
      </div>
    ),
    address: (
      <div className="space-y-6">
        <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <SectionTitle icon={MapPin} label="Billing Address" eyebrow="ADDRESS" />
          <AddressBlock title="Billing" value={billing} onChange={setBilling} />
        </div>
        <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <SectionTitle icon={MapPin} label="Shipping Address" eyebrow="ADDRESS" />
          <AddressBlock title="Shipping" value={shipping} onChange={setShipping} />
        </div>
      </div>
    ),
    contact: (
      <div className="space-y-6">
        <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <SectionTitle icon={Users} label="Contact Persons" eyebrow="CONTACTS" />
          {contacts.map((c, i) => (
            <div key={i} className="rounded-xl border border-border bg-background p-4 space-y-3 relative">
              <div className="absolute top-3 right-3 flex gap-2">
                <button type="button" onClick={() => setContacts((cs) => cs.map((x, idx) => ({ ...x, is_primary: idx === i })))}
                  className={`text-xs px-2 py-0.5 rounded-full border flex items-center gap-1 ${c.is_primary ? "text-white border-transparent" : "border-input text-muted-foreground"}`}
                  style={c.is_primary ? { background: INDIGO } : {}}>
                  <Star className="h-3 w-3" /> Primary
                </button>
                <button type="button" onClick={() => setContacts((cs) => cs.filter((_, idx) => idx !== i))}
                  className="text-destructive"><Trash2 className="h-4 w-4" /></button>
              </div>
              <div className="grid grid-cols-2 gap-3 pr-28">
                <Field label="Name"><input className={inputCls} value={c.name} onChange={setContact(i, "name")} /></Field>
                <Field label="Designation"><input className={inputCls} value={c.designation} onChange={setContact(i, "designation")} /></Field>
                <Field label="Phone"><input className={inputCls} value={c.phone} onChange={setContact(i, "phone")} /></Field>
                <Field label="Email"><input type="email" className={inputCls} value={c.email} onChange={setContact(i, "email")} /></Field>
              </div>
            </div>
          ))}
          <button type="button" onClick={() => setContacts((cs) => [...cs, { name: "", designation: "", phone: "", email: "", is_primary: false }])}
            className="flex items-center gap-1.5 text-sm text-primary hover:underline">
            <Plus className="h-4 w-4" /> Add Contact Person
          </button>
        </div>

        <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <SectionTitle icon={FileText} label="Additional Details" eyebrow="CUSTOM FIELDS" />
          {details.map((d, i) => (
            <div key={i} className="flex gap-2 items-center">
              <input className={`${inputCls} flex-1`} value={d.label}
                onChange={(e) => setDetails((ds) => ds.map((x, idx) => idx === i ? { ...x, label: e.target.value } : x))} placeholder="Label" />
              <input className={`${inputCls} flex-1`} value={d.value}
                onChange={(e) => setDetails((ds) => ds.map((x, idx) => idx === i ? { ...x, value: e.target.value } : x))} placeholder="Value" />
              <button type="button" onClick={() => setDetails((ds) => ds.filter((_, idx) => idx !== i))}
                className="text-destructive flex-shrink-0"><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
          <button type="button" onClick={() => setDetails((ds) => [...ds, { label: "", value: "", sort_order: ds.length }])}
            className="flex items-center gap-1.5 text-sm text-primary hover:underline">
            <Plus className="h-4 w-4" /> Add Row
          </button>
        </div>
      </div>
    ),
    accounting: (
      <div className="space-y-6">
        <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <SectionTitle icon={CreditCard} label="Credit Terms" eyebrow="ACCOUNTING" />
          <div className="grid grid-cols-2 gap-4">
            <Field label="Credit Limit (₹)"><input type="number" min="0" className={inputCls} value={form.credit_limit} onChange={set("credit_limit")} /></Field>
            <Field label="Credit Days"><input type="number" min="0" className={inputCls} value={form.credit_days} onChange={set("credit_days")} /></Field>
            <Field label="Due Days"><input type="number" min="0" className={inputCls} value={form.due_days} onChange={set("due_days")} /></Field>
            <Field label="Discount %"><input type="number" min="0" max="100" step="0.01" className={inputCls} value={form.discount_percent} onChange={set("discount_percent")} /></Field>
          </div>
        </div>
        <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <SectionTitle icon={CreditCard} label="Opening Balances" eyebrow="BALANCES" />
          <div className="grid grid-cols-2 gap-4">
            <Field label="Receivable (₹)"><input type="number" min="0" className={inputCls} value={form.receivable_opening_balance} onChange={set("receivable_opening_balance")} /></Field>
            <Field label="Payable (₹)"><input type="number" min="0" className={inputCls} value={form.payable_opening_balance} onChange={set("payable_opening_balance")} /></Field>
          </div>
        </div>
        <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <SectionTitle icon={CreditCard} label="Tax" eyebrow="TAX SETTINGS" />
          <div className="grid grid-cols-2 gap-4">
            <Field label="TDS %"><input type="number" min="0" max="100" step="0.01" className={inputCls} value={form.tds_percent} onChange={set("tds_percent")} /></Field>
            <Field label="TCS">
              <div className="flex items-center gap-2 h-[38px]">
                <input type="checkbox" checked={form.enable_tcs} onChange={(e) => setForm((f) => ({ ...f, enable_tcs: e.target.checked }))} className="accent-primary" />
                <label className="text-sm">Enable TCS</label>
              </div>
            </Field>
          </div>
        </div>
      </div>
    ),
    team: (
      <div className="space-y-6">
        <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <SectionTitle icon={Users} label="Team" eyebrow="ASSIGNMENT" />
          <div className="grid grid-cols-2 gap-4">
            {(["sales_person_id", "accounts_manager_id", "agent_id"] as const).map((k) => (
              <Field key={k} label={k === "sales_person_id" ? "Sales Person" : k === "accounts_manager_id" ? "Accounts Manager" : "Agent"}>
                <SearchableSelect
                  value={form[k]}
                  onChange={(v) => setForm((f) => ({ ...f, [k]: v }))}
                  placeholder="— None —"
                  accent="#0049A7"
                  options={[
                    { value: "", label: "— None —" },
                    ...userList.map((u) => ({ value: u.id, label: u.full_name })),
                  ]}
                />
              </Field>
            ))}
            <Field label="Commission %"><input type="number" min="0" max="100" step="0.01" className={inputCls} value={form.agent_commission_percent} onChange={set("agent_commission_percent")} /></Field>
          </div>
        </div>
      </div>
    ),
    extra: (
      <div className="space-y-6">
        <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <SectionTitle icon={Star} label="CRM" eyebrow="ENGAGEMENT" />
          <Field label="Rating">
            <div className="flex gap-1 mt-1">
              {[1, 2, 3, 4, 5].map((n) => (
                <button key={n} type="button" onClick={() => setForm((f) => ({ ...f, customer_rating: n }))}
                  className={`p-1 rounded ${form.customer_rating >= n ? "text-violet-400" : "text-muted-foreground/30"}`}>
                  <Star className="h-6 w-6 fill-current" />
                </button>
              ))}
            </div>
          </Field>
          <div className="flex items-center gap-2">
            <input type="checkbox" checked={form.customer_portal_enabled}
              onChange={(e) => setForm((f) => ({ ...f, customer_portal_enabled: e.target.checked }))} className="accent-primary" />
            <label className="text-sm">Enable Customer Portal</label>
          </div>
          <Field label="Other Details">
            <textarea className={`${inputCls} min-h-[80px] resize-y`} value={form.other_details} onChange={set("other_details")} />
          </Field>
          <Field label="Remarks">
            <textarea className={`${inputCls} min-h-[80px] resize-y`} value={form.remarks} onChange={set("remarks")} />
          </Field>
        </div>
      </div>
    ),
  };

  return (
    <div className="min-h-full bg-background">
      {/* Sticky header */}
      <div className="sticky top-0 z-10 bg-background border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button type="button" onClick={() => router.push("/crm/customers")} className="text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground leading-none">CRM / CUSTOMERS</p>
            <div className="flex items-center gap-2 mt-0.5">
              <Edit2 className="h-4 w-4 text-muted-foreground" />
              <span className="text-base font-semibold leading-tight">{customer.legal_name}</span>
              <span className="text-sm text-muted-foreground">({customer.code})</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {error && <p className="text-xs text-destructive max-w-xs text-right">{error}</p>}
          <button type="button" onClick={() => router.push("/crm/customers")}
            className="px-4 py-1.5 rounded-md border border-input text-sm hover:bg-muted">Cancel</button>
          <button type="button" onClick={() => handleSubmit()} disabled={mut.isPending}
            className="px-4 py-1.5 rounded-xl text-sm font-semibold text-white disabled:opacity-60 flex items-center gap-1.5 transition-all hover:opacity-90 active:scale-95"
            style={{ background: INDIGO }}>
            {mut.isPending ? "Saving…" : <><ChevronRight className="h-4 w-4" /> Save Changes</>}
          </button>
        </div>
      </div>

      <div className="flex">
        {/* Sidebar nav */}
        <nav className="w-48 border-r min-h-[calc(100vh-56px)] p-3 space-y-0.5 flex-shrink-0">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button key={id} type="button" onClick={() => setTab(id)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-colors text-left ${
                tab === id ? "font-medium text-white" : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
              style={tab === id ? { background: `${INDIGO}18`, color: INDIGO } : {}}>
              <Icon className="h-4 w-4 flex-shrink-0" />{label}
            </button>
          ))}
        </nav>

        {/* Form panel */}
        <form onSubmit={handleSubmit} className="flex-1 p-6 max-w-3xl">
          {panels[tab]}
        </form>
      </div>
    </div>
  );
}
