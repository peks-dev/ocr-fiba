"use client";

import { useEffect, useMemo, useState } from "react";

import { readSavedGames } from "./storage";
import {
  computeSummary,
  computeTrend,
  PERIOD_OPTIONS,
  selectPeriodGames,
  sortChronologically,
  type GamesPeriod,
  type TrendDelta,
} from "./stats-utils";
import type { SavedSinglePlayerGame } from "./types";
import { EmptyState, Panel } from "./ui";

const DEFAULT_BASE_PATH = "/test/player";

export function ProgressClient({ basePath = DEFAULT_BASE_PATH }: { basePath?: string }) {
  const [games, setGames] = useState<SavedSinglePlayerGame[]>([]);
  const [period, setPeriod] = useState<GamesPeriod>("5");
  const [isBooting, setIsBooting] = useState(true);

  useEffect(() => {
    setGames(readSavedGames());
    setIsBooting(false);
  }, []);

  const periodGames = useMemo(() => selectPeriodGames(games, period), [games, period]);
  const summary = useMemo(() => computeSummary(periodGames), [periodGames]);
  const pointsTrend = useMemo(() => computeTrend(periodGames, (game) => game.player.totalPoints), [periodGames]);
  const foulsTrend = useMemo(() => computeTrend(periodGames, (game) => game.player.foulsCount), [periodGames]);
  const chronologicalGames = useMemo(() => sortChronologically(periodGames), [periodGames]);

  if (isBooting) {
    return <Panel className="p-8 text-muted">Loading progress...</Panel>;
  }

  if (games.length === 0) {
    return (
      <Panel className="p-5 sm:p-8">
        <EmptyState
          title="No games saved yet"
          description="Capture a game from a FIBA scoresheet and save it to start measuring your averages and long-term progress."
          ctaHref={`${basePath}/capture`}
          ctaLabel="Capture your first game"
        />
      </Panel>
    );
  }

  return (
    <div className="space-y-6 sm:space-y-8">
      <Panel className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep sm:text-sm">Progress</p>
            <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">Your averages</h2>
            <p className="mt-2 text-sm text-muted">
              Based on {summary.games} saved {summary.games === 1 ? "game" : "games"} in this browser.
            </p>
          </div>
          <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
            {PERIOD_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setPeriod(option.value)}
                className={`shrink-0 rounded-full px-4 py-2 text-sm font-semibold transition ${period === option.value ? "bg-ink text-background" : "border border-border text-muted hover:bg-elevated"}`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 sm:mt-6 xl:grid-cols-4">
          <SummaryCard label="Points per game" value={summary.pointsPerGame} hint="Average points scored" />
          <SummaryCard label="Fouls per game" value={summary.foulsPerGame} hint="Average fouls committed" />
          <SummaryCard label="3PT per game" value={summary.threesPerGame} hint="Average threes made" />
          <SummaryCard label="Record" value={`${summary.wins}-${summary.losses}`} hint="Wins-Losses (decided games)" />
        </div>
      </Panel>

      <div className="grid gap-6 sm:gap-8 lg:grid-cols-2">
        <Panel className="p-5 sm:p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep sm:text-sm">Game by game</p>
          <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">Points per game</h2>
          <PointsBars games={chronologicalGames} />
          <p className="mt-3 text-xs text-muted">Oldest on the left, most recent on the right (by save order).</p>
        </Panel>

        <Panel className="p-5 sm:p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep sm:text-sm">Trends</p>
          <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">Are you improving?</h2>

          <div className="mt-5 space-y-3 sm:mt-6">
            <TrendCard title="Scoring" unit="pts/game" trend={pointsTrend} />
            <TrendCard title="Foul control" unit="fouls/game" trend={foulsTrend} positiveWhenLower />
          </div>

          {summary.pointsShare ? (
            <div className="mt-6">
              <p className="text-sm font-semibold text-ink">Where your points come from</p>
              <div className="mt-3 flex h-4 overflow-hidden rounded-full bg-elevated">
                <div className="bg-accent" style={{ width: `${summary.pointsShare.one}%` }} />
                <div className="bg-primary" style={{ width: `${summary.pointsShare.two}%` }} />
                <div className="bg-warning" style={{ width: `${summary.pointsShare.three}%` }} />
              </div>
              <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted">
                <LegendItem colorClass="bg-accent" label={`Free throws ${summary.pointsShare.one}%`} />
                <LegendItem colorClass="bg-primary" label={`2-pointers ${summary.pointsShare.two}%`} />
                <LegendItem colorClass="bg-warning" label={`3-pointers ${summary.pointsShare.three}%`} />
              </div>
            </div>
          ) : null}
        </Panel>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, hint }: { label: string; value: number | string; hint: string }) {
  return (
    <div className="rounded-card border border-border bg-elevated p-4 sm:p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-2 text-2xl font-black text-ink sm:text-3xl">{value}</p>
      <p className="mt-1 text-xs text-faint">{hint}</p>
    </div>
  );
}

function TrendCard({
  title,
  unit,
  trend,
  positiveWhenLower = false,
}: {
  title: string;
  unit: string;
  trend: TrendDelta | null;
  positiveWhenLower?: boolean;
}) {
  if (!trend) {
    return (
      <div className="rounded-card border border-dashed border-border p-4 text-sm text-muted">
        <span className="font-semibold text-ink">{title}:</span> save at least 2 games in this period to unlock the trend.
      </div>
    );
  }

  const isFlat = trend.delta === 0;
  const isGood = positiveWhenLower ? trend.delta < 0 : trend.delta > 0;
  const arrow = isFlat ? "→" : trend.delta > 0 ? "▲" : "▼";
  const toneClass = isFlat ? "text-muted" : isGood ? "text-success" : "text-danger";

  return (
    <div className="rounded-card border border-border bg-elevated p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="font-semibold text-ink">{title}</p>
        <span className={`text-sm font-bold ${toneClass}`}>
          {arrow} {trend.delta > 0 ? "+" : ""}{trend.delta} {unit}
        </span>
      </div>
      <p className="mt-2 text-xs text-muted">
        Earlier games avg {trend.previous} → recent games avg {trend.recent}.
      </p>
    </div>
  );
}

function PointsBars({ games }: { games: SavedSinglePlayerGame[] }) {
  const maxPoints = Math.max(...games.map((game) => game.player.totalPoints), 1);

  return (
    <div className="mt-5 flex h-40 items-end gap-1.5 sm:mt-6 sm:h-48 sm:gap-2">
      {games.map((game) => (
        <div
          key={game.id}
          className="flex h-full flex-1 flex-col items-center justify-end gap-1"
          title={`${game.gameDate} · vs ${game.opponent} · ${game.player.totalPoints} pts`}
        >
          <span className="text-xs font-semibold text-ink">{game.player.totalPoints}</span>
          <div
            className="w-full max-w-12 rounded-t-lg bg-primary/85"
            style={{ height: `${Math.max((game.player.totalPoints / maxPoints) * 100, 3)}%` }}
          />
        </div>
      ))}
    </div>
  );
}

function LegendItem({ colorClass, label }: { colorClass: string; label: string }) {
  return (
    <span className="flex items-center gap-2">
      <span className={`size-2.5 rounded-full ${colorClass}`} />
      {label}
    </span>
  );
}
