import type { SavedSinglePlayerGame } from "./types";

export const SINGLE_PLAYER_HISTORY_STORAGE_KEY = "fiba-ocr:single-player-demo:v1";

export function readSavedGames(): SavedSinglePlayerGame[] {
  if (typeof window === "undefined") return [];

  try {
    const raw = window.localStorage.getItem(SINGLE_PLAYER_HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isSavedGame);
  } catch {
    return [];
  }
}

export function writeSavedGames(games: SavedSinglePlayerGame[]) {
  window.localStorage.setItem(SINGLE_PLAYER_HISTORY_STORAGE_KEY, JSON.stringify(games.slice(0, 30)));
}

function isSavedGame(value: unknown): value is SavedSinglePlayerGame {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<SavedSinglePlayerGame>;
  return typeof item.id === "string" && typeof item.savedAt === "string" && typeof item.runId === "string" && !!item.player;
}
