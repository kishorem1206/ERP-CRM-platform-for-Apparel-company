"use client";
import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Plus, Phone, Users, StickyNote, CheckSquare, Mail, CheckCircle2, Circle,
  List as ListIcon, CalendarDays, ChevronLeft, ChevronRight, X, Pencil, Trash2,
} from "lucide-react";
import { useRouter } from "next/navigation";
import {
  addDays, addMonths, endOfMonth, endOfWeek, format, isSameDay, isSameMonth,
  isToday, startOfMonth, startOfWeek, subMonths,
} from "date-fns";
import api from "@/lib/api";
import { DataTable, Column } from "@/components/shared/data-table";
import { ModalPortal } from "@/components/shared/modal-portal";
import { ModalShell } from "@/components/shared/modal-shell";
import { SearchableSelect } from "@/components/shared/searchable-select";

const inputCls =
  "w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

const INDIGO = "#0049A7";

const ACTIVITY_ICONS: Record<string, React.ReactNode> = {
  call: <Phone className="h-3.5 w-3.5" />,
  meeting: <Users className="h-3.5 w-3.5" />,
  note: <StickyNote className="h-3.5 w-3.5" />,
  task: <CheckSquare className="h-3.5 w-3.5" />,
  email: <Mail className="h-3.5 w-3.5" />,
};

const ACTIVITY_COLORS: Record<string, string> = {
  call: "#0049A7",
  meeting: "#0F78FF",
  note: "#A096F7",
  task: "#0F78FF",
  email: "#0049A7",
};

const TYPE_FILTERS = [
  { label: "All", value: "" },
  { label: "Call", value: "call" },
  { label: "Meeting", value: "meeting" },
  { label: "Note", value: "note" },
  { label: "Task", value: "task" },
  { label: "Email", value: "email" },
];

interface Activity {
  id: string;
  type: string;
  title: string;
  lead_id: string | null;
  lead_title: string | null;
  person_id: string | null;
  person_name: string | null;
  schedule_from: string | null;
  schedule_to: string | null;
  is_done: boolean;
  comment: string | null;
  assigned_to: string | null;
  assigned_to_name: string | null;
}

interface UserOption {
  id: string;
  name: string;
  email: string;
}

const ACTIVITY_TYPES = ["call", "meeting", "note", "task", "email"] as const;

function toDatetimeLocal(iso: string | null): string {
  if (!iso) return "";
  return format(new Date(iso), "yyyy-MM-dd'T'HH:mm");
}

