"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Settings, CheckCircle2, XCircle, Loader2, Eye, EyeOff, X,
  Mail, Plus, Pencil, Trash2, Globe, Gauge, Users as UsersIcon,
} from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { QualificationStageCard } from "@/components/crm/qualification-stage-card";
import { ModalShell } from "@/components/shared/modal-shell";
import { Can } from "@/lib/permissions";

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
      // The endpoint returns { success, message, data: null } on success.
      setTestResult({ success: true, message: data?.message ?? "Test email sent successfully" });
    },
    onError: (err: unknown) => {
      // App error envelope: { success: false, error: "<str>" }
      const errField = (err as { response?: { data?: { error?: unknown } } })?.response?.data?.error;
      const msg = typeof errField === "string" ? errField : "Connection test failed";
      setTestResult({ success: false, message: msg });
    },
  });

  // ── Template mutations ─────────────────────────────────────────────────────
  // ── Lead Assignment (admin.settings) ────────────────────────────────────────
  const { data: assignableUsersData } = useQuery({
    queryKey: ["crm-assignable-users"],
    queryFn: async () => (await api.get("/crm/assignable-users")).data,
  });
  const assignableUsers: { id: string; name: string }[] = assignableUsersData?.data ?? [];

  const { data: rulesData } = useQuery({
    queryKey: ["crm-assignment-rules"],
    queryFn: async () => (await api.get("/crm/assignment-rules")).data,
  });
  const assignmentRules: { id: string; name: string; sort_order: number; is_active: boolean; source_id: string | null; min_score: number | null; location_tier: string | null; assign_to: string; assign_to_name: string | null }[] =
    rulesData?.data ?? [];

  const { data: poolData } = useQuery({
    queryKey: ["crm-assignment-pool"],
    queryFn: async () => (await api.get("/crm/assignment-pool")).data,
  });
  const assignmentPool: { id: string; user_id: string; user_name: string | null; sort_order: number; is_active: boolean }[] =
    poolData?.data ?? [];

  const [showRuleModal, setShowRuleModal] = useState(false);
  const [poolAddUserId, setPoolAddUserId] = useState("");

  const deleteRuleMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/crm/assignment-rules/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["crm-assignment-rules"] }),
  });
  const toggleRuleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.patch(`/crm/assignment-rules/${id}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["crm-assignment-rules"] }),
  });
  const addPoolMemberMutation = useMutation({
    mutationFn: (user_id: string) => api.post("/crm/assignment-pool", { user_id, sort_order: assignmentPool.length }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["crm-assignment-pool"] }); setPoolAddUserId(""); },
  });
  const removePoolMemberMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/crm/assignment-pool/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["crm-assignment-pool"] }),
  });

  const { data: responseTargetsData } = useQuery({
    queryKey: ["crm-response-targets"],
    queryFn: async () => (await api.get("/crm/response-targets")).data,
  });
  const responseTargets = responseTargetsData?.data as {
    response_target_high_minutes: number; response_target_medium_hours: number; response_target_low_hours: number;
    escalation_employee_hours: number; escalation_manager_hours: number;
  } | undefined;
  const [targetForm, setTargetForm] = useState({ high: "", medium: "", low: "", escEmp: "", escMgr: "" });
  useEffect(() => {
    if (responseTargets) {
      setTargetForm({
        high: String(responseTargets.response_target_high_minutes),
        medium: String(responseTargets.response_target_medium_hours),
        low: String(responseTargets.response_target_low_hours),
        escEmp: String(responseTargets.escalation_employee_hours),
        escMgr: String(responseTargets.escalation_manager_hours),
      });
    }
  }, [responseTargets]);
  const updateTargetsMutation = useMutation({
    mutationFn: () => api.put("/crm/response-targets", {
      response_target_high_minutes: parseInt(targetForm.high, 10),
      response_target_medium_hours: parseInt(targetForm.medium, 10),
      response_target_low_hours: parseInt(targetForm.low, 10),
      escalation_employee_hours: parseInt(targetForm.escEmp, 10),
      escalation_manager_hours: parseInt(targetForm.escMgr, 10),
    }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["crm-response-targets"] }),
  });

  // ── Predictive Scoring readiness (read-only status, not a feature) ─────────
  const { data: readinessData } = useQuery({
    queryKey: ["crm-predictive-readiness"],
    queryFn: async () => (await api.get("/crm/predictive-scoring/readiness")).data,
  });
  const readiness = readinessData?.data as {
    ready: boolean; leads_total: number; leads_total_required: number;
    converted: number; not_converted: number; outcomes_required_per_class: number; reason: string;
  } | undefined;

  // ── Lead Scoring (admin.settings) ───────────────────────────────────────────
  const { data: scoringRulesData, isLoading: rulesLoading } = useQuery({
    queryKey: ["crm-scoring-rules"],
    queryFn: async () => (await api.get("/crm/scoring-rules")).data,
  });
  const scoringRules: { id: string; category: string; code: string; label: string; weight: number; is_active: boolean }[] =
    scoringRulesData?.data ?? [];

  const { data: thresholdsData } = useQuery({
    queryKey: ["crm-scoring-thresholds"],
    queryFn: async () => (await api.get("/crm/scoring-thresholds")).data,
  });
  const thresholds = thresholdsData?.data as { lead_score_high_threshold: number; lead_score_medium_threshold: number } | undefined;
  const [highThreshold, setHighThreshold] = useState("");
  const [mediumThreshold, setMediumThreshold] = useState("");
  useEffect(() => {
    if (thresholds) {
      setHighThreshold(String(thresholds.lead_score_high_threshold));
      setMediumThreshold(String(thresholds.lead_score_medium_threshold));
    }
  }, [thresholds]);

  const updateRuleMutation = useMutation({
    mutationFn: ({ id, ...body }: { id: string; weight?: number; is_active?: boolean }) =>
      api.patch(`/crm/scoring-rules/${id}`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["crm-scoring-rules"] }),
  });

  const updateThresholdsMutation = useMutation({
    mutationFn: () =>
      api.put("/crm/scoring-thresholds", {
        lead_score_high_threshold: parseInt(highThreshold, 10),
        lead_score_medium_threshold: parseInt(mediumThreshold, 10),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["crm-scoring-thresholds"] }),
  });

  const rulesByCategory = scoringRules.reduce<Record<string, typeof scoringRules>>((acc, r) => {
    (acc[r.category] ??= []).push(r);
    return acc;
  }, {});

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
            <Can perm="crm.edit"><button
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
            </button></Can>
            <Can perm="crm.edit"><button
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
            </button></Can>
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
                    <Can perm="crm.edit"><button
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
                    </button></Can>

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

      {/* ── Lead Assignment Section ──────────────────────────────────────────── */}
      <Can perm="admin.settings">
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <div className="flex items-center gap-2">
              <UsersIcon className="h-4 w-4 text-muted-foreground" />
              <p className="font-semibold">Lead Assignment</p>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              A new lead with no manual assignee is auto-assigned: the first matching rule wins, otherwise it rotates through the round-robin pool below.
            </p>
          </div>
          <button
            onClick={() => setShowRuleModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90"
            style={{ background: INDIGO }}
          >
            <Plus className="h-4 w-4" /> New Rule
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">Rules (checked in order)</p>
            {assignmentRules.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4">No rules yet — every lead falls through to the round-robin pool.</p>
            ) : (
              <div className="divide-y divide-border rounded-xl border border-border overflow-hidden">
                {assignmentRules.map((rule) => (
                  <div key={rule.id} className={`flex items-center justify-between gap-4 px-4 py-2.5 ${rule.is_active ? "" : "opacity-50"}`}>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{rule.name}</p>
                      <p className="text-xs text-muted-foreground truncate">
                        {[
                          rule.source_id && "specific source",
                          rule.min_score !== null && `score ≥ ${rule.min_score}`,
                          rule.location_tier && `${rule.location_tier} area`,
                        ].filter(Boolean).join(" · ") || "Matches everything"}
                        {" → "}{rule.assign_to_name ?? "—"}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        onClick={() => toggleRuleMutation.mutate({ id: rule.id, is_active: !rule.is_active })}
                        className="relative inline-flex h-5 w-9 items-center rounded-full transition-colors"
                        style={{ background: rule.is_active ? INDIGO : "hsl(var(--muted))" }}
                      >
                        <span
                          className="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform"
                          style={{ transform: rule.is_active ? "translateX(18px)" : "translateX(3px)" }}
                        />
                      </button>
                      <button
                        onClick={() => deleteRuleMutation.mutate(rule.id)}
                        className="p-1 rounded hover:bg-violet-50 transition-colors text-muted-foreground hover:text-violet-500"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">Round-Robin Pool</p>
            <div className="flex flex-wrap gap-2 mb-3">
              {assignmentPool.length === 0 && <p className="text-sm text-muted-foreground">No one in the pool yet.</p>}
              {assignmentPool.map((m) => (
                <div key={m.id} className="flex items-center gap-2 rounded-full border border-border pl-3 pr-1.5 py-1.5 text-sm">
                  <span>{m.user_name ?? "—"}</span>
                  <button
                    onClick={() => removePoolMemberMutation.mutate(m.id)}
                    className="p-1 rounded-full hover:bg-violet-50 transition-colors text-muted-foreground hover:text-violet-500"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
            <div className="w-64">
              <SearchableSelect
                value={poolAddUserId}
                onChange={(v) => { setPoolAddUserId(v); if (v) addPoolMemberMutation.mutate(v); }}
                placeholder="Add employee to pool…"
                accent={INDIGO}
                options={assignableUsers
                  .filter((u) => !assignmentPool.some((m) => m.user_id === u.id))
                  .map((u) => ({ value: u.id, label: u.name }))}
              />
            </div>
          </div>

          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">Response Targets &amp; Escalation</p>
            <div className="flex flex-wrap gap-4 p-4 rounded-xl bg-muted/20">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">High priority (minutes)</label>
                <input type="number" min={1} value={targetForm.high}
                  onChange={(e) => setTargetForm((f) => ({ ...f, high: e.target.value }))}
                  onBlur={() => updateTargetsMutation.mutate()}
                  className="w-20 rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Medium priority (hours)</label>
                <input type="number" min={1} value={targetForm.medium}
                  onChange={(e) => setTargetForm((f) => ({ ...f, medium: e.target.value }))}
                  onBlur={() => updateTargetsMutation.mutate()}
                  className="w-20 rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Low priority (hours)</label>
                <input type="number" min={1} value={targetForm.low}
                  onChange={(e) => setTargetForm((f) => ({ ...f, low: e.target.value }))}
                  onBlur={() => updateTargetsMutation.mutate()}
                  className="w-20 rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Notify employee after (hours)</label>
                <input type="number" min={1} value={targetForm.escEmp}
                  onChange={(e) => setTargetForm((f) => ({ ...f, escEmp: e.target.value }))}
                  onBlur={() => updateTargetsMutation.mutate()}
                  className="w-20 rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Escalate to owner after (hours)</label>
                <input type="number" min={1} value={targetForm.escMgr}
                  onChange={(e) => setTargetForm((f) => ({ ...f, escMgr: e.target.value }))}
                  onBlur={() => updateTargetsMutation.mutate()}
                  className="w-20 rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              "Notify employee" and "Escalate to owner" count from the response target above — e.g. a high-priority lead with a 30-minute target and a 2-hour employee escalation gets a reminder 2.5 hours after creation if still not contacted.
            </p>
          </div>
        </div>
      </div>
      </Can>

      {showRuleModal && (
        <AssignmentRuleModal
          sources={sources}
          assignableUsers={assignableUsers}
          onClose={() => setShowRuleModal(false)}
          onSaved={() => queryClient.invalidateQueries({ queryKey: ["crm-assignment-rules"] })}
        />
      )}

      {/* ── Predictive Scoring Section (status only — no model exists yet) ───── */}
      <Can perm="admin.settings">
      {readiness && (
        <div className="bg-card border border-border rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-1">
            <Gauge className="h-4 w-4 text-muted-foreground" />
            <p className="font-semibold">Predictive Scoring</p>
            <span className="px-2 py-0.5 rounded-full text-[11px] font-bold uppercase bg-muted text-muted-foreground">
              Not Available Yet
            </span>
          </div>
          <p className="text-xs text-muted-foreground mb-4">
            This isn't a feature yet — just an honest status check. Once enough real leads with known outcomes accumulate, this unlocks a model-based prediction alongside (not instead of) the rule-based score above. See docs/PREDICTIVE_SCORING_DATA_AUDIT.md.
          </p>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="p-3 rounded-xl bg-muted/20">
              <p className="text-lg font-bold tabular-nums">{readiness.leads_total} / {readiness.leads_total_required}</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">Total Leads</p>
            </div>
            <div className="p-3 rounded-xl bg-muted/20">
              <p className="text-lg font-bold tabular-nums">{readiness.converted} / {readiness.outcomes_required_per_class}</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">Converted Outcomes</p>
            </div>
            <div className="p-3 rounded-xl bg-muted/20">
              <p className="text-lg font-bold tabular-nums">{readiness.not_converted} / {readiness.outcomes_required_per_class}</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">Lost Outcomes</p>
            </div>
          </div>
        </div>
      )}
      </Can>

      {/* ── Qualification stage (drives the Sales KPI "Lead → Qualified") ──── */}
      <Can perm="admin.settings">
        <QualificationStageCard />
      </Can>

      {/* ── Lead Scoring Section ─────────────────────────────────────────────── */}
      <Can perm="admin.settings">
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-muted-foreground" />
            <p className="font-semibold">Lead Scoring</p>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Every rule below contributes to a lead&rsquo;s score when it applies. Weights can be negative. Turn a rule off without losing its history by switching it inactive.
          </p>
        </div>

        <div className="p-6 space-y-6">
          <div className="flex flex-wrap items-end gap-4 p-4 rounded-xl bg-muted/20">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">High priority at score ≥</label>
              <input
                type="number" min={1} max={100} value={highThreshold}
                onChange={(e) => setHighThreshold(e.target.value)}
                onBlur={() => updateThresholdsMutation.mutate()}
                className="w-24 rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Medium priority at score ≥</label>
              <input
                type="number" min={0} max={99} value={mediumThreshold}
                onChange={(e) => setMediumThreshold(e.target.value)}
                onBlur={() => updateThresholdsMutation.mutate()}
                className="w-24 rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <p className="text-xs text-muted-foreground">Below the medium threshold, a lead is Low priority.</p>
          </div>

          {rulesLoading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
              <Loader2 className="h-4 w-4 animate-spin mr-2" /> Loading…
            </div>
          ) : (
            Object.entries(rulesByCategory).map(([category, rules]) => (
              <div key={category}>
                <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">
                  {CATEGORY_LABELS[category] ?? category}
                </p>
                <div className="divide-y divide-border rounded-xl border border-border overflow-hidden">
                  {rules.map((rule) => (
                    <RuleRow key={rule.id} rule={rule} onSave={(body) => updateRuleMutation.mutate({ id: rule.id, ...body })} />
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
      </Can>
    </div>
  );
}

const CATEGORY_LABELS: Record<string, string> = {
  requirement: "Requirement", intent: "Intent", contact: "Contact",
  business: "Business", location: "Location", repeat: "Repeat Contact", quality: "Message Quality",
};

function RuleRow({
  rule, onSave,
}: {
  rule: { id: string; label: string; weight: number; is_active: boolean };
  onSave: (body: { weight?: number; is_active?: boolean }) => void;
}) {
  const [weight, setWeight] = useState(String(rule.weight));
  useEffect(() => setWeight(String(rule.weight)), [rule.weight]);

  return (
    <div className={`flex items-center justify-between gap-4 px-4 py-2.5 ${rule.is_active ? "" : "opacity-50"}`}>
      <p className="text-sm">{rule.label}</p>
      <div className="flex items-center gap-3 flex-shrink-0">
        <input
          type="number" value={weight}
          onChange={(e) => setWeight(e.target.value)}
          onBlur={() => {
            const n = parseInt(weight, 10);
            if (!Number.isNaN(n) && n !== rule.weight) onSave({ weight: n });
          }}
          className="w-16 rounded-lg border border-input bg-background px-2 py-1 text-sm text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-ring"
        />
        <button
          onClick={() => onSave({ is_active: !rule.is_active })}
          className="relative inline-flex h-5 w-9 items-center rounded-full transition-colors"
          style={{ background: rule.is_active ? INDIGO : "hsl(var(--muted))" }}
          title={rule.is_active ? "Deactivate rule" : "Activate rule"}
        >
          <span
            className="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform"
            style={{ transform: rule.is_active ? "translateX(18px)" : "translateX(3px)" }}
          />
        </button>
      </div>
    </div>
  );
}

function AssignmentRuleModal({
  sources, assignableUsers, onClose, onSaved,
}: {
  sources: { id: string; name: string }[];
  assignableUsers: { id: string; name: string }[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [minScore, setMinScore] = useState("");
  const [locationTier, setLocationTier] = useState("");
  const [assignTo, setAssignTo] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => api.post("/crm/assignment-rules", {
      name,
      source_id: sourceId || undefined,
      min_score: minScore ? parseInt(minScore, 10) : undefined,
      location_tier: locationTier || undefined,
      assign_to: assignTo,
    }),
    onSuccess: () => { onSaved(); onClose(); },
    onError: (err: unknown) => {
      const e = (err as { response?: { data?: { error?: unknown } } })?.response?.data?.error;
      setError(typeof e === "string" ? e : "Could not create rule.");
    },
  });

  return (
    <ModalShell maxWidth="max-w-md" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">New Assignment Rule</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        {error && <p className="text-xs text-destructive">{error}</p>}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Rule name</label>
          <input
            value={name} onChange={(e) => setName(e.target.value)}
            placeholder="e.g. IndiaMART high-value to senior team"
            className="w-full rounded-xl border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">If source is (optional)</label>
          <SearchableSelect
            value={sourceId} onChange={setSourceId} accent={INDIGO}
            placeholder="Any source"
            options={sources.map((s) => ({ value: s.id, label: s.name }))}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">And score is at least (optional)</label>
          <input
            type="number" min={0} max={100} value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            placeholder="Any score"
            className="w-full rounded-xl border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">And location tier is (optional)</label>
          <SearchableSelect
            value={locationTier} onChange={setLocationTier} accent={INDIGO}
            placeholder="Any location"
            options={[
              { value: "preferred", label: "Preferred" },
              { value: "secondary", label: "Secondary" },
              { value: "non_serviceable", label: "Non-serviceable" },
            ]}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Assign to</label>
          <SearchableSelect
            value={assignTo} onChange={setAssignTo} accent={INDIGO}
            placeholder="Select employee…"
            options={assignableUsers.map((u) => ({ value: u.id, label: u.name }))}
          />
        </div>
      </div>
      <div className="flex justify-end gap-3 px-6 py-4 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => mutation.mutate()}
          disabled={!name.trim() || !assignTo || mutation.isPending}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-colors disabled:opacity-50 hover:opacity-90"
          style={{ background: INDIGO }}
        >
          {mutation.isPending ? "Saving…" : "Create Rule"}
        </button>
      </div>
    </ModalShell>
  );
}
