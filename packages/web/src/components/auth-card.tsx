"use client";

import { useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";

export function AuthCard() {
  const searchParams = useSearchParams();
  const requestedNextPath = getSafeNextPath(searchParams.get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const initialError = searchParams.get("error");
  const [error, setError] = useState<string | null>(initialError);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, next: requestedNextPath }),
      });
      const payload = (await response.json()) as { destination?: string; error?: string };

      if (!response.ok || !payload.destination) {
        const message = payload.error || "Could not log in.";
        setError(message);
        toast.error(message);
        setIsLoading(false);
        return;
      }

      toast.success("Logged in successfully.");
      window.location.assign(payload.destination);
    } catch {
      const message = "Could not reach the login service. Please try again.";
      setError(message);
      toast.error(message);
      setIsLoading(false);
    }
  }

  return (
    <div className="w-full max-w-md rounded-panel border border-border bg-surface p-6 shadow-xl shadow-ink/5 sm:p-8">
      <div className="mb-7">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary-deep">Invite-only beta</p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">Welcome back</h1>
        <p className="mt-3 text-sm leading-6 text-muted">
          Log in with the email invited by the admin. New tester accounts are created through Supabase invitation links only.
        </p>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium text-ink">
          Email
          <input
            className="mt-2 w-full rounded-field border border-border bg-surface px-4 py-3 text-ink outline-none transition placeholder:text-faint focus:border-primary focus:ring-4 focus:ring-primary/15"
            type="email"
            autoComplete="off"
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
            autoComplete="off"
            placeholder="Your password"
            minLength={6}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        {error ? (
          <p className="rounded-field bg-danger-soft p-3 text-sm text-danger" role="alert">
            {error.includes("Email not confirmed")
              ? "Email not confirmed. Please open the Supabase invitation email, set your password, then log in."
              : error}
          </p>
        ) : null}

        <button
          className="w-full rounded-field bg-primary px-5 py-3 font-semibold text-primary-contrast transition hover:bg-primary/85 disabled:cursor-not-allowed disabled:opacity-60"
          type="submit"
          disabled={isLoading}
        >
          {isLoading ? "Logging in..." : "Log in"}
        </button>
      </form>
    </div>
  );
}

function getSafeNextPath(value: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return null;
  return value;
}
