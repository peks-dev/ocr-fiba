"use client";

import { useEffect, useMemo, useState } from "react";

import { clubSummary, formatDateLabel } from "./result-utils";
import { readClubStore } from "./storage";
import type { ClubStore } from "./types";
import { EmptyState, MiniStat, Panel, ResultChip } from "./ui";

const DEFAULT_BASE_PATH = "/test/club";
const INITIAL_STORE: ClubStore = { clubName: "My Club", roster: [], games: [] };

export function OverviewClient({ basePath = DEFAULT_BASE_PATH }: { basePath?: string }) {
  const [store, setStore] = useState<ClubStore>(INITIAL_STORE);
  const [isBooting, setIsBooting] = useState(true);

  useEffect(() => {
    setStore(readClubStore());
    setIsBooting(false);
  }, []);

  const summary = useMemo(() => clubSummary(store.games), [store.games]);
  const topScorer = [...summary].sort((a, b) => b.ppg - a.ppg)[0];
  const rising = [...summary].filter((item) => item.games >= 2).sort((a, b) => b.trend - a.trend)[0];
  const regular = [...summary].filter((item) => item.games >= 2).sort((a, b) => b.regularity - a.regularity)[0];
  const totalPoints = store.games.reduce((sum, game) => sum + game.stats.reduce((inner, stat) => inner + stat.totalPoints, 0), 0);

  if (isBooting) return <Panel className="p-6 text-muted">Loading club analysis...</Panel>;

  if (store.games.length === 0) {
    return (
      <Panel className="p-5 sm:p-8">
        <EmptyState title="Import the first game to create your roster." description="Upload a FIBA scoresheet, choose your team, and the demo will create the roster from extracted player names automatically." ctaHref={`${basePath}/capture`} ctaLabel="Capture first game" />
      </Panel>
    );
  }

  return (
    <div className="space-y-6 sm:space-y-8">
      <Panel className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep">Club overview</p>
            <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">{store.clubName} performance tracker</h2>
            <p className="mt-2 text-sm text-muted">{store.games.length} saved {store.games.length === 1 ? "game" : "games"} · {store.roster.length} roster players.</p>
          </div>
        </div>
        <div className="mt-5 grid grid-cols-2 gap-3 xl:grid-cols-4">
          <MiniStat label="Games" value={store.games.length} hint="Imported sheets" />
          <MiniStat label="Roster" value={store.roster.length} hint="Tracked players" />
          <MiniStat label="Team points" value={totalPoints} hint="Across saved games" />
          <MiniStat label="Avg / game" value={Math.round(totalPoints / Math.max(store.games.length, 1))} hint="From OCR stats" />
        </div>
      </Panel>

      <div className="grid gap-6 lg:grid-cols-3">
        <InsightCard title="Top scorer" value={topScorer ? `#${topScorer.number} ${topScorer.name}` : "n/d"} metric={topScorer ? `${topScorer.ppg} ppg` : "Import games"} />
        <InsightCard title="Trending up" value={rising ? `#${rising.number} ${rising.name}` : "Needs 2+ games"} metric={rising ? `${rising.trend > 0 ? "+" : ""}${rising.trend} pts` : "No trend yet"} />
        <InsightCard title="Most regular" value={regular ? `#${regular.number} ${regular.name}` : "Needs 2+ games"} metric={regular ? `${regular.regularity}/100 consistency` : "No signal yet"} />
      </div>

      <Panel className="p-5 sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep">Recent games</p>
        <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">Imported match sheets</h2>
        <div className="mt-5 space-y-3">
          {store.games.slice(0, 6).map((game) => (
            <div key={game.id} className="rounded-card border border-border bg-elevated p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-ink">{game.clubTeamName} vs {game.opponent}</p>
                  <p className="mt-1 text-xs text-muted">{game.tournament} · {formatDateLabel(game.gameDate)} · {game.finalScore}</p>
                </div>
                <ResultChip label={game.resultLabel} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted">
                {game.stats.slice(0, 5).map((stat) => (
                  <span key={`${game.id}:${stat.number}`} className="rounded-full bg-surface px-3 py-1">#{stat.number} {stat.totalPoints} pts</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function InsightCard({ title, value, metric }: { title: string; value: string; metric: string }) {
  return (
    <Panel className="p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep">{title}</p>
      <p className="mt-3 text-lg font-semibold text-ink">{value}</p>
      <p className="mt-1 text-sm text-muted">{metric}</p>
    </Panel>
  );
}
