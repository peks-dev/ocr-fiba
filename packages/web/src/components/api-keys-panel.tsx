"use client";

import { useEffect, useRef, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { toast } from "sonner";

import { KeyStatusChip, NewApiKeyBanner } from "@/components/api-key-widgets";
import {
  bootstrapApiKey,
  createApiKey,
  listApiKeys,
  deleteApiKey,
  type ApiKeyRecord,
} from "@/lib/api";
import { useSupabaseSession } from "@/lib/supabase/use-session";

export function ApiKeysPanel() {
  const { session, isBooting } = useSupabaseSession();
  const [keys, setKeys] = useState<ApiKeyRecord[]>([]);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [keyName, setKeyName] = useState("default");
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const didInitialLoadRef = useRef(false);

  async function refresh(currentSession: Session) {
    setError(null);
    const response = await listApiKeys(currentSession);
    setKeys(response.keys);
  }

  useEffect(() => {
    if (isBooting) return;
    if (!session) {
      setIsLoading(false);
      setError("No active Supabase session. Please log in again.");
      return;
    }
    if (didInitialLoadRef.current) return;
    didInitialLoadRef.current = true;

    let mounted = true;
    listApiKeys(session)
      .then((response) => {
        if (!mounted) return;
        setKeys(response.keys);
      })
      .catch((err) => {
        if (!mounted) return;
        const message = err instanceof Error ? err.message : "Failed to load API keys";
        setError(message);
        toast.error(message);
      })
      .finally(() => {
        if (mounted) setIsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [isBooting, session]);

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

  function confirmDelete(key: ApiKeyRecord) {
    if (window.confirm("Delete this API key permanently? This cannot be undone.")) {
      mutate(() => deleteApiKey(session!, key.id));
    }
  }

  const activeKeys = keys.filter((key) => key.status === "active");

  if (isLoading) {
    return <div className="rounded-panel border border-border bg-surface p-8 text-muted shadow-sm">Loading API keys...</div>;
  }

  return (
    <div className="space-y-6">
      {newKey ? (
        <NewApiKeyBanner
          apiKey={newKey}
          helperText="It will not be shown again after you dismiss this message."
          onDismiss={() => setNewKey(null)}
        />
      ) : null}

      {error ? <div className="rounded-card bg-danger-soft p-4 text-sm text-danger">{error}</div> : null}

      <div className="rounded-panel border border-border bg-surface p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep sm:text-sm">Credentials</p>
            <h2 className="mt-2 text-2xl font-semibold text-ink">API Keys</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
              These keys belong to your admin account and are for service-to-service calls to the OCR API. Full keys are only shown once. Deleted keys are removed from the system.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              className="rounded-field border border-border bg-surface px-4 py-3 text-sm text-ink outline-none placeholder:text-faint focus:border-primary focus:ring-4 focus:ring-primary/15"
              value={keyName}
              onChange={(event) => setKeyName(event.target.value)}
              placeholder="Key name"
            />
            <button
              className="rounded-field bg-primary px-5 py-3 text-sm font-semibold text-primary-contrast transition hover:bg-primary/85 disabled:opacity-60"
              type="button"
              disabled={isMutating || !session}
              onClick={() =>
                mutate(() => (activeKeys.length === 0 ? bootstrapApiKey(session!) : createApiKey(session!, keyName || "default")))
              }
            >
              {activeKeys.length === 0 ? "Create First API Key" : "Create New Key"}
            </button>
          </div>
        </div>

        {keys.length === 0 ? (
          <div className="mt-6 rounded-card border border-dashed border-border p-8 text-center text-sm text-muted">No API keys yet.</div>
        ) : (
          <>
            <div className="mt-6 space-y-3 md:hidden">
              {keys.map((key) => (
                <article key={key.id} className="rounded-card border border-border bg-elevated p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-ink">{key.name}</p>
                      <p className="mt-1 font-mono text-xs text-muted">{key.key_prefix}</p>
                    </div>
                    <KeyStatusChip status={key.status} />
                  </div>
                  <div className="mt-4 flex items-center justify-between gap-3 text-xs text-faint">
                    <span>{new Date(key.created_at).toLocaleString()}</span>
                    <button
                      className="text-sm font-semibold text-danger disabled:text-faint"
                      type="button"
                      disabled={isMutating}
                      onClick={() => confirmDelete(key)}
                    >
                      Delete
                    </button>
                  </div>
                </article>
              ))}
            </div>

            <div className="mt-6 hidden overflow-hidden rounded-card border border-border md:block">
              <table className="w-full divide-y divide-border text-left text-sm">
                <thead className="bg-elevated text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th className="px-4 py-3">Prefix</th>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Created</th>
                    <th className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {keys.map((key) => (
                    <tr key={key.id} className="bg-surface">
                      <td className="px-4 py-4 font-mono text-xs text-ink">{key.key_prefix}</td>
                      <td className="px-4 py-4 text-ink">{key.name}</td>
                      <td className="px-4 py-4">
                        <KeyStatusChip status={key.status} />
                      </td>
                      <td className="px-4 py-4 text-muted">{new Date(key.created_at).toLocaleString()}</td>
                      <td className="px-4 py-4 text-right">
                        <button
                          className="text-sm font-semibold text-danger disabled:text-faint"
                          type="button"
                          disabled={isMutating}
                          onClick={() => confirmDelete(key)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
