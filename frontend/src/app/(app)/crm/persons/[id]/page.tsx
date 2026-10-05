"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, Phone, Mail, MapPin, Building2, Thermometer,
  MessageCircle, Plus, Pencil, Trash2, X, Check,
} from "lucide-react";
import api from "@/lib/api";
import { Can } from "@/lib/permissions";

const INDIGO = "#0049A7";

// ── Types ──────────────────────────────────────────────────────────────────────
interface StageStrip {
  id: string;
  name: string;
  color: string | null;
  sort_order: number;
  is_won: boolean;
  is_lost: boolean;
}

interface Lead {
  id: string;
  title: string;
  lead_value: number;
  temperature: string;
  status: string;
  pipeline_id: string | null;
  pipeline_name: string | null;
  stage_id: string | null;
  stage_name: string | null;
  stage_color: string | null;
  all_stages: StageStrip[];
  assigned_to: string | null;
  created_at: string;
}

interface Activity {
  id: string;
  title: string;
  type: string;
  comment: string | null;
  is_done: boolean;
  schedule_from: string | null;
  lead_id: string | null;
}

interface Note {
  id: string;
  body: string;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

interface Person360 {
  id: string;
  name: string;
  job_title: string | null;
  city: string | null;
  emails: { value: string; label: string }[];
  contact_numbers: { value: string; label: string }[];
  whatsapp_number: string | null;
  organization_id: string | null;
  organization_name: string | null;
  assigned_to: string | null;
  created_at: string;
  leads: Lead[];
  activities: Activity[];
  notes: Note[];
}

// ── Temperature badge ─────────────────────────────────────────────────────────
const TEMP_COLORS: Record<string, string> = {
  hot: "bg-violet-100 text-violet-700",
  warm: "bg-violet-100 text-violet-700",
  cold: "bg-blue-100 text-blue-700",
};

function TempBadge({ t }: { t: string }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold ${TEMP_COLORS[t] ?? "bg-muted text-muted-foreground"}`}>
      <Thermometer className="h-3 w-3" />
      {t.charAt(0).toUpperCase() + t.slice(1)}
    </span>
  );
}

// ── Stage journey strip ───────────────────────────────────────────────────────
function StageStrip({ stages, currentStageId }: { stages: StageStrip[]; currentStageId: string | null }) {
  const sorted = [...stages].sort((a, b) => a.sort_order - b.sort_order);
  return (
    <div className="flex items-center gap-0 overflow-x-auto pb-1 scrollbar-thin">
      {sorted.map((s, i) => {
        const isCurrent = s.id === currentStageId;
        const color = s.color ?? INDIGO;
        return (
          <div key={s.id} className="flex items-center shrink-0">
            {i > 0 && (
              <div className="w-4 h-px bg-border shrink-0" />
            )}
            <div
              className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-all whitespace-nowrap ${
                isCurrent
                  ? "text-white border-transparent shadow-sm"
                  : "bg-transparent border-border text-muted-foreground"
              }`}
              style={isCurrent ? { background: color, borderColor: color } : undefined}
            >
              {s.name}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Lead card ─────────────────────────────────────────────────────────────────
function LeadCard({ lead }: { lead: Lead }) {
  const router = useRouter();
  return (
    <div
      onClick={() => router.push(`/crm/leads/${lead.id}`)}
      className="border border-border rounded-xl p-4 hover:border-[#0049A7]/40 hover:shadow-sm transition-all cursor-pointer space-y-3"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-medium text-sm leading-tight">{lead.title}</p>
          {lead.pipeline_name && (
            <p className="text-xs text-muted-foreground mt-0.5">{lead.pipeline_name}</p>
          )}
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <TempBadge t={lead.temperature} />
          <span
            className={`text-[11px] px-2 py-0.5 rounded font-bold ${
              lead.status === "won" ? "bg-blue-100 text-blue-700"
              : lead.status === "lost" ? "bg-violet-100 text-violet-700"
              : "bg-muted text-muted-foreground"
            }`}
          >
            {lead.status}
          </span>
        </div>
      </div>

      {lead.all_stages.length > 0 && (
        <StageStrip stages={lead.all_stages} currentStageId={lead.stage_id} />
      )}

      {lead.lead_value > 0 && (
        <p className="text-sm font-semibold" style={{ color: INDIGO }}>
          ₹{new Intl.NumberFormat("en-IN").format(lead.lead_value)}
        </p>
      )}
    </div>
  );
}

// ── Note card ─────────────────────────────────────────────────────────────────
function NoteCard({
  note, personId, onDeleted,
}: {
  note: Note; personId: string; onDeleted: () => void;
}) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(note.body);

