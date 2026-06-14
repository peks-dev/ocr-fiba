// Pure helpers to edit the working acta immutably, apply suggestions, and
// build the structured league submission payload.

import { computeReconciliation, finalScore, teamName } from "./validation";
import type {
  LeagueSubmissionPayload,
  OcrPlayer,
  OcrResult,
  PlayerPoints,
  ProgressiveEvent,
  QuarterKey,
  Suggestion,
  TeamKey,
} from "./types";

export function applySuggestion(result: OcrResult, suggestion: Suggestion): OcrResult {
  switch (suggestion.kind) {
    case "set_final_score":
      return setFinalScore(result, suggestion.team, suggestion.value);
    case "set_winner":
      return setWinner(result, suggestion.winner);
    default:
      return result;
  }
}

export function setHeaderField(
  result: OcrResult,
  field: "league" | "tournament" | "date" | "time" | "gender" | "first_judge" | "second_judge",
  value: string,
): OcrResult {
  return { ...result, header: { ...(result.header || {}), [field]: value } };
}

export function setTeamName(result: OcrResult, team: TeamKey, value: string): OcrResult {
  return { ...result, [team]: { ...(result[team] || {}), name: value } };
}

export function setTeamCaptain(result: OcrResult, team: TeamKey, value: string): OcrResult {
  return { ...result, [team]: { ...(result[team] || {}), captain: value } };
}

export function setFinalScore(result: OcrResult, team: TeamKey, value: number | null): OcrResult {
  const footer = result.footer || {};
  return {
    ...result,
    footer: {
      ...footer,
      final_score: { ...(footer.final_score || {}), [team]: value },
    },
  };
}

export function setWinner(result: OcrResult, winner: string): OcrResult {
  return {
    ...result,
    footer: { ...(result.footer || {}), winner },
  };
}

export function setQuarter(result: OcrResult, quarter: QuarterKey, team: TeamKey, value: number | null): OcrResult {
  const footer = result.footer || {};
  const quarters = footer.quarters || {};
  const current = quarters[quarter] || {};
  return {
    ...result,
    footer: {
      ...footer,
      quarters: { ...quarters, [quarter]: { ...current, [team]: value } },
    },
  };
}

export function setPlayerTextField(result: OcrResult, team: TeamKey, index: number, field: "name" | "number", value: string): OcrResult {
  return updatePlayer(result, team, index, (player) => ({ ...player, [field]: value }));
}

export function setPlayerPoint(result: OcrResult, team: TeamKey, index: number, field: keyof PlayerPoints, value: number | null): OcrResult {
  return updatePlayer(result, team, index, (player) => ({
    ...player,
    points: { ...(player.points || {}), [field]: value },
  }));
}

export function setPlayerFoulsText(result: OcrResult, team: TeamKey, index: number, value: string): OcrResult {
  const fouls = value
    .split(/[ ,;]+/)
    .map((foul) => foul.trim())
    .filter(Boolean);
  return updatePlayer(result, team, index, (player) => ({ ...player, fouls }));
}

export function setTeamFoul(result: OcrResult, team: TeamKey, quarterIndex: number, value: number | null): OcrResult {
  const current = result[team]?.team_fouls_quarters || [];
  const next = [...current];
  next[quarterIndex] = value;
  return { ...result, [team]: { ...(result[team] || {}), team_fouls_quarters: next } };
}

export function setProgressiveEventField(
  result: OcrResult,
  team: TeamKey,
  index: number,
  field: keyof ProgressiveEvent,
  value: string | number | null,
): OcrResult {
  const progressive = result.progressive_score || {};
  const events = progressive[team] || [];
  const next = events.map((event, idx) => (idx === index ? { ...event, [field]: value } : event));
  return { ...result, progressive_score: { ...progressive, [team]: next } };
}

export function addProgressiveEvent(result: OcrResult, team: TeamKey): OcrResult {
  const progressive = result.progressive_score || {};
  const events = progressive[team] || [];
  const previous = events[events.length - 1];
  const nextEvent: ProgressiveEvent = {
    player_number: null,
    running_score: previous?.running_score ?? null,
    points: null,
    period: previous?.period ?? null,
  };
  return { ...result, progressive_score: { ...progressive, [team]: [...events, nextEvent] } };
}

export function removeProgressiveEvent(result: OcrResult, team: TeamKey, index: number): OcrResult {
  const progressive = result.progressive_score || {};
  const events = progressive[team] || [];
  return { ...result, progressive_score: { ...progressive, [team]: events.filter((_, idx) => idx !== index) } };
}

export function formatFinalScore(result: OcrResult): string {
  const a = finalScore(result, "team_a");
  const b = finalScore(result, "team_b");
  if (a === null || b === null) return "Marcador pendiente";
  return `${a} - ${b}`;
}

export function gameTitle(result: OcrResult): string {
  return `${teamName(result, "team_a")} vs ${teamName(result, "team_b")}`;
}

export function buildSubmissionPayload(result: OcrResult, runId: string): LeagueSubmissionPayload {
  const summary = computeReconciliation(result);
  const a = finalScore(result, "team_a");
  const b = finalScore(result, "team_b");
  const header = result.header || {};

  return {
    match_id: `referee:${runId}:${Date.now()}`,
    league: text(header.league),
    tournament: text(header.tournament),
    game_date: text(header.date),
    team_a: teamName(result, "team_a"),
    team_b: teamName(result, "team_b"),
    final_score: a !== null && b !== null ? `${a} - ${b}` : "",
    winner: text(result.footer?.winner),
    reconcile_status: summary.status,
    warnings_remaining: summary.blockingCount,
    source_run_id: runId,
    payload_json: JSON.stringify(result),
  };
}

function updatePlayer(result: OcrResult, team: TeamKey, index: number, updater: (player: OcrPlayer) => OcrPlayer): OcrResult {
  const players = result[team]?.players || [];
  const nextPlayers = players.map((player, idx) => (idx === index ? updater(player) : player));
  return { ...result, [team]: { ...(result[team] || {}), players: nextPlayers } };
}

function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : typeof value === "number" ? String(value) : "";
}
