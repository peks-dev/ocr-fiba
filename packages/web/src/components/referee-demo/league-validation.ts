import type { LeagueSubmissionPayload } from "@/components/referee-demo/types";

const MAX_PAYLOAD_JSON_BYTES = 512_000;
const STRING_FIELDS = [
  "match_id",
  "league",
  "tournament",
  "game_date",
  "team_a",
  "team_b",
  "final_score",
  "winner",
  "source_run_id",
  "payload_json",
] as const satisfies readonly (keyof LeagueSubmissionPayload)[];

export type LeagueValidationResult =
  | { ok: true; fields: Record<string, unknown> }
  | { ok: false; error: string };

export function validateLeagueSubmissionPayload(body: unknown): LeagueValidationResult {
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return { ok: false, error: "Cuerpo de la petición inválido." };
  }

  const raw = body as Record<string, unknown>;
  if (typeof raw.match_id !== "string" || !raw.match_id.trim()) {
    return { ok: false, error: "Falta match_id en el envío." };
  }
  if (raw.match_id.trim().length > 200) {
    return { ok: false, error: "match_id excede el tamaño máximo permitido." };
  }

  const fields: Record<string, unknown> = {};
  for (const key of STRING_FIELDS) {
    const value = raw[key];
    if (value === undefined) continue;
    if (typeof value !== "string") {
      return { ok: false, error: `El campo ${key} debe ser texto.` };
    }
    if (key === "payload_json" && value.length > MAX_PAYLOAD_JSON_BYTES) {
      return { ok: false, error: "payload_json excede el tamaño máximo permitido." };
    }
    if (key !== "payload_json" && value.length > 500) {
      return { ok: false, error: `El campo ${key} excede la longitud permitida.` };
    }
    fields[key] = value.trim();
  }

  if (raw.reconcile_status !== undefined) {
    if (raw.reconcile_status !== "cuadrada" && raw.reconcile_status !== "con_observaciones") {
      return { ok: false, error: "reconcile_status inválido." };
    }
    fields.reconcile_status = raw.reconcile_status;
  }

  if (raw.warnings_remaining !== undefined) {
    if (
      typeof raw.warnings_remaining !== "number" ||
      !Number.isInteger(raw.warnings_remaining) ||
      raw.warnings_remaining < 0
    ) {
      return { ok: false, error: "warnings_remaining debe ser un entero no negativo." };
    }
    fields.warnings_remaining = raw.warnings_remaining;
  }

  return { ok: true, fields };
}
