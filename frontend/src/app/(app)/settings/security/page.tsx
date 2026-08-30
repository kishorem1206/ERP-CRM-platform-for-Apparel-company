"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Key, Smartphone, CheckCircle, AlertCircle } from "lucide-react";
import api from "@/lib/api";

const INDIGO   = "#5347CE";
const LAVENDER = "#887CFD";
const BLUE     = "#4896FE";
const TEAL     = "#16C8C7";

// ── Types ─────────────────────────────────────────────────────────────────────

type MeData = { totp_enabled: boolean; email: string };

// ── Change Password Section ───────────────────────────────────────────────────

function ChangePasswordSection() {
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  function set(k: keyof typeof form, v: string) { setForm((f) => ({ ...f, [k]: v })); }

  const mutation = useMutation({
    mutationFn: () => api.post("/auth/change-password", {
      current_password: form.current,
      new_password: form.next,
    }),
    onSuccess: () => {
      setMsg({ ok: true, text: "Password changed successfully." });
      setForm({ current: "", next: "", confirm: "" });
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { error?: string } } })?.response?.data?.error;
      setMsg({ ok: false, text: typeof detail === "string" ? detail : "Failed to change password." });
    },
  });

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    if (form.next !== form.confirm) { setMsg({ ok: false, text: "Passwords do not match." }); return; }
    if (form.next.length < 8) { setMsg({ ok: false, text: "Password must be at least 8 characters." }); return; }
    mutation.mutate();
  }

  return (
    <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
      <div className="flex items-center gap-2">
        <Key className="w-4 h-4 text-muted-foreground" />
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">CHANGE PASSWORD</p>
          <p className="text-sm font-medium mt-0.5">Update your login credentials</p>
        </div>
      </div>
      <form onSubmit={onSubmit} className="space-y-3 max-w-sm">
        {(["current", "next", "confirm"] as const).map((k) => (
          <div key={k} className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">
              {k === "current" ? "Current password" : k === "next" ? "New password" : "Confirm new password"}
            </label>
            <input
              type="password"
              value={form[k]}
              onChange={(e) => set(k, e.target.value)}
              required
              className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>
        ))}
        {msg && (
          <div className={`flex items-start gap-2 text-xs rounded-xl px-3 py-2 ${msg.ok ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400" : "bg-red-50 dark:bg-red-950/30 text-red-600"}`}>
            {msg.ok ? <CheckCircle className="w-3 h-3 mt-0.5 shrink-0" /> : <AlertCircle className="w-3 h-3 mt-0.5 shrink-0" />}
            {msg.text}
          </div>
        )}
        <button
          type="submit"
          disabled={mutation.isPending}
          className="rounded-xl px-4 py-2 text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-60"
          style={{ background: INDIGO }}
        >
          {mutation.isPending ? "Saving…" : "Update Password"}
        </button>
      </form>
    </div>
  );
}

// ── 2FA Section ────────────────────────────────────────────────────────────────

