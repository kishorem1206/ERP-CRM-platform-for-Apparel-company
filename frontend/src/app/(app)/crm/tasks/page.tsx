"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Plus, CheckCircle2, Circle } from "lucide-react";
import api from "@/lib/api";
import { getCurrentUserId } from "@/lib/auth";
import { DataTable, Column } from "@/components/shared/data-table";
import { StatusBadge } from "@/components/shared/status-badge";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { CreateTaskModal } from "@/components/crm/create-task-modal";
import { Can } from "@/lib/permissions";

const INDIGO = "#0049A7";
const RED = "#1D0DB0";

type Task = Record<string, unknown> & {
  id: string;
  title: string;
  notes: string | null;
  lead_id: string | null;
  lead_title: string | null;
  customer_id: string | null;
  customer_name: string | null;
  assigned_to: string | null;
  assigned_to_name: string | null;
  due_at: string | null;
  priority: string;
  status: string;
  source: string;
};

const PRIORITY_COLORS: Record<string, string> = {
  low: "#64748B", medium: "#A096F7", high: "#1D0DB0",
};

const STATUS_OPTIONS = [
  { value: "pending", label: "Pending" },
  { value: "in_progress", label: "In Progress" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

const PRIORITY_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

export default function TasksPage() {
  const queryClient = useQueryClient();
  const currentUserId = getCurrentUserId();
  const [mineOnly, setMineOnly] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const { data: tasksData, isLoading } = useQuery({
    queryKey: ["crm-tasks", mineOnly, statusFilter, priorityFilter, currentUserId],
    queryFn: async () => {
      const params = new URLSearchParams({ page_size: "100" });
      if (mineOnly && currentUserId) params.set("assigned_to", currentUserId);
      if (statusFilter) params.set("status", statusFilter);
      if (priorityFilter) params.set("priority", priorityFilter);
      const res = await api.get(`/crm/tasks?${params}`);
      return res.data;
    },
  });
  const tasks: Task[] = tasksData?.data ?? [];

  const completeMutation = useMutation({
    mutationFn: (id: string) => api.patch(`/crm/tasks/${id}/complete`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["crm-tasks"] }),
  });

  const columns: Column<Task>[] = [
    {
      key: "title", header: "Task", sortable: true,
      render: (t) => (
        <div>
          <p className="font-medium">{t.title}</p>
          {t.lead_id && t.lead_title && (
            <Link href={`/crm/leads/${t.lead_id}`} className="text-[11px] text-muted-foreground hover:underline">
              {t.lead_title}
            </Link>
          )}
        </div>
      ),
    },
    {
      key: "due_at", header: "Due", sortable: true,
      render: (t) => {
        if (!t.due_at) return <span className="text-muted-foreground">—</span>;
        const overdue = ["pending", "in_progress"].includes(t.status) && new Date(t.due_at) < new Date();
        return (
          <span style={{ color: overdue ? RED : undefined }}>
            {new Date(t.due_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
          </span>
        );
      },
    },
    {
      key: "priority", header: "Priority",
      render: (t) => (
        <span
          className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold capitalize whitespace-nowrap"
          style={{ background: `${PRIORITY_COLORS[t.priority] ?? INDIGO}18`, color: PRIORITY_COLORS[t.priority] ?? INDIGO }}
        >
          {t.priority}
        </span>
      ),
    },
    { key: "assigned_to_name", header: "Assignee", render: (t) => t.assigned_to_name ?? "Unassigned" },
    { key: "status", header: "Status", render: (t) => <StatusBadge status={t.status.replace("_", " ")} /> },
    {
      key: "id", header: "", className: "w-10",
      render: (t) => (
        <Can perm="crm.edit"><button
          onClick={() => t.status !== "completed" && completeMutation.mutate(t.id)}
          disabled={t.status === "completed" || completeMutation.isPending}
          className="p-1 rounded transition-colors hover:bg-muted disabled:cursor-default"
          title={t.status === "completed" ? "Completed" : "Mark complete"}
        >
          {t.status === "completed" ? (
            <CheckCircle2 className="h-4 w-4 text-blue-500" />
          ) : (
            <Circle className="h-4 w-4 text-muted-foreground" />
          )}
        </button></Can>
      ),
    },
  ];

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">CRM / TASKS</p>
          <h1 className="text-2xl font-bold tracking-tight">Tasks</h1>
          <p className="text-sm text-muted-foreground mt-1">What needs doing next, across your leads and customers.</p>
        </div>
        <Can perm="crm.create"><button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: INDIGO }}
        >
          <Plus className="h-4 w-4" /> New Task
        </button></Can>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <button
          onClick={() => setMineOnly((v) => !v)}
          className="px-3 py-2 rounded-xl text-sm font-semibold border transition-colors"
          style={mineOnly ? { background: `${INDIGO}14`, borderColor: `${INDIGO}40`, color: INDIGO } : { borderColor: "hsl(var(--input))" }}
        >
          My Tasks
        </button>
        <div className="w-44">
          <SearchableSelect
            value={statusFilter} onChange={setStatusFilter} placeholder="Status" accent={INDIGO}
            options={[{ value: "", label: "All Statuses" }, ...STATUS_OPTIONS]}
          />
        </div>
        <div className="w-40">
          <SearchableSelect
            value={priorityFilter} onChange={setPriorityFilter} placeholder="Priority" accent={INDIGO}
            options={[{ value: "", label: "All Priorities" }, ...PRIORITY_OPTIONS]}
          />
        </div>
      </div>

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <p className="text-sm font-medium">{tasks.length} task{tasks.length !== 1 ? "s" : ""}</p>
        </div>
        <DataTable columns={columns} data={tasks} loading={isLoading} />
      </div>

      {showCreate && <CreateTaskModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
