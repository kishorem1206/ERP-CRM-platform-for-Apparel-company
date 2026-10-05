"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { ModalShell } from "@/components/shared/modal-shell";
import { DatePicker } from "@/components/shared/date-picker";

const INDIGO = "#0049A7";

const inputCls =
  "w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

interface UserOption {
  id: string;
  name: string;
  email: string;
}

const PRIORITY_COLORS: Record<string, string> = {
  low: "#64748B", medium: "#A096F7", high: "#1D0DB0",
};

const PRIORITY_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

export function CreateTaskModal({ onClose, leadId }: { onClose: () => void; leadId?: string }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [assignedTo, setAssignedTo] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [priority, setPriority] = useState("medium");

  const { data: usersData } = useQuery({
    queryKey: ["crm-assignable-users"],
    queryFn: () => api.get("/crm/assignable-users").then((r) => r.data),
  });
  const users: UserOption[] = usersData?.data ?? [];

  const { data: customersData } = useQuery({
    queryKey: ["sales-customers-all"],
    queryFn: () => api.get("/sales/customers?page_size=200").then((r) => r.data),
  });
  const customers: { id: string; legal_name: string }[] = customersData?.data ?? [];

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post("/crm/tasks", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-tasks"] });
      if (leadId) queryClient.invalidateQueries({ queryKey: ["crm-tasks-lead", leadId] });
      onClose();
    },
  });

  function handleSubmit() {
    if (!title.trim()) return;
    mutation.mutate({
      title,
      notes: notes || undefined,
      lead_id: leadId || undefined,
      customer_id: customerId || undefined,
      assigned_to: assignedTo || undefined,
      due_at: dueAt ? new Date(dueAt).toISOString() : undefined,
      priority,
    });
  }

  return (
    <ModalShell maxWidth="max-w-md" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">New Task</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Title <span className="text-destructive">*</span>
          </label>
          <input className={inputCls} placeholder="What needs to be done?" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
          <textarea className={`${inputCls} resize-none`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-2">Priority</label>
          <div className="flex gap-2">
            {PRIORITY_OPTIONS.map((p) => {
              const color = PRIORITY_COLORS[p.value];
              const active = priority === p.value;
              return (
                <button
                  key={p.value} type="button" onClick={() => setPriority(p.value)}
                  className="flex-1 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all"
                  style={{
                    borderColor: active ? color : "hsl(var(--border))",
                    background: active ? `${color}18` : "transparent",
                    color: active ? color : "hsl(var(--muted-foreground))",
                  }}
                >
                  {p.label}
                </button>
              );
            })}
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Due</label>
          <DatePicker value={dueAt} onChange={(v) => setDueAt(v)} mode="datetime" />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Assign To</label>
          <SearchableSelect
            options={users.map((u) => ({ value: u.id, label: u.name, meta: u.email }))}
            value={assignedTo} onChange={setAssignedTo} placeholder="Unassigned" accent={INDIGO}
          />
        </div>
        {!leadId && (
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Related Customer</label>
            <SearchableSelect
              options={customers.map((c) => ({ value: c.id, label: c.legal_name }))}
              value={customerId} onChange={setCustomerId} placeholder="None" accent={INDIGO}
            />
          </div>
        )}
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={!title.trim() || mutation.isPending}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mutation.isPending ? "Saving…" : "Create Task"}
        </button>
      </div>
    </ModalShell>
  );
}
