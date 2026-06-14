"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";

import { readDraft } from "./draft";
import { createSubmission } from "./league-store";
import { buildSubmissionPayload, formatFinalScore, gameTitle } from "./reconcile-utils";
import { computeReconciliation } from "./validation";
import type { OcrResult } from "./types";
import { EmptyState, Panel, StatusBanner, TextField } from "./ui";

const LEAGUE_PATH = "/dashboard/demos/referee/league";
const CAPTURE_PATH = "/dashboard/demos/referee/capture";
const RECONCILE_PATH = "/dashboard/demos/referee/reconcile";

export function SubmitClient() {
  const [runId, setRunId] = useState<string | null>(null);
  const [result, setResult] = useState<OcrResult | null>(null);
  const [isBooting, setIsBooting] = useState(true);
  const [league, setLeague] = useState("");
  const [gameDate, setGameDate] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    const draft = readDraft();
    if (draft) {
      setRunId(draft.runId);
      setResult(draft.result);
      setLeague(draft.result.header?.league || draft.result.header?.tournament || "");
      setGameDate(draft.result.header?.date || "");
    }
    setIsBooting(false);
  }, []);

  const summary = useMemo(() => (result ? computeReconciliation(result) : null), [result]);

  async function send() {
    if (!result || !runId) return;
    setIsSending(true);
    try {
      const payload = buildSubmissionPayload(result, runId);
      payload.league = league.trim() || payload.league;
      payload.game_date = gameDate.trim() || payload.game_date;
      await createSubmission(payload);
      setSent(true);
      toast.success("Partido enviado a la liga.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "No se pudo enviar el partido a la liga.");
    } finally {
      setIsSending(false);
    }
  }

  if (isBooting) return <Panel className="p-6 text-muted">Cargando acta...</Panel>;

  if (!result || !runId || !summary) {
    return (
      <Panel className="p-5 sm:p-6">
        <EmptyState
          title="No hay un acta en curso"
          description="Captura, extrae y cuadra un acta antes de enviarla a la liga."
          ctaHref={CAPTURE_PATH}
          ctaLabel="Ir a Capturar acta"
        />
      </Panel>
    );
  }

  return (
    <div className="mx-auto max-w-xl space-y-4 pb-28 sm:space-y-6 sm:pb-0">
      <Panel className="p-5 sm:p-6">
        <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18em] text-primary-deep">Paso 3/3 · Enviar</p>
        <h2 className="mt-2 text-2xl font-semibold text-ink">Listo para enviar</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Revisa el resumen final. La liga recibirá el partido como datos estructurados.
        </p>

        <div className="mt-5 rounded-card border border-border bg-elevated p-4">
          <p className="text-sm font-semibold text-ink">{gameTitle(result)}</p>
          <p className="mt-1 text-3xl font-semibold tracking-tight text-ink">{formatFinalScore(result)}</p>
          <div className="mt-3 grid gap-2 text-sm text-muted">
            <div className="flex justify-between gap-4">
              <span>Ganador</span>
              <span className="text-right font-semibold text-ink">{result.footer?.winner || "Sin declarar"}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span>Estado</span>
              <span className="text-right font-semibold text-ink">{summary.status === "cuadrada" ? "Acta cuadrada" : "Con observaciones"}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span>Pendientes</span>
              <span className="text-right font-semibold text-ink">{summary.blockingCount}</span>
            </div>
          </div>
        </div>

        <div className="mt-4">
          <StatusBanner status={summary.status} blockingCount={summary.blockingCount} />
        </div>

        {summary.blockingCount > 0 ? (
          <p className="mt-4 rounded-card bg-warning-soft px-4 py-3 text-xs font-semibold text-warning">
            Aún hay campos por cuadrar. Puedes enviar igual; quedará marcado como <span className="font-mono">con_observaciones</span>.{" "}
            <Link href={RECONCILE_PATH} className="underline">
              Volver a corregir
            </Link>
          </p>
        ) : null}
      </Panel>

      <Panel className="p-5 sm:p-6">
        <p className="text-sm font-semibold text-ink">Datos de liga</p>
        <div className="mt-4 space-y-4">
          <TextField value={league} onChange={setLeague} label="Liga / torneo" placeholder="p. ej. Liga amateur municipal" />
          <TextField value={gameDate} onChange={setGameDate} label="Fecha del partido" placeholder="p. ej. 2026-06-13" />
        </div>
      </Panel>

      <details className="rounded-panel border border-border bg-surface p-5 text-sm text-muted shadow-sm">
        <summary className="cursor-pointer font-semibold text-ink">Ver datos técnicos</summary>
        <pre className="mt-4 max-h-80 overflow-auto rounded-card bg-inverse p-4 text-xs leading-5 text-inverse-foreground">
          {JSON.stringify(buildPreview(result, runId, league, gameDate), null, 2)}
        </pre>
      </details>

      {sent ? (
        <Panel className="p-5 text-center">
          <p className="font-semibold text-success">Partido enviado correctamente.</p>
          <Link href={LEAGUE_PATH} className="mt-3 inline-block rounded-field bg-ink px-5 py-3 text-sm font-semibold text-background">
            Ver en la vista de liga →
          </Link>
        </Panel>
      ) : null}

      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-surface/95 p-4 shadow-2xl backdrop-blur sm:static sm:border-0 sm:bg-transparent sm:p-0 sm:shadow-none">
        <button
          type="button"
          disabled={isSending || sent}
          onClick={send}
          className="w-full rounded-field bg-primary px-5 py-4 text-base font-semibold text-primary-contrast transition hover:bg-primary/85 disabled:opacity-60"
        >
          {isSending ? "Enviando..." : sent ? "Enviado" : "Enviar a la liga"}
        </button>
      </div>
    </div>
  );
}

function buildPreview(result: OcrResult, runId: string, league: string, gameDate: string) {
  const payload = buildSubmissionPayload(result, runId);
  return {
    ...payload,
    league: league.trim() || payload.league,
    game_date: gameDate.trim() || payload.game_date,
    payload_json: "<JSON completo del acta>",
  };
}
