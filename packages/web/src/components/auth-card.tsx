"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { createClient } from "@/lib/supabase/client";

export function AuthCard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = searchParams.get("next") || "/dashboard/api-keys";
  const supabase = useMemo(() => createClient(), []);
  const [mode, setMode] = useState<"signup" | "login">("signup");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const initialError = searchParams.get("error");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(initialError);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setIsLoading(true);

    const result =
      mode === "signup"
        ? await supabase.auth.signUp({
            email,
            password,
            options: {
              emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(nextPath)}`,
            },
          })
        : await supabase.auth.signInWithPassword({ email, password });

    setIsLoading(false);

    if (result.error) {
      setError(result.error.message);
      toast.error(result.error.message);
      return;
    }

    if (mode === "signup" && !result.data.session) {
      const confirmationMessage = "Account created. If email confirmation is enabled, open the Supabase confirmation email before logging in.";
      setMessage(confirmationMessage);
      toast.success("Account created. Please confirm your email before logging in.");
      setMode("login");
      return;
    }

    toast.success(mode === "signup" ? "Account created. Redirecting..." : "Logged in successfully.");
    router.push(nextPath);
    router.refresh();
  }

  return (
    <div className="w-full max-w-md rounded-3xl border border-white/10 bg-white/90 p-8 shadow-2xl shadow-slate-950/10 backdrop-blur dark:bg-slate-950/80">
      <div className="mb-8">
        <p className="text-sm font-semibold uppercase tracking-[0.24em] text-emerald-500">Beta access</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 dark:text-white">
          {mode === "signup" ? "Create your OCR account" : "Welcome back"}
        </h1>
        <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
          Sign up or log in to generate API keys and start using the FIBA scoresheet OCR API locally.
        </p>
      </div>

      <div className="mb-6 grid grid-cols-2 rounded-full bg-slate-100 p-1 text-sm font-medium dark:bg-slate-900">
        <button
          type="button"
          onClick={() => setMode("signup")}
          className={`rounded-full px-4 py-2 transition ${mode === "signup" ? "bg-white text-slate-950 shadow-sm dark:bg-slate-800 dark:text-white" : "text-slate-500"}`}
        >
          Sign Up
        </button>
        <button
          type="button"
          onClick={() => setMode("login")}
          className={`rounded-full px-4 py-2 transition ${mode === "login" ? "bg-white text-slate-950 shadow-sm dark:bg-slate-800 dark:text-white" : "text-slate-500"}`}
        >
          Log In
        </button>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">
          Email
          <input
            className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-950 outline-none transition focus:border-emerald-400 focus:ring-4 focus:ring-emerald-400/10 dark:border-slate-800 dark:bg-slate-900 dark:text-white"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">
          Password
          <input
            className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-950 outline-none transition focus:border-emerald-400 focus:ring-4 focus:ring-emerald-400/10 dark:border-slate-800 dark:bg-slate-900 dark:text-white"
            type="password"
            autoComplete={mode === "signup" ? "new-password" : "current-password"}
            minLength={6}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        {error ? (
          <p className="rounded-2xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-200">
            {error.includes("Email not confirmed")
              ? "Email not confirmed. Please confirm the signup email in Supabase/email inbox, then log in with the same password."
              : error}
          </p>
        ) : null}
        {message ? <p className="rounded-2xl bg-emerald-50 p-3 text-sm text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200">{message}</p> : null}

        <button
          className="w-full rounded-2xl bg-slate-950 px-5 py-3 font-semibold text-white transition hover:-translate-y-0.5 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-emerald-400 dark:text-slate-950 dark:hover:bg-emerald-300"
          type="submit"
          disabled={isLoading}
        >
          {isLoading ? "Working..." : mode === "signup" ? "Create account" : "Log in"}
        </button>
      </form>
    </div>
  );
}
