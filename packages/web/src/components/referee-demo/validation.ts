// Client-side re-validation for the referee demo.
//
// Mirrors the highest-value checks from the engine's validation plugins
// (core_quarter_sums, referee_player_points_sum, referee_winner_consistency,
// fiba_player_fouls) plus required-empty-field checks that are specific to the
// "complete the acta" workflow. Issues are recomputed after every edit so the
// referee gets instant feedback. Engine-only warnings (ghost players, duplicate
// numbers, progressive mismatch, team fouls) are passed through as informational
// context — our UI does not auto-fix those.

import type {
  IssueSeverity,
  OcrResult,
  QuarterKey,
  ReconcileIssue,
  ReconcileSummary,
  TeamKey,
} from "./types";

const REQUIRED_QUARTERS: QuarterKey[] = ["first", "second", "third", "fourth"];

// Engine warning types we already recompute live — skip them in the passthrough.
const RECOMPUTED_TYPES = new Set([
  "quarter_sum_mismatch",
  "player_points_mismatch",
  "winner_inconsistency",
  "fouls_exceeded",
]);

export function teamName(result: OcrResult, team: TeamKey): string {
  const name = result[team]?.name;
  const fallback = team === "team_a" ? "Equipo A" : "Equipo B";
  return typeof name === "string" && name.trim() ? name.trim() : fallback;
}

export function finalScore(result: OcrResult, team: TeamKey): number | null {
  return toNum(result.footer?.final_score?.[team]);
}

export function quarterScore(result: OcrResult, quarter: QuarterKey, team: TeamKey): number | null {
  return toNum(result.footer?.quarters?.[quarter]?.[team]);
}

export function quartersSum(result: OcrResult, team: TeamKey): number | null {
  let sum = 0;
  for (const q of [...REQUIRED_QUARTERS, "extra" as QuarterKey]) {
    const value = quarterScore(result, q, team);
    if (value !== null) sum += value;
  }
  return sum;
}

export function playerPointsSum(result: OcrResult, team: TeamKey): number {
  const players = result[team]?.players || [];
  return players.reduce((acc, player) => {
    const points = player.points || {};
    const one = toNum(points.one_point) || 0;
    const two = toNum(points.two_point) || 0;
    const three = toNum(points.tree_point ?? points.three_point) || 0;
    return acc + one + two * 2 + three * 3;
  }, 0);
}

