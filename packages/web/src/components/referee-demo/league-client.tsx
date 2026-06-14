"use client";

import { useCallback, useEffect, useState } from "react";

import { listSubmissions } from "./league-store";
import type { LeagueRecord } from "./types";
import { Panel } from "./ui";

export function LeagueClient() {
  const [records, setRecords] = useState<LeagueRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setRecords(await listSubmissions());
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar los partidos.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Panel className="p-5 sm:p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep sm:text-sm">Vista de liga</p>
          <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">Partidos recibidos</h2>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={isLoading}
          className="rounded-field border border-border bg-surface px-4 py-2 text-sm font-semibold text-ink transition hover:border-primary disabled:opacity-60"
        >
          {isLoading ? "Cargando..." : "Actualizar"}
        </button>
      </div>

      {error ? <div className="mt-4 rounded-card bg-danger-soft p-4 text-sm text-danger">{error}</div> : null}

      {!error && !isLoading && records.length === 0 ? (
        <div className="mt-5 rounded-card border border-dashed border-border p-8 text-center text-sm text-muted">
          Aún no hay partidos enviados. Cuadra un acta y envíala a la liga para verla aquí.
        </div>
      ) : null}

      {records.length > 0 ? (
        <div className="mt-5 space-y-3">
          {records.map((record) => {
            const f = record.fields;
            const cuadrada = f.reconcile_status === "cuadrada";
            return (
              <div key={record.id} className="rounded-card border border-border bg-surface p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-ink">
                      {f.team_a || "Equipo A"} vs {f.team_b || "Equipo B"}
                    </p>
                    <p className="mt-1 text-xs text-muted">
                      {(f.league || "Liga sin nombre") + " · " + (f.game_date || "fecha n/d")}
                    </p>
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${cuadrada ? "bg-success-soft text-success" : "bg-warning-soft text-warning"}`}
                  >
                    {cuadrada ? "Cuadrada" : "Con observaciones"}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted">
                  <span>
                    Marcador: <span className="font-semibold text-ink">{f.final_score || "n/d"}</span>
                  </span>
                  <span>
                    Ganador: <span className="font-semibold text-ink">{f.winner || "n/d"}</span>
                  </span>
                  {typeof f.warnings_remaining === "number" ? (
                    <span>
                      Pendientes: <span className="font-semibold text-ink">{f.warnings_remaining}</span>
                    </span>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}
    </Panel>
  );
}
