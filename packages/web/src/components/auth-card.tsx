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
    <div className="w-full max-w-md rounded-panel border border-border bg-surface p-6 shadow-xl shadow-ink/5 sm:p-8">
      <div className="mb-7">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary-deep">Beta access</p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
          {mode === "signup" ? "Create your OCR account" : "Welcome back"}
        </h1>
        <p className="mt-3 text-sm leading-6 text-muted">
          Sign up or log in to generate API keys and start using the FIBA scoresheet OCR API locally.
        </p>
      </div>

      <div className="mb-6 grid grid-cols-2 rounded-full bg-elevated p-1 text-sm font-medium" role="tablist" aria-label="Authentication mode">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "signup"}
          onClick={() => setMode("signup")}
          className={`rounded-full px-4 py-2 transition ${mode === "signup" ? "bg-surface text-ink shadow-sm" : "text-faint hover:text-muted"}`}
        >
          Sign Up
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "login"}
          onClick={() => setMode("login")}
          className={`rounded-full px-4 py-2 transition ${mode === "login" ? "bg-surface text-ink shadow-sm" : "text-faint hover:text-muted"}`}
        >
          Log In
        </button>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium text-ink">
          Email
          <input
            className="mt-2 w-full rounded-field border border-border bg-surface px-4 py-3 text-ink outline-none transition placeholder:text-faint focus:border-primary focus:ring-4 focus:ring-primary/15"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <label className="block text-sm font-medium text-ink">
          Password
          <input
            className="mt-2 w-full rounded-field border border-border bg-surface px-4 py-3 text-ink outline-none transition placeholder:text-faint focus:border-primary focus:ring-4 focus:ring-primary/15"
            type="password"
            autoComplete={mode === "signup" ? "new-password" : "current-password"}
            placeholder={mode === "signup" ? "At least 6 characters" : "Your password"}
            minLength={6}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        {error ? (
          <p className="rounded-field bg-danger-soft p-3 text-sm text-danger" role="alert">
            {error.includes("Email not confirmed")
              ? "Email not confirmed. Please confirm the signup email in Supabase/email inbox, then log in with the same password."
              : error}
          </p>
        ) : null}
        {message ? <p className="rounded-field bg-success-soft p-3 text-sm text-success">{message}</p> : null}

        <button
          className="w-full rounded-field bg-primary px-5 py-3 font-semibold text-primary-contrast transition hover:bg-primary/85 disabled:cursor-not-allowed disabled:opacity-60"
          type="submit"
          disabled={isLoading}
        >
          {isLoading ? "Working..." : mode === "signup" ? "Create account" : "Log in"}
        </button>
      </form>
    </div>
  );
}
