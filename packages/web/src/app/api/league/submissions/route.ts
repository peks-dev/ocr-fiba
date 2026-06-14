// Server-side proxy to Airtable for the referee demo's league view.
//
// The Airtable Personal Access Token lives ONLY in server env (AIRTABLE_TOKEN)
// and is never exposed to the browser. The client talks to this route handler.

import { NextResponse } from "next/server";

import type { LeagueRecord, LeagueSubmissionPayload } from "@/components/referee-demo/types";

export const dynamic = "force-dynamic";

const AIRTABLE_API = "https://api.airtable.com/v0";
const SUBMISSION_FIELDS: (keyof LeagueSubmissionPayload)[] = [
  "match_id",
  "league",
  "tournament",
  "game_date",
  "team_a",
  "team_b",
  "final_score",
  "winner",
  "reconcile_status",
  "warnings_remaining",
  "source_run_id",
  "payload_json",
];

type AirtableConfig = { token: string; baseId: string; table: string };

function readConfig(): AirtableConfig | null {
  const token = process.env.AIRTABLE_TOKEN;
  const baseId = process.env.AIRTABLE_BASE_ID;
  const table = process.env.AIRTABLE_LEAGUE_TABLE || "League Submissions";
  if (!token || !baseId) return null;
  return { token, baseId, table };
}

function airtableUrl({ baseId, table }: AirtableConfig, query = ""): string {
  return `${AIRTABLE_API}/${baseId}/${encodeURIComponent(table)}${query}`;
}

function notConfigured() {
  return NextResponse.json(
    { error: "La liga no está configurada. Define AIRTABLE_TOKEN y AIRTABLE_BASE_ID en el entorno." },
    { status: 503 },
  );
}

export async function GET() {
  const config = readConfig();
  if (!config) return notConfigured();

  try {
    const response = await fetch(
      airtableUrl(config, "?sort%5B0%5D%5Bfield%5D=match_id&sort%5B0%5D%5Bdirection%5D=desc&pageSize=50"),
      { headers: { Authorization: `Bearer ${config.token}` }, cache: "no-store" },
    );
    const payload = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { error: payload?.error?.message || "Airtable rechazó la consulta." },
        { status: response.status },
      );
    }

    const records: LeagueRecord[] = (payload.records || []).map((record: AirtableRecord) => ({
      id: record.id,
      submittedAt: record.createdTime ?? null,
      fields: record.fields || {},
    }));
    return NextResponse.json({ records });
  } catch {
    return NextResponse.json({ error: "No se pudo contactar a Airtable." }, { status: 502 });
  }
}

export async function POST(request: Request) {
  const config = readConfig();
  if (!config) return notConfigured();

  let body: Partial<LeagueSubmissionPayload>;
  try {
    body = (await request.json()) as Partial<LeagueSubmissionPayload>;
  } catch {
    return NextResponse.json({ error: "Cuerpo de la petición inválido." }, { status: 400 });
  }

  if (!body.match_id) {
    return NextResponse.json({ error: "Falta match_id en el envío." }, { status: 400 });
  }

  const fields: Record<string, unknown> = {};
  for (const key of SUBMISSION_FIELDS) {
    if (body[key] !== undefined) fields[key] = body[key];
  }

  try {
    const response = await fetch(airtableUrl(config), {
      method: "POST",
      headers: { Authorization: `Bearer ${config.token}`, "content-type": "application/json" },
      body: JSON.stringify({ fields, typecast: true }),
    });
    const payload = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { error: payload?.error?.message || "Airtable rechazó el envío." },
        { status: response.status },
      );
    }

    const record: LeagueRecord = {
      id: payload.id,
      submittedAt: payload.createdTime ?? null,
      fields: payload.fields || {},
    };
    return NextResponse.json({ record }, { status: 201 });
  } catch {
    return NextResponse.json({ error: "No se pudo contactar a Airtable." }, { status: 502 });
  }
}

type AirtableRecord = { id: string; createdTime?: string; fields?: Record<string, unknown> };
