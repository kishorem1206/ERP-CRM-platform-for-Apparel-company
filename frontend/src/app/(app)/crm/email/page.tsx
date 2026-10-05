"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Mail, Search, Send, Inbox, X, Loader2, Plus, ChevronRight,
} from "lucide-react";
import api from "@/lib/api";
import { ModalShell } from "@/components/shared/modal-shell";
import { Can } from "@/lib/permissions";

// ── Palette ───────────────────────────────────────────────────────────────────
const INDIGO = "#0049A7";

// ── Types ─────────────────────────────────────────────────────────────────────
interface EmailRecord {
  id: string;
  direction: "inbound" | "outbound";
  subject: string;
  from_address: string;
  to_addresses: string[];
  cc_addresses?: string[];
  status: string;
  sent_at: string | null;
  created_at: string;
  body_text?: string;
}

type FilterType = "all" | "sent" | "received";

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatRelativeTime(ts: string): string {
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0)
    return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return d.toLocaleDateString("en-IN", { weekday: "short" });
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

const inputCls =
  "w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

// ── ComposeEmailModal ─────────────────────────────────────────────────────────
function ComposeEmailModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [to, setTo] = useState("");
  const [cc, setCc] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [smtpError, setSmtpError] = useState("");

  const sendMutation = useMutation({
    mutationFn: async () => {
      const toAddresses = to.split(",").map((s) => s.trim()).filter(Boolean);
      const ccAddresses = cc.split(",").map((s) => s.trim()).filter(Boolean);
      const res = await api.post("/crm/emails", {
        subject,
        body_text: body,
        to_addresses: toAddresses,
        cc_addresses: ccAddresses.length ? ccAddresses : undefined,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-emails-inbox"] });
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

  const canSend = to.trim() && subject.trim() && body.trim() && !sendMutation.isPending;

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
                  <Link
                    href="/crm/settings"
                    className="underline font-semibold"
                    style={{ color: INDIGO }}
                    onClick={onClose}
                  >
                    Go to Settings
                  </Link>
                )}
              </span>
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              To <span className="text-destructive">*</span>
            </label>
            <input
              className={inputCls}
              placeholder="email@example.com, another@example.com"
              value={to}
              onChange={(e) => setTo(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">CC</label>
            <input
              className={inputCls}
              placeholder="cc@example.com"
              value={cc}
              onChange={(e) => setCc(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Subject <span className="text-destructive">*</span>
            </label>
            <input
              className={inputCls}
              placeholder="Subject…"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Body <span className="text-destructive">*</span>
            </label>
            <textarea
              className={`${inputCls} resize-none`}
              rows={7}
              placeholder="Write your message…"
              value={body}
              onChange={(e) => setBody(e.target.value)}
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
            disabled={!canSend}
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

// ── Email Detail Panel ────────────────────────────────────────────────────────
function EmailDetail({ email }: { email: EmailRecord }) {
  const ts = email.sent_at ?? email.created_at;
  const isOut = email.direction === "outbound";

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-5">
      <div className="flex items-start gap-3">
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white shrink-0"
          style={{ background: isOut ? INDIGO : "#64748B" }}
        >
          <Mail className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-base font-semibold leading-tight">{email.subject}</h2>
          <div className="mt-2 space-y-1 text-sm text-muted-foreground">
            <p>
              <span className="font-medium text-foreground">From:</span>{" "}
              {email.from_address}
            </p>
            <p>
              <span className="font-medium text-foreground">To:</span>{" "}
              {email.to_addresses.join(", ")}
            </p>
            {email.cc_addresses && email.cc_addresses.length > 0 && (
              <p>
                <span className="font-medium text-foreground">CC:</span>{" "}
                {email.cc_addresses.join(", ")}
              </p>
            )}
            <p>
              <span className="font-medium text-foreground">Date:</span>{" "}
              {new Date(ts).toLocaleString("en-IN", {
                dateStyle: "long",
                timeStyle: "short",
              })}
            </p>
          </div>
          <div className="flex items-center gap-2 mt-3">
            <span
              className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
              style={
                isOut
                  ? { background: `${INDIGO}14`, color: INDIGO }
                  : { background: "#94A3B820", color: "#64748B" }
              }
            >
              {isOut ? "Sent" : "Received"}
            </span>
            {email.status && (
              <span className="text-[10px] text-muted-foreground capitalize">{email.status}</span>
            )}
          </div>
        </div>
      </div>

      <div className="border-t border-border pt-5">
        <pre className="whitespace-pre-wrap text-sm leading-relaxed font-sans">
          {email.body_text ?? ""}
        </pre>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function EmailInboxPage() {
  const [selectedEmail, setSelectedEmail] = useState<EmailRecord | null>(null);
  const [filter, setFilter] = useState<FilterType>("all");
  const [search, setSearch] = useState("");
  const [showCompose, setShowCompose] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["crm-emails-inbox", filter],
    queryFn: async () => {
      const params = new URLSearchParams({ page: "1" });
      if (filter === "sent") params.set("direction", "outbound");
      if (filter === "received") params.set("direction", "inbound");
      const res = await api.get(`/crm/emails?${params}`);
      return res.data;
    },
  });

  const allEmails: EmailRecord[] = data?.data ?? [];
  const emails = search
    ? allEmails.filter(
        (e) =>
          e.subject.toLowerCase().includes(search.toLowerCase()) ||
          e.from_address.toLowerCase().includes(search.toLowerCase()) ||
          e.to_addresses.some((a) => a.toLowerCase().includes(search.toLowerCase()))
      )
    : allEmails;

  return (
    <div className="flex flex-col h-full">
      {/* Page header */}
      <div className="px-8 py-5 border-b border-border shrink-0">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          CRM / EMAIL
        </p>
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight">Email</h1>
              <Mail className="h-5 w-5 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground mt-0.5">Email conversations with leads and contacts</p>
          </div>
          <Can perm="crm.create"><button
            onClick={() => setShowCompose(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90"
            style={{ background: INDIGO }}
          >
            <Plus className="h-4 w-4" />
            Compose
          </button></Can>
        </div>
      </div>

      {/* Two-panel layout */}
      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* ── Left panel: Email list (300px) ────────────────────────────────── */}
        <div className="w-[300px] border-r border-border flex flex-col shrink-0">
          {/* Search + filter */}
          <div className="p-3 border-b border-border space-y-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <input
                className="w-full rounded-xl border border-input bg-muted/40 pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Search emails…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            {/* Filter tabs */}
            <div className="flex gap-1 bg-muted/50 rounded-xl p-1">
              {(["all", "sent", "received"] as FilterType[]).map((f) => (
                <button
                  key={f}
                  onClick={() => {
                    setFilter(f);
                    setSelectedEmail(null);
                  }}
                  className="flex-1 py-1 text-[11px] font-semibold rounded-lg capitalize transition-all"
                  style={
                    filter === f
                      ? { background: "hsl(var(--card))", color: INDIGO, boxShadow: "0 1px 3px rgba(0,0,0,.08)" }
                      : { color: "hsl(var(--muted-foreground))" }
                  }
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          {/* Email list */}
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : emails.length === 0 ? (
              <div className="px-5 py-12 text-center">
                <Inbox className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
                <p className="text-sm text-muted-foreground">
                  {search ? "No emails match your search" : "No emails yet"}
                </p>
              </div>
            ) : (
              emails.map((email) => {
                const isSelected = selectedEmail?.id === email.id;
                const isOut = email.direction === "outbound";
                const ts = email.sent_at ?? email.created_at;
                return (
                  <button
                    key={email.id}
                    onClick={() => setSelectedEmail(email)}
                    className="w-full flex items-start gap-3 px-4 py-3.5 text-left border-b border-border/50 transition-colors hover:bg-muted/40"
                    style={isSelected ? { background: `${INDIGO}10` } : {}}
                  >
                    <div
                      className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 mt-0.5"
                      style={{
                        background: isOut ? `${INDIGO}18` : "#94A3B818",
                        color: isOut ? INDIGO : "#64748B",
                      }}
                    >
                      <Mail className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline justify-between gap-1">
                        <span
                          className="font-medium text-sm truncate"
                          style={isSelected ? { color: INDIGO } : {}}
                        >
                          {isOut ? email.to_addresses[0] : email.from_address}
                        </span>
                        <span className="text-[10px] text-muted-foreground shrink-0">
                          {formatRelativeTime(ts)}
                        </span>
                      </div>
                      <p className="text-xs font-medium truncate mt-0.5">{email.subject}</p>
                      <div className="flex items-center gap-1.5 mt-1">
                        <span
                          className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                          style={
                            isOut
                              ? { background: `${INDIGO}14`, color: INDIGO }
                              : { background: "#94A3B820", color: "#64748B" }
                          }
                        >
                          {isOut ? "Sent" : "Received"}
                        </span>
                        {email.status && (
                          <span className="text-[10px] text-muted-foreground capitalize">
                            {email.status}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* ── Right panel: Email detail (flex-1) ───────────────────────────── */}
        <div className="flex-1 flex flex-col min-w-0">
          {!selectedEmail ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center p-8">
              <div
                className="w-20 h-20 rounded-full flex items-center justify-center"
                style={{ background: `${INDIGO}14` }}
              >
                <Mail className="h-10 w-10" style={{ color: INDIGO }} />
              </div>
              <div>
                <p className="font-semibold text-base">Select an email to read</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Choose an email from the left panel
                </p>
              </div>
              <Can perm="crm.create"><button
                onClick={() => setShowCompose(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90"
                style={{ background: INDIGO }}
              >
                <Plus className="h-4 w-4" />
                Compose Email
              </button></Can>
            </div>
          ) : (
            <>
              {/* Detail header */}
              <div className="flex items-center gap-3 px-6 py-3.5 border-b border-border shrink-0">
                <p
                  className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground"
                >
                  Email Detail
                </p>
                <div className="flex-1" />
                {selectedEmail.direction === "inbound" && (
                  <Can perm="crm.create"><button
                    onClick={() => setShowCompose(true)}
                    className="flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-colors hover:bg-muted"
                    style={{ borderColor: `${INDIGO}40`, color: INDIGO }}
                  >
                    Reply
                    <ChevronRight className="h-3 w-3" />
                  </button></Can>
                )}
              </div>
              <EmailDetail email={selectedEmail} />
            </>
          )}
        </div>
      </div>

      {/* Compose modal */}
      {showCompose && <ComposeEmailModal onClose={() => setShowCompose(false)} />}
    </div>
  );
}
