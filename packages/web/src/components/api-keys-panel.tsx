"use client";

import { useEffect, useMemo, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { toast } from "sonner";

import {
  bootstrapApiKey,
  createApiKey,
  listApiKeys,
  deleteApiKey,
  type ApiKeyRecord,
} from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

export function ApiKeysPanel() {
  const supabase = useMemo(() => createClient(), []);
  const [session, setSession] = useState<Session | null>(null);
  const [keys, setKeys] = useState<ApiKeyRecord[]>([]);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [keyName, setKeyName] = useState("default");
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh(currentSession: Session) {
    setError(null);
    const response = await listApiKeys(currentSession);
    setKeys(response.keys);
  }

  useEffect(() => {
    let mounted = true;

    async function loadSessionAndKeys() {
      const { data } = await supabase.auth.getSession();
      if (!mounted) return;

      if (!data.session) {
        setSession(null);
        setIsLoading(false);
        setError("No active Supabase session. Please log in again.");
        toast.error("No active Supabase session. Please log in again.");
        return;
      }

      setSession(data.session);

      try {
        const response = await listApiKeys(data.session);
        if (!mounted) return;
        setKeys(response.keys);
      } catch (err) {
        if (!mounted) return;
        const message = err instanceof Error ? err.message : "Failed to load API keys";
        setError(message);
        toast.error(message);
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    loadSessionAndKeys();

    return () => {
      mounted = false;
    };
  }, [supabase]);

  async function mutate(action: () => Promise<{ key?: string } | unknown>) {
    if (!session) return;
    setIsMutating(true);
    setError(null);
    try {
      const response = await action();
      if (response && typeof response === "object" && "key" in response && typeof response.key === "string") {
        setNewKey(response.key);
        toast.success("API key created. Save it now — it will only be shown once.");
      } else {
        toast.success("API key deleted.");
      }
      await refresh(session);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Request failed";
      setError(message);
      toast.error(message);
    } finally {
      setIsMutating(false);
    }
  }

  const activeKeys = keys.filter((key) => key.status === "active");

  if (isLoading) {
    return <div className="rounded-3xl border border-slate-200 bg-white p-8 text-slate-500 shadow-sm dark:border-slate-800 dark:bg-slate-950">Loading API keys...</div>;
  }

  return (
    <div className="space-y-6">
      {newKey ? (
        <div className="rounded-3xl border border-emerald-200 bg-emerald-50 p-6 text-emerald-950 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-50">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em]">Save this key now</p>
              <p className="mt-2 text-sm text-emerald-800 dark:text-emerald-200">It will not be shown again after you dismiss this message.</p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 dark:bg-emerald-300 dark:text-emerald-950 dark:hover:bg-emerald-200"
                  type="button"
                  onClick={async () => {
                    await navigator.clipboard.writeText(newKey);
                    toast.success("API key copied to clipboard.");
                  }}
                >
                  Copy key
                </button>
              </div>
            </div>
            <button className="text-sm font-semibold underline" onClick={() => setNewKey(null)} type="button">
              Dismiss
            </button>
          </div>
          <code className="mt-4 block overflow-x-auto rounded-2xl bg-white p-4 text-sm text-slate-950 dark:bg-slate-950 dark:text-emerald-100">{newKey}</code>
        </div>
      ) : null}

      {error ? <div className="rounded-2xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-200">{error}</div> : null}

      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-500">Credentials</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-950 dark:text-white">API Keys</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">
              Create keys for service-to-service calls to the local FastAPI OCR engine. Full keys are only shown once. Deleted keys are removed from the system.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-emerald-400 focus:ring-4 focus:ring-emerald-400/10 dark:border-slate-800 dark:bg-slate-900"
              value={keyName}
              onChange={(event) => setKeyName(event.target.value)}
              placeholder="Key name"
            />
            <button
              className="rounded-2xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60 dark:bg-emerald-400 dark:text-slate-950"
              type="button"
              disabled={isMutating}
              onClick={() =>
                mutate(() => (activeKeys.length === 0 ? bootstrapApiKey(session!) : createApiKey(session!, keyName || "default")))
              }
            >
              {activeKeys.length === 0 ? "Create First API Key" : "Create New Key"}
            </button>
          </div>
        </div>

        <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800">
          <table className="w-full divide-y divide-slate-200 text-left text-sm dark:divide-slate-800">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900/70">
              <tr>
                <th className="px-4 py-3">Prefix</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {keys.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-500" colSpan={5}>No API keys yet.</td>
                </tr>
              ) : (
                keys.map((key) => (
                  <tr key={key.id} className="bg-white dark:bg-slate-950">
                    <td className="px-4 py-4 font-mono text-xs text-slate-700 dark:text-slate-200">{key.key_prefix}</td>
                    <td className="px-4 py-4 text-slate-700 dark:text-slate-200">{key.name}</td>
                    <td className="px-4 py-4">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${key.status === "active" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-200" : "bg-slate-100 text-slate-500 dark:bg-slate-900"}`}>
                        {key.status}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-slate-500">{new Date(key.created_at).toLocaleString()}</td>
                    <td className="px-4 py-4 text-right">
                      <button
                        className="text-sm font-semibold text-red-600 disabled:text-slate-400"
                        type="button"
                        disabled={isMutating}
                        onClick={() => {
                          if (window.confirm("Delete this API key permanently? This cannot be undone.")) {
                            mutate(() => deleteApiKey(session!, key.id));
                          }
                        }}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
