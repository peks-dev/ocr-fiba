import type { SavedSinglePlayerGame } from "./types";

export type GamesPeriod = "5" | "10" | "all";

export const PERIOD_OPTIONS: { value: GamesPeriod; label: string }[] = [
  { value: "5", label: "Last 5 games" },
  { value: "10", label: "Last 10 games" },
  { value: "all", label: "All games" },
];

export type PeriodSummary = {
  games: number;
  pointsPerGame: number;
  foulsPerGame: number;
  threesPerGame: number;
  wins: number;
  losses: number;
  pointsShare: { one: number; two: number; three: number } | null;
};

export type TrendDelta = {
  previous: number;
  recent: number;
  delta: number;
};

export function sortMostRecentFirst(games: SavedSinglePlayerGame[]) {
  return [...games].sort((a, b) => b.savedAt.localeCompare(a.savedAt));
}

export function sortChronologically(games: SavedSinglePlayerGame[]) {
  return [...games].sort((a, b) => a.savedAt.localeCompare(b.savedAt));
}

export function selectPeriodGames(games: SavedSinglePlayerGame[], period: GamesPeriod) {
  const ordered = sortMostRecentFirst(games);
  return period === "all" ? ordered : ordered.slice(0, Number(period));
}

export function computeSummary(games: SavedSinglePlayerGame[]): PeriodSummary {
  if (games.length === 0) {
    return { games: 0, pointsPerGame: 0, foulsPerGame: 0, threesPerGame: 0, wins: 0, losses: 0, pointsShare: null };
  }

  let points = 0;
  let fouls = 0;
  let threes = 0;
  let wins = 0;
  let losses = 0;
  let pointsFromOne = 0;
  let pointsFromTwo = 0;
  let pointsFromThree = 0;

  for (const game of games) {
    points += game.player.totalPoints;
    fouls += game.player.foulsCount;
    threes += game.player.threePoint;
    pointsFromOne += game.player.onePoint;
    pointsFromTwo += game.player.twoPoint * 2;
    pointsFromThree += game.player.threePoint * 3;
    if (game.resultLabel === "Win") wins += 1;
    if (game.resultLabel === "Loss") losses += 1;
  }

  return {
    games: games.length,
    pointsPerGame: roundOneDecimal(points / games.length),
    foulsPerGame: roundOneDecimal(fouls / games.length),
    threesPerGame: roundOneDecimal(threes / games.length),
    wins,
    losses,
    pointsShare:
      points > 0
        ? {
            one: Math.round((pointsFromOne / points) * 100),
            two: Math.round((pointsFromTwo / points) * 100),
            three: Math.round((pointsFromThree / points) * 100),
          }
        : null,
  };
}

export function computeTrend(
  games: SavedSinglePlayerGame[],
  getValue: (game: SavedSinglePlayerGame) => number,
): TrendDelta | null {
  if (games.length < 2) return null;

  const ordered = sortChronologically(games);
  const splitAt = Math.floor(ordered.length / 2);
  const previous = average(ordered.slice(0, splitAt).map(getValue));
  const recent = average(ordered.slice(splitAt).map(getValue));

  return {
    previous: roundOneDecimal(previous),
    recent: roundOneDecimal(recent),
    delta: roundOneDecimal(recent - previous),
  };
}

function average(values: number[]) {
  return values.length === 0 ? 0 : values.reduce((sum, value) => sum + value, 0) / values.length;
}

function roundOneDecimal(value: number) {
  return Math.round(value * 10) / 10;
}