function EditActivityModal({
  activity, onClose,
}: {
  activity: Activity;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    type: activity.type,
    title: activity.title,
    comment: activity.comment ?? "",
    schedule_from: toDatetimeLocal(activity.schedule_from),
    schedule_to: toDatetimeLocal(activity.schedule_to),
    assigned_to: activity.assigned_to ?? "",
  });

  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: usersData } = useQuery({
    queryKey: ["crm-admin-users"],
    queryFn: () => api.get("/admin/users?page_size=200").then((r) => r.data),
  });
  const users: UserOption[] = usersData?.data ?? [];

  function invalidateActivityQueries() {
    queryClient.invalidateQueries({ queryKey: ["crm-activities-list"] });
    queryClient.invalidateQueries({ queryKey: ["crm-activities-calendar"] });
    queryClient.invalidateQueries({ queryKey: ["crm-activities-unscheduled"] });
  }

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.patch(`/crm/activities/${activity.id}`, data),
    onSuccess: () => {
      invalidateActivityQueries();
      onClose();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/crm/activities/${activity.id}`),
    onSuccess: () => {
      invalidateActivityQueries();
      onClose();
    },
  });

  function set<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function handleSubmit() {
    if (!form.title.trim()) return;
    mutation.mutate({
      type: form.type,
      title: form.title,
      comment: form.comment || null,
      schedule_from: form.schedule_from || null,
      schedule_to: form.schedule_to || null,
      assigned_to: form.assigned_to || null,
    });
  }

  return (
    <ModalShell maxWidth="max-w-md" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">Edit Activity</h2>
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
      <div className="flex items-center justify-between gap-3 p-6 border-t">
        <button
          onClick={() => setConfirmDelete(true)}
          className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-xl text-[#1D0DB0] hover:bg-[#1D0DB0]/10 transition-colors"
        >
          <Trash2 className="h-3.5 w-3.5" /> Delete
        </button>
        <div className="flex gap-3">
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
            {mutation.isPending ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </div>

      {confirmDelete && (
        <ModalShell maxWidth="max-w-xs" onClose={() => setConfirmDelete(false)}>
          <div className="p-6">
            <p className="text-sm font-medium mb-1">Delete this activity?</p>
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
                className="px-4 py-2 text-sm rounded-xl text-white font-semibold bg-[#1D0DB0] hover:bg-[#170a8f] transition-colors disabled:opacity-50"
              >
                {deleteMutation.isPending ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </ModalShell>
      )}
    </ModalShell>
  );
}

function ActivityTypeBadge({ type }: { type: string }) {
  const color = ACTIVITY_COLORS[type] ?? INDIGO;
  const icon = ACTIVITY_ICONS[type] ?? <CheckSquare className="h-3.5 w-3.5" />;
  const label = type.charAt(0).toUpperCase() + type.slice(1);
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap"
      style={{ background: `${color}18`, color }}
    >
      {icon}
      {label}
    </span>
  );
}

// ── Calendar view ──────────────────────────────────────────────────────────────
const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MAX_CHIPS_PER_DAY = 3;

function ActivityDetailPanel({
  title, subtitle, activities, onClose, onMarkDone, onEdit, doneMutationPending, emptyMessage,
}: {
  title: string;
  subtitle?: string;
  activities: Activity[];
  onClose: () => void;
  onMarkDone: (id: string, done: boolean) => void;
  onEdit: (activity: Activity) => void;
  doneMutationPending: boolean;
  emptyMessage: string;
}) {
  const sorted = [...activities].sort((a, b) =>
    (a.schedule_from ?? "").localeCompare(b.schedule_from ?? "")
  );
  return (
    <ModalPortal>
    <>
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />
      <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-sm bg-card border-l border-border shadow-2xl flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div>
            {subtitle && (
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                {subtitle}
              </p>
            )}
            <h3 className="text-base font-semibold mt-0.5">{title}</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-md hover:bg-muted text-muted-foreground transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          {sorted.length === 0 && (
            <p className="text-sm text-muted-foreground">{emptyMessage}</p>
          )}
          {sorted.map((a) => {
            const color = ACTIVITY_COLORS[a.type] ?? INDIGO;
            return (
              <div key={a.id} className="flex gap-3 p-3 rounded-xl border border-border bg-background">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{ background: `${color}18`, color }}
                >
                  {ACTIVITY_ICONS[a.type] ?? <CheckSquare className="h-3.5 w-3.5" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium leading-tight">{a.title}</p>
                    <div className="flex items-center gap-0.5 flex-shrink-0">
                      <button
                        onClick={() => onEdit(a)}
                        className="p-0.5 rounded transition-colors hover:bg-muted text-muted-foreground"
                        title="Edit"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => onMarkDone(a.id, !a.is_done)}
                        disabled={doneMutationPending}
                        className="p-0.5 rounded transition-colors hover:bg-muted disabled:cursor-default disabled:opacity-50"
                        title={a.is_done ? "Mark not done" : "Mark done"}
                      >
                        {a.is_done ? (
                          <CheckCircle2 className="h-4 w-4 text-blue-500" />
                        ) : (
                          <Circle className="h-4 w-4 text-muted-foreground" />
                        )}
                      </button>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {a.schedule_from ? format(new Date(a.schedule_from), "h:mm a") : "No time set"}
                  </p>
                  {(a.lead_title || a.person_name) && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {[a.lead_title, a.person_name].filter(Boolean).join(" · ")}
                    </p>
                  )}
                  {a.comment && <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">{a.comment}</p>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
    </ModalPortal>
  );
}

function ActivityCalendar({
  typeFilter, doneMutation, onEdit,
}: {
  typeFilter: string;
  doneMutation: ReturnType<typeof useMutation<unknown, unknown, { id: string; done: boolean }>>;
  onEdit: (activity: Activity) => void;
}) {
  const [month, setMonth] = useState(() => startOfMonth(new Date()));
  const [selectedDay, setSelectedDay] = useState<Date | null>(null);
  const [showUnscheduled, setShowUnscheduled] = useState(false);

  const gridStart = startOfWeek(startOfMonth(month), { weekStartsOn: 1 });
  const gridEnd = endOfWeek(endOfMonth(month), { weekStartsOn: 1 });

  const days = useMemo(() => {
    const result: Date[] = [];
    let cursor = gridStart;
    while (cursor <= gridEnd) {
      result.push(cursor);
      cursor = addDays(cursor, 1);
    }
    return result;
  }, [gridStart, gridEnd]);

  const { data, isLoading } = useQuery({
    queryKey: ["crm-activities-calendar", typeFilter, format(gridStart, "yyyy-MM-dd"), format(gridEnd, "yyyy-MM-dd")],
    queryFn: async () => {
      const params = new URLSearchParams({
        page_size: "500",
        date_from: gridStart.toISOString(),
        date_to: addDays(gridEnd, 1).toISOString(),
      });
      if (typeFilter) params.set("activity_type", typeFilter);
      const res = await api.get(`/crm/activities?${params}`);
      return res.data;
    },
  });

  const activities: Activity[] = data?.data ?? [];

  const { data: unscheduledData } = useQuery({
    queryKey: ["crm-activities-unscheduled", typeFilter],
    queryFn: async () => {
      const params = new URLSearchParams({ page_size: "200", unscheduled: "true" });
      if (typeFilter) params.set("activity_type", typeFilter);
      const res = await api.get(`/crm/activities?${params}`);
      return res.data;
    },
  });
  const unscheduledActivities: Activity[] = unscheduledData?.data ?? [];

  const byDay = useMemo(() => {
    const map = new Map<string, Activity[]>();
    for (const a of activities) {
      if (!a.schedule_from) continue;
      const key = format(new Date(a.schedule_from), "yyyy-MM-dd");
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(a);
    }
    return map;
  }, [activities]);

  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <h2 className="text-base font-semibold">{format(month, "MMMM yyyy")}</h2>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setMonth((m) => subMonths(m, 1))}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            onClick={() => setMonth(startOfMonth(new Date()))}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            Today
          </button>
          <button
            onClick={() => setMonth((m) => addMonths(m, 1))}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground transition-colors"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {unscheduledActivities.length > 0 && (
        <button
          onClick={() => setShowUnscheduled(true)}
          className="flex items-center gap-2 w-full px-6 py-2.5 border-b border-border text-xs text-muted-foreground hover:bg-muted/30 transition-colors text-left"
        >
          <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 bg-muted-foreground/50" />
          <span>
            <span className="font-semibold text-foreground">{unscheduledActivities.length}</span> unscheduled — no date set, won't appear on the calendar grid
          </span>
        </button>
      )}

      <div className="grid grid-cols-7 border-b border-border">
        {WEEKDAY_LABELS.map((d) => (
          <div key={d} className="px-2 py-2 text-center text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            {d}
          </div>
        ))}
      </div>

      <div className={`grid grid-cols-7 ${isLoading ? "opacity-50" : ""}`}>
        {days.map((day) => {
          const key = format(day, "yyyy-MM-dd");
          const dayActivities = byDay.get(key) ?? [];
          const inMonth = isSameMonth(day, month);
          const today = isToday(day);
          const overflow = dayActivities.length - MAX_CHIPS_PER_DAY;
          return (
            <button
              key={key}
              onClick={() => setSelectedDay(day)}
              className={`min-h-[104px] border-b border-r border-border p-1.5 text-left align-top hover:bg-muted/30 transition-colors ${
                inMonth ? "" : "bg-muted/20"
              }`}
            >
              <span
                className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-semibold ${
                  today ? "text-white" : inMonth ? "text-foreground" : "text-muted-foreground"
                }`}
                style={today ? { background: INDIGO } : undefined}
              >
                {format(day, "d")}
              </span>
              <div className="mt-1 space-y-0.5">
                {dayActivities.slice(0, MAX_CHIPS_PER_DAY).map((a) => {
                  const color = ACTIVITY_COLORS[a.type] ?? INDIGO;
                  return (
                    <div
                      key={a.id}
                      className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium truncate"
                      style={{ background: `${color}18`, color }}
                      title={a.title}
                    >
                      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
                      <span className="truncate">{a.title}</span>
                    </div>
                  );
                })}
                {overflow > 0 && (
                  <p className="text-[10px] text-muted-foreground pl-1.5">+{overflow} more</p>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {selectedDay && (
        <ActivityDetailPanel
          title={format(selectedDay, "d MMMM yyyy")}
          subtitle={format(selectedDay, "EEEE")}
          activities={byDay.get(format(selectedDay, "yyyy-MM-dd")) ?? []}
          onClose={() => setSelectedDay(null)}
          onMarkDone={(id, done) => doneMutation.mutate({ id, done })}
          onEdit={onEdit}
          doneMutationPending={doneMutation.isPending}
          emptyMessage="No activities scheduled on this day."
        />
      )}

      {showUnscheduled && (
        <ActivityDetailPanel
          title="Unscheduled"
          subtitle="No date set"
          activities={unscheduledActivities}
          onClose={() => setShowUnscheduled(false)}
          onMarkDone={(id, done) => doneMutation.mutate({ id, done })}
          onEdit={onEdit}
          doneMutationPending={doneMutation.isPending}
          emptyMessage="Nothing unscheduled."
        />
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function ActivitiesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [typeFilter, setTypeFilter] = useState("");
  const [view, setView] = useState<"list" | "calendar">("list");
  const [editingActivity, setEditingActivity] = useState<Activity | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["crm-activities-list", typeFilter],
    queryFn: async () => {
      const params = new URLSearchParams({ page_size: "100" });
      if (typeFilter) params.set("activity_type", typeFilter);
      const res = await api.get(`/crm/activities?${params}`);
      return res.data;
    },
    enabled: view === "list",
  });

  const doneMutation = useMutation({
    mutationFn: ({ id, done }: { id: string; done: boolean }) =>
      api.patch(`/crm/activities/${id}/done`, { is_done: done }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-activities-list"] });
      queryClient.invalidateQueries({ queryKey: ["crm-activities-calendar"] });
      queryClient.invalidateQueries({ queryKey: ["crm-activities-unscheduled"] });
    },
  });

  const activities: Activity[] = data?.data ?? [];

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: "type",
      header: "Type",
      render: (row) => <ActivityTypeBadge type={row.type as string} />,
    },
    { key: "title", header: "Title", sortable: true },
    {
      key: "lead_title",
      header: "Lead",
      render: (row) => (row.lead_title as string) || "—",
    },
    {
      key: "person_name",
      header: "Person",
      render: (row) => (row.person_name as string) || "—",
    },
    {
      key: "schedule_from",
      header: "Scheduled",
      render: (row) =>
        row.schedule_from
          ? new Date(row.schedule_from as string).toLocaleString("en-IN", {
              dateStyle: "medium",
              timeStyle: "short",
            })
          : "—",
    },
    {
      key: "is_done",
      header: "Done",
      render: (row) => {
        const isDone = row.is_done as boolean;
        return (
          <button
            onClick={(e) => {
              e.stopPropagation();
              doneMutation.mutate({ id: row.id as string, done: !isDone });
            }}
            disabled={doneMutation.isPending}
            className="p-0.5 rounded transition-colors hover:bg-muted disabled:cursor-default disabled:opacity-50"
            title={isDone ? "Mark not done" : "Mark done"}
          >
            {isDone ? (
              <CheckCircle2 className="h-4 w-4 text-blue-500" />
            ) : (
              <Circle className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
        );
      },
    },
    {
      key: "edit",
      header: "",
      render: (row) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            setEditingActivity(row as unknown as Activity);
          }}
          className="p-1 rounded transition-colors hover:bg-muted text-muted-foreground"
          title="Edit activity"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
      ),
    },
  ];

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            CRM / ACTIVITIES
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Activities</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Calls, meetings, notes, tasks, and emails across all leads.
          </p>
        </div>
        <button
          onClick={() => router.push("/crm/activities/new")}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
          style={{ background: INDIGO }}
        >
          <Plus className="h-4 w-4" /> Log Activity
        </button>
      </div>

      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit flex-wrap">
          {TYPE_FILTERS.map((t) => (
            <button
              key={t.value}
              onClick={() => setTypeFilter(t.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                typeFilter === t.value
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl w-fit">
          <button
            onClick={() => setView("list")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
              view === "list" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <ListIcon className="h-3.5 w-3.5" /> List
          </button>
          <button
            onClick={() => setView("calendar")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
              view === "calendar" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <CalendarDays className="h-3.5 w-3.5" /> Calendar
          </button>
        </div>
      </div>

      {view === "list" ? (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-border">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                {typeFilter ? typeFilter.toUpperCase() + "S" : "ALL ACTIVITIES"}
              </p>
              <p className="text-sm font-medium mt-0.5">
                {activities.length} record{activities.length !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
          <div className="p-6">
            <DataTable
              columns={columns}
              data={activities as unknown as Record<string, unknown>[]}
              loading={isLoading}
              emptyMessage="No activities found — click Log Activity to add one"
            />
          </div>
        </div>
      ) : (
        <ActivityCalendar typeFilter={typeFilter} doneMutation={doneMutation} onEdit={setEditingActivity} />
      )}

      {editingActivity && (
        <EditActivityModal activity={editingActivity} onClose={() => setEditingActivity(null)} />
      )}
    </div>
  );
}
