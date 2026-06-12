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

export async function apiFetch<T>(
  path: string,
  session: Pick<Session, "access_token">,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${siteConfig.apiBaseUrl}${path}`, {
    ...init,
    headers: buildHeaders(session, init),
    cache: "no-store",
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const detail = typeof payload === "object" && payload !== null ? payload.detail || payload.error?.message : payload;
    const code = typeof payload === "object" && payload !== null ? payload.error?.code : undefined;
    throw new OcrApiError(detail || `Request failed with ${response.status}`, response.status, code);
  }

  return payload as T;
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


export async function uploadRun(session: Pick<Session, "access_token">, file: File) {
  const formData = new FormData();
  formData.append("file", file);
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
