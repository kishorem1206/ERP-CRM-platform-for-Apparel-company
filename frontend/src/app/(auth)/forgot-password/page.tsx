"use client";
import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import api from "@/lib/api";

const schema = z.object({ email: z.string().email("Enter a valid email") });
type FormData = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [done, setDone] = useState(false);
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  async function onSubmit(data: FormData) {
    setError(null);
    try {
      const res = await api.post("/auth/forgot-password", data);
      const otp = res.data?.data?.otp as string | undefined;
      if (otp) setDevOtp(otp);
      setDone(true);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { error?: string } } })?.response?.data?.error;
      setError(typeof detail === "string" ? detail : "Something went wrong.");
    }
  }

  if (done) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="w-full max-w-sm space-y-6 text-center">
          <div className="w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center mx-auto">
            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold">Check your email</h2>
          <p className="text-sm text-muted-foreground">
            If that email exists, a reset code has been sent.
          </p>
          {devOtp && (
            <div className="bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-700 rounded-lg px-4 py-3">
              <p className="text-xs text-violet-700 dark:text-violet-400 font-medium">Dev mode — OTP not emailed:</p>
              <p className="text-2xl font-mono font-bold tracking-widest text-violet-800 dark:text-violet-300 mt-1">{devOtp}</p>
            </div>
          )}
          <Link href="/reset-password" className="block text-sm text-primary hover:underline">
            Enter reset code
          </Link>
          <Link href="/login" className="block text-xs text-muted-foreground hover:underline">
            Back to login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-semibold">Reset Password</h1>
          <p className="text-sm text-muted-foreground mt-1">Enter your email to receive a reset code</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 bg-card border rounded-xl p-6">
          <div className="space-y-1">
            <label className="text-sm font-medium">Email</label>
            <input
              {...register("email")}
              type="email"
              autoComplete="email"
              placeholder="you@company.com"
              className="w-full border rounded-md px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30"
            />
            {errors.email && <p className="text-xs text-violet-500">{errors.email.message}</p>}
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
            {isSubmitting ? "Sending…" : "Send Reset Code"}
          </button>
        </form>

        <p className="text-center">
          <Link href="/login" className="text-xs text-muted-foreground hover:underline">
            Back to login
          </Link>
        </p>
      </div>
    </div>
  );
}
