"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  ArrowLeft, X, Phone, Users, StickyNote, CheckSquare, Mail,
  Plus, CheckCircle2, Circle, ShoppingCart, Send, Loader2, Inbox,
  ChevronDown, FileText, Trash2,
} from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { ModalShell } from "@/components/shared/modal-shell";

// ── Palette ───────────────────────────────────────────────────────────────────
const INDIGO = "#0049A7";

const STATUS_HEX: Record<string, string> = {
  open: "#0049A7", won: "#0F78FF", lost: "#1D0DB0",
};

const ACTIVITY_ICONS: Record<string, React.ReactNode> = {
  call: <Phone className="h-3.5 w-3.5" />,
  meeting: <Users className="h-3.5 w-3.5" />,
  note: <StickyNote className="h-3.5 w-3.5" />,
  task: <CheckSquare className="h-3.5 w-3.5" />,
  email: <Mail className="h-3.5 w-3.5" />,
};

const ACTIVITY_COLORS: Record<string, string> = {
  call: "#0049A7", meeting: "#0F78FF", note: "#A096F7",
  task: "#0F78FF", email: "#0049A7",
};

const ACTIVITY_TYPES = ["call", "meeting", "note", "task", "email"] as const;
type ActivityType = typeof ACTIVITY_TYPES[number];

// ── Types ─────────────────────────────────────────────────────────────────────
interface PipelineStage {
  id: string;
  name: string;
  sort_order: number;
  is_won: boolean;
  is_lost: boolean;
  probability: number;
}

interface Pipeline {
  id: string;
  name: string;
  stages: PipelineStage[];
}

interface LookupItem {
  id: string;
  name: string;
}

interface Lead {
  id: string;
  title: string;
  status: string;
  pipeline_id: string | null;
  pipeline_name: string | null;
  stage_id: string | null;
  stage_name: string | null;
  person_id: string | null;
  person_name: string | null;
  org_id: string | null;
  org_name: string | null;
  lead_value: number | null;
  source_id: string | null;
  source_name: string | null;
  type_id: string | null;
  type_name: string | null;
  expected_close_date: string | null;
  tags: string[];
  notes: string | null;
  assigned_to_name: string | null;
  lost_reason: string | null;
}

interface Activity {
  id: string;
  type: string;
  title: string;
  comment: string | null;
  schedule_from: string | null;
  schedule_to: string | null;
  is_done: boolean;
  assigned_to_name: string | null;
}

interface UserOption {
  id: string;
  name: string;
  email: string;
}

interface EmailRecord {
  id: string;
  direction: "inbound" | "outbound";
  subject: string;
  from_address: string;
  to_addresses: string[];
  status: string;
  sent_at: string | null;
  created_at: string;
  body_text?: string;
}

interface AddActivityForm {
  type: ActivityType;
  title: string;
  comment: string;
  schedule_from: string;
  schedule_to: string;
  assigned_to: string;
}

interface ConvertForm {
  customer_id: string;
  order_date: string;
  expected_delivery: string;
  notes: string;
  intrastate: boolean;
}

interface ComposeForm {
  to: string;
  cc: string;
  subject: string;
  body_text: string;
}

const emptyActivityForm = (): AddActivityForm => ({
  type: "call",
  title: "",
  comment: "",
  schedule_from: "",
  schedule_to: "",
  assigned_to: "",
});

const today = () => new Date().toISOString().split("T")[0];

const inputCls =
  "w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

// ── Toast ─────────────────────────────────────────────────────────────────────
let _toastTimeout: ReturnType<typeof setTimeout> | null = null;

function showToast(msg: string | React.ReactNode) {
  // We use a simple DOM toast since we don't have a toast library imported
  const div = document.createElement("div");
  div.style.cssText = [
    "position:fixed", "bottom:24px", "right:24px", "z-index:9999",
    "background:#1e293b", "color:#f8fafc", "border-radius:14px",
    "padding:12px 18px", "font-size:13px", "box-shadow:0 4px 24px rgba(0,0,0,.3)",
    "max-width:380px", "line-height:1.5",
  ].join(";");
  div.textContent = typeof msg === "string" ? msg : "";
  document.body.appendChild(div);
  if (_toastTimeout) clearTimeout(_toastTimeout);
  _toastTimeout = setTimeout(() => div.remove(), 5000);
}

