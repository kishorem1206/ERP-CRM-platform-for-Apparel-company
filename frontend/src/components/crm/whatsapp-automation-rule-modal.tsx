"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { ModalShell } from "@/components/shared/modal-shell";

const INDIGO = "#0049A7";
const inputCls =
  "w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

export interface AutomationRuleEntry {
  id: string;
  name: string;
  trigger_event: string;
  template_id: string | null;
  message_body: string | null;
  recipient_type: string;
  delay_minutes: number;
  is_active: boolean;
}

const TRIGGER_OPTIONS = [
  { value: "lead_assigned", label: "Lead Assigned" },
  { value: "catalogue_shared", label: "Catalogue / Product Shared" },
  { value: "follow_up_due", label: "Follow-Up Due" },
  { value: "quotation_generated", label: "Quotation Generated" },
  { value: "sample_dispatched", label: "Sample Dispatched" },
];

const RECIPIENT_OPTIONS = [
  { value: "customer", label: "Customer" },
  { value: "employee", label: "Employee (assignee)" },
  { value: "both", label: "Both" },
];

const TRIGGER_VARIABLES: Record<string, string[]> = {
  lead_assigned: ["customer_name", "company_name", "employee_name", "lead_title"],
  catalogue_shared: ["customer_name", "product_name", "company_name"],
  follow_up_due: ["customer_name", "followup_date", "employee_name"],
  quotation_generated: ["customer_name", "quotation_number", "company_name"],
  sample_dispatched: ["customer_name", "product_name", "company_name"],
};

interface TemplateLite {
  id: string;
  name: string;
  status: string | null;
}

export function WhatsappAutomationRuleModal({
  initial, onClose,
}: {
  initial?: AutomationRuleEntry;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(initial?.name ?? "");
  const [triggerEvent, setTriggerEvent] = useState(initial?.trigger_event ?? "");
  const [recipientType, setRecipientType] = useState(initial?.recipient_type ?? "customer");
  const [delayMinutes, setDelayMinutes] = useState(String(initial?.delay_minutes ?? 0));
  const [isActive, setIsActive] = useState(initial?.is_active ?? true);
  const [useTemplate, setUseTemplate] = useState(Boolean(initial?.template_id));
  const [templateId, setTemplateId] = useState(initial?.template_id ?? "");
  const [messageBody, setMessageBody] = useState(initial?.message_body ?? "");
  const [error, setError] = useState("");

  const { data: templatesData } = useQuery({
    queryKey: ["whatsapp-templates"],
    queryFn: () => api.get("/whatsapp/templates").then((r) => r.data),
  });
  const templates: TemplateLite[] = templatesData?.data ?? [];

  const mutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name,
        trigger_event: triggerEvent,
        recipient_type: recipientType,
        delay_minutes: delayMinutes ? Number(delayMinutes) : 0,
        is_active: isActive,
        template_id: useTemplate ? (templateId || undefined) : undefined,
        message_body: useTemplate ? undefined : (messageBody || undefined),
      };
      if (initial) {
        await api.patch(`/whatsapp/automation-rules/${initial.id}`, payload);
      } else {
        await api.post("/whatsapp/automation-rules", payload);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["whatsapp-automation-rules"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Failed to save");
    },
  });

  const canSave =
    name.trim() && triggerEvent && recipientType &&
    (useTemplate ? Boolean(templateId) : Boolean(messageBody.trim()));

  const availableVars = TRIGGER_VARIABLES[triggerEvent] ?? [];

  return (
    <ModalShell maxWidth="max-w-lg" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">{initial ? "Edit Automation Rule" : "New Automation Rule"}</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Rule Name <span className="text-destructive">*</span>
          </label>
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Welcome message on assignment" />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Trigger <span className="text-destructive">*</span>
            </label>
            <SearchableSelect
              options={TRIGGER_OPTIONS}
              value={triggerEvent}
              onChange={setTriggerEvent}
              placeholder="Select trigger…"
              accent={INDIGO}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Recipient</label>
            <SearchableSelect
              options={RECIPIENT_OPTIONS}
              value={recipientType}
              onChange={setRecipientType}
              placeholder="Select recipient…"
              accent={INDIGO}
            />
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input type="radio" checked={!useTemplate} onChange={() => setUseTemplate(false)} />
            Freeform message
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input type="radio" checked={useTemplate} onChange={() => setUseTemplate(true)} />
            Approved Meta template
          </label>
        </div>

        {useTemplate ? (
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Template</label>
            <SearchableSelect
              options={templates.map((t) => ({ value: t.id, label: t.name, meta: t.status ?? undefined }))}
              value={templateId}
              onChange={setTemplateId}
              placeholder="Select an approved template…"
              accent={INDIGO}
            />
          </div>
        ) : (
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Message Body <span className="text-destructive">*</span>
            </label>
            <textarea
              className={inputCls}
              rows={4}
              value={messageBody}
              onChange={(e) => setMessageBody(e.target.value)}
              placeholder="Hi {{customer_name}}, thanks for your interest..."
            />
            {triggerEvent && (
              <p className="text-[11px] text-muted-foreground mt-1">
                Available variables: {availableVars.map((v) => `{{${v}}}`).join(", ")}
              </p>
            )}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Delay (minutes)</label>
            <input className={inputCls} type="number" min="0" value={delayMinutes} onChange={(e) => setDelayMinutes(e.target.value)} />
          </div>
          <div className="flex items-end pb-2.5">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
              Active
            </label>
          </div>
        </div>

        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => { setError(""); mutation.mutate(); }}
          disabled={!canSave || mutation.isPending}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </ModalShell>
  );
}
