"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import api from "@/lib/api";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  otp: z.string().length(6, "Enter 6-digit code"),
  new_password: z.string().min(8, "Password must be at least 8 characters"),
  confirm: z.string(),
}).refine((d) => d.new_password === d.confirm, {
  message: "Passwords do not match",
  path: ["confirm"],
});
type FormData = z.infer<typeof schema>;

export default function ResetPasswordPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  async function onSubmit(data: FormData) {
    setError(null);
    try {
      await api.post("/auth/reset-password", {
        email: data.email,
        otp: data.otp,
        new_password: data.new_password,
      });
      router.push("/login");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { error?: string } } })?.response?.data?.error;
      setError(typeof detail === "string" ? detail : "Invalid or expired code.");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-semibold">Set New Password</h1>
          <p className="text-sm text-muted-foreground mt-1">Enter the code from your email</p>
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

          <div className="space-y-1">
            <label className="text-sm font-medium">Reset Code</label>
            <input
              {...register("otp")}
              type="text"
              inputMode="numeric"
              maxLength={6}
              placeholder="000000"
              className="w-full border rounded-md px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30 tracking-widest text-center"
            />
            {errors.otp && <p className="text-xs text-violet-500">{errors.otp.message}</p>}
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium">New Password</label>
            <input
              {...register("new_password")}
              type="password"
              autoComplete="new-password"
              placeholder="••••••••"
              className="w-full border rounded-md px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30"
            />
            {errors.new_password && <p className="text-xs text-violet-500">{errors.new_password.message}</p>}
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium">Confirm Password</label>
            <input
              {...register("confirm")}
              type="password"
              autoComplete="new-password"
              placeholder="••••••••"
              className="w-full border rounded-md px-3 py-2 text-sm bg-background outline-none focus:ring-2 focus:ring-primary/30"
            />
            {errors.confirm && <p className="text-xs text-violet-500">{errors.confirm.message}</p>}
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
            {isSubmitting ? "Saving…" : "Set New Password"}
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
