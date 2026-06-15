import { findBestRosterNameMatch } from "./name-match";

import type { ClubGame, ClubGamePlayerStat, ClubPlayer, OcrPlayer, OcrResult, OcrTeam, TeamKey } from "./types";

export function teamName(result: OcrResult | null, team: TeamKey): string {
  return normalizeText(result?.[team]?.name) || (team === "team_a" ? "Team A" : "Team B");
}

export function createGameFromResult(result: OcrResult, runId: string, clubTeam: TeamKey, roster: ClubPlayer[]): ClubGame {
  const opponentTeam: TeamKey = clubTeam === "team_a" ? "team_b" : "team_a";
  const finalScore = result.footer?.final_score;
  const ownScore = clubTeam === "team_a" ? finalScore?.team_a : finalScore?.team_b;
  const otherScore = clubTeam === "team_a" ? finalScore?.team_b : finalScore?.team_a;
  const clubTeamName = teamName(result, clubTeam);
  const opponent = teamName(result, opponentTeam);
  const winner = normalizeText(result.footer?.winner);

  return {
    id: `${runId}:${clubTeam}:${Date.now()}`,
    runId,
    savedAt: new Date().toISOString(),
    gameDate: normalizeText(result.header?.date) || "Unknown date",
    tournament: normalizeText(result.header?.tournament) || normalizeText(result.header?.league) || "Unknown tournament",
    clubTeamName,
    opponent,
    finalScore: typeof ownScore === "number" && typeof otherScore === "number" ? `${ownScore}-${otherScore}` : "Score pending",
    resultLabel: winner ? (winner.toLowerCase() === clubTeamName.toLowerCase() ? "Win" : "Loss") : "Result pending",
    stats: extractTeamStats(result[clubTeam], roster),
  };
}

export function extractTeamStats(team: OcrTeam | null | undefined, roster: ClubPlayer[]): ClubGamePlayerStat[] {
  return (team?.players || [])
    .map((player, index) => toClubStat(player, roster, index))
    .sort((a, b) => b.totalPoints - a.totalPoints || Number(a.number) - Number(b.number) || a.playerName.localeCompare(b.playerName));
}

export function clubSummary(games: ClubGame[]) {
  const totals = new Map<string, { name: string; number: string; games: number; points: number; fouls: number; threes: number; series: number[] }>();
  for (const game of games) {
    for (const stat of game.stats) {
      const key = stat.playerId || `detected:${stat.number}:${stat.playerName}`;
      const current = totals.get(key) || { name: stat.playerName, number: stat.number, games: 0, points: 0, fouls: 0, threes: 0, series: [] };
      current.games += 1;
      current.points += stat.totalPoints;
      current.fouls += stat.foulsCount;
      current.threes += stat.threePoint;
      current.series.push(stat.totalPoints);
      totals.set(key, current);
    }
  }
  return Array.from(totals.values()).map((item) => ({
    ...item,
    ppg: round(item.points / Math.max(item.games, 1)),
    fpg: round(item.fouls / Math.max(item.games, 1)),
    trend: computeTrend(item.series),
    regularity: computeRegularity(item.series),
  }));
}

export function playerSeries(games: ClubGame[], playerId: string) {
  return [...games]
    .reverse()
    .map((game) => {
      const stat = game.stats.find((item) => item.playerId === playerId);
      return stat ? { game, stat } : null;
    })
    .filter((item): item is NonNullable<typeof item> => Boolean(item));
}

export function formatDateLabel(value: string) {
  if (!value || value === "Unknown date") return "n/d";
  return value.length > 10 ? value.slice(0, 10) : value;
}

function toClubStat(player: OcrPlayer, roster: ClubPlayer[], index: number): ClubGamePlayerStat {
  const points = player.points || {};
  const onePoint = toNumber(points.one_point);
  const twoPoint = toNumber(points.two_point);
  const threePoint = toNumber(points.tree_point ?? points.three_point);
  const number = normalizeNumber(player.number) || `?${index + 1}`;
  const detectedName = normalizeText(player.name) || `Player #${number}`;
  const matched = findBestRosterNameMatch(detectedName, roster)?.player;

  return {
    playerId: matched?.id,
    playerName: matched?.name || detectedName,
    number,
    onePoint,
    twoPoint,
    threePoint,
    totalPoints: onePoint + twoPoint * 2 + threePoint * 3,
    foulsCount: Array.isArray(player.fouls) ? player.fouls.length : 0,
    started: Boolean(player.started),
    entered: Boolean(player.entered),
    matchedRoster: Boolean(matched),
  };
}

function computeTrend(series: number[]) {
  if (series.length < 2) return 0;
  const midpoint = Math.floor(series.length / 2);
  const previous = average(series.slice(0, midpoint));
  const recent = average(series.slice(midpoint));
  return round(recent - previous);
}

function computeRegularity(series: number[]) {
  if (series.length < 2) return 100;
  const avg = average(series);
  const variance = average(series.map((value) => (value - avg) ** 2));
  const stdDev = Math.sqrt(variance);
  return Math.max(0, Math.round(100 - stdDev * 8));
}

function average(values: number[]) {
  return values.reduce((sum, value) => sum + value, 0) / Math.max(values.length, 1);
}

function round(value: number) {
  return Math.round(value * 10) / 10;
}

function toNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function normalizeText(value: unknown) {
  return typeof value === "string" ? value.trim() : typeof value === "number" ? String(value) : "";
}

function normalizeNumber(value: unknown) {
  return normalizeText(value).replace(/^0+(?=\d)/, "");
}
