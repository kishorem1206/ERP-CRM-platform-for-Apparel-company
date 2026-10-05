"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  MessageSquare, Search, Send, FileText, Check, CheckCheck,
  X, ChevronRight, User, Loader2, AlertCircle, Plus, Link2,
} from "lucide-react";
import api from "@/lib/api";
import { ModalShell } from "@/components/shared/modal-shell";
import { Can } from "@/lib/permissions";

// ── Palette ───────────────────────────────────────────────────────────────────
const INDIGO = "#0049A7";
const WA_GREEN = "#0F78FF";

// ── Types ─────────────────────────────────────────────────────────────────────
interface WhatsAppContact {
  id: string;
  phone_number: string;
  display_name: string | null;
  person_id: string | null;
  lead_id: string | null;
  last_message: string | null;
  last_message_at: string | null;
}

interface WhatsAppMessage {
  id: string;
  direction: "inbound" | "outbound";
  body: string;
  status: "sent" | "delivered" | "read" | "failed";
  wa_timestamp: string;
  message_type: string;
  from_number: string;
  to_number: string;
}

interface WhatsAppTemplate {
  id: string;
  name: string;
  category: "MARKETING" | "UTILITY" | "AUTHENTICATION";
  body_text: string;
  status: string;
}

interface Lead {
  id: string;
  title: string;
  status: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function getInitials(name: string | null, phone: string): string {
  if (name) {
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
  }
  return phone.slice(-2);
}

function formatTime(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function formatContactTime(ts: string | null): string {
  if (!ts) return "";
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return formatTime(ts);
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return d.toLocaleDateString("en-IN", { weekday: "short" });
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

// ── StatusIcon ────────────────────────────────────────────────────────────────
function StatusIcon({ status }: { status: WhatsAppMessage["status"] }) {
  if (status === "read")
    return <CheckCheck className="h-3.5 w-3.5" style={{ color: "#8FC0FF" }} />;
  if (status === "delivered")
    return <CheckCheck className="h-3.5 w-3.5 text-white/60" />;
  if (status === "sent")
    return <Check className="h-3.5 w-3.5 text-white/60" />;
  if (status === "failed")
    return <AlertCircle className="h-3.5 w-3.5" style={{ color: "#1D0DB0" }} />;
  return null;
}

// ── TemplatesModal ────────────────────────────────────────────────────────────
const CATEGORY_STYLE: Record<
  string,
  { bg: string; color: string; label: string }
> = {
  MARKETING: { bg: "#E9E8F8", color: "#8174F5", label: "Marketing" },
  UTILITY: { bg: "#E7EFF9", color: "#0049A7", label: "Utility" },
  AUTHENTICATION: { bg: "#E7EFF9", color: "#0F78FF", label: "Auth" },
};

function TemplatesModal({
  onClose,
  onSelect,
}: {
  onClose: () => void;
  onSelect: (body: string) => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["whatsapp-templates"],
    queryFn: async () => {
      const res = await api.get("/whatsapp/templates");
      return res.data;
    },
  });

  const templates: WhatsAppTemplate[] = data?.data ?? [];

  return (
    <ModalShell maxWidth="max-w-lg" onClose={onClose}>
      <div className="flex flex-col max-h-[80vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="font-semibold">Message Templates</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-muted transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : templates.length === 0 ? (
            <div className="text-center py-10">
              <FileText className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">No approved templates found</p>
            </div>
          ) : (
            templates.map((t) => {
              const style = CATEGORY_STYLE[t.category] ?? CATEGORY_STYLE.UTILITY;
              return (
                <button
                  key={t.id}
                  onClick={() => {
                    onSelect(t.body_text);
                    onClose();
                  }}
                  className="w-full text-left bg-muted/40 hover:bg-muted rounded-xl p-4 transition-colors border border-transparent hover:border-border"
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="font-medium text-sm">{t.name}</span>
                    <span
                      className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                      style={{ background: style.bg, color: style.color }}
                    >
                      {style.label}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-2">{t.body_text}</p>
                </button>
              );
            })
          )}
        </div>
      </div>
    </ModalShell>
  );
}