  const updateMut = useMutation({
    mutationFn: (body: string) => api.patch(`/crm/notes/${note.id}`, { body }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["person360", personId] }); setEditing(false); },
  });

  const deleteMut = useMutation({
    mutationFn: () => api.delete(`/crm/notes/${note.id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["person360", personId] }); onDeleted(); },
  });

  return (
    <div className="border border-border rounded-xl p-4 space-y-2">
      {editing ? (
        <>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={3}
            className="w-full text-sm border border-input rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-ring resize-none"
          />
          <div className="flex gap-2">
            <Can perm="crm.edit"><button
              onClick={() => updateMut.mutate(draft)}
              disabled={updateMut.isPending || !draft.trim()}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-white disabled:opacity-50"
              style={{ background: INDIGO }}
            >
              <Check className="h-3 w-3" /> Save
            </button></Can>
            <button
              onClick={() => { setEditing(false); setDraft(note.body); }}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium border border-input hover:bg-muted"
            >
              <X className="h-3 w-3" /> Cancel
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="text-sm whitespace-pre-wrap leading-relaxed">{note.body}</p>
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              {note.created_by_name ?? "You"} · {new Date(note.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
            </p>
            <div className="flex gap-1">
              <Can perm="crm.edit"><button
                onClick={() => setEditing(true)}
                className="p-1 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
              >
                <Pencil className="h-3.5 w-3.5" />
              </button></Can>
              <Can perm="crm.edit"><button
                onClick={() => deleteMut.mutate()}
                disabled={deleteMut.isPending}
                className="p-1 rounded hover:bg-violet-50 hover:text-violet-600 transition-colors text-muted-foreground"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button></Can>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── Add Note form ─────────────────────────────────────────────────────────────
function AddNoteForm({ personId }: { personId: string }) {
  const qc = useQueryClient();
  const [body, setBody] = useState("");
  const [open, setOpen] = useState(false);

  const mut = useMutation({
    mutationFn: () => api.post("/crm/notes", { body, person_id: personId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["person360", personId] });
      setBody("");
      setOpen(false);
    },
  });

  if (!open) {
    return (
      <Can perm="crm.create"><button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
      >
        <Plus className="h-4 w-4" /> Add Note
      </button></Can>
    );
  }

  return (
    <div className="border border-input rounded-xl p-4 space-y-3 bg-muted/20">
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Write a note…"
        rows={3}
        autoFocus
        className="w-full text-sm border border-input rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-ring resize-none bg-background"
      />
      <div className="flex gap-2">
        <button
          onClick={() => mut.mutate()}
          disabled={mut.isPending || !body.trim()}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mut.isPending ? "Saving…" : "Save Note"}
        </button>
        <button
          onClick={() => { setOpen(false); setBody(""); }}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-input hover:bg-muted"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
type Tab = "leads" | "notes" | "activities";

// ── Page ──────────────────────────────────────────────────────────────────────
export default function PersonDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("leads");

  const { data, isLoading } = useQuery({
    queryKey: ["person360", id],
    queryFn: async () => {
      const res = await api.get(`/crm/persons/${id}/360`);
      return res.data?.data as Person360;
    },
    enabled: !!id,
  });

  if (isLoading) {
    return <div className="p-8 text-sm text-muted-foreground">Loading…</div>;
  }
  if (!data) {
    return <div className="p-8 text-sm text-muted-foreground">Person not found.</div>;
  }

  const primaryPhone = data.contact_numbers?.[0]?.value;
  const primaryEmail = data.emails?.[0]?.value;

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: "leads", label: "Leads", count: data.leads.length },
    { key: "notes", label: "Notes", count: data.notes.length },
    { key: "activities", label: "Activities", count: data.activities.length },
  ];

  return (
    <div className="p-8 space-y-8 max-w-5xl mx-auto">
      {/* Back */}
      <button
        onClick={() => router.push("/crm/persons")}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" /> Back to Contacts
      </button>

      {/* Header card */}
      <div className="bg-card border border-border rounded-2xl p-6 flex flex-col sm:flex-row sm:items-start gap-5">
        {/* Avatar */}
        <div
          className="h-16 w-16 rounded-2xl flex items-center justify-center text-2xl font-bold text-white shrink-0"
          style={{ background: INDIGO }}
        >
          {data.name.charAt(0).toUpperCase()}
        </div>

        {/* Info */}
        <div className="flex-1 space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">{data.name}</h1>
          {data.job_title && (
            <p className="text-sm text-muted-foreground">{data.job_title}</p>
          )}
          <div className="flex flex-wrap gap-3 pt-1">
            {primaryPhone && (
              <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Phone className="h-3.5 w-3.5" /> {primaryPhone}
              </span>
            )}
            {primaryEmail && (
              <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Mail className="h-3.5 w-3.5" /> {primaryEmail}
              </span>
            )}
            {data.city && (
              <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <MapPin className="h-3.5 w-3.5" /> {data.city}
              </span>
            )}
            {data.organization_name && (
              <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Building2 className="h-3.5 w-3.5" /> {data.organization_name}
              </span>
            )}
            {data.whatsapp_number && (
              <a
                href={`https://wa.me/${data.whatsapp_number.replace(/\D/g, "")}`}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 transition-colors"
              >
                <MessageCircle className="h-3.5 w-3.5" /> WhatsApp
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div>
        <div className="flex gap-0.5 border-b border-border mb-6">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all -mb-px ${
                tab === t.key
                  ? "border-[#0049A7] text-[#0049A7]"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
              {t.count > 0 && (
                <span className="ml-1.5 text-[11px] bg-muted px-1.5 py-0.5 rounded font-bold">
                  {t.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === "leads" && (
          <div className="space-y-4">
            {data.leads.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No leads yet. Create a lead and link it to this person.
              </p>
            ) : (
              data.leads.map((lead) => <LeadCard key={lead.id} lead={lead} />)
            )}
          </div>
        )}

        {tab === "notes" && (
          <div className="space-y-4">
            <AddNoteForm personId={id} />
            {data.notes.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No notes yet.</p>
            ) : (
              data.notes.map((note) => (
                <NoteCard key={note.id} note={note} personId={id} onDeleted={() => {}} />
              ))
            )}
          </div>
        )}

        {tab === "activities" && (
          <div className="space-y-3">
            {data.activities.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No activities yet.</p>
            ) : (
              data.activities.map((a) => (
                <div key={a.id} className="border border-border rounded-xl px-4 py-3 flex items-center gap-3">
                  <div className={`h-2 w-2 rounded-full shrink-0 ${a.is_done ? "bg-blue-500" : "bg-violet-400"}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{a.title}</p>
                    {a.comment && <p className="text-xs text-muted-foreground truncate">{a.comment}</p>}
                  </div>
                  <div className="text-xs text-muted-foreground shrink-0">
                    {a.type}
                    {a.schedule_from && (
                      <> · {new Date(a.schedule_from).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}</>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
