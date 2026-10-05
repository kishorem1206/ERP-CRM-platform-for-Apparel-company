"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Flame, Phone, AlertTriangle, CheckSquare, Inbox, ArrowRight, Loader2 } from "lucide-react";
import api from "@/lib/api";
import { getCurrentUserId } from "@/lib/auth";

// ── Palette ───────────────────────────────────────────────────────────────────
const INDIGO = "#0049A7";

interface LeadRow {
  id: string;
  title: string;
  person_name: string | null;
  organization_name: string | null;
  priority: string | null;
  score: number | null;
  first_contacted_at: string | null;
  next_follow_up_at: string | null;
  created_at: string;
}

interface TaskRow {
  id: string;
  title: string;
  lead_id: string | null;
  lead_title: string | null;
  due_at: string | null;
  priority: string;
  status: string;
}

function Section({
  title, icon: Icon, count, color, children, emptyMessage,
}: {
  title: string; icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>; count: number; color: string;
  children: React.ReactNode; emptyMessage: string;
}) {
  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4" style={{ color }} />
          <p className="font-semibold">{title}</p>
        </div>
        <span
          className="px-2 py-0.5 rounded-full text-xs font-bold tabular-nums"
          style={{ background: `${color}18`, color }}
        >
          {count}
        </span>
      </div>
      <div className="divide-y divide-border">
        {count === 0 ? (
          <p className="px-5 py-6 text-sm text-muted-foreground text-center">{emptyMessage}</p>
        ) : (
          children
        )}
      </div>
    </div>
  );
}

export default function MyWorkPage() {
  const router = useRouter();
  const myId = getCurrentUserId();

  const { data: highPriorityData, isLoading: highLoading } = useQuery({
    queryKey: ["my-work-high-priority", myId],
    queryFn: async () => (await api.get(`/crm/leads?assigned_to=${myId}&priority=high&page_size=50`)).data,
    enabled: !!myId,
  });
  const highPriorityLeads: LeadRow[] = (highPriorityData?.data ?? []).filter((l: LeadRow) => !l.first_contacted_at);

  const { data: dueData } = useQuery({
    queryKey: ["my-work-followups-due", myId],
    queryFn: async () => (await api.get(`/crm/leads?assigned_to=${myId}&follow_up_due=true&page_size=50`)).data,
    enabled: !!myId,
  });
  const followUpsDue: LeadRow[] = dueData?.data ?? [];
  const now = Date.now();
  const overdue = followUpsDue.filter((l) => l.next_follow_up_at && new Date(l.next_follow_up_at).getTime() < now);
  const dueToday = followUpsDue.filter((l) => !overdue.includes(l));

  const { data: tasksData, isLoading: tasksLoading } = useQuery({
    queryKey: ["my-work-tasks", myId],
    queryFn: async () => (await api.get(`/crm/tasks?assigned_to=${myId}&status=pending&page_size=50`)).data,
    enabled: !!myId,
  });
  const tasks: TaskRow[] = tasksData?.data ?? [];

  const { data: newLeadsData } = useQuery({
    queryKey: ["my-work-new-leads", myId],
    queryFn: async () => (await api.get(`/crm/leads?assigned_to=${myId}&page_size=50`)).data,
    enabled: !!myId,
  });
  const newLeads: LeadRow[] = (newLeadsData?.data ?? []).filter((l: LeadRow) => {
    const ageMs = now - new Date(l.created_at).getTime();
    return ageMs < 24 * 60 * 60 * 1000;
  });

  const loading = highLoading || tasksLoading;

  return (
    <div className="p-8 space-y-6">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">CRM</p>
        <h1 className="text-2xl font-bold tracking-tight">My Work</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Everything that needs your attention today, in one place.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-muted-foreground text-sm">
          <Loader2 className="h-4 w-4 animate-spin mr-2" /> Loading…
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <Section title="High Priority — Not Yet Contacted" icon={Flame} count={highPriorityLeads.length} color="#EF4444" emptyMessage="No uncontacted high-priority leads. Nice work.">
            {highPriorityLeads.map((l) => (
              <button
                key={l.id}
                onClick={() => router.push(`/crm/leads/${l.id}`)}
                className="w-full flex items-center justify-between gap-3 px-5 py-3 text-left hover:bg-muted/30 transition-colors"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{l.title}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {[l.person_name, l.organization_name].filter(Boolean).join(" · ") || "—"}
                  </p>
                </div>
                <span className="text-xs font-bold tabular-nums flex-shrink-0" style={{ color: "#EF4444" }}>
                  {l.score}
                </span>
              </button>
            ))}
          </Section>

          <Section title="Overdue Follow-ups" icon={AlertTriangle} count={overdue.length} color="#F59E0B" emptyMessage="No overdue follow-ups.">
            {overdue.map((l) => (
              <button
                key={l.id}
                onClick={() => router.push(`/crm/leads/${l.id}`)}
                className="w-full flex items-center justify-between gap-3 px-5 py-3 text-left hover:bg-muted/30 transition-colors"
              >
                <p className="text-sm font-medium truncate">{l.title}</p>
                <span className="text-xs text-muted-foreground flex-shrink-0">
                  {l.next_follow_up_at && new Date(l.next_follow_up_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}
                </span>
              </button>
            ))}
          </Section>

          <Section title="Follow-ups Due Today" icon={Phone} count={dueToday.length} color={INDIGO} emptyMessage="Nothing scheduled for today.">
            {dueToday.map((l) => (
              <button
                key={l.id}
                onClick={() => router.push(`/crm/leads/${l.id}`)}
                className="w-full flex items-center justify-between gap-3 px-5 py-3 text-left hover:bg-muted/30 transition-colors"
              >
                <p className="text-sm font-medium truncate">{l.title}</p>
                <span className="text-xs text-muted-foreground flex-shrink-0">
                  {l.next_follow_up_at && new Date(l.next_follow_up_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                </span>
              </button>
            ))}
          </Section>

          <Section title="My Pending Tasks" icon={CheckSquare} count={tasks.length} color="#8174F5" emptyMessage="No pending tasks.">
            {tasks.map((t) => (
              <Link
                key={t.id}
                href={t.lead_id ? `/crm/leads/${t.lead_id}` : "/crm/tasks"}
                className="w-full flex items-center justify-between gap-3 px-5 py-3 hover:bg-muted/30 transition-colors"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{t.title}</p>
                  {t.lead_title && <p className="text-xs text-muted-foreground truncate">{t.lead_title}</p>}
                </div>
                {t.due_at && (
                  <span className="text-xs text-muted-foreground flex-shrink-0">
                    {new Date(t.due_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}
                  </span>
                )}
              </Link>
            ))}
          </Section>

          <Section title="New Leads (Last 24h)" icon={Inbox} count={newLeads.length} color="#10B981" emptyMessage="No new leads assigned in the last day.">
            {newLeads.map((l) => (
              <button
                key={l.id}
                onClick={() => router.push(`/crm/leads/${l.id}`)}
                className="w-full flex items-center justify-between gap-3 px-5 py-3 text-left hover:bg-muted/30 transition-colors"
              >
                <p className="text-sm font-medium truncate">{l.title}</p>
                <ArrowRight className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
              </button>
            ))}
          </Section>
        </div>
      )}
    </div>
  );
}
