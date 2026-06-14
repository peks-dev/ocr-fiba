// Client for the league backend, talking only to our server-side proxy
// (/api/league/submissions). The Airtable token never reaches the browser.
// This thin layer keeps the persistence backend swappable (Airtable → Supabase).

import type { LeagueRecord, LeagueSubmissionPayload } from "./types";

const ENDPOINT = "/api/league/submissions";

export class LeagueStoreError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "LeagueStoreError";
  }
}

export async function listSubmissions(): Promise<LeagueRecord[]> {
  const response = await fetch(ENDPOINT, { cache: "no-store" });
  const payload = await safeJson(response);
  if (!response.ok) {
    throw new LeagueStoreError(errorText(payload, "No se pudieron cargar los partidos de la liga."), response.status);
  }
  return (payload?.records as LeagueRecord[]) || [];
}

export async function createSubmission(submission: LeagueSubmissionPayload): Promise<LeagueRecord> {
  const response = await fetch(ENDPOINT, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(submission),
  });
  const payload = await safeJson(response);
  if (!response.ok) {
    throw new LeagueStoreError(errorText(payload, "No se pudo enviar el partido a la liga."), response.status);
  }
  return payload?.record as LeagueRecord;
}

function errorText(payload: Record<string, unknown> | null, fallback: string): string {
  return typeof payload?.error === "string" ? payload.error : fallback;
}

async function safeJson(response: Response): Promise<Record<string, unknown> | null> {
  try {
    return (await response.json()) as Record<string, unknown>;
  } catch {
    return null;
  }
}
