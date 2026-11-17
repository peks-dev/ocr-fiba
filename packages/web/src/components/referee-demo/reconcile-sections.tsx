import type { SheetSectionId } from "./sections";
import { sectionHasFieldIssue, teamForSection } from "./sections";
import type { OcrResult, QuarterKey, ReconcileIssue, TeamKey } from "./types";
import { NumberField, SeverityChip, TextField } from "./ui";
import {
  addProgressiveEvent,
  removeProgressiveEvent,
  setFinalScore,
  setHeaderField,
  setPlayerFlag,
  setPlayerFoulsText,
  setPlayerPoint,
  setPlayerTextField,
  setProgressiveEventField,
  setQuarter,
  setTeamFoul,
  setTeamName,
  setTeamCaptain,
  setWinner,
} from "./reconcile-utils";
import { teamName } from "./validation";

const QUARTERS: { key: QuarterKey; label: string }[] = [
  { key: "first", label: "1C" },
  { key: "second", label: "2C" },
  { key: "third", label: "3C" },
  { key: "fourth", label: "4C" },
  { key: "extra", label: "EX" },
];

export function ReconcileSectionEditor({
  sectionId,
  result,
  issues,
  onChange,
}: {
  sectionId: SheetSectionId;
  result: OcrResult;
  issues: ReconcileIssue[];
  onChange: (next: OcrResult) => void;
}) {
  if (sectionId === "footer_score") return <FooterScoreSection result={result} issues={issues} onChange={onChange} />;
  if (sectionId === "header") return <HeaderSection result={result} issues={issues} onChange={onChange} />;

  const team = teamForSection(sectionId);
  if (!team) return null;
  if (sectionId === "team_a_roster" || sectionId === "team_b_roster") {
    return <TeamPlayersSection team={team} result={result} issues={issues} onChange={onChange} />;
  }
  if (sectionId === "team_a_fouls" || sectionId === "team_b_fouls") {
    return <TeamFoulsSection team={team} result={result} issues={issues} onChange={onChange} />;
  }
  return <ProgressiveScoreSection team={team} result={result} issues={issues} onChange={onChange} />;
}

export function SectionIssues({ issues }: { issues: ReconcileIssue[] }) {
  if (issues.length === 0) {
    return (
      <div className="rounded-card bg-success-soft px-4 py-3 text-sm font-semibold text-success">
        Esta sección no tiene pendientes detectados.
      </div>
    );
  }
  return (
    <div className="space-y-2">
      {issues.map((issue) => (
        <div key={issue.id} className="rounded-card border border-border bg-elevated p-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-ink">{issue.title}</p>
              <p className="mt-1 text-xs leading-5 text-muted">{issue.message}</p>
              {issue.field ? <p className="mt-1 font-mono text-[0.65rem] text-faint">{issue.field}</p> : null}
            </div>
            <SeverityChip severity={issue.severity} />
          </div>
        </div>
      ))}
    </div>
  );
}

