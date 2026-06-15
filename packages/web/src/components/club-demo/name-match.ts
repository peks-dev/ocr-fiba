import type { ClubPlayer } from "./types";

const MATCH_THRESHOLD = 0.72;

export type NameMatch = {
  player: ClubPlayer;
  score: number;
};

export function findBestRosterNameMatch(name: string, roster: ClubPlayer[]): NameMatch | null {
  const normalizedName = normalizePlayerName(name);
  if (!normalizedName) return null;

  let best: NameMatch | null = null;
  for (const player of roster) {
    const score = nameSimilarity(normalizedName, normalizePlayerName(player.name));
    if (!best || score > best.score) best = { player, score };
  }

  return best && best.score >= MATCH_THRESHOLD ? best : null;
}

export function hasRosterNameMatch(name: string, roster: ClubPlayer[]): boolean {
  return Boolean(findBestRosterNameMatch(name, roster));
}

export function normalizePlayerName(value: unknown): string {
  if (typeof value !== "string" && typeof value !== "number") return "";
  return String(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9ñ\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function nameSimilarity(a: string, b: string): number {
  if (!a || !b) return 0;
  if (a === b) return 1;

  const tokenScore = tokenContainmentScore(a, b);
  const charScore = 1 - levenshtein(a, b) / Math.max(a.length, b.length, 1);
  const initialsScore = initials(a) === initials(b) ? 0.08 : 0;

  return Math.min(1, Math.max(tokenScore, charScore) + initialsScore);
}

function tokenContainmentScore(a: string, b: string): number {
  const aTokens = significantTokens(a);
  const bTokens = significantTokens(b);
  if (aTokens.length === 0 || bTokens.length === 0) return 0;

  const [shorter, longer] = aTokens.length <= bTokens.length ? [aTokens, bTokens] : [bTokens, aTokens];
  let matched = 0;
  for (const token of shorter) {
    if (longer.some((candidate) => candidate === token || candidate.startsWith(token) || token.startsWith(candidate) || partialTokenScore(token, candidate) >= 0.82)) {
      matched += 1;
    }
  }

  const containment = matched / shorter.length;
  const coverage = matched / longer.length;
  return containment * 0.78 + coverage * 0.22;
}

function partialTokenScore(a: string, b: string): number {
  if (!a || !b) return 0;
  return 1 - levenshtein(a, b) / Math.max(a.length, b.length, 1);
}

function significantTokens(value: string): string[] {
  return value.split(" ").filter((token) => token.length > 1);
}

function initials(value: string): string {
  return significantTokens(value).map((token) => token[0]).join("");
}

function levenshtein(a: string, b: string): number {
  const previous = Array.from({ length: b.length + 1 }, (_, index) => index);
  const current = new Array<number>(b.length + 1);

  for (let i = 1; i <= a.length; i += 1) {
    current[0] = i;
    for (let j = 1; j <= b.length; j += 1) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      current[j] = Math.min(current[j - 1] + 1, previous[j] + 1, previous[j - 1] + cost);
    }
    for (let j = 0; j <= b.length; j += 1) previous[j] = current[j];
  }

  return previous[b.length];
}
