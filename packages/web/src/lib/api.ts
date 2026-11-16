import type { Session } from "@supabase/supabase-js";

import { siteConfig } from "@/lib/env";

export type ApiKeyRecord = {
  id: string;
  key_prefix: string;
  name: string;
  status: "active" | string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
};

export type ApiEnvelope<T> = T & { success: boolean };

export type RunStatus = "queued" | "pending" | "running" | "completed" | "failed" | "cancelled" | "skipped" | string;

export type RunRecord = {
  success?: boolean;
  run_id: string;
  status: RunStatus;
  created_at?: string;
  updated_at?: string;
  error?: unknown;
};

export class OcrApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
  ) {
    super(message);
    this.name = "OcrApiError";
  }
}

const IDEMPOTENT_METHODS = new Set(["GET", "HEAD", "OPTIONS", "DELETE"]);
const RETRYABLE_STATUS = new Set([502, 503, 504]);
const RETRY_BACKOFF_MS = [1_500, 3_000];

function requestMethod(init: RequestInit): string {
  return (init.method ?? "GET").toUpperCase();
}

function canRetryRequest(method: string): boolean {
  return IDEMPOTENT_METHODS.has(method);
}

function isRetryableStatus(status: number): boolean {
  return RETRYABLE_STATUS.has(status);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function unreachableApiMessage(): string {
  return `Could not reach the OCR API at ${siteConfig.apiBaseUrl}. The API may be starting up; retry in a few seconds.`;
}

export async function apiFetch<T>(
  path: string,
  session: Pick<Session, "access_token">,
  init: RequestInit = {},
): Promise<T> {
  const method = requestMethod(init);
  const retryable = canRetryRequest(method);
  const maxAttempts = retryable ? RETRY_BACKOFF_MS.length + 1 : 1;
  let lastNetworkError: OcrApiError | undefined;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (attempt > 0) {
      await sleep(RETRY_BACKOFF_MS[attempt - 1] ?? RETRY_BACKOFF_MS[RETRY_BACKOFF_MS.length - 1]);
    }

    let response: Response;
    try {
      response = await fetch(`${siteConfig.apiBaseUrl}${path}`, {
        ...init,
        headers: buildHeaders(session, init),
        cache: "no-store",
      });
    } catch {
      lastNetworkError = new OcrApiError(unreachableApiMessage(), 0, "network_error");
      if (!retryable || attempt === maxAttempts - 1) {
        throw lastNetworkError;
      }
      continue;
    }

    if (retryable && isRetryableStatus(response.status) && attempt < maxAttempts - 1) {
      if (response.body) {
        void response.body.cancel();
      }
      continue;
    }

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json") ? await response.json() : await response.text();

    if (!response.ok) {
      const { message, code } = extractApiError(payload, response.status);
      throw new OcrApiError(message, response.status, code);
    }

    return payload as T;
  }

  throw lastNetworkError ?? new OcrApiError(unreachableApiMessage(), 0, "network_error");
}


function extractApiError(payload: unknown, status: number): { message: string; code?: string } {
  const fallback = `Request failed with ${status}`;
  if (typeof payload === "string" && payload.trim()) {
    return { message: payload };
  }
  if (!payload || typeof payload !== "object") {
    return { message: fallback };
  }
  const body = payload as { detail?: unknown; error?: { code?: string; message?: string } };
  const nested = body.detail && typeof body.detail === "object" ? (body.detail as { error?: { code?: string; message?: string } }) : null;
  const error = body.error || nested?.error;
  const detailMessage = typeof body.detail === "string" ? body.detail : undefined;
  return { message: error?.message || detailMessage || fallback, code: error?.code };
}

function buildHeaders(session: Pick<Session, "access_token">, init: RequestInit) {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${session.access_token}`);

  if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  return headers;
}

export async function listApiKeys(session: Pick<Session, "access_token">) {
  return apiFetch<ApiEnvelope<{ keys: ApiKeyRecord[] }>>("/v1/me/api-keys", session);
}

export async function bootstrapApiKey(session: Pick<Session, "access_token">) {
  return apiFetch<ApiEnvelope<{ key: string; key_prefix: string; message: string }>>(
    "/v1/me/api-keys/bootstrap",
    session,
    { method: "POST" },
  );
}

export async function createApiKey(session: Pick<Session, "access_token">, name: string) {
  const params = new URLSearchParams({ name });
  return apiFetch<ApiEnvelope<{ key: string; key_prefix: string; name: string; message: string }>>(
    `/v1/me/api-keys?${params.toString()}`,
    session,
    { method: "POST" },
  );
}

export async function deleteApiKey(session: Pick<Session, "access_token">, keyId: string) {
  return apiFetch<ApiEnvelope<{ key_id: string; status: "deleted" | string }>>(`/v1/me/api-keys/${keyId}`, session, {
    method: "DELETE",
  });
}


export async function uploadRun(
  session: Pick<Session, "access_token">,
  file: File,
  options?: { validationPlugins?: string[] | "all" },
) {
  const formData = new FormData();
  formData.append("file", file);
  if (options?.validationPlugins) {
    formData.append("options_json", JSON.stringify({ validation_plugins: options.validationPlugins }));
  }
  return apiFetch<ApiEnvelope<RunRecord>>("/v1/runs/upload", session, {
    method: "POST",
    body: formData,
    headers: {},
  });
}

export async function getRun(session: Pick<Session, "access_token">, runId: string) {
  return apiFetch<RunRecord>(`/v1/runs/${encodeURIComponent(runId)}`, session);
}

export async function getRunResult<T>(session: Pick<Session, "access_token">, runId: string) {
  return apiFetch<T>(`/v1/runs/${encodeURIComponent(runId)}/result`, session);
}

export type AccountRecord = {
  id: string;
  email: string;
  role: string;
  status: string;
  plan?: string | null;
  assigned_demo?: string | null;
  created_at?: string | null;
  accepted_at?: string | null;
  invited_at?: string | null;
};

export async function listAdminAccounts(session: Pick<Session, "access_token">) {
  return apiFetch<ApiEnvelope<{ accounts: AccountRecord[] }>>("/v1/admin/accounts", session);
}

export async function listAccountApiKeys(session: Pick<Session, "access_token">, accountId: string) {
  return apiFetch<ApiEnvelope<{ account_id: string; keys: ApiKeyRecord[] }>>(
    `/v1/admin/accounts/${encodeURIComponent(accountId)}/api-keys`,
    session,
  );
}

export async function createAccountApiKey(session: Pick<Session, "access_token">, accountId: string, name: string) {
  const params = new URLSearchParams({ name });
  return apiFetch<ApiEnvelope<{ key: string; key_prefix: string; name: string; account_id: string; message: string }>>(
    `/v1/admin/accounts/${encodeURIComponent(accountId)}/api-keys?${params.toString()}`,
    session,
    { method: "POST" },
  );
}

export async function deleteAccountApiKey(session: Pick<Session, "access_token">, accountId: string, keyId: string) {
  return apiFetch<ApiEnvelope<{ key_id: string; account_id: string; status: "deleted" | string }>>(
    `/v1/admin/accounts/${encodeURIComponent(accountId)}/api-keys/${encodeURIComponent(keyId)}`,
    session,
    { method: "DELETE" },
  );
}

