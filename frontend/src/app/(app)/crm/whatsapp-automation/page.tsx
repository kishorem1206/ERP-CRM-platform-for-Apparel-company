"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2 } from "lucide-react";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { ModalShell } from "@/components/shared/modal-shell";
import {
  WhatsappAutomationRuleModal,
  AutomationRuleEntry,
} from "@/components/crm/whatsapp-automation-rule-modal";
import { Can } from "@/lib/permissions";

const INDIGO = "#0049A7";

type RuleRow = Record<string, unknown> & AutomationRuleEntry;

interface LogRow {
  id: string;
  rule_id: string;
  lead_id: string | null;
  recipient_phone: string | null;
  rendered_body: string | null;
  status: string;
  error_message: string | null;
  created_at: string;
}
type LogTableRow = Record<string, unknown> & LogRow;

const TRIGGER_LABELS: Record<string, string> = {
  lead_assigned: "Lead Assigned",
  catalogue_shared: "Catalogue Shared",
  follow_up_due: "Follow-Up Due",
  quotation_generated: "Quotation Generated",
  sample_dispatched: "Sample Dispatched",
};

const STATUS_STYLES: Record<string, string> = {
  sent: "bg-blue-50 text-blue-600",
  queued: "bg-amber-50 text-amber-600",
  failed: "bg-violet-50 text-violet-600",
  skipped_no_phone: "bg-muted text-muted-foreground",
  skipped_disabled: "bg-muted text-muted-foreground",
};

export default function WhatsappAutomationPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"rules" | "logs">("rules");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<RuleRow | undefined>(undefined);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const { data: rulesData, isLoading: rulesLoading } = useQuery({
    queryKey: ["whatsapp-automation-rules"],
    queryFn: () => api.get("/whatsapp/automation-rules").then((r) => r.data),
  });
  const rules: RuleRow[] = rulesData?.data ?? [];

  const { data: logsData, isLoading: logsLoading } = useQuery({
    queryKey: ["whatsapp-automation-logs"],
    queryFn: () => api.get("/whatsapp/automation-logs?page_size=100").then((r) => r.data),
    enabled: tab === "logs",
  });
  const logs: LogTableRow[] = logsData?.data ?? [];

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.patch(`/whatsapp/automation-rules/${id}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["whatsapp-automation-rules"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/whatsapp/automation-rules/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["whatsapp-automation-rules"] }),
  });

  const ruleColumns: Column<RuleRow>[] = [
    { key: "name", header: "Rule", sortable: true },
    { key: "trigger_event", header: "Trigger", render: (r) => TRIGGER_LABELS[r.trigger_event] ?? r.trigger_event },
    { key: "recipient_type", header: "Recipient", render: (r) => r.recipient_type },
    { key: "delay_minutes", header: "Delay", render: (r) => (r.delay_minutes > 0 ? `${r.delay_minutes} min` : "Immediate") },
    {
      key: "is_active", header: "Active",
      render: (r) => (
        <Can perm="crm.edit"><button
          onClick={() => toggleActiveMutation.mutate({ id: r.id, is_active: !r.is_active })}
          className={`px-2.5 py-1 rounded-full text-[11px] font-semibold transition-colors ${
            r.is_active ? "bg-blue-50 text-blue-600" : "bg-muted text-muted-foreground"
          }`}
        >
          {r.is_active ? "Active" : "Disabled"}
        </button></Can>
      ),
    },
    {
      key: "id", header: "", className: "w-16",
      render: (r) => (
        <div className="flex items-center gap-1">
          <Can perm="crm.edit"><button
            onClick={() => { setEditing(r); setShowForm(true); }}
            className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button></Can>
          <Can perm="crm.delete"><button
            onClick={() => setConfirmDeleteId(r.id)}
            className="p-1.5 rounded-lg hover:bg-violet-50 transition-colors text-muted-foreground hover:text-violet-500"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button></Can>
        </div>
      ),
    },
  ];

  const logColumns: Column<LogTableRow>[] = [
    { key: "created_at", header: "Time", render: (r) => new Date(r.created_at).toLocaleString(), sortable: true },
    { key: "recipient_phone", header: "Recipient", render: (r) => r.recipient_phone ?? "—" },
    { key: "rendered_body", header: "Message", render: (r) => <span className="line-clamp-2 max-w-sm">{r.rendered_body ?? "—"}</span> },
    {
      key: "status", header: "Status",
      render: (r) => (
        <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold ${STATUS_STYLES[r.status] ?? "bg-muted"}`}>
          {r.status.replace(/_/g, " ")}
        </span>
      ),
    },
    { key: "error_message", header: "Error", render: (r) => r.error_message ?? "—" },
  ];

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">CRM / ACTIVITY</p>
          <h1 className="text-2xl font-bold tracking-tight">WhatsApp Automation</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Configure messages that auto-send on lead assignment, catalogue sharing, follow-up due,
            quotation generation, and sample dispatch — no hard-coded messages.
          </p>
        </div>
        {tab === "rules" && (
          <Can perm="crm.create"><button
            onClick={() => { setEditing(undefined); setShowForm(true); }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
            style={{ background: INDIGO }}
          >
            <Plus className="h-4 w-4" /> New Rule
          </button></Can>
        )}
      </div>

      <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit">
        {(["rules", "logs"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
              tab === t ? "bg-card shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t === "rules" ? "Rules" : "Send Log"}
          </button>
        ))}
      </div>

      {tab === "rules" ? (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
          <DataTable
            columns={ruleColumns}
            data={rules}
            loading={rulesLoading}
            emptyMessage="No automation rules yet — click New Rule to configure one."
          />
        </div>
      ) : (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
          <DataTable
            columns={logColumns}
            data={logs}
            loading={logsLoading}
            emptyMessage="No sends logged yet."
          />
        </div>
      )}

      {showForm && (
        <WhatsappAutomationRuleModal initial={editing} onClose={() => { setShowForm(false); setEditing(undefined); }} />
      )}

      {confirmDeleteId && (
        <ModalShell maxWidth="max-w-xs" onClose={() => setConfirmDeleteId(null)}>
          <div className="p-6">
            <p className="text-sm font-medium mb-1">Delete this automation rule?</p>
            <p className="text-xs text-muted-foreground mb-5">This can&rsquo;t be undone. Past logs are kept.</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDeleteId(null)}
                className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => { deleteMutation.mutate(confirmDeleteId); setConfirmDeleteId(null); }}
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
