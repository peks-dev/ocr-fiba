"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { readSavedGames, writeSavedGames } from "./storage";
import { sortMostRecentFirst } from "./stats-utils";
import type { SavedSinglePlayerGame } from "./types";
import { EmptyState, GameDetailCard, MiniStat, Panel, ResultChip } from "./ui";

const CAPTURE_PATH = "/dashboard/demos/single-player/capture";

export function HistoryClient() {
  const [games, setGames] = useState<SavedSinglePlayerGame[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isBooting, setIsBooting] = useState(true);

  useEffect(() => {
    setGames(sortMostRecentFirst(readSavedGames()));
    setIsBooting(false);
  }, []);

  const selectedGame = games.find((game) => game.id === selectedId) || games[0] || null;

  function deleteGame(id: string) {
    const next = games.filter((game) => game.id !== id);
    writeSavedGames(next);
    setGames(next);
    if (selectedId === id) setSelectedId(null);
    toast.success("Game removed from local history.");
  }

  function clearHistory() {
    writeSavedGames([]);
    setGames([]);
    setSelectedId(null);
    toast.success("Local demo history cleared.");
  }

  if (isBooting) {
    return <Panel className="p-8 text-muted">Loading history...</Panel>;
  }

  return (
    <Panel className="p-5 sm:p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep sm:text-sm">History</p>
          <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">Saved games in this browser</h2>
          <p className="mt-2 text-sm text-muted">
            {games.length} {games.length === 1 ? "game" : "games"} stored locally. Nothing is written to Supabase yet.
          </p>
        </div>
        <button
          type="button"
          disabled={games.length === 0}
          onClick={clearHistory}
          className="self-start rounded-full border border-border px-4 py-2 text-sm font-semibold text-ink transition hover:bg-elevated disabled:opacity-50 md:self-auto"
        >
          Clear local history
        </button>
      </div>

      {games.length > 0 ? (
        <div className="mt-5 grid gap-5 sm:mt-6 sm:gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="max-h-80 space-y-3 overflow-y-auto pr-1 xl:max-h-[36rem]">
            {games.map((game) => (
              <button
                key={game.id}
                type="button"
                onClick={() => setSelectedId(game.id)}
                className={`w-full rounded-card border p-4 text-left transition sm:p-5 ${selectedGame?.id === game.id ? "border-primary bg-primary/10" : "border-border bg-elevated hover:border-faint"}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-ink">#{game.player.number} {game.player.name}</p>
                    <p className="mt-1 truncate text-xs text-muted">{game.teamName} vs {game.opponent}</p>
                  </div>
                  <ResultChip label={game.resultLabel} />
                </div>
                <div className="mt-4 grid grid-cols-3 gap-2 text-center text-sm">
                  <MiniStat label="PTS" value={game.player.totalPoints} />
                  <MiniStat label="3PT" value={game.player.threePoint} />
                  <MiniStat label="FLS" value={game.player.foulsCount} />
                </div>
                <p className="mt-4 truncate text-xs text-faint">{game.tournament} · {game.gameDate} · {game.finalScore}</p>
              </button>
            ))}
          </div>

          {selectedGame ? (
            <GameDetailCard
              game={selectedGame}
              eyebrow="Game review"
              footer={
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-xs text-inverse-foreground/60">Saved {new Date(selectedGame.savedAt).toLocaleString()}</p>
                  <button
                    type="button"
                    onClick={() => deleteGame(selectedGame.id)}
                    className="rounded-full border border-danger/40 px-4 py-2 text-sm font-semibold text-danger transition hover:bg-danger/10"
                  >
                    Delete game
                  </button>
                </div>
              }
            />
          ) : null}
        </div>
      ) : (
        <div className="mt-6">
          <EmptyState
            title="No games in your history"
            description="Capture a game and save your stats to be able to review it here later."
            ctaHref={CAPTURE_PATH}
            ctaLabel="Capture a game"
          />
        </div>
      )}
    </Panel>
  );
}
