"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Settings, CheckCircle2, XCircle, Loader2, Eye, EyeOff, X,
  Mail, Plus, Pencil, Trash2, Globe,
} from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { ModalShell } from "@/components/shared/modal-shell";

// ── Palette ───────────────────────────────────────────────────────────────────
const INDIGO = "#0049A7";

// ── Types ─────────────────────────────────────────────────────────────────────
interface SmtpConfig {
  host: string;
  port: number;
  username: string;
  from_name: string;
  from_email: string;
  use_tls: boolean;
  is_verified: boolean;
}

interface SmtpForm {
  host: string;
  port: string;
  username: string;
  password: string;
  from_name: string;
  from_email: string;
  use_tls: boolean;
}

interface EmailTemplate {
  id: string;
  name: string;
  subject: string;
  body_text: string;
  category: string;
  is_active: boolean;
}

interface TemplateForm {
  name: string;
  category: string;
  subject: string;
  body_text: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const inputCls =
  "w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

const emptySmtpForm = (): SmtpForm => ({
  host: "",
  port: "587",
  username: "",
  password: "",
  from_name: "",
  from_email: "",
  use_tls: true,
});

const emptyTemplateForm = (): TemplateForm => ({
  name: "",
  category: "",
  subject: "",
  body_text: "",
});

const TEMPLATE_CATEGORIES = [
  { value: "intro", label: "Introduction" },
  { value: "follow-up", label: "Follow-up" },
  { value: "quote", label: "Quote" },
  { value: "closing", label: "Closing" },
];

const CATEGORY_COLORS: Record<string, string> = {
  intro: "#0049A7",
  "follow-up": "#0F78FF",
  quote: "#A096F7",
  closing: "#0F78FF",
};

function CategoryBadge({ category }: { category: string }) {
  const color = CATEGORY_COLORS[category] ?? "#94A3B8";
  const label = TEMPLATE_CATEGORIES.find((c) => c.value === category)?.label ?? category;
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"
      style={{ background: `${color}18`, color }}
    >
      {label}
    </span>
  );
}

// ── TemplateFormModal ─────────────────────────────────────────────────────────
interface LeadSource {
  id: string;
  name: string;
}

function LeadSourceFormModal({
  initial,
  onClose,
  onSaved,
}: {
  initial?: LeadSource;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: async () => {
      if (initial) {
        await api.patch(`/crm/lead-sources/${initial.id}`, { name });
      } else {
        await api.post("/crm/lead-sources", { name });
      }
    },
    onSuccess: () => {
      onSaved();
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Failed to save source");
    },
  });

  return (
    <ModalShell maxWidth="max-w-sm" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">{initial ? "Rename Source" : "New Source / Platform"}</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-3">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Name <span className="text-destructive">*</span>
          </label>
          <input
            className="w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="e.g. Instagram, IndiaMART, Trade Show"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => { setError(""); mutation.mutate(); }}
          disabled={!name.trim() || mutation.isPending}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </ModalShell>
  );
}

