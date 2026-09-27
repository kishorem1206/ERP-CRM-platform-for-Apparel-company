"use client";
import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2, RefreshCw } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import api from "@/lib/api";
import { cn } from "@/lib/utils";

const INDIGO   = "#0049A7";
const LAVENDER = "#0F78FF";
const BLUE     = "#0049A7";
const TEAL     = "#8174F5";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTIONS = [
  "What is the current stock balance?",
  "Show me open sales orders",
  "Which production lots are in progress?",
  "What are our outstanding customer invoices?",
  "Show vendor payables",
  "What purchase orders are pending?",
];

const WELCOME = "Hello! I'm the Apparel ERP AI Assistant. I can answer questions about your inventory, sales orders, production lots, finance, and more — all from live data.\n\nTry asking one of the suggested questions below, or type your own.";

export default function AIAssistantPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: WELCOME },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const res = await api.post("/agents/chat", {
        message: text,
        conversation_id: conversationId,
      });
      const data = res.data;
      if (data?.conversation_id) setConversationId(data.conversation_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data?.response ?? "I couldn't process that request." },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I encountered an error. Please check the backend is running and try again." },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function reset() {
    setMessages([{ role: "assistant", content: WELCOME }]);
    setConversationId(null);
    setInput("");
    inputRef.current?.focus();
  }

  const showSuggestions = messages.length <= 1;

  return (
    <div className="p-8 flex flex-col h-[calc(100vh-3.5rem-3rem)] max-w-3xl mx-auto space-y-0 gap-6">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap flex-shrink-0">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">AI</p>
          <h1 className="text-2xl font-bold tracking-tight">AI Assistant</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Ask questions about your manufacturing data.
          </p>
        </div>
        <button
          onClick={reset}
          title="New conversation"
          className="p-2 rounded-xl hover:bg-muted transition-colors text-muted-foreground flex-shrink-0"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 min-h-0">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn("flex gap-3 items-start", msg.role === "user" && "flex-row-reverse")}
          >
            <div
              className={cn(
                "h-7 w-7 rounded-full flex items-center justify-center shrink-0 mt-0.5",
                msg.role === "assistant" ? "text-white" : "bg-muted text-muted-foreground"
              )}
              style={msg.role === "assistant" ? { background: INDIGO } : {}}
            >
              {msg.role === "assistant" ? <Bot className="h-4 w-4" /> : <User className="h-4 w-4" />}
            </div>
            <div
              className={cn(
                "max-w-[78%] rounded-2xl px-4 py-3 text-sm",
                msg.role === "assistant" ? "bg-card border border-border" : "text-white whitespace-pre-wrap"
              )}
              style={msg.role === "user" ? { background: INDIGO } : {}}
            >
              {msg.role === "assistant" ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    table: ({ children }) => (
                      <div className="overflow-x-auto my-2">
                        <table className="w-full border-collapse text-xs">{children}</table>
                      </div>
                    ),
                    thead: ({ children }) => (
                      <thead className="bg-muted/60">{children}</thead>
                    ),
                    th: ({ children }) => (
                      <th className="border border-border px-3 py-1.5 text-left font-semibold">{children}</th>
                    ),
                    td: ({ children }) => (
                      <td className="border border-border px-3 py-1.5">{children}</td>
                    ),
                    tr: ({ children }) => (
                      <tr className="even:bg-muted/20">{children}</tr>
                    ),
                    p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
                    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                    em: ({ children }) => <em className="italic text-muted-foreground">{children}</em>,
                    ul: ({ children }) => <ul className="list-disc pl-4 space-y-0.5 my-1">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal pl-4 space-y-0.5 my-1">{children}</ol>,
                    code: ({ children }) => <code className="bg-muted rounded px-1 py-0.5 text-xs font-mono">{children}</code>,
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 items-center">
            <div className="h-7 w-7 rounded-full flex items-center justify-center shrink-0 text-white"
              style={{ background: INDIGO }}>
              <Bot className="h-4 w-4" />
            </div>
            <div className="bg-card border border-border rounded-2xl px-4 py-3 text-sm text-muted-foreground flex items-center gap-2">
              <Loader2 className="h-3 w-3 animate-spin" />
              Querying live data…
            </div>
          </div>
        )}

        {/* Suggestion chips */}
        {showSuggestions && !loading && (
          <div className="flex flex-wrap gap-2 pt-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => sendMessage(s)}
                className="text-xs border rounded-full px-3 py-1.5 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2 flex-shrink-0">
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage(input)}
          placeholder="Ask anything — e.g. 'Show me all in-progress production lots'"
          className="flex-1 border border-border rounded-xl px-4 py-2.5 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30"
          disabled={loading}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
          className="rounded-xl px-4 py-2.5 text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