export function computeReconciliation(result: OcrResult): ReconcileSummary {
  const issues: ReconcileIssue[] = [];

  for (const team of ["team_a", "team_b"] as TeamKey[]) {
    const name = teamName(result, team);
    const final = finalScore(result, team);

    // Required: final score present.
    if (final === null) {
      issues.push({
        id: `final-empty-${team}`,
        severity: "high",
        source: "live",
        field: `footer.final_score.${team}`,
        title: `Marcador final de ${name} vacío`,
        message: `Falta el marcador final de ${name}. Complétalo para cerrar el acta.`,
      });
    }

    // Required: every regulation quarter present.
    for (const q of REQUIRED_QUARTERS) {
      if (quarterScore(result, q, team) === null) {
        issues.push({
          id: `quarter-empty-${team}-${q}`,
          severity: "medium",
          source: "live",
          field: `footer.quarters.${q}.${team}`,
          title: `Cuarto ${quarterLabel(q)} de ${name} sin rellenar`,
          message: `El cuarto ${quarterLabel(q)} de ${name} no tiene puntuación.`,
        });
      }
    }

    // Quarter sum must match the final score (only when both are complete).
    const allQuartersPresent = REQUIRED_QUARTERS.every((q) => quarterScore(result, q, team) !== null);
    if (final !== null && allQuartersPresent) {
      const sum = quartersSum(result, team) ?? 0;
      if (sum !== final) {
        issues.push({
          id: `quarter-sum-${team}`,
          severity: "high",
          source: "live",
          field: `footer.final_score.${team}`,
          title: `Suma de cuartos ≠ marcador (${name})`,
          message: `La suma de cuartos (${sum}) no coincide con el marcador final (${final}) de ${name}.`,
          suggestion: {
            kind: "set_final_score",
            team,
            value: sum,
            label: `Ajustar marcador a ${sum}`,
          },
        });
      }
    }

    // Sum of player points vs final score (informational — needs per-player edits).
    if (final !== null) {
      const playersSum = playerPointsSum(result, team);
      if (playersSum !== final) {
        issues.push({
          id: `players-sum-${team}`,
          severity: "medium",
          source: "live",
          field: `${team}.players`,
          title: `Puntos de jugadores ≠ marcador (${name})`,
          message: `La suma de puntos individuales (${playersSum}) no coincide con el marcador final (${final}) de ${name}. Revisa las anotaciones de los jugadores.`,
        });
      }
    }

    // No player above 5 personal fouls (informational).
    const players = result[team]?.players || [];
    players.forEach((player, idx) => {
      const personalFouls = Array.isArray(player.fouls)
        ? player.fouls.filter((f) => typeof f === "string" && f.toUpperCase().startsWith("P")).length
        : 0;
      if (personalFouls > 5) {
        const label = (typeof player.name === "string" && player.name.trim()) || `jugador #${player.number ?? idx}`;
        issues.push({
          id: `fouls-${team}-${idx}`,
          severity: "medium",
          source: "live",
          field: `${team}.players[${idx}].fouls`,
          title: `${label} con ${personalFouls} faltas personales`,
          message: `${label} (${name}) tiene ${personalFouls} faltas personales; el máximo FIBA es 5.`,
        });
      }
    });
  }

  // Winner consistency / presence.
  const winner = normalize(result.footer?.winner);
  const scoreA = finalScore(result, "team_a");
  const scoreB = finalScore(result, "team_b");
  if (!winner) {
    issues.push({
      id: "winner-empty",
      severity: "high",
      source: "live",
      field: "footer.winner",
      title: "Ganador no declarado",
      message: "Falta declarar el equipo ganador del partido.",
    });
  } else if (scoreA !== null && scoreB !== null && scoreA !== scoreB) {
    const higherTeam: TeamKey = scoreA > scoreB ? "team_a" : "team_b";
    const higherName = teamName(result, higherTeam);
    const winnerMatchesHigher = winner === higherName.toLowerCase() || winner === higherTeam;
    if (!winnerMatchesHigher) {
      issues.push({
        id: "winner-inconsistent",
        severity: "high",
        source: "live",
        field: "footer.winner",
        title: "Ganador inconsistente con el marcador",
        message: `El ganador declarado ("${result.footer?.winner}") no es el equipo con mayor marcador (${higherName}, ${Math.max(scoreA, scoreB)}-${Math.min(scoreA, scoreB)}).`,
        suggestion: {
          kind: "set_winner",
          winner: higherName,
          label: `Declarar ganador a ${higherName}`,
        },
      });
    }
  }

  // Passthrough of engine warnings we do not recompute (informational context).
  for (const warning of result.validation_warnings || []) {
    if (!warning || RECOMPUTED_TYPES.has(warning.type || "")) continue;
    issues.push({
      id: `engine-${warning.type || "warning"}-${issues.length}`,
      severity: normalizeSeverity(warning.severity),
      source: "engine",
      field: warning.field,
      title: engineTitle(warning.type),
      message: warning.message || "Observación del motor de validación.",
      warning,
    });
  }

  const blockingCount = issues.filter(
    (i) => i.source === "live" && (i.severity === "high" || i.severity === "critical"),
  ).length;

  return {
    issues: issues.sort((a, b) => severityRank(b.severity) - severityRank(a.severity)),
    blockingCount,
    totalCount: issues.length,
    status: blockingCount === 0 ? "cuadrada" : "con_observaciones",
  };
}

function quarterLabel(q: QuarterKey): string {
  return { first: "1", second: "2", third: "3", fourth: "4", extra: "EX" }[q];
}

const ENGINE_WARNING_TITLES: Record<string, string> = {
  ghost_player: "Jugador fantasma detectado",
  duplicate_jersey_number: "Dorsal duplicado",
  progressive_final_mismatch: "Marcador progresivo ≠ final",
  player_progressive_mismatch: "Puntos de jugador ≠ progresivo",
  player_shot_breakdown_mismatch: "Desglose de tiros ≠ progresivo",
  progressive_sequence_jump: "Salto inválido en progresivo",
  progressive_null_player: "Evento progresivo sin dorsal",
  progressive_quarter_mismatch: "Progresivo ≠ puntos del cuarto",
  invalid_entry_state: "Estado de entrada inconsistente",
  unentered_player_activity: "Actividad sin marca de entrada",
  team_fouls_mismatch: "Faltas de equipo ≠ individuales",
  team_fouls_exceeded: "Faltas de equipo excedidas",
  illegible_mark: "Marca ilegible detectada",
  preprocess_fallback: "Recorte automático con respaldo",
  plugin_error: "Error en plugin de validación",
};

function engineTitle(type?: string): string {
  return (type && ENGINE_WARNING_TITLES[type]) || "Observación del motor";
}

function severityRank(severity: IssueSeverity): number {
  return { critical: 3, high: 2, medium: 1, low: 0 }[severity];
}

function normalizeSeverity(value: unknown): IssueSeverity {
  return value === "critical" || value === "high" || value === "medium" || value === "low" ? value : "medium";
}

function toNum(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function normalize(value: unknown): string {
  return typeof value === "string" ? value.trim().toLowerCase() : "";
}