function TemplateFormModal({
  initial,
  onClose,
  onSaved,
}: {
  initial?: EmailTemplate;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<TemplateForm>(
    initial
      ? {
          name: initial.name,
          category: initial.category,
          subject: initial.subject,
          body_text: initial.body_text,
        }
      : emptyTemplateForm()
  );

  const mutation = useMutation({
    mutationFn: async () => {
      if (initial) {
        await api.patch(`/crm/email-templates/${initial.id}`, form);
      } else {
        await api.post("/crm/email-templates", form);
      }
    },
    onSuccess: () => {
      onSaved();
      onClose();
    },
  });

  function set<K extends keyof TemplateForm>(k: K, v: TemplateForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  const canSave = form.name.trim() && form.subject.trim() && form.body_text.trim();

  return (
    <ModalShell maxWidth="max-w-lg" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold">
            {initial ? "Edit Template" : "New Template"}
          </h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Name <span className="text-destructive">*</span>
            </label>
            <input
              className={inputCls}
              placeholder="Template name…"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Category
            </label>
            <SearchableSelect
              options={TEMPLATE_CATEGORIES}
              value={form.category}
              onChange={(v) => set("category", v)}
              placeholder="Select category…"
              accent={INDIGO}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Subject <span className="text-destructive">*</span>
            </label>
            <input
              className={inputCls}
              placeholder="Email subject…"
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
              rows={8}
              placeholder="Email body…"
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
            onClick={() => mutation.mutate()}
            disabled={!canSave || mutation.isPending}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
            style={{ background: INDIGO }}
          >
            {mutation.isPending ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Saving…</>
            ) : (
              "Save Template"
            )}
          </button>
        </div>
    </ModalShell>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function CRMSettingsPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<SmtpForm>(emptySmtpForm());
  const [showPassword, setShowPassword] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Template modal state
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<EmailTemplate | undefined>(undefined);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // ── Fetch SMTP config ──────────────────────────────────────────────────────
  const { data: configData, isLoading } = useQuery({
    queryKey: ["crm-smtp-config"],
    queryFn: async () => {
      const res = await api.get("/crm/email/smtp-config");
      return res.data;
    },
  });

  const config: SmtpConfig | null = configData?.data ?? null;

  useEffect(() => {
    if (config) {
      setForm({
        host: config.host ?? "",
        port: String(config.port ?? 587),
        username: config.username ?? "",
        password: "••••••••",
        from_name: config.from_name ?? "",
        from_email: config.from_email ?? "",
        use_tls: config.use_tls ?? true,
      });
    }
  }, [config]);

  function set<K extends keyof SmtpForm>(k: K, v: SmtpForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
    setSaveSuccess(false);
    setTestResult(null);
  }

  // ── Fetch templates ────────────────────────────────────────────────────────
  const { data: templatesData, isLoading: templatesLoading } = useQuery({
    queryKey: ["crm-email-templates"],
    queryFn: async () => {
      const res = await api.get("/crm/email-templates");
      return res.data;
    },
  });
  const templates: EmailTemplate[] = templatesData?.data ?? [];

  // ── SMTP mutations ─────────────────────────────────────────────────────────
  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {
        host: form.host,
        port: parseInt(form.port, 10),
        username: form.username,
        from_name: form.from_name,
        from_email: form.from_email,
        use_tls: form.use_tls,
      };
      if (form.password && form.password !== "••••••••") {
        payload.password = form.password;
      }
      const res = await api.post("/crm/email/smtp-config", payload);
      return res.data;
    },
    onSuccess: () => {
      setSaveSuccess(true);
      setTestResult(null);
    },
  });

  const testMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post("/crm/email/smtp-config/test");
      return res.data;
    },
    onSuccess: (data) => {
      setTestResult(data?.data ?? { success: false, message: "Unknown result" });
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Connection test failed";
      setTestResult({ success: false, message: msg });
    },
  });

  // ── Template mutations ─────────────────────────────────────────────────────
  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.patch(`/crm/email-templates/${id}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["crm-email-templates"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/crm/email-templates/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["crm-email-templates"] }),
  });

  // ── Lead Sources / Platforms ───────────────────────────────────────────────
  const [showSourceModal, setShowSourceModal] = useState(false);
  const [editingSource, setEditingSource] = useState<LeadSource | undefined>(undefined);
  const [confirmDeleteSourceId, setConfirmDeleteSourceId] = useState<string | null>(null);
  const [sourceDeleteError, setSourceDeleteError] = useState("");

  const { data: sourcesData, isLoading: sourcesLoading } = useQuery({
    queryKey: ["crm-lead-sources"],
    queryFn: async () => {
      const res = await api.get("/crm/lead-sources");
      return res.data;
    },
  });
  const sources: LeadSource[] = sourcesData?.data ?? [];

  const deleteSourceMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/crm/lead-sources/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-lead-sources"] });
      setSourceDeleteError("");
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setSourceDeleteError(typeof msg === "string" ? msg : "Failed to delete source");
    },
  });

  return (
    <div className="p-8 max-w-2xl space-y-8">
      {/* Page header */}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          CRM / SETTINGS
        </p>
        <div className="flex items-center gap-2.5">
          <Settings className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-2xl font-bold tracking-tight">CRM Settings</h1>
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          Configure SMTP and CRM preferences
        </p>
      </div>

      {/* ── SMTP Section ─────────────────────────────────────────────────────── */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <p className="font-semibold">Email (SMTP) Settings</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Configure outbound email delivery for CRM communications
            </p>
          </div>
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : config ? (
            <span
              className="flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full"
              style={{ background: "#0F78FF18", color: "#0F78FF" }}
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              Configured
            </span>
          ) : (
            <span
              className="flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full"
              style={{ background: "#94A3B818", color: "#64748B" }}
            >
              <X className="h-3.5 w-3.5" />
              Not configured
            </span>
          )}
        </div>

        <div className="p-6 space-y-5">
          {/* Host + Port */}
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-muted-foreground mb-1">
                SMTP Host <span className="text-destructive">*</span>
              </label>
              <input
                className={inputCls}
                placeholder="smtp.gmail.com"
                value={form.host}
                onChange={(e) => set("host", e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Port</label>
              <input
                className={inputCls}
                type="number"
                placeholder="587"
                value={form.port}
                onChange={(e) => set("port", e.target.value)}
              />
            </div>
          </div>

          {/* Username */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Username / Email <span className="text-destructive">*</span>
            </label>
            <input
              className={inputCls}
              placeholder="you@gmail.com"
              value={form.username}
              onChange={(e) => set("username", e.target.value)}
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Password / App Password <span className="text-destructive">*</span>
            </label>
            <div className="relative">
              <input
                className={`${inputCls} pr-10`}
                type={showPassword ? "text" : "password"}
                placeholder="App password or SMTP password"
                value={form.password}
                onFocus={(e) => {
                  if (e.target.value === "••••••••") set("password", "");
                }}
                onChange={(e) => set("password", e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {config && (
              <p className="text-[11px] text-muted-foreground mt-1">
                Leave unchanged to keep existing password.
              </p>
            )}
          </div>

          {/* From Name + From Email */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">
                From Name <span className="text-destructive">*</span>
              </label>
              <input
                className={inputCls}
                placeholder="Acme Corp"
                value={form.from_name}
                onChange={(e) => set("from_name", e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">
                From Email <span className="text-destructive">*</span>
              </label>
              <input
                className={inputCls}
                placeholder="sales@acmecorp.com"
                value={form.from_email}
                onChange={(e) => set("from_email", e.target.value)}
              />
            </div>
          </div>

          {/* TLS toggle */}
          <div className="flex items-center justify-between py-1">
            <div>
              <p className="text-sm font-medium">Use TLS</p>
              <p className="text-xs text-muted-foreground">
                Recommended for ports 587 (STARTTLS) and 465 (SSL)
              </p>
            </div>
            <button
              type="button"
              onClick={() => set("use_tls", !form.use_tls)}
              className="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none"
              style={{ background: form.use_tls ? INDIGO : "#E2E8F0" }}
            >
              <span
                className="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform"
                style={{ transform: form.use_tls ? "translateX(22px)" : "translateX(2px)" }}
              />
            </button>
          </div>

          {/* Test result */}
          {testResult && (
            <div
              className="flex items-start gap-2.5 rounded-xl border p-3.5 text-sm"
              style={
                testResult.success
                  ? { background: "#0F78FF10", borderColor: "#0F78FF30", color: "#0049A7" }
                  : { background: "#1D0DB010", borderColor: "#1D0DB030", color: "#1D0DB0" }
              }
            >
              {testResult.success ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
              ) : (
                <XCircle className="h-4 w-4 shrink-0 mt-0.5" />
              )}
              <span>{testResult.message}</span>
            </div>
          )}

          {/* Save success */}
          {saveSuccess && (
            <div
              className="flex items-center gap-2 rounded-xl border p-3 text-sm"
              style={{ background: "#0F78FF10", borderColor: "#0F78FF30", color: "#0049A7" }}
            >
              <CheckCircle2 className="h-4 w-4" />
              SMTP settings saved successfully.
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={() => saveMutation.mutate()}
              disabled={
                !form.host || !form.username || !form.from_name || !form.from_email || saveMutation.isPending
              }
              className="flex items-center gap-2 px-5 py-2.5 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
              style={{ background: INDIGO }}
            >
              {saveMutation.isPending ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Saving…</>
              ) : (
                "Save"
              )}
            </button>
            <button
              onClick={() => testMutation.mutate()}
              disabled={!config || testMutation.isPending}
              title={!config ? "Save your SMTP config first before testing" : undefined}
              className="flex items-center gap-2 px-5 py-2.5 text-sm rounded-xl border border-input font-medium hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {testMutation.isPending ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Testing…</>
              ) : (
                "Test Connection"
              )}
            </button>
          </div>
        </div>
      </div>

      {/* ── Email Templates Section ───────────────────────────────────────────── */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <div className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <p className="font-semibold">Email Templates</p>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Reusable email templates for CRM communications
            </p>
          </div>
          <button
            onClick={() => { setEditingTemplate(undefined); setShowTemplateModal(true); }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90"
            style={{ background: INDIGO }}
          >
            <Plus className="h-4 w-4" /> New Template
          </button>
        </div>

        <div className="p-6">
          {templatesLoading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
              <Loader2 className="h-4 w-4 animate-spin mr-2" /> Loading…
            </div>
          ) : templates.length === 0 ? (
            <div className="text-center py-10">
              <Mail className="h-8 w-8 mx-auto mb-2 text-muted-foreground/30" />
              <p className="text-sm text-muted-foreground">
                No templates yet — click New Template to create one.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {templates.map((tpl) => (
                <div
                  key={tpl.id}
                  className="flex items-start gap-4 rounded-xl border border-border p-4 transition-colors hover:bg-muted/20"
                >
                  {/* Left: info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <p className="text-sm font-semibold">{tpl.name}</p>
                      {tpl.category && <CategoryBadge category={tpl.category} />}
                      {!tpl.is_active && (
                        <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                          Inactive
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground truncate">{tpl.subject}</p>
                  </div>

                  {/* Right: actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    {/* Active toggle */}
                    <button
                      type="button"
                      title={tpl.is_active ? "Deactivate" : "Activate"}
                      onClick={() =>
                        toggleActiveMutation.mutate({ id: tpl.id, is_active: !tpl.is_active })
                      }
                      className="relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none"
                      style={{ background: tpl.is_active ? INDIGO : "#E2E8F0" }}
                    >
                      <span
                        className="inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform"
                        style={{ transform: tpl.is_active ? "translateX(18px)" : "translateX(2px)" }}
                      />
                    </button>

                    {/* Edit */}
                    <button
                      title="Edit template"
                      onClick={() => { setEditingTemplate(tpl); setShowTemplateModal(true); }}
                      className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>

                    {/* Delete */}
                    <button
                      title="Delete template"
                      onClick={() => setConfirmDeleteId(tpl.id)}
                      className="p-1.5 rounded-lg hover:bg-violet-50 transition-colors text-muted-foreground hover:text-violet-500"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Lead Sources / Platforms Section ───────────────────────────────────── */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-muted-foreground" />
              <p className="font-semibold">Lead Sources / Platforms</p>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Where your leads come from — WhatsApp, Instagram, IndiaMART, referrals, and so on
            </p>
          </div>
          <button
            onClick={() => { setEditingSource(undefined); setShowSourceModal(true); }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90"
            style={{ background: INDIGO }}
          >
            <Plus className="h-4 w-4" /> New Source
          </button>
        </div>

        <div className="p-6">
          {sourceDeleteError && (
            <p className="text-xs text-destructive mb-3">{sourceDeleteError}</p>
          )}
          {sourcesLoading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
              <Loader2 className="h-4 w-4 animate-spin mr-2" /> Loading…
            </div>
          ) : sources.length === 0 ? (
            <div className="text-center py-10">
              <Globe className="h-8 w-8 mx-auto mb-2 text-muted-foreground/30" />
              <p className="text-sm text-muted-foreground">
                No sources yet — click New Source to add one.
              </p>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {sources.map((s) => (
                <div
                  key={s.id}
                  className="group flex items-center gap-2 rounded-full border border-border pl-3 pr-1.5 py-1.5 text-sm hover:bg-muted/20 transition-colors"
                >
                  <span>{s.name}</span>
                  <button
                    title="Rename"
                    onClick={() => { setEditingSource(s); setShowSourceModal(true); }}
                    className="p-1 rounded-full hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                  >
                    <Pencil className="h-3 w-3" />
                  </button>
                  <button
                    title="Delete"
                    onClick={() => { setSourceDeleteError(""); setConfirmDeleteSourceId(s.id); }}
                    className="p-1 rounded-full hover:bg-violet-50 transition-colors text-muted-foreground hover:text-violet-500"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {showSourceModal && (
        <LeadSourceFormModal
          initial={editingSource}
          onClose={() => { setShowSourceModal(false); setEditingSource(undefined); }}
          onSaved={() => queryClient.invalidateQueries({ queryKey: ["crm-lead-sources"] })}
        />
      )}

      {confirmDeleteSourceId && (
        <ModalShell maxWidth="max-w-xs" onClose={() => setConfirmDeleteSourceId(null)}>
          <div className="p-6">
            <p className="text-sm font-medium mb-1">Delete this source?</p>
            <p className="text-xs text-muted-foreground mb-5">
              This can&rsquo;t be undone. Sources still used by existing leads can&rsquo;t be deleted.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDeleteSourceId(null)}
                className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  deleteSourceMutation.mutate(confirmDeleteSourceId);
                  setConfirmDeleteSourceId(null);
                }}
                disabled={deleteSourceMutation.isPending}
                className="px-4 py-2 text-sm rounded-xl text-white font-semibold bg-violet-500 hover:bg-violet-600 transition-colors disabled:opacity-50"
              >
                Delete
              </button>
            </div>
          </div>
        </ModalShell>
      )}

      {/* ── Template Form Modal ───────────────────────────────────────────────── */}
      {showTemplateModal && (
        <TemplateFormModal
          initial={editingTemplate}
          onClose={() => { setShowTemplateModal(false); setEditingTemplate(undefined); }}
          onSaved={() => queryClient.invalidateQueries({ queryKey: ["crm-email-templates"] })}
        />
      )}

      {/* ── Delete Confirmation ───────────────────────────────────────────────── */}
      {confirmDeleteId && (
        <ModalShell maxWidth="max-w-xs" onClose={() => setConfirmDeleteId(null)}>
          <div className="p-6">
            <p className="text-sm font-medium mb-1">Delete template?</p>
            <p className="text-xs text-muted-foreground mb-5">This action cannot be undone.</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDeleteId(null)}
                className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  deleteMutation.mutate(confirmDeleteId);
                  setConfirmDeleteId(null);
                }}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 text-sm rounded-xl text-white font-semibold bg-violet-500 hover:bg-violet-600 transition-colors disabled:opacity-50"
              >
                Delete
              </button>
            </div>
          </div>
        </ModalShell>
      )}
    </div>
  );
}
