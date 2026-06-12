import Link from "next/link";

import { getPlayerInsight } from "./result-utils";
import type { SavedSinglePlayerGame } from "./types";

export function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`rounded-panel border border-border bg-surface shadow-sm ${className}`}>{children}</section>;
}

export function EmptyState({
  title,
  description,
  ctaHref,
  ctaLabel,
}: {
  title: string;
  description: string;
  ctaHref?: string;
  ctaLabel?: string;
}) {
  return (
    <div className="rounded-card border border-dashed border-border p-8 text-center sm:p-10">
      <p className="text-base font-semibold text-ink">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted">{description}</p>
      {ctaHref && ctaLabel ? (
        <Link
          href={ctaHref}
          className="mt-5 inline-block rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-contrast transition hover:bg-primary/85"
        >
          {ctaLabel}
        </Link>
      ) : null}
    </div>
  );
}

export function ResultChip({ label }: { label: string }) {
  const styles =
    label === "Win"
      ? "bg-success-soft text-success"
      : label === "Loss"
        ? "bg-danger-soft text-danger"
        : "bg-elevated text-muted";

  return <span className={`rounded-full px-3 py-1 text-xs font-semibold ${styles}`}>{label}</span>;
}

export function GameDetailCard({
  game,
  eyebrow = "Selected player",
  footer,
}: {
  game: SavedSinglePlayerGame;
  eyebrow?: string;
  footer?: React.ReactNode;
}) {
  const { player } = game;

  return (
    <div className="rounded-card bg-inverse p-5 text-inverse-foreground shadow-sm sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-primary">{eyebrow}</p>
          <h3 className="mt-2 text-2xl font-semibold sm:text-3xl">#{player.number} {player.name}</h3>
          <p className="mt-1 text-sm text-inverse-foreground/70">{player.teamName}</p>
        </div>
        <ResultChip label={game.resultLabel} />
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3">
        <QuickStat label="Points scored" value={player.totalPoints} />
        <QuickStat label="Fouls committed" value={player.foulsCount} />
      </div>

      <div className="mt-3 grid grid-cols-3 gap-3">
        <DarkStat label="1PT made" value={player.onePoint} />
        <DarkStat label="2PT made" value={player.twoPoint} />
        <DarkStat label="3PT made" value={player.threePoint} />
        <DarkStat label="Pts from 3" value={player.threePoint * 3} />
        <DarkStat label="Started" value={player.started ? "Yes" : "No"} />
        <DarkStat label="Entered" value={player.entered ? "Yes" : "No"} />
      </div>

      <div className="mt-4 rounded-card bg-inverse-foreground/10 p-4 text-sm text-inverse-foreground/85">
        <p className="font-semibold text-inverse-foreground">{game.teamName} vs {game.opponent} · {game.finalScore}</p>
        <p className="mt-1 text-xs text-inverse-foreground/60">{game.tournament} · {game.gameDate}</p>
      </div>

      <div className="mt-4 rounded-card bg-inverse-foreground/10 p-4 text-sm leading-6 text-inverse-foreground/85">
        <span className="font-semibold text-primary">Insight: </span>
        {getPlayerInsight(player)}
      </div>

      {footer ? <div className="mt-5">{footer}</div> : null}
    </div>
  );
}

export function MiniStat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-card bg-surface p-3">
      <p className="text-base font-bold text-ink">{value}</p>
      <p className="text-[0.65rem] font-semibold uppercase tracking-wide text-faint">{label}</p>
    </div>
  );
}

function QuickStat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-card bg-primary/15 p-4 ring-1 ring-primary/30">
      <p className="text-3xl font-black text-primary sm:text-4xl">{value}</p>
      <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-inverse-foreground/70">{label}</p>
    </div>
  );
}

function DarkStat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-card bg-inverse-foreground/10 p-3">
      <p className="text-lg font-bold text-inverse-foreground">{value}</p>
      <p className="mt-1 text-[0.65rem] font-semibold uppercase tracking-wide text-inverse-foreground/55">{label}</p>
    </div>
  );
}