// ── LeadLinkPopover ───────────────────────────────────────────────────────────
function LeadLinkPopover({
  contactId,
  onClose,
  onLinked,
}: {
  contactId: string;
  onClose: () => void;
  onLinked: () => void;
}) {
  const [leadSearch, setLeadSearch] = useState("");
  const queryClient = useQueryClient();

  const { data: leadsData, isLoading } = useQuery({
    queryKey: ["crm-leads-search", leadSearch],
    queryFn: async () => {
      const params = new URLSearchParams({ page: "1", page_size: "20" });
      if (leadSearch) params.set("search", leadSearch);
      const res = await api.get(`/crm/leads?${params}`);
      return res.data;
    },
    enabled: true,
  });

  const leads: Lead[] = leadsData?.data ?? [];

  const linkMutation = useMutation({
    mutationFn: async (leadId: string) => {
      const res = await api.patch(`/whatsapp/contacts/${contactId}`, { lead_id: leadId });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["whatsapp-contacts"] });
      onLinked();
      onClose();
    },
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border rounded-2xl w-full max-w-sm shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="font-semibold text-sm">Link to Lead</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-muted transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              className="w-full rounded-xl border border-input bg-muted/40 pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Search leads…"
              value={leadSearch}
              onChange={(e) => setLeadSearch(e.target.value)}
              autoFocus
            />
          </div>
        </div>

        <div className="max-h-60 overflow-y-auto pb-3 px-3 space-y-1">
          {isLoading ? (
            <div className="flex justify-center py-6">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          ) : leads.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-6">No leads found</p>
          ) : (
            leads.map((lead) => (
              <Can perm="crm.edit"><button
                key={lead.id}
                onClick={() => linkMutation.mutate(lead.id)}
                disabled={linkMutation.isPending}
                className="w-full text-left flex items-center justify-between gap-2 rounded-xl px-3 py-2.5 text-sm hover:bg-muted transition-colors"
              >
                <span className="truncate font-medium">{lead.title}</span>
                <span className="text-[11px] text-muted-foreground shrink-0">{lead.status}</span>
              </button></Can>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function WhatsAppPage() {
  const queryClient = useQueryClient();
  const [selectedContact, setSelectedContact] = useState<WhatsAppContact | null>(null);
  const [contactSearch, setContactSearch] = useState("");
  const [messageBody, setMessageBody] = useState("");
  const [showTemplates, setShowTemplates] = useState(false);
  const [showLeadLink, setShowLeadLink] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ── Contacts query ────────────────────────────────────────────────────────
  const { data: contactsData, isLoading: contactsLoading } = useQuery({
    queryKey: ["whatsapp-contacts", contactSearch],
    queryFn: async () => {
      const params = new URLSearchParams({ page: "1" });
      if (contactSearch) params.set("search", contactSearch);
      const res = await api.get(`/whatsapp/contacts?${params}`);
      return res.data;
    },
  });
  const contacts: WhatsAppContact[] = contactsData?.data ?? [];

  // ── Messages query ────────────────────────────────────────────────────────
  const { data: messagesData, isLoading: messagesLoading } = useQuery({
    queryKey: ["whatsapp-messages", selectedContact?.id],
    queryFn: async () => {
      const res = await api.get(
        `/whatsapp/contacts/${selectedContact!.id}/messages`
      );
      return res.data;
    },
    enabled: !!selectedContact,
    refetchInterval: 30000,
  });
  const messages: WhatsAppMessage[] = messagesData?.data ?? [];

  // Auto-scroll to bottom when messages load or change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Send mutation ─────────────────────────────────────────────────────────
  const sendMutation = useMutation({
    mutationFn: async (body: string) => {
      const res = await api.post("/whatsapp/send", {
        contact_id: selectedContact!.id,
        to_number: selectedContact!.phone_number,
        body,
      });
      return res.data;
    },
    onMutate: async (body) => {
      const queryKey = ["whatsapp-messages", selectedContact?.id];
      await queryClient.cancelQueries({ queryKey });
      const prev = queryClient.getQueryData(queryKey);
      queryClient.setQueryData(
        queryKey,
        (old: { data: WhatsAppMessage[] } | undefined) => {
          const optimistic: WhatsAppMessage = {
            id: `optimistic-${Date.now()}`,
            direction: "outbound",
            body,
            status: "sent",
            wa_timestamp: new Date().toISOString(),
            message_type: "text",
            from_number: "",
            to_number: selectedContact?.phone_number ?? "",
          };
          return { data: [...(old?.data ?? []), optimistic] };
        }
      );
      return { prev };
    },
    onError: (_err, _body, ctx) => {
      if (ctx?.prev) {
        queryClient.setQueryData(
          ["whatsapp-messages", selectedContact?.id],
          ctx.prev
        );
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["whatsapp-messages", selectedContact?.id],
      });
      queryClient.invalidateQueries({ queryKey: ["whatsapp-contacts"] });
    },
  });

  // ── Handlers ──────────────────────────────────────────────────────────────
  function handleSend() {
    const body = messageBody.trim();
    if (!body || !selectedContact || sendMutation.isPending) return;
    setMessageBody("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    sendMutation.mutate(body);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleTextareaChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setMessageBody(e.target.value);
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 120)}px`;
  }

  function handleSelectContact(contact: WhatsAppContact) {
    setSelectedContact(contact);
    setMessageBody("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  const contactDisplayName =
    selectedContact?.display_name || selectedContact?.phone_number || "";

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full">
      {/* Page header */}
      <div className="px-8 py-5 border-b border-border shrink-0">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
          CRM / WHATSAPP
        </p>
        <div className="flex items-center gap-2.5">
          <h1 className="text-2xl font-bold tracking-tight">WhatsApp</h1>
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ background: WA_GREEN }}
            title="WhatsApp"
          />
        </div>
        <p className="text-sm text-muted-foreground mt-0.5">
          Manage customer WhatsApp conversations
        </p>
      </div>

      {/* Three-panel layout */}
      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* ── Left panel: Contact list (320px) ─────────────────────────────── */}
        <div className="w-80 border-r border-border flex flex-col shrink-0">
          {/* Search */}
          <div className="p-3 border-b border-border">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <input
                className="w-full rounded-xl border border-input bg-muted/40 pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Search contacts…"
                value={contactSearch}
                onChange={(e) => setContactSearch(e.target.value)}
              />
            </div>
          </div>

          {/* Contact list */}
          <div className="flex-1 overflow-y-auto">
            {contactsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : contacts.length === 0 ? (
              <div className="px-5 py-12 text-center">
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3"
                  style={{ background: `${WA_GREEN}18` }}
                >
                  <MessageSquare
                    className="h-6 w-6"
                    style={{ color: WA_GREEN }}
                  />
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {contactSearch
                    ? "No contacts match your search"
                    : "No WhatsApp contacts yet. When customers message you, they’ll appear here."}
                </p>
              </div>
            ) : (
              contacts.map((contact) => {
                const isSelected = selectedContact?.id === contact.id;
                const initials = getInitials(
                  contact.display_name,
                  contact.phone_number
                );
                const displayName =
                  contact.display_name || contact.phone_number;
                const preview = contact.last_message
                  ? contact.last_message.length > 40
                    ? contact.last_message.slice(0, 40) + "…"
                    : contact.last_message
                  : "";

                return (
                  <button
                    key={contact.id}
                    onClick={() => handleSelectContact(contact)}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left border-b border-border/50 transition-colors hover:bg-muted/40"
                    style={isSelected ? { background: `${INDIGO}10` } : {}}
                  >
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold text-white shrink-0"
                      style={{ background: WA_GREEN }}
                    >
                      {initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline justify-between gap-1">
                        <span
                          className="font-medium text-sm truncate"
                          style={isSelected ? { color: INDIGO } : {}}
                        >
                          {displayName}
                        </span>
                        <span className="text-[10px] text-muted-foreground shrink-0">
                          {formatContactTime(contact.last_message_at)}
                        </span>
                      </div>
                      {preview && (
                        <p className="text-xs text-muted-foreground truncate mt-0.5">
                          {preview}
                        </p>
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* ── Middle panel: Chat thread (flex-1) ───────────────────────────── */}
        <div className="flex-1 flex flex-col min-w-0">
          {!selectedContact ? (
            /* Empty state */
            <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center p-8">
              <div
                className="w-20 h-20 rounded-full flex items-center justify-center"
                style={{ background: `${WA_GREEN}14` }}
              >
                <MessageSquare
                  className="h-10 w-10"
                  style={{ color: WA_GREEN }}
                />
              </div>
              <div>
                <p className="font-semibold text-base">
                  Select a conversation to start messaging
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  Choose a contact from the left panel
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* Thread header */}
              <div className="flex items-center gap-3 px-5 py-3.5 border-b border-border shrink-0">
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold text-white shrink-0"
                  style={{ background: WA_GREEN }}
                >
                  {getInitials(
                    selectedContact.display_name,
                    selectedContact.phone_number
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm truncate">
                    {contactDisplayName}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {selectedContact.phone_number}
                  </p>
                </div>
                {selectedContact.lead_id && (
                  <Link
                    href={`/crm/leads/${selectedContact.lead_id}`}
                    className="flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-colors hover:bg-muted shrink-0"
                    style={{
                      borderColor: `${INDIGO}40`,
                      color: INDIGO,
                    }}
                  >
                    Linked Lead
                    <ChevronRight className="h-3 w-3" />
                  </Link>
                )}
              </div>

              {/* Messages area */}
              <div className="flex-1 overflow-y-auto px-5 py-4 space-y-1.5">
                {messagesLoading ? (
                  <div className="flex justify-center pt-8">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  </div>
                ) : messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center">
                    <p className="text-sm text-muted-foreground">
                      No messages yet. Send a message to start the conversation.
                    </p>
                  </div>
                ) : (
                  messages.map((msg) => {
                    const isOut = msg.direction === "outbound";
                    return (
                      <div
                        key={msg.id}
                        className={`flex ${isOut ? "justify-end" : "justify-start"}`}
                      >
                        <div
                          className={`max-w-[70%] rounded-2xl px-3.5 py-2.5 ${
                            isOut
                              ? "text-white rounded-tr-sm"
                              : "bg-card border border-border rounded-tl-sm"
                          }`}
                          style={isOut ? { background: INDIGO } : {}}
                        >
                          <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">
                            {msg.body}
                          </p>
                          <div
                            className={`flex items-center gap-1 mt-1 ${
                              isOut ? "justify-end" : "justify-start"
                            }`}
                          >
                            <span
                              className={`text-[10px] ${
                                isOut ? "text-white/60" : "text-muted-foreground"
                              }`}
                            >
                              {formatTime(msg.wa_timestamp)}
                            </span>
                            {isOut && <StatusIcon status={msg.status} />}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input area */}
              <div className="px-5 py-3 border-t border-border shrink-0">
                <div className="flex items-end gap-2">
                  {/* Templates button */}
                  <Can perm="crm.create"><button
                    onClick={() => setShowTemplates(true)}
                    title="Message Templates"
                    className="shrink-0 p-2 rounded-xl border border-input text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                    style={{ marginBottom: "1px" }}
                  >
                    <FileText className="h-4 w-4" />
                  </button></Can>

                  {/* Textarea */}
                  <textarea
                    ref={textareaRef}
                    rows={1}
                    value={messageBody}
                    onChange={handleTextareaChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Type a message… (Enter to send, Shift​+Enter for new line)"
                    className="flex-1 rounded-xl border border-input bg-muted/40 px-3.5 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring leading-relaxed"
                    style={{ minHeight: "40px", maxHeight: "120px" }}
                  />

                  {/* Send button */}
                  <Can perm="crm.create"><button
                    onClick={handleSend}
                    disabled={!messageBody.trim() || sendMutation.isPending}
                    className="shrink-0 p-2.5 rounded-xl text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-40"
                    style={{ background: INDIGO, marginBottom: "1px" }}
                  >
                    {sendMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </button></Can>
                </div>
              </div>
            </>
          )}
        </div>

        {/* ── Right panel: Contact info (280px, hidden on mobile) ──────────── */}
        {selectedContact && (
          <div className="hidden lg:flex w-[280px] border-l border-border flex-col shrink-0">
            <div className="px-5 py-4 border-b border-border">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                Contact Info
              </p>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {/* Avatar + name */}
              <div className="flex flex-col items-center gap-3 text-center pt-1">
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold text-white"
                  style={{ background: WA_GREEN }}
                >
                  {getInitials(
                    selectedContact.display_name,
                    selectedContact.phone_number
                  )}
                </div>
                <div>
                  <p className="font-semibold">{contactDisplayName}</p>
                  <p className="text-sm text-muted-foreground">
                    {selectedContact.phone_number}
                  </p>
                </div>
              </div>

              {/* Linked Person */}
              {selectedContact.person_id && (
                <div className="rounded-xl border border-border p-4 space-y-2">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                    Linked Person
                  </p>
                  <Link
                    href={`/crm/persons/${selectedContact.person_id}`}
                    className="flex items-center gap-1.5 text-sm font-medium transition-colors hover:opacity-80"
                    style={{ color: INDIGO }}
                  >
                    <User className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">View Person</span>
                    <ChevronRight className="h-3 w-3 shrink-0" />
                  </Link>
                </div>
              )}

              {/* Linked Lead */}
              {selectedContact.lead_id ? (
                <div className="rounded-xl border border-border p-4 space-y-2">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                    Linked Lead
                  </p>
                  <Link
                    href={`/crm/leads/${selectedContact.lead_id}`}
                    className="flex items-center gap-1.5 text-sm font-medium transition-colors hover:opacity-80"
                    style={{ color: INDIGO }}
                  >
                    <Link2 className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">View Lead</span>
                    <ChevronRight className="h-3 w-3 shrink-0" />
                  </Link>
                </div>
              ) : (
                /* Link to Lead button */
                <Can perm="crm.edit"><button
                  onClick={() => setShowLeadLink(true)}
                  className="w-full flex items-center justify-center gap-2 rounded-xl border border-dashed border-border px-4 py-3 text-sm text-muted-foreground hover:text-foreground hover:border-primary transition-colors"
                >
                  <Plus className="h-4 w-4" />
                  Link to Lead
                </button></Can>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Templates modal */}
      {showTemplates && (
        <TemplatesModal
          onClose={() => setShowTemplates(false)}
          onSelect={(body) => {
            setMessageBody(body);
            if (textareaRef.current) {
              textareaRef.current.style.height = "auto";
              textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
              textareaRef.current.focus();
            }
          }}
        />
      )}

      {/* Lead link modal */}
      {showLeadLink && selectedContact && (
        <LeadLinkPopover
          contactId={selectedContact.id}
          onClose={() => setShowLeadLink(false)}
          onLinked={() => {
            // Refresh the selected contact data
            queryClient.invalidateQueries({ queryKey: ["whatsapp-contacts"] });
          }}
        />
      )}
    </div>
  );
}
