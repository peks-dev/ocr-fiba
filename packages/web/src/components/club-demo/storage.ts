import { hasRosterNameMatch } from "./name-match";

import type { ClubGame, ClubGamePlayerStat, ClubPlayer, ClubStore } from "./types";

export const CLUB_DEMO_STORAGE_KEY = "fiba-ocr:club-demo:v1";

const EMPTY_STORE: ClubStore = { clubName: "My Club", roster: [], games: [] };

export function readClubStore(): ClubStore {
  if (typeof window === "undefined") return EMPTY_STORE;
  try {
    const raw = window.localStorage.getItem(CLUB_DEMO_STORAGE_KEY);
    if (!raw) return EMPTY_STORE;
    const parsed = JSON.parse(raw) as Partial<ClubStore>;
    return {
      clubName: typeof parsed.clubName === "string" && parsed.clubName.trim() ? parsed.clubName : EMPTY_STORE.clubName,
      roster: Array.isArray(parsed.roster) ? parsed.roster.filter(isClubPlayer).slice(0, 50) : [],
      games: Array.isArray(parsed.games) ? parsed.games.filter(isClubGame).slice(0, 40) : [],
    };
  } catch {
    return EMPTY_STORE;
  }
}

export function writeClubStore(store: ClubStore): void {
  window.localStorage.setItem(
    CLUB_DEMO_STORAGE_KEY,
    JSON.stringify({ clubName: store.clubName || EMPTY_STORE.clubName, roster: store.roster.slice(0, 50), games: store.games.slice(0, 40) }),
  );
}

export function upsertRosterPlayer(store: ClubStore, player: ClubPlayer): ClubStore {
  const existingIndex = store.roster.findIndex((item) => item.id === player.id);
  const roster = existingIndex >= 0 ? [...store.roster] : [player, ...store.roster];
  if (existingIndex >= 0) roster[existingIndex] = player;
  return { ...store, roster: roster.sort((a, b) => Number(a.number) - Number(b.number) || a.name.localeCompare(b.name)) };
}

export function deleteRosterPlayer(store: ClubStore, playerId: string): ClubStore {
  return { ...store, roster: store.roster.filter((player) => player.id !== playerId) };
}

export function addDetectedPlayersToRoster(store: ClubStore, stats: ClubGamePlayerStat[]): { store: ClubStore; addedCount: number } {
  const additions: ClubPlayer[] = [];

  for (const stat of stats) {
    const name = stat.playerName.trim();
    if (!name || name.startsWith("Player #")) continue;
    const rosterWithAdditions = [...store.roster, ...additions];
    if (hasRosterNameMatch(name, rosterWithAdditions)) continue;
    additions.push({
      id: `player:${slugifyName(name)}:${Date.now()}:${additions.length}`,
      name,
      number: normalizeNumber(stat.number),
      createdAt: new Date().toISOString(),
    });
  }

  if (additions.length === 0) return { store, addedCount: 0 };
  const roster = [...store.roster, ...additions].sort((a, b) => a.name.localeCompare(b.name) || Number(a.number) - Number(b.number));
  return { store: { ...store, roster }, addedCount: additions.length };
}


export function addClubGame(store: ClubStore, game: ClubGame): ClubStore {
  const games = [game, ...store.games.filter((item) => item.runId !== game.runId)].slice(0, 40);
  return { ...store, games };
}

function isClubPlayer(value: unknown): value is ClubPlayer {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<ClubPlayer>;
  return typeof item.id === "string" && typeof item.name === "string" && typeof item.number === "string";
}

function isClubGame(value: unknown): value is ClubGame {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<ClubGame>;
  return typeof item.id === "string" && typeof item.runId === "string" && Array.isArray(item.stats);
}

function normalizeNumber(value: unknown): string {
  return typeof value === "string" || typeof value === "number" ? String(value).trim().replace(/^0+(?=\d)/, "") : "";
}

function slugifyName(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") || "player";
}