// ── StatusBadge ───────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const color = STATUS_HEX[status?.toLowerCase()] ?? "#94A3B8";
  const label = status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
      style={{ background: `${color}18`, color }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}

// ── ConvertLeadModal ──────────────────────────────────────────────────────────
function ConvertLeadModal({
  leadId,
  onClose,
  markWonFirst,
}: {
  leadId: string;
  onClose: () => void;
  markWonFirst?: boolean;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ConvertForm>({
    customer_id: "",
    order_date: today(),
    expected_delivery: "",
    notes: "",
    intrastate: true,
  });
  const { data: customersData } = useQuery({
    queryKey: ["sales-customers"],
    queryFn: async () => {
      const res = await api.get("/api/v1/sales/customers?search=");
      return res.data;
    },
  });

  const customerOptions = (customersData?.data ?? []).map(
    (c: { id: string; legal_name: string; code: string }) => ({
      value: c.id,
      label: `${c.legal_name} (${c.code})`,
    })
  );

  const wonMutation = useMutation({
    mutationFn: () => api.patch(`/crm/leads/${leadId}/status`, { status: "won" }),
  });

  const convertMutation = useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      if (markWonFirst) {
        await wonMutation.mutateAsync();
      }
      const res = await api.post(`/crm/leads/${leadId}/convert`, body);
      return res.data;
    },
    onSuccess: (data) => {
      const orderNumber = data?.data?.order_number ?? "";
      queryClient.invalidateQueries({ queryKey: ["crm-lead", leadId] });
      showToast(
        `Sales Order ${orderNumber} created successfully. Go to Sales → Orders to add products.`
      );
      onClose();
    },
  });

  function set<K extends keyof ConvertForm>(k: K, v: ConvertForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function handleSubmit() {
    if (!form.customer_id) return;
    convertMutation.mutate({
      customer_id: form.customer_id,
      order_date: form.order_date,
      expected_delivery: form.expected_delivery || undefined,
      notes: form.notes || undefined,
      intrastate: form.intrastate,
    });
  }

  return (
    <ModalShell maxWidth="max-w-lg" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-lg font-semibold">Convert to Sales Order</h2>
            {markWonFirst && (
              <p className="text-xs text-muted-foreground mt-0.5">Lead will be marked Won and converted</p>
            )}
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          {/* Customer */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Customer <span className="text-destructive">*</span>
            </label>
            <SearchableSelect
              options={customerOptions}
              value={form.customer_id}
              onChange={(v) => set("customer_id", v)}
              placeholder="Search customer…"
              accent={INDIGO}
            />
          </div>

          {/* Order Date */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Order Date <span className="text-destructive">*</span>
            </label>
            <input
              type="date"
              className={inputCls}
              value={form.order_date}
              onChange={(e) => set("order_date", e.target.value)}
            />
          </div>

          {/* Expected Delivery */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Expected Delivery <span className="text-muted-foreground font-normal">(optional)</span>
            </label>
            <input
              type="date"
              className={inputCls}
              value={form.expected_delivery}
              onChange={(e) => set("expected_delivery", e.target.value)}
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
            <textarea
              className={`${inputCls} resize-none`}
              rows={3}
              placeholder="Order notes…"
              value={form.notes}
              onChange={(e) => set("notes", e.target.value)}
            />
          </div>

          {/* Intrastate */}
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="text-sm font-medium">Intrastate</p>
              <p className="text-xs text-muted-foreground">Same state (affects GST calculation)</p>
            </div>
            <button
              type="button"
              onClick={() => set("intrastate", !form.intrastate)}
              className="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none"
              style={{ background: form.intrastate ? INDIGO : "#E2E8F0" }}
            >
              <span
                className="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform"
                style={{ transform: form.intrastate ? "translateX(22px)" : "translateX(2px)" }}
              />
            </button>
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!form.customer_id || convertMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
            style={{ background: INDIGO }}
          >
            {convertMutation.isPending ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Converting…</>
            ) : (
              <><ShoppingCart className="h-4 w-4" /> Convert to Sales Order</>
            )}
          </button>
        </div>
    </ModalShell>
  );
}

// ── EmailTemplate type (for template picker) ──────────────────────────────────
interface EmailTemplateOption {
  id: string;
  name: string;
  subject: string;
  body_text: string;
  category: string;
  is_active: boolean;
}

// ── ComposeEmailModal ─────────────────────────────────────────────────────────
function ComposeEmailModal({
  leadId,
  personId,
  onClose,
}: {
  leadId?: string;
  personId?: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ComposeForm>({ to: "", cc: "", subject: "", body_text: "" });
  const [smtpError, setSmtpError] = useState("");
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);

  // Fetch active email templates (cached)
  const { data: templatesData } = useQuery({
    queryKey: ["crm-email-templates-active"],
    queryFn: async () => {
      const res = await api.get("/crm/email-templates?is_active=true");
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });
  const emailTemplates: EmailTemplateOption[] = templatesData?.data ?? [];

  function set<K extends keyof ComposeForm>(k: K, v: ComposeForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function applyTemplate(tpl: EmailTemplateOption) {
    setForm((f) => ({ ...f, subject: tpl.subject, body_text: tpl.body_text }));
    setShowTemplatePicker(false);
  }

  const sendMutation = useMutation({
    mutationFn: async () => {
      const toAddresses = form.to.split(",").map((s) => s.trim()).filter(Boolean);
      const ccAddresses = form.cc.split(",").map((s) => s.trim()).filter(Boolean);
      const res = await api.post("/crm/emails", {
        subject: form.subject,
        body_text: form.body_text,
        to_addresses: toAddresses,
        cc_addresses: ccAddresses.length ? ccAddresses : undefined,
        lead_id: leadId ?? undefined,
        person_id: personId ?? undefined,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-emails", leadId] });
      showToast("Email sent successfully.");
      onClose();
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "";
      if (msg.toLowerCase().includes("smtp") || msg.toLowerCase().includes("not configured")) {
        setSmtpError("Please configure SMTP settings in CRM Settings first.");
      } else {
        setSmtpError(msg || "Failed to send email.");
      }
    },
  });

  return (
    <ModalShell maxWidth="max-w-lg" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold">Compose Email</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          {smtpError && (
            <div className="rounded-xl bg-violet-50 border border-violet-200 p-3 text-sm text-violet-700 flex items-start gap-2">
              <X className="h-4 w-4 shrink-0 mt-0.5" />
              <span>
                {smtpError}{" "}
                {smtpError.includes("SMTP") && (
                  <Link href="/crm/settings" className="underline font-semibold" style={{ color: INDIGO }}>
                    Go to Settings
                  </Link>
                )}
              </span>
            </div>
          )}

          {/* Template picker */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowTemplatePicker((v) => !v)}
              className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border border-input hover:bg-muted transition-colors"
              style={{ color: INDIGO }}
            >
              <FileText className="h-3.5 w-3.5" />
              Use Template
              <ChevronDown className="h-3 w-3 text-muted-foreground" />
            </button>
            {showTemplatePicker && (
              <div className="absolute top-full mt-1 left-0 w-72 bg-card border border-border rounded-xl shadow-2xl z-50 max-h-60 overflow-y-auto py-1">
                {emailTemplates.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-4">
                    No active templates — create one in Settings.
                  </p>
                ) : (
                  emailTemplates.map((tpl) => (
                    <button
                      key={tpl.id}
                      type="button"
                      onClick={() => applyTemplate(tpl)}
                      className="w-full text-left px-4 py-2.5 hover:bg-muted/50 transition-colors"
                    >
                      <p className="text-sm font-medium">{tpl.name}</p>
                      <p className="text-xs text-muted-foreground truncate">{tpl.subject}</p>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              To <span className="text-destructive">*</span>
            </label>
            <input
              className={inputCls}
              placeholder="email@example.com, another@example.com"
              value={form.to}
              onChange={(e) => set("to", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">CC</label>
            <input
              className={inputCls}
              placeholder="cc@example.com"
              value={form.cc}
              onChange={(e) => set("cc", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Subject <span className="text-destructive">*</span>
            </label>
            <input
              className={inputCls}
              placeholder="Subject…"
              value={form.subject}
              onChange={(e) => set("subject", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Body <span className="text-destructive">*</span>
            </label>
            <textarea
              className={`${inputCls} resize-none`}
              rows={6}
              placeholder="Write your message…"
              value={form.body_text}
              onChange={(e) => set("body_text", e.target.value)}
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => sendMutation.mutate()}
            disabled={!form.to.trim() || !form.subject.trim() || !form.body_text.trim() || sendMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
            style={{ background: INDIGO }}
          >
            {sendMutation.isPending ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Sending…</>
            ) : (
              <><Send className="h-4 w-4" /> Send</>
            )}
          </button>
        </div>
    </ModalShell>
  );
}

// ── EmailCard ─────────────────────────────────────────────────────────────────
function EmailCard({ email }: { email: EmailRecord }) {
  const isOut = email.direction === "outbound";
  const ts = email.sent_at ?? email.created_at;
  return (
    <div
      className={`flex ${isOut ? "justify-end" : "justify-start"} mb-3`}
    >
      <div
        className={`w-full max-w-[90%] rounded-xl border p-4 ${
          isOut
            ? "border-l-4 bg-card"
            : "border-l-4 bg-muted/30"
        }`}
        style={{ borderLeftColor: isOut ? INDIGO : "#94A3B8" }}
      >
        <div className="flex items-start justify-between gap-3 mb-1.5">
          <p className="text-sm font-semibold truncate flex-1">{email.subject}</p>
          <span
            className="text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0"
            style={
              isOut
                ? { background: `${INDIGO}14`, color: INDIGO }
                : { background: "#94A3B820", color: "#64748B" }
            }
          >
            {isOut ? "Sent" : "Received"}
          </span>
        </div>
        <p className="text-xs text-muted-foreground mb-1">
          {isOut
            ? `To: ${email.to_addresses.join(", ")}`
            : `From: ${email.from_address}`}
        </p>
        {email.body_text && (
          <p className="text-sm text-muted-foreground leading-relaxed">
            {email.body_text.slice(0, 100)}{email.body_text.length > 100 ? "…" : ""}
          </p>
        )}
        <p className="text-[11px] text-muted-foreground mt-2">
          {new Date(ts).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
        </p>
      </div>
    </div>
  );
}

// ── Add Activity Modal ─────────────────────────────────────────────────────────
function AddActivityModal({
  leadId,
  onClose,
}: {
  leadId: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<AddActivityForm>(emptyActivityForm());

  const { data: usersData } = useQuery({
    queryKey: ["crm-admin-users"],
    queryFn: () => api.get("/admin/users?page_size=200").then((r) => r.data),
  });
  const users: UserOption[] = usersData?.data ?? [];

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post("/crm/activities", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-activities", leadId] });
      onClose();
    },
  });

  function set<K extends keyof AddActivityForm>(k: K, v: AddActivityForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function handleSubmit() {
    if (!form.title.trim()) return;
    mutation.mutate({
      type: form.type,
      title: form.title,
      comment: form.comment || undefined,
      schedule_from: form.schedule_from || undefined,
      schedule_to: form.schedule_to || undefined,
      assigned_to: form.assigned_to || undefined,
      lead_id: leadId,
    });
  }

  return (
    <ModalShell maxWidth="max-w-md" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold">Add Activity</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-2">Type</label>
            <div className="flex flex-wrap gap-2">
              {ACTIVITY_TYPES.map((t) => {
                const color = ACTIVITY_COLORS[t];
                const isActive = form.type === t;
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => set("type", t)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all duration-150"
                    style={{
                      borderColor: isActive ? color : "hsl(var(--border))",
                      background: isActive ? `${color}18` : "transparent",
                      color: isActive ? color : "hsl(var(--muted-foreground))",
                    }}
                  >
                    {ACTIVITY_ICONS[t]}
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                );
              })}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Title <span className="text-destructive">*</span>
            </label>
            <input
              className={inputCls}
              placeholder="Activity title…"
              value={form.title}
              onChange={(e) => set("title", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Comment</label>
            <textarea
              className={`${inputCls} resize-none`}
              rows={3}
              placeholder="Notes or details…"
              value={form.comment}
              onChange={(e) => set("comment", e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Schedule From</label>
              <input
                className={inputCls}
                type="datetime-local"
                value={form.schedule_from}
                onChange={(e) => set("schedule_from", e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Schedule To</label>
              <input
                className={inputCls}
                type="datetime-local"
                value={form.schedule_to}
                onChange={(e) => set("schedule_to", e.target.value)}
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Assign To</label>
            <SearchableSelect
              options={users.map((u) => ({ value: u.id, label: u.name }))}
              value={form.assigned_to}
              onChange={(v) => set("assigned_to", v)}
              placeholder="Unassigned"
              accent={INDIGO}
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!form.title.trim() || mutation.isPending}
            className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
            style={{ background: INDIGO }}
          >
            {mutation.isPending ? "Saving…" : "Save Activity"}
          </button>
        </div>
    </ModalShell>
  );
}

// ── Mark Lost Modal ───────────────────────────────────────────────────────────
function MarkLostModal({
  leadId,
  onClose,
}: {
  leadId: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.patch(`/crm/leads/${leadId}/status`, { status: "lost", lost_reason: reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-lead", leadId] });
      onClose();
    },
  });

  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold">Mark as Lost</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-6">
          <label className="block text-xs font-medium text-muted-foreground mb-1">Lost Reason (optional)</label>
          <textarea
            className={`${inputCls} resize-none`}
            rows={3}
            placeholder="Why was this lead lost?"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
        <div className="flex justify-end gap-3 p-6 border-t">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="px-4 py-2 text-sm rounded-xl text-white font-semibold bg-violet-500 hover:bg-violet-600 transition-colors disabled:opacity-50"
          >
            {mutation.isPending ? "Marking…" : "Mark Lost"}
          </button>
        </div>
    </ModalShell>
  );
}

// ── Activity Item ─────────────────────────────────────────────────────────────
function ActivityItem({ activity, leadId }: { activity: Activity; leadId: string }) {
  const queryClient = useQueryClient();
  const color = ACTIVITY_COLORS[activity.type] ?? INDIGO;
  const icon = ACTIVITY_ICONS[activity.type] ?? <CheckSquare className="h-3.5 w-3.5" />;

  const doneMutation = useMutation({
    mutationFn: (done: boolean) => api.patch(`/crm/activities/${activity.id}/done`, { is_done: done }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["crm-activities", leadId] }),
  });

  return (
    <div className="flex gap-3 py-3 border-b border-border last:border-0">
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
        style={{ background: `${color}18`, color }}
      >
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium">{activity.title}</p>
          <button
            onClick={() => doneMutation.mutate(!activity.is_done)}
            disabled={doneMutation.isPending}
            className="flex-shrink-0 p-0.5 rounded transition-colors hover:bg-muted disabled:cursor-default disabled:opacity-50"
            title={activity.is_done ? "Mark not done" : "Mark done"}
          >
            {activity.is_done ? (
              <CheckCircle2 className="h-4 w-4 text-blue-500" />
            ) : (
              <Circle className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
        </div>
        {activity.comment && (
          <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{activity.comment}</p>
        )}
        <div className="flex flex-wrap gap-3 mt-1">
          {activity.schedule_from && (
            <p className="text-[11px] text-muted-foreground">
              {new Date(activity.schedule_from).toLocaleString("en-IN", {
                dateStyle: "medium",
                timeStyle: "short",
              })}
            </p>
          )}
          {activity.assigned_to_name && (
            <p className="text-[11px] text-muted-foreground">→ {activity.assigned_to_name}</p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function LeadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [showAddActivity, setShowAddActivity] = useState(false);
  const [showMarkLost, setShowMarkLost] = useState(false);
  const [showConvert, setShowConvert] = useState(false);
  const [convertMarkWon, setConvertMarkWon] = useState(false);
  const [showCompose, setShowCompose] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [activeTab, setActiveTab] = useState<"activities" | "emails">("activities");
  const [editingField, setEditingField] = useState<string | null>(null);

  // ── Data fetches ────────────────────────────────────────────────────────────
  const { data: leadData, isLoading } = useQuery({
    queryKey: ["crm-lead", id],
    queryFn: async () => {
      const res = await api.get(`/crm/leads/${id}`);
      return res.data;
    },
  });

  const { data: activitiesData } = useQuery({
    queryKey: ["crm-activities", id],
    queryFn: async () => {
      const res = await api.get(`/crm/activities?lead_id=${id}`);
      return res.data;
    },
  });

  const { data: emailsData } = useQuery({
    queryKey: ["crm-emails", id],
    queryFn: async () => {
      const res = await api.get(`/crm/emails?lead_id=${id}`);
      return res.data;
    },
    enabled: activeTab === "emails",
  });

  const { data: pipelinesData } = useQuery({
    queryKey: ["crm-pipelines"],
    queryFn: async () => {
      const res = await api.get("/crm/pipelines");
      return res.data;
    },
  });

  const { data: sourcesData } = useQuery({
    queryKey: ["crm-lead-sources"],
    queryFn: async () => {
      const res = await api.get("/crm/lead-sources");
      return res.data;
    },
  });

  const { data: typesData } = useQuery({
    queryKey: ["crm-lead-types"],
    queryFn: async () => {
      const res = await api.get("/crm/lead-types");
      return res.data;
    },
  });

  // ── Update mutation ──────────────────────────────────────────────────────────
  const updateMutation = useMutation({
    mutationFn: (patch: Record<string, unknown>) => api.patch(`/crm/leads/${id}`, patch),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-lead", id] });
      setEditingField(null);
    },
  });

  // ── Delete mutation ──────────────────────────────────────────────────────────
  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/crm/leads/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-leads"] });
      router.push("/crm/leads");
    },
  });

  const lead: Lead | null = leadData?.data ?? null;
  const activities: Activity[] = activitiesData?.data ?? [];
  const emails: EmailRecord[] = emailsData?.data ?? [];
  const pipelines: Pipeline[] = pipelinesData?.data ?? [];
  const sources: LookupItem[] = sourcesData?.data ?? [];
  const types: LookupItem[] = typesData?.data ?? [];

  const selectedPipeline = pipelines.find((p) => p.id === lead?.pipeline_id) ?? null;
  const stageOptions = selectedPipeline?.stages.map((s) => ({ value: s.id, label: s.name })) ?? [];

  if (isLoading) {
    return (
      <div className="p-8 text-muted-foreground text-sm">Loading…</div>
    );
  }

  if (!lead) {
    return (
      <div className="p-8 text-muted-foreground text-sm">Lead not found.</div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <button
          onClick={() => router.push("/crm/leads")}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Leads
        </button>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
              CRM / LEADS
            </p>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold tracking-tight">{lead.title}</h1>
              <StatusBadge status={lead.status} />
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {lead.status === "open" && (
              <>
                <button
                  onClick={() => {
                    setConvertMarkWon(true);
                    setShowConvert(true);
                  }}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-blue-500 hover:bg-blue-600 transition-colors"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Mark Won
                </button>
                <button
                  onClick={() => setShowMarkLost(true)}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-violet-500 hover:bg-violet-600 transition-colors"
                >
                  <X className="h-4 w-4" />
                  Mark Lost
                </button>
              </>
            )}
            {lead.status === "won" && (
              <button
                onClick={() => {
                  setConvertMarkWon(false);
                  setShowConvert(true);
                }}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90"
                style={{ background: INDIGO }}
              >
                <ShoppingCart className="h-4 w-4" />
                Convert to Sales Order
              </button>
            )}
            <button
              onClick={() => setConfirmDelete(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-violet-500 border border-violet-200 hover:bg-violet-50 transition-colors"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </button>
          </div>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Left — Details */}
        <div className="lg:col-span-3 space-y-6">
          <div className="bg-card border border-border rounded-2xl p-6 space-y-5">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              Lead Details
            </p>

            {/* Pipeline & Stage */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Stage</label>
              <SearchableSelect
                options={stageOptions}
                value={lead.stage_id ?? ""}
                onChange={(v) => {
                  const pipeline = pipelines.find((p) =>
                    p.stages.some((s) => s.id === v)
                  );
                  updateMutation.mutate({
                    stage_id: v,
                    pipeline_id: pipeline?.id ?? lead.pipeline_id,
                  });
                }}
                placeholder="Select stage…"
                accent={INDIGO}
              />
            </div>

            {/* Value */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Lead Value (₹)</label>
              {editingField === "lead_value" ? (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const val = (e.currentTarget.elements.namedItem("val") as HTMLInputElement).value;
                    updateMutation.mutate({ lead_value: val ? parseFloat(val) : null });
                  }}
                  className="flex gap-2"
                >
                  <input
                    name="val"
                    defaultValue={lead.lead_value ?? ""}
                    type="number"
                    className="flex-1 rounded-xl border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    autoFocus
                  />
                  <button type="submit" className="px-3 py-2 text-sm rounded-xl text-white" style={{ background: INDIGO }}>
                    Save
                  </button>
                  <button type="button" onClick={() => setEditingField(null)} className="px-3 py-2 text-sm rounded-xl border">
                    Cancel
                  </button>
                </form>
              ) : (
                <button
                  onClick={() => setEditingField("lead_value")}
                  className="text-sm text-left w-full px-3 py-2 rounded-xl border border-transparent hover:border-input hover:bg-muted/30 transition-all"
                >
                  {lead.lead_value ? `₹${lead.lead_value.toLocaleString("en-IN")}` : <span className="text-muted-foreground">Click to set value…</span>}
                </button>
              )}
            </div>

            {/* Person */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Person</label>
              <p className="text-sm px-3 py-2">{lead.person_name ?? "—"}</p>
            </div>

            {/* Organization */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Organization</label>
              <p className="text-sm px-3 py-2">{lead.org_name ?? "—"}</p>
            </div>

            {/* Source */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Source</label>
              <SearchableSelect
                options={sources.map((s) => ({ value: s.id, label: s.name }))}
                value={lead.source_id ?? ""}
                onChange={(v) => updateMutation.mutate({ source_id: v })}
                placeholder="Select source…"
                accent={INDIGO}
              />
            </div>

            {/* Type */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Type</label>
              <SearchableSelect
                options={types.map((t) => ({ value: t.id, label: t.name }))}
                value={lead.type_id ?? ""}
                onChange={(v) => updateMutation.mutate({ type_id: v })}
                placeholder="Select type…"
                accent={INDIGO}
              />
            </div>

            {/* Expected Close Date */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Expected Close Date</label>
              <input
                type="date"
                defaultValue={lead.expected_close_date ?? ""}
                onBlur={(e) => {
                  if (e.target.value !== (lead.expected_close_date ?? "")) {
                    updateMutation.mutate({ expected_close_date: e.target.value || null });
                  }
                }}
                className="w-full rounded-xl border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            {/* Tags */}
            {lead.tags && lead.tags.length > 0 && (
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-2">Tags</label>
                <div className="flex flex-wrap gap-2">
                  {lead.tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold"
                      style={{ background: `${INDIGO}14`, color: INDIGO }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Notes */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
              {editingField === "notes" ? (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const val = (e.currentTarget.elements.namedItem("notes") as HTMLTextAreaElement).value;
                    updateMutation.mutate({ notes: val });
                  }}
                >
                  <textarea
                    name="notes"
                    defaultValue={lead.notes ?? ""}
                    rows={4}
                    className="w-full rounded-xl border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none mb-2"
                    autoFocus
                  />
                  <div className="flex gap-2">
                    <button type="submit" className="px-3 py-1.5 text-sm rounded-xl text-white" style={{ background: INDIGO }}>
                      Save
                    </button>
                    <button type="button" onClick={() => setEditingField(null)} className="px-3 py-1.5 text-sm rounded-xl border">
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <button
                  onClick={() => setEditingField("notes")}
                  className="text-sm text-left w-full px-3 py-2 rounded-xl border border-transparent hover:border-input hover:bg-muted/30 transition-all whitespace-pre-wrap"
                >
                  {lead.notes ? lead.notes : <span className="text-muted-foreground">Click to add notes…</span>}
                </button>
              )}
            </div>

            {/* Lost reason (if lost) */}
            {lead.status === "lost" && lead.lost_reason && (
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Lost Reason</label>
                <p className="text-sm px-3 py-2 text-violet-500">{lead.lost_reason}</p>
              </div>
            )}
          </div>
        </div>

        {/* Right — Activities / Emails tab panel */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-card border border-border rounded-2xl p-6">
            {/* Tab switcher */}
            <div className="flex items-center gap-1 mb-4 bg-muted/50 rounded-xl p-1">
              <button
                onClick={() => setActiveTab("activities")}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                style={
                  activeTab === "activities"
                    ? { background: "hsl(var(--card))", color: INDIGO, boxShadow: "0 1px 3px rgba(0,0,0,.08)" }
                    : { color: "hsl(var(--muted-foreground))" }
                }
              >
                <CheckSquare className="h-3.5 w-3.5" />
                Activities
              </button>
              <button
                onClick={() => setActiveTab("emails")}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                style={
                  activeTab === "emails"
                    ? { background: "hsl(var(--card))", color: INDIGO, boxShadow: "0 1px 3px rgba(0,0,0,.08)" }
                    : { color: "hsl(var(--muted-foreground))" }
                }
              >
                <Mail className="h-3.5 w-3.5" />
                Emails
              </button>
            </div>

            {/* Activities tab */}
            {activeTab === "activities" && (
              <>
                <div className="flex items-center justify-between mb-4">
                  <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                    Activity Timeline
                  </p>
                  <button
                    onClick={() => setShowAddActivity(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white transition-all hover:opacity-90"
                    style={{ background: INDIGO }}
                  >
                    <Plus className="h-3.5 w-3.5" /> Add
                  </button>
                </div>
                {activities.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No activities yet — click Add to log one.
                  </p>
                ) : (
                  <div>
                    {activities.map((a) => (
                      <ActivityItem key={a.id} activity={a} leadId={id} />
                    ))}
                  </div>
                )}
              </>
            )}

            {/* Emails tab */}
            {activeTab === "emails" && (
              <>
                <div className="flex items-center justify-between mb-4">
                  <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                    Email Thread
                  </p>
                  <button
                    onClick={() => setShowCompose(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white transition-all hover:opacity-90"
                    style={{ background: INDIGO }}
                  >
                    <Plus className="h-3.5 w-3.5" /> Compose
                  </button>
                </div>
                {emails.length === 0 ? (
                  <div className="text-center py-10">
                    <Inbox className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
                    <p className="text-sm text-muted-foreground">
                      No emails yet — click Compose to send one.
                    </p>
                  </div>
                ) : (
                  <div>
                    {emails.map((e) => (
                      <EmailCard key={e.id} email={e} />
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Modals */}
      {showAddActivity && (
        <AddActivityModal leadId={id} onClose={() => setShowAddActivity(false)} />
      )}
      {showMarkLost && (
        <MarkLostModal leadId={id} onClose={() => setShowMarkLost(false)} />
      )}
      {showConvert && (
        <ConvertLeadModal
          leadId={id}
          markWonFirst={convertMarkWon}
          onClose={() => setShowConvert(false)}
        />
      )}
      {showCompose && (
        <ComposeEmailModal
          leadId={id}
          onClose={() => setShowCompose(false)}
        />
      )}
      {confirmDelete && (
        <ModalShell maxWidth="max-w-xs" onClose={() => setConfirmDelete(false)}>
          <div className="p-6">
            <p className="text-sm font-medium mb-1">Delete this lead?</p>
            <p className="text-xs text-muted-foreground mb-5">This action cannot be undone.</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDelete(false)}
                className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 text-sm rounded-xl text-white font-semibold bg-violet-500 hover:bg-violet-600 transition-colors disabled:opacity-50"
              >
                {deleteMutation.isPending ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </ModalShell>
      )}
    </div>
  );
}