function TwoFASection({ enabled, email }: { enabled: boolean; email: string }) {
  const qc = useQueryClient();
  const [step, setStep] = useState<"idle" | "setup" | "disable">("idle");
  const [setupData, setSetupData] = useState<{ secret: string; uri: string } | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function startSetup() {
    setMsg(null);
    try {
      const res = await api.post("/auth/2fa/setup");
      setSetupData(res.data.data);
      setStep("setup");
    } catch {
      setMsg({ ok: false, text: "Failed to generate 2FA secret." });
    }
  }

  async function enableTOTP(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await api.post("/auth/2fa/enable", { code });
      setMsg({ ok: true, text: "2FA enabled successfully." });
      setStep("idle");
      setCode("");
      setSetupData(null);
      qc.invalidateQueries({ queryKey: ["me"] });
    } catch {
      setMsg({ ok: false, text: "Invalid code. Try again." });
    }
  }

  async function disableTOTP(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await api.post("/auth/2fa/disable", { password });
      setMsg({ ok: true, text: "2FA disabled." });
      setStep("idle");
      setPassword("");
      qc.invalidateQueries({ queryKey: ["me"] });
    } catch {
      setMsg({ ok: false, text: "Incorrect password." });
    }
  }

  const qrUrl = setupData
    ? `https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(setupData.uri)}`
    : null;

  const statusColor = enabled ? "#10B981" : "#94A3B8";

  return (
    <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Smartphone className="w-4 h-4 text-muted-foreground" />
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">TWO-FACTOR AUTH</p>
            <p className="text-sm font-medium mt-0.5">Authenticator app (TOTP)</p>
          </div>
        </div>
        <span
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"
          style={{ background: `${statusColor}18`, color: statusColor }}
        >
          <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: statusColor }} />
          {enabled ? "Enabled" : "Disabled"}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">
        Use an authenticator app (Google Authenticator, Authy) to add an extra layer of security to your account.
      </p>

      {msg && (
        <div className={`flex items-start gap-2 text-xs rounded-xl px-3 py-2 ${msg.ok ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400" : "bg-red-50 dark:bg-red-950/30 text-red-600"}`}>
          {msg.ok ? <CheckCircle className="w-3 h-3 mt-0.5 shrink-0" /> : <AlertCircle className="w-3 h-3 mt-0.5 shrink-0" />}
          {msg.text}
        </div>
      )}

      {step === "idle" && (
        <div>
          {!enabled ? (
            <button
              onClick={startSetup}
              className="rounded-xl px-4 py-2 text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
              style={{ background: INDIGO }}
            >
              Set up 2FA
            </button>
          ) : (
            <button
              onClick={() => { setStep("disable"); setMsg(null); }}
              className="border border-red-300 text-red-600 rounded-xl px-4 py-2 text-sm font-medium hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
            >
              Disable 2FA
            </button>
          )}
        </div>
      )}

      {step === "setup" && setupData && (
        <div className="space-y-4 max-w-sm">
          <div className="space-y-2">
            <p className="text-xs font-medium">1. Scan this QR code with your authenticator app</p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={qrUrl!} alt="QR code" width={160} height={160} className="border rounded-xl" />
          </div>
          <div className="space-y-1">
            <p className="text-xs font-medium">Or enter the secret manually:</p>
            <code className="block bg-muted rounded-xl px-2 py-1 text-xs font-mono break-all">{setupData.secret}</code>
          </div>
          <form onSubmit={enableTOTP} className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-medium">2. Enter 6-digit code to confirm</label>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="000000"
                className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30 tracking-widest text-center"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                className="rounded-xl px-4 py-2 text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
                style={{ background: INDIGO }}
              >
                Enable 2FA
              </button>
              <button
                type="button"
                onClick={() => { setStep("idle"); setSetupData(null); setCode(""); }}
                className="border rounded-xl px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {step === "disable" && (
        <form onSubmit={disableTOTP} className="space-y-3 max-w-sm">
          <div className="space-y-1">
            <label className="text-xs font-medium">Confirm your password to disable 2FA</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              className="w-full border rounded-xl px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              className="bg-red-600 text-white rounded-xl px-4 py-2 text-sm font-semibold hover:bg-red-700 transition-colors"
            >
              Disable 2FA
            </button>
            <button
              type="button"
              onClick={() => { setStep("idle"); setPassword(""); }}
              className="border rounded-xl px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SecurityPage() {
  const { data, isLoading } = useQuery<MeData>({
    queryKey: ["me"],
    queryFn: async () => {
      const res = await api.get("/auth/me");
      return res.data.data as MeData;
    },
  });

  return (
    <div className="p-8 space-y-8 max-w-2xl mx-auto">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            SETTINGS / SECURITY
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Security</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Password and session management.
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading…</div>
      ) : (
        <>
          <ChangePasswordSection />
          <TwoFASection enabled={data?.totp_enabled ?? false} email={data?.email ?? ""} />
        </>
      )}
    </div>
  );
}
