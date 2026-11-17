"use client";

import { useEffect, useRef, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { toast } from "sonner";

import { KeyStatusChip, NewApiKeyBanner } from "@/components/api-key-widgets";
import {
  createAccountApiKey,
  deleteAccountApiKey,
  listAccountApiKeys,
  listAdminAccounts,
  type AccountRecord,
  type ApiKeyRecord,
} from "@/lib/api";
import { useSupabaseSession } from "@/lib/supabase/use-session";

export function AccountKeysPanel() {
  const { session, isBooting } = useSupabaseSession();
  const [accounts, setAccounts] = useState<AccountRecord[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [keys, setKeys] = useState<ApiKeyRecord[]>([]);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [keyName, setKeyName] = useState("default");
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const didInitialLoadRef = useRef(false);

  const selectedAccount = accounts.find((account) => account.id === selectedAccountId) ?? null;

  async function loadKeys(currentSession: Session, accountId: string) {
    const response = await listAccountApiKeys(currentSession, accountId);
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
    async function load() {
      try {
        const response = await listAdminAccounts(session!);
        if (!mounted) return;
        const nextAccounts = response.accounts;
        setAccounts(nextAccounts);
        const initialId = nextAccounts[0]?.id ?? "";
        setSelectedAccountId(initialId);
        if (initialId) {
          const keysResponse = await listAccountApiKeys(session!, initialId);
          if (!mounted) return;
          setKeys(keysResponse.keys);
        }
      } catch (err) {
        if (!mounted) return;
        const message = err instanceof Error ? err.message : "Failed to load accounts";
        setError(message);
        toast.error(message);
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    load();

    return () => {
      mounted = false;
    };
  }, [isBooting, session]);

  async function onSelectAccount(accountId: string) {
    if (!session) return;
    setSelectedAccountId(accountId);
    setNewKey(null);
    setError(null);
    setIsMutating(true);
    try {
      await loadKeys(session, accountId);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load API keys";
      setError(message);
      toast.error(message);
      setKeys([]);
    } finally {
      setIsMutating(false);
    }
  }

  async function issueKey() {
    if (!session || !selectedAccountId) return;
    setIsMutating(true);
    setError(null);
    try {
      const response = await createAccountApiKey(session, selectedAccountId, keyName || "default");
      setNewKey(response.key);
      toast.success("API key created. Save it now — it will only be shown once.");
      await loadKeys(session, selectedAccountId);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Request failed";
      setError(message);
      toast.error(message);
    } finally {
      setIsMutating(false);
    }
  }

  async function revokeKey(key: ApiKeyRecord) {
    if (!session || !selectedAccountId) return;
    if (!window.confirm("Revoke this API key permanently? This cannot be undone.")) return;
    setIsMutating(true);
    setError(null);
    try {
      await deleteAccountApiKey(session, selectedAccountId, key.id);
      toast.success("API key revoked.");
      await loadKeys(session, selectedAccountId);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Request failed";
      setError(message);
      toast.error(message);
    } finally {
      setIsMutating(false);
    }
  }

  if (isLoading) {
    return <div className="rounded-panel border border-border bg-surface p-8 text-muted shadow-sm">Loading accounts...</div>;
  }

  return (
    <div className="space-y-6">
      {newKey ? (
        <NewApiKeyBanner
          apiKey={newKey}
          helperText="It will not be shown again after you dismiss this message. Share it out of band with the account owner."
          onDismiss={() => setNewKey(null)}
        />
      ) : null}

      {error ? <div className="rounded-card bg-danger-soft p-4 text-sm text-danger">{error}</div> : null}

      <div className="rounded-panel border border-border bg-surface p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep sm:text-sm">Accounts</p>
            <h2 className="mt-2 text-2xl font-semibold text-ink">Issue keys for another account</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
              Pick any account, including invited testers, then issue or revoke an <code className="rounded bg-elevated px-1.5 py-0.5">ocr_live_</code> key. The raw key is shown once.
            </p>
          </div>

          <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
            <label className="flex min-w-0 flex-1 flex-col gap-2 text-sm text-muted">
              Account
              <select
                className="rounded-field border border-border bg-surface px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-4 focus:ring-primary/15"
                value={selectedAccountId}
                onChange={(event) => onSelectAccount(event.target.value)}
                disabled={isMutating || accounts.length === 0}
              >
                {accounts.length === 0 ? <option value="">No accounts found</option> : null}
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.email || account.id} · {account.role} · {account.status}
                  </option>
                ))}
              </select>
            </label>
            <input
              className="rounded-field border border-border bg-surface px-4 py-3 text-sm text-ink outline-none placeholder:text-faint focus:border-primary focus:ring-4 focus:ring-primary/15"
              value={keyName}
              onChange={(event) => setKeyName(event.target.value)}
              placeholder="Key name"
              disabled={!selectedAccount || selectedAccount.status !== "active"}
            />
            <button
              className="rounded-field bg-primary px-5 py-3 text-sm font-semibold text-primary-contrast transition hover:bg-primary/85 disabled:opacity-60"
              type="button"
              disabled={isMutating || !selectedAccount || selectedAccount.status !== "active"}
              onClick={issueKey}
            >
              Issue key
            </button>
          </div>

          {selectedAccount && selectedAccount.status !== "active" ? (
            <p className="text-sm text-muted">This account is {selectedAccount.status}. Keys can only be issued to active accounts.</p>
          ) : null}
        </div>

        {keys.length === 0 ? (
          <div className="mt-6 rounded-card border border-dashed border-border p-8 text-center text-sm text-muted">
            {selectedAccount ? "No API keys for this account yet." : "Select an account to manage keys."}
          </div>
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
                      onClick={() => revokeKey(key)}
                    >
                      Revoke
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
                          onClick={() => revokeKey(key)}
                        >
                          Revoke
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
