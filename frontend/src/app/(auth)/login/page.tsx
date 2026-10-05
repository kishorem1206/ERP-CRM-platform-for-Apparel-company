"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { AUTH_ME_QUERY_KEY } from "@/lib/permissions";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import api from "@/lib/api";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type FormData = z.infer<typeof schema>;

const otpSchema = z.object({ code: z.string().length(6, "Enter 6-digit code") });
type OtpData = z.infer<typeof otpSchema>;

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const {
    register: regOtp,
    handleSubmit: handleOtp,
    formState: { errors: otpErrors, isSubmitting: otpSubmitting },
  } = useForm<OtpData>({ resolver: zodResolver(otpSchema) });

  async function onSubmit(data: FormData) {
    setError(null);
    try {
      const res = await api.post("/auth/login", data);
      const payload = res.data?.data ?? res.data;
      if (payload?.requires_2fa) {
        setSessionId(payload.session_id);
        return;
      }
      const token = payload?.access_token;
      if (token) {
        localStorage.setItem("access_token", token);
        queryClient.removeQueries({ queryKey: AUTH_ME_QUERY_KEY });
        router.push("/dashboard");
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { error?: unknown } } })?.response?.data?.error;
      const message = typeof detail === "object" && detail !== null
        ? (detail as { message?: string }).message ?? "Login failed."
        : typeof detail === "string" ? detail : "Login failed. Please try again.";
      setError(message);
    }
  }

  async function onVerify2FA(data: OtpData) {
    setError(null);
    try {
      const res = await api.post("/auth/login/verify-2fa", { session_id: sessionId, code: data.code });
      const token = res.data?.data?.access_token;
      if (token) {
        localStorage.setItem("access_token", token);
        queryClient.removeQueries({ queryKey: AUTH_ME_QUERY_KEY });
        router.push("/dashboard");
      }
    } catch (err: unknown) {
      // App error envelope: { success: false, error: "<str>" }
      const detail = (err as { response?: { data?: { error?: unknown } } })?.response?.data?.error;
      const message = typeof detail === "string" ? detail : "Invalid 2FA code. Please try again.";
      setError(message);
      // The 2FA session has ended (expired or too many wrong codes): restart from the password step.
      if (/session|too many/i.test(message)) setSessionId(null);
    }
  }

  if (sessionId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="w-full max-w-sm space-y-6">
          <div className="text-center">
            <h1 className="text-2xl font-semibold">Two-Factor Auth</h1>
            <p className="text-sm text-muted-foreground mt-1">Enter the 6-digit code from your authenticator app</p>
          </div>
          <form onSubmit={handleOtp(onVerify2FA)} className="space-y-4 bg-card border rounded-xl p-6">
            <div className="space-y-1">
              <label className="text-sm font-medium">Authentication Code</label>
              <input
                {...regOtp("code")}
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder="000000"
                className="w-full border rounded-md px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30 tracking-widest text-center text-lg"
              />
              {otpErrors.code && <p className="text-xs text-violet-500">{otpErrors.code.message}</p>}
            </div>
            {error && (
              <p className="text-xs text-violet-500 bg-violet-50 dark:bg-violet-950/30 border border-violet-200 dark:border-violet-800 rounded-md px-3 py-2">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={otpSubmitting}
              className="w-full bg-primary text-primary-foreground rounded-md py-2 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-60"
            >
              {otpSubmitting ? "Verifying…" : "Verify"}
            </button>
            <button
              type="button"
              onClick={() => { setSessionId(null); setError(null); }}
              className="w-full text-xs text-muted-foreground hover:underline"
            >
              Back to login
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-semibold">Apparel ERP</h1>
          <p className="text-sm text-muted-foreground mt-1">Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 bg-card border rounded-xl p-6">
          <div className="space-y-1">
            <label className="text-sm font-medium">Email</label>
            <input
              {...register("email")}
              type="email"
              autoComplete="email"
              placeholder="admin@company.com"
              className="w-full border rounded-md px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30"
            />
            {errors.email && (
              <p className="text-xs text-violet-500">{errors.email.message}</p>
            )}
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Password</label>
              <Link href="/forgot-password" className="text-xs text-primary hover:underline">
                Forgot password?
              </Link>
            </div>
            <input
              {...register("password")}
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              className="w-full border rounded-md px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30"
            />
            {errors.password && (
              <p className="text-xs text-violet-500">{errors.password.message}</p>
            )}
          </div>

          {error && (
            <p className="text-xs text-violet-500 bg-violet-50 dark:bg-violet-950/30 border border-violet-200 dark:border-violet-800 rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-primary text-primary-foreground rounded-md py-2 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-60"
          >
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="text-center text-xs text-muted-foreground">
          Contact your administrator for access credentials.
        </p>
      </div>
    </div>
  );
}
