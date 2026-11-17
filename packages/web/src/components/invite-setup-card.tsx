"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import type { EmailOtpType } from "@supabase/supabase-js";
import { toast } from "sonner";

import { createClient } from "@/lib/supabase/client";

type AssignedDemo = "referee" | "player" | "club";
type AccountRole = "admin" | "tester";

type AccountPayload = {
  email: string;
  role: AccountRole;
  status?: string;
  assigned_demo: AssignedDemo | null;
  accepted_at: string | null;
};

type InviteStatus = "checking" | "ready" | "error" | "complete";

const demoLabels: Record<AssignedDemo, string> = {
  player: "Single Player",
  referee: "Arbitros Helper",
  club: "Club Analysis",
};

const demoHomePaths: Record<AssignedDemo, string> = {
  player: "/test/player",
  referee: "/test/referee",
  club: "/test/club",
};

export function InviteSetupCard() {
  const [status, setStatus] = useState<InviteStatus>("checking");
  const [error, setError] = useState<string | null>(null);
  const [account, setAccount] = useState<AccountPayload | null>(null);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const destination = useMemo(() => destinationForAccount(account), [account]);

  useEffect(() => {
    let isMounted = true;

    async function prepareInviteSession() {
      const supabase = createClient();
      const url = new URL(window.location.href);
      const hashParams = new URLSearchParams(url.hash.replace(/^#/, ""));
      const accessToken = hashParams.get("access_token");
      const refreshToken = hashParams.get("refresh_token");
      const code = url.searchParams.get("code");
      const tokenHash = url.searchParams.get("token_hash");
      const type = url.searchParams.get("type") as EmailOtpType | null;
      const hasAuthParams = Boolean((accessToken && refreshToken) || code || (tokenHash && type));

      try {
        if (accessToken && refreshToken) {
          const { error: sessionError } = await supabase.auth.setSession({ access_token: accessToken, refresh_token: refreshToken });
          if (sessionError) throw sessionError;
          clearAuthParamsFromUrl(url.pathname);
        } else if (code) {
          const { error: codeError } = await supabase.auth.exchangeCodeForSession(code);
          if (codeError) throw codeError;
          clearAuthParamsFromUrl(url.pathname);
        } else if (tokenHash && type) {
          const { error: otpError } = await supabase.auth.verifyOtp({ token_hash: tokenHash, type });
          if (otpError) throw otpError;
          clearAuthParamsFromUrl(url.pathname);
        }

        const {
          data: { user },
          error: userError,
        } = await supabase.auth.getUser();

        if (userError) throw userError;
        if (!user) {
          throw new Error("This invite link is missing or expired. Ask the admin to send a new invitation.");
        }

        const { data: accountData, error: accountError } = await supabase
          .from("accounts")
          .select("email,role,status,assigned_demo,accepted_at")
          .eq("supabase_user_id", user.id)
          .single();

        if (accountError || !accountData) {
          throw new Error("Your product account is not ready yet. Ask the admin to verify your invite.");
        }

        const nextAccount = accountData as AccountPayload;
        if (nextAccount.status && nextAccount.status !== "active") {
          throw new Error("This account is inactive. Contact an administrator.");
        }
        if (!hasAuthParams && nextAccount.accepted_at) {
          window.location.assign(destinationForAccount(nextAccount));
          return;
        }

        if (!isMounted) return;
        setAccount(nextAccount);
        setStatus("ready");
      } catch (cause) {
        if (!isMounted) return;
        const message = cause instanceof Error ? cause.message : "Could not verify the invitation link.";
        setError(message);
        setStatus("error");
      }
    }

    void prepareInviteSession();
    return () => {
      isMounted = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    const supabase = createClient();
    const { error: updateError } = await supabase.auth.updateUser({ password });

    if (updateError) {
      const message = updateError.message || "Could not set your password.";
      setError(message);
      toast.error(message);
      setIsSubmitting(false);
      return;
    }

    let nextDestination = destination;
    try {
      const response = await fetch("/auth/accept-invite", { method: "POST" });
      const payload = (await response.json()) as { destination?: string };
      if (response.ok && payload.destination) nextDestination = payload.destination;
    } catch {
      // Password update succeeded; use the client-side account destination as a safe fallback.
    }

    setStatus("complete");
    toast.success("Password set successfully.");
    window.location.assign(nextDestination || "/login");
  }

  return (
    <div className="w-full max-w-md rounded-panel border border-border bg-surface p-6 shadow-xl shadow-ink/5 sm:p-8">
      <div className="mb-7">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary-deep">Invitation</p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">Set your password</h1>
        <p className="mt-3 text-sm leading-6 text-muted">
          Accept your invite by choosing a password. After that, we will send you directly to your assigned demo.
        </p>
      </div>

      {status === "checking" ? <p className="rounded-field bg-elevated p-3 text-sm text-muted">Verifying invitation link...</p> : null}

      {status === "error" ? (
        <div className="space-y-4">
          <p className="rounded-field bg-danger-soft p-3 text-sm text-danger" role="alert">{error || "Could not verify the invitation link."}</p>
          <a className="block rounded-field border border-border px-5 py-3 text-center text-sm font-semibold text-ink transition hover:bg-elevated" href="/login">
            Back to login
          </a>
        </div>
      ) : null}

      {status === "ready" || status === "complete" ? (
        <form className="space-y-4" onSubmit={handleSubmit}>
          {account ? (
            <p className="rounded-field bg-elevated p-3 text-sm text-muted">
              Account: <span className="font-semibold text-ink">{account.email}</span>
              {account.role === "tester" && account.assigned_demo ? <> · Demo: <span className="font-semibold text-ink">{demoLabels[account.assigned_demo]}</span></> : null}
            </p>
          ) : null}

          <label className="block text-sm font-medium text-ink">
            Password
            <input
              className="mt-2 w-full rounded-field border border-border bg-surface px-4 py-3 text-ink outline-none transition placeholder:text-faint focus:border-primary focus:ring-4 focus:ring-primary/15"
              type="password"
              autoComplete="new-password"
              minLength={6}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>

          <label className="block text-sm font-medium text-ink">
            Confirm password
            <input
              className="mt-2 w-full rounded-field border border-border bg-surface px-4 py-3 text-ink outline-none transition placeholder:text-faint focus:border-primary focus:ring-4 focus:ring-primary/15"
              type="password"
              autoComplete="new-password"
              minLength={6}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
            />
          </label>

          {error ? <p className="rounded-field bg-danger-soft p-3 text-sm text-danger" role="alert">{error}</p> : null}

          <button
            className="w-full rounded-field bg-primary px-5 py-3 font-semibold text-primary-contrast transition hover:bg-primary/85 disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
            disabled={isSubmitting || status === "complete"}
          >
            {isSubmitting ? "Setting password..." : "Set password and continue"}
          </button>
        </form>
      ) : null}
    </div>
  );
}

function destinationForAccount(account: AccountPayload | null) {
  if (!account) return "/login";
  if (account.role === "admin") return "/admin";
  if (account.assigned_demo) return demoHomePaths[account.assigned_demo];
  return "/login";
}

function clearAuthParamsFromUrl(pathname: string) {
  window.history.replaceState({}, document.title, pathname);
}
