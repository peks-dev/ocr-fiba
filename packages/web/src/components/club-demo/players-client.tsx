"use client";

import { useEffect, useMemo, useState } from "react";

import { formatDateLabel, playerSeries } from "./result-utils";
import { readClubStore } from "./storage";
import type { ClubStore } from "./types";
import { EmptyState, MiniStat, Panel } from "./ui";

const DEFAULT_BASE_PATH = "/test/club";
const INITIAL_STORE: ClubStore = { clubName: "My Club", roster: [], games: [] };

export function PlayersClient({ basePath = DEFAULT_BASE_PATH }: { basePath?: string }) {
  const [store, setStore] = useState<ClubStore>(INITIAL_STORE);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isBooting, setIsBooting] = useState(true);

  useEffect(() => {
    const next = readClubStore();
    setStore(next);
    setSelectedId(next.roster[0]?.id || null);
    setIsBooting(false);
  }, []);

  const selectedPlayer = store.roster.find((player) => player.id === selectedId) || store.roster[0] || null;
  const series = useMemo(() => (selectedPlayer ? playerSeries(store.games, selectedPlayer.id) : []), [selectedPlayer, store.games]);
  const totals = useMemo(() => computePlayerTotals(series), [series]);

  if (isBooting) return <Panel className="p-6 text-muted">Loading players...</Panel>;

  if (store.roster.length === 0) {
    return (
      <Panel className="p-5 sm:p-8">
        <EmptyState title="No roster players" description="Add players before opening individual progress profiles." ctaHref={`${basePath}/roster`} ctaLabel="Create roster" />
      </Panel>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
      <Panel className="h-fit p-5 sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep">Players</p>
        <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">Individual progress</h2>
        <div className="mt-5 max-h-[34rem] space-y-2 overflow-y-auto pr-1">
          {store.roster.map((player) => {
            const playerGames = playerSeries(store.games, player.id);
            const active = selectedPlayer?.id === player.id;
            return (
              <button key={player.id} type="button" onClick={() => setSelectedId(player.id)} className={`w-full rounded-card border p-4 text-left transition ${active ? "border-primary bg-primary/10" : "border-border bg-elevated hover:border-faint"}`}>
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-ink">#{player.number} {player.name}</p>
                    <p className="mt-1 text-xs text-muted">{player.position || "No role"}</p>
                  </div>
                  <span className="rounded-full bg-surface px-3 py-1 text-xs font-semibold text-muted">{playerGames.length} games</span>
                </div>
              </button>
            );
          })}
        </div>
      </Panel>

      <Panel className="p-5 sm:p-6">
        {selectedPlayer ? (
          <>
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep">Player profile</p>
                <h2 className="mt-2 text-2xl font-semibold text-ink">#{selectedPlayer.number} {selectedPlayer.name}</h2>
                <p className="mt-1 text-sm text-muted">{selectedPlayer.position || store.clubName}</p>
              </div>
            </div>

            {series.length === 0 ? (
              <div className="mt-6">
                <EmptyState title="No games for this player yet" description="Import a scoresheet where this jersey number appears to unlock the player profile." ctaHref={`${basePath}/capture`} ctaLabel="Capture game" />
              </div>
            ) : (
              <div className="mt-5 space-y-6">
                <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
                  <MiniStat label="Games" value={series.length} />
                  <MiniStat label="PPG" value={totals.ppg} />
                  <MiniStat label="Best" value={totals.best} hint="points" />
                  <MiniStat label="Fouls / game" value={totals.fpg} />
                </div>

                <div className="rounded-card border border-border bg-elevated p-4 sm:p-5">
                  <p className="text-sm font-semibold text-ink">Points trend</p>
                  <PointsChart values={series.map((item) => item.stat.totalPoints)} />
                  <div className="mt-3 flex justify-between gap-2 text-xs text-muted">
                    <span>{formatDateLabel(series[0]?.game.gameDate || "")}</span>
                    <span>{formatDateLabel(series[series.length - 1]?.game.gameDate || "")}</span>
                  </div>
                </div>

                <div className="space-y-3">
                  {series.slice().reverse().map(({ game, stat }) => (
                    <div key={`${game.id}:${stat.number}`} className="rounded-card border border-border bg-elevated p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-ink">vs {game.opponent}</p>
                          <p className="mt-1 text-xs text-muted">{game.tournament} · {formatDateLabel(game.gameDate)} · {game.finalScore}</p>
                        </div>
                        <span className="text-2xl font-black text-ink">{stat.totalPoints}</span>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted">
                        <span className="rounded-full bg-surface px-3 py-1">1PT {stat.onePoint}</span>
                        <span className="rounded-full bg-surface px-3 py-1">2PT {stat.twoPoint}</span>
                        <span className="rounded-full bg-surface px-3 py-1">3PT {stat.threePoint}</span>
                        <span className="rounded-full bg-surface px-3 py-1">Fouls {stat.foulsCount}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : null}
      </Panel>
    </div>
  );
}

function computePlayerTotals(series: ReturnType<typeof playerSeries>) {
  const points = series.map((item) => item.stat.totalPoints);
  const fouls = series.map((item) => item.stat.foulsCount);
  const games = Math.max(series.length, 1);
  return {
    ppg: round(points.reduce((sum, value) => sum + value, 0) / games),
    fpg: round(fouls.reduce((sum, value) => sum + value, 0) / games),
    best: Math.max(...points, 0),
  };
}

function PointsChart({ values }: { values: number[] }) {
  const max = Math.max(...values, 1);
  const width = 320;
  const height = 140;
  const points = values.map((value, index) => {
    const x = values.length === 1 ? width / 2 : (index / (values.length - 1)) * width;
    const y = height - (value / max) * (height - 18) - 8;
    return { x, y, value };
  });
  const path = points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="mt-4 h-44 w-full overflow-visible" role="img" aria-label="Points trend chart">
      <path d="M 0 132 L 320 132" stroke="currentColor" className="text-border" strokeWidth="2" />
      {points.length > 1 ? <path d={path} fill="none" stroke="var(--color-primary)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" /> : null}
      {points.map((point, index) => (
        <g key={`${point.x}:${point.y}`}>
          <circle cx={point.x} cy={point.y} r="5" fill="var(--color-primary)" />
          <text x={point.x} y={Math.max(point.y - 10, 12)} textAnchor="middle" className="fill-ink text-[10px] font-bold">{values[index]}</text>
        </g>
      ))}
    </svg>
  );
}

function round(value: number) {
  return Math.round(value * 10) / 10;
}