function FooterScoreSection({ result, issues, onChange }: SectionProps) {
  const teamAName = teamName(result, "team_a");
  const teamBName = teamName(result, "team_b");
  return (
    <div className="space-y-5">
      <SectionIssues issues={issues} />

      <div className="rounded-card border border-border p-4">
        <p className="text-sm font-semibold text-ink">Marcador final</p>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <NumberField
            label={teamAName}
            value={result.footer?.final_score?.team_a ?? null}
            highlighted={sectionHasFieldIssue(issues, "footer.final_score.team_a")}
            onChange={(value) => onChange(setFinalScore(result, "team_a", value))}
          />
          <NumberField
            label={teamBName}
            value={result.footer?.final_score?.team_b ?? null}
            highlighted={sectionHasFieldIssue(issues, "footer.final_score.team_b")}
            onChange={(value) => onChange(setFinalScore(result, "team_b", value))}
          />
        </div>
      </div>

      <label className="block rounded-card border border-border p-4">
        <span className="text-sm font-semibold text-ink">Ganador</span>
        <select
          value={matchWinner(result, teamAName, teamBName)}
          onChange={(event) => onChange(setWinner(result, event.target.value))}
          className={`mt-3 w-full rounded-field border bg-surface px-3 py-3 text-base text-ink outline-none transition focus:border-primary ${sectionHasFieldIssue(issues, "footer.winner") ? "border-warning bg-warning-soft/40" : "border-border"}`}
        >
          <option value="">Sin declarar</option>
          <option value={teamAName}>{teamAName}</option>
          <option value={teamBName}>{teamBName}</option>
        </select>
      </label>

      <div className="rounded-card border border-border p-4">
        <p className="text-sm font-semibold text-ink">Puntuación por cuarto</p>
        <div className="mt-3 space-y-3">
          {QUARTERS.map((quarter) => (
            <div key={quarter.key} className="grid grid-cols-[3rem_1fr_1fr] items-center gap-2">
              <span className="text-sm font-semibold text-muted">{quarter.label}</span>
              <NumberField
                label="A"
                value={result.footer?.quarters?.[quarter.key]?.team_a ?? null}
                highlighted={sectionHasFieldIssue(issues, `footer.quarters.${quarter.key}.team_a`)}
                onChange={(value) => onChange(setQuarter(result, quarter.key, "team_a", value))}
              />
              <NumberField
                label="B"
                value={result.footer?.quarters?.[quarter.key]?.team_b ?? null}
                highlighted={sectionHasFieldIssue(issues, `footer.quarters.${quarter.key}.team_b`)}
                onChange={(value) => onChange(setQuarter(result, quarter.key, "team_b", value))}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function TeamPlayersSection({ team, result, issues, onChange }: SectionProps & { team: TeamKey }) {
  const players = result[team]?.players || [];
  const teamLabel = teamName(result, team);
  return (
    <div className="space-y-5">
      <SectionIssues issues={issues} />
      <div className="grid gap-3 rounded-card border border-border p-4">
        <TextField label="Nombre del equipo" value={teamLabel} onChange={(value) => onChange(setTeamName(result, team, value))} />
        <TextField
          label="Capitán"
          value={result[team]?.captain || ""}
          highlighted={sectionHasFieldIssue(issues, `${team}.captain`)}
          onChange={(value) => onChange(setTeamCaptain(result, team, value))}
        />
      </div>

      <div className="space-y-3">
        {players.length === 0 ? (
          <div className="rounded-card border border-dashed border-border p-5 text-sm text-muted">No se detectaron jugadores para este equipo.</div>
        ) : null}
        {players.map((player, index) => {
          const base = `${team}.players[${index}]`;
          return (
            <div key={`${player.number ?? "player"}-${index}`} className="rounded-card border border-border p-4">
              <div className="grid grid-cols-[5rem_1fr] gap-3">
                <TextField
                  label="Dorsal"
                  value={player.number == null ? "" : String(player.number)}
                  highlighted={sectionHasFieldIssue(issues, `${base}.number`) || sectionHasFieldIssue(issues, `${team}.players`)}
                  onChange={(value) => onChange(setPlayerTextField(result, team, index, "number", value))}
                />
                <TextField
                  label="Jugador"
                  value={player.name || ""}
                  highlighted={sectionHasFieldIssue(issues, `${base}.name`)}
                  onChange={(value) => onChange(setPlayerTextField(result, team, index, "name", value))}
                />
              </div>
              <div className="mt-3 grid grid-cols-4 gap-2">
                <NumberField label="1P" value={player.points?.one_point ?? null} onChange={(value) => onChange(setPlayerPoint(result, team, index, "one_point", value))} />
                <NumberField label="2P" value={player.points?.two_point ?? null} onChange={(value) => onChange(setPlayerPoint(result, team, index, "two_point", value))} />
                <NumberField label="3P" value={player.points?.tree_point ?? player.points?.three_point ?? null} onChange={(value) => onChange(setPlayerPoint(result, team, index, "tree_point", value))} />
                <TextField
                  label="Faltas"
                  value={(player.fouls || []).join(" ")}
                  highlighted={sectionHasFieldIssue(issues, `${base}.fouls`)}
                  onChange={(value) => onChange(setPlayerFoulsText(result, team, index, value))}
                />
              </div>
              <div className="mt-3 flex flex-wrap gap-4 border-t border-border/60 pt-3 text-xs text-muted">
                <label className="inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={Boolean(player.started)}
                    onChange={(event) => onChange(setPlayerFlag(result, team, index, "started", event.target.checked))}
                    className="size-4 accent-[var(--color-primary)]"
                  />
                  <span>Titular</span>
                </label>
                <label
                  className={`inline-flex items-center gap-2 rounded px-1.5 py-0.5 ${sectionHasFieldIssue(issues, `${base}.entered`) ? "bg-warning-soft/50 text-ink" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={Boolean(player.entered)}
                    onChange={(event) => onChange(setPlayerFlag(result, team, index, "entered", event.target.checked))}
                    className="size-4 accent-[var(--color-primary)]"
                  />
                  <span>Entró a jugar</span>
                </label>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TeamFoulsSection({ team, result, issues, onChange }: SectionProps & { team: TeamKey }) {
  const fouls = result[team]?.team_fouls_quarters || [];
  return (
    <div className="space-y-5">
      <SectionIssues issues={issues} />
      <div className="rounded-card border border-border p-4">
        <p className="text-sm font-semibold text-ink">Faltas de equipo por cuarto</p>
        <div className="mt-3 grid grid-cols-2 gap-3">
          {[0, 1, 2, 3].map((quarterIndex) => (
            <NumberField
              key={quarterIndex}
              label={`${quarterIndex + 1}C`}
              value={fouls[quarterIndex] ?? null}
              highlighted={sectionHasFieldIssue(issues, `${team}.team_fouls_quarters[${quarterIndex}]`)}
              onChange={(value) => onChange(setTeamFoul(result, team, quarterIndex, value))}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function ProgressiveScoreSection({ team, result, issues, onChange }: SectionProps & { team: TeamKey }) {
  const events = result.progressive_score?.[team] || [];
  const suspiciousIndexes = collectSuspiciousProgressiveIndices(issues);

  return (
    <div className="space-y-5">
      <SectionIssues issues={issues} />
      <div className="rounded-card border border-border p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-ink">Anotación progresiva completa</p>
            <p className="mt-1 text-xs leading-5 text-muted">
              Revisa todos los eventos del equipo. Los eventos sospechosos aparecen resaltados.
            </p>
          </div>
          <span className="shrink-0 rounded-full bg-elevated px-3 py-1 text-xs font-semibold text-muted">
            {events.length} eventos
          </span>
        </div>

        <div className="mt-3 space-y-3">
          {events.length === 0 ? <p className="text-sm text-muted">No hay eventos de progresivo detectados.</p> : null}
          {events.map((event, index) => {
            const highlighted = suspiciousIndexes.has(index) || sectionHasFieldIssue(issues, `progressive_score.${team}`);
            return (
              <div key={`${event.running_score ?? "event"}-${index}`} className={`rounded-card border p-3 ${highlighted ? "border-warning bg-warning-soft/30" : "border-border"}`}>
                <div className="mb-3 flex items-center justify-between gap-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-faint">Evento #{index + 1}</p>
                  <button
                    type="button"
                    onClick={() => onChange(removeProgressiveEvent(result, team, index))}
                    className="rounded-full bg-danger-soft px-3 py-1 text-xs font-semibold text-danger transition hover:opacity-80"
                  >
                    Eliminar
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <TextField
                    label="Dorsal"
                    value={event.player_number == null ? "" : String(event.player_number)}
                    highlighted={highlighted}
                    onChange={(value) => onChange(setProgressiveEventField(result, team, index, "player_number", value))}
                  />
                  <NumberField
                    label="Running"
                    value={event.running_score ?? null}
                    highlighted={highlighted}
                    onChange={(value) => onChange(setProgressiveEventField(result, team, index, "running_score", value))}
                  />
                  <NumberField
                    label="Pts"
                    value={event.points ?? null}
                    onChange={(value) => onChange(setProgressiveEventField(result, team, index, "points", value))}
                  />
                  <NumberField
                    label="Periodo"
                    value={event.period ?? null}
                    onChange={(value) => onChange(setProgressiveEventField(result, team, index, "period", value))}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <button
          type="button"
          onClick={() => onChange(addProgressiveEvent(result, team))}
          className="mt-4 w-full rounded-field border border-primary/40 bg-primary/10 px-4 py-3 text-sm font-semibold text-primary-deep transition hover:bg-primary/20"
        >
          Agregar evento de anotación
        </button>
      </div>
    </div>
  );
}

function HeaderSection({ result, issues, onChange }: SectionProps) {
  const header = result.header || {};
  return (
    <div className="space-y-5">
      <SectionIssues issues={issues} />
      <div className="grid gap-3">
        <TextField label="Liga" value={header.league || ""} highlighted={sectionHasFieldIssue(issues, "header.league")} onChange={(value) => onChange(setHeaderField(result, "league", value))} />
        <TextField label="Torneo" value={header.tournament || ""} highlighted={sectionHasFieldIssue(issues, "header.tournament")} onChange={(value) => onChange(setHeaderField(result, "tournament", value))} />
        <div className="grid grid-cols-2 gap-3">
          <TextField label="Fecha" value={header.date || ""} highlighted={sectionHasFieldIssue(issues, "header.date")} onChange={(value) => onChange(setHeaderField(result, "date", value))} />
          <TextField label="Hora" value={header.time || ""} highlighted={sectionHasFieldIssue(issues, "header.time")} onChange={(value) => onChange(setHeaderField(result, "time", value))} />
        </div>
        <TextField label="Árbitro 1" value={header.first_judge || ""} onChange={(value) => onChange(setHeaderField(result, "first_judge", value))} />
        <TextField label="Árbitro 2" value={header.second_judge || ""} onChange={(value) => onChange(setHeaderField(result, "second_judge", value))} />
      </div>
    </div>
  );
}

type SectionProps = {
  result: OcrResult;
  issues: ReconcileIssue[];
  onChange: (next: OcrResult) => void;
};

function collectSuspiciousProgressiveIndices(issues: ReconcileIssue[]): Set<number> {
  const suspiciousIndexes = new Set<number>();
  for (const issue of issues) {
    const details = issue.warning?.details;
    if (!details) continue;
    if (Array.isArray(details.event_indices)) {
      for (const idx of details.event_indices) {
        if (typeof idx === "number") suspiciousIndexes.add(idx);
      }
    }
    for (const list of [details.invalid_jumps, details.events]) {
      if (!Array.isArray(list)) continue;
      for (const item of list) {
        if (item && typeof item === "object" && "index" in item && typeof item.index === "number") {
          suspiciousIndexes.add(item.index);
        }
      }
    }
  }
  return suspiciousIndexes;
}

function matchWinner(result: OcrResult, teamAName: string, teamBName: string): string {
  const winner = typeof result.footer?.winner === "string" ? result.footer.winner.trim().toLowerCase() : "";
  if (!winner) return "";
  if (winner === teamAName.toLowerCase() || winner === "team_a" || winner === "a") return teamAName;
  if (winner === teamBName.toLowerCase() || winner === "team_b" || winner === "b") return teamBName;
  return "";
}
