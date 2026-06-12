import type { DemoPlayer, OcrPlayer, OcrResult, OcrTeam, SavedSinglePlayerGame } from "./types";

export function extractPlayers(result: OcrResult | null): DemoPlayer[] {
  if (!result) return [];
  return [
    ...extractTeamPlayers(result.team_a, "team_a"),
    ...extractTeamPlayers(result.team_b, "team_b"),
  ].sort((a, b) => b.totalPoints - a.totalPoints || a.name.localeCompare(b.name));
}

export function createSavedGame(result: OcrResult, runId: string, player: DemoPlayer): SavedSinglePlayerGame {
  const opponentTeam = player.teamKey === "team_a" ? result.team_b : result.team_a;
  const finalScore = result.footer?.final_score;
  const ownScore = player.teamKey === "team_a" ? finalScore?.team_a : finalScore?.team_b;
  const otherScore = player.teamKey === "team_a" ? finalScore?.team_b : finalScore?.team_a;
  const winner = normalizeText(result.footer?.winner);
  const teamName = normalizeText(player.teamName);
  const won = winner && teamName && winner.toLowerCase() === teamName.toLowerCase();

  return {
    id: `${runId}:${player.id}:${Date.now()}`,
    savedAt: new Date().toISOString(),
    runId,
    player,
    opponent: normalizeText(opponentTeam?.name) || "Unknown opponent",
    teamName: player.teamName,
    gameDate: normalizeText(result.header?.date) || "Unknown date",
    tournament: normalizeText(result.header?.tournament) || normalizeText(result.header?.league) || "Unknown tournament",
    finalScore: typeof ownScore === "number" && typeof otherScore === "number" ? `${ownScore}-${otherScore}` : "Pending score",
    resultLabel: winner ? (won ? "Win" : "Loss") : "Result pending",
  };
}

export function formatGameTitle(result: OcrResult | null) {
  if (!result) return "Upload a FIBA scoresheet to start";
  const teamA = normalizeText(result.team_a?.name) || "Team A";
  const teamB = normalizeText(result.team_b?.name) || "Team B";
  return `${teamA} vs ${teamB}`;
}

export function formatFinalScore(result: OcrResult | null) {
  const score = result?.footer?.final_score;
  if (typeof score?.team_a !== "number" || typeof score.team_b !== "number") return "Score pending";
  return `${score.team_a} - ${score.team_b}`;
}

export function getPlayerInsight(player: DemoPlayer) {
  if (player.totalPoints >= 20) return "High-impact scoring game. Great candidate for tracking shot profile and usage.";
  if (player.totalPoints >= 10) return "Solid offensive contribution. Track consistency across the next games.";
  if (player.foulsCount >= 4) return "Watch foul control: staying available could improve minutes and rhythm.";
  if (player.started) return "Starter minutes detected. Add more games to compare role and production.";
  return "Save this game and add more sheets to build a useful trend line.";
}

function extractTeamPlayers(team: OcrTeam | null | undefined, teamKey: "team_a" | "team_b") {
  const teamName = normalizeText(team?.name) || (teamKey === "team_a" ? "Team A" : "Team B");
  return (team?.players || []).map((player, index) => toDemoPlayer(player, teamKey, teamName, index));
}

function toDemoPlayer(player: OcrPlayer, teamKey: "team_a" | "team_b", teamName: string, index: number): DemoPlayer {
  const points = player.points || {};
  const onePoint = toNumber(points.one_point);
  const twoPoint = toNumber(points.two_point);
  const threePoint = toNumber(points.tree_point ?? points.three_point);
  const number = normalizeText(player.number) || "?";
  const name = normalizeText(player.name) || `Player #${number}`;

  return {
    id: `${teamKey}:${number}:${index}`,
    teamKey,
    teamName,
    name,
    number,
    onePoint,
    twoPoint,
    threePoint,
    totalPoints: onePoint + twoPoint * 2 + threePoint * 3,
    foulsCount: Array.isArray(player.fouls) ? player.fouls.length : 0,
    started: Boolean(player.started),
    entered: Boolean(player.entered),
  };
}

function toNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function normalizeText(value: unknown) {
  return typeof value === "string" ? value.trim() : typeof value === "number" ? String(value) : "";
}
