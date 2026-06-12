"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { toast } from "sonner";

import { getRun, getRunResult, uploadRun, type RunRecord } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

import { createSavedGame, extractPlayers, formatFinalScore, formatGameTitle } from "./result-utils";
import { readSavedGames, writeSavedGames } from "./storage";
import type { OcrResult } from "./types";
import { GameDetailCard, Panel } from "./ui";

const POLL_INTERVAL_MS = 2200;
const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

export function CaptureClient() {
  const supabase = useMemo(() => createClient(), []);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [run, setRun] = useState<RunRecord | null>(null);
  const [result, setResult] = useState<OcrResult | null>(null);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);
  const [isBooting, setIsBooting] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingResult, setIsLoadingResult] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const players = useMemo(() => extractPlayers(result), [result]);
  const selectedPlayer = players.find((player) => player.id === selectedPlayerId) || players[0] || null;
  const status = run?.status || "idle";
  const isProcessing = status === "queued" || status === "pending" || status === "running";

  const pendingGame = useMemo(
    () => (result && run?.run_id && selectedPlayer ? createSavedGame(result, run.run_id, selectedPlayer) : null),
    [result, run?.run_id, selectedPlayer],
  );

  const loadResult = useCallback(
    async (
      currentSession = session,
      runId = run?.run_id,
      options: { silent?: boolean } = {},
    ) => {
      if (!currentSession || !runId) return;

      setIsLoadingResult(true);
      setError(null);
      try {
        const nextResult = await getRunResult<OcrResult>(currentSession, runId);
        setResult(nextResult);
        setSelectedPlayerId(null);
        if (!options.silent) {
          toast.success("OCR result loaded. Pick yourself from the roster to see your game.");
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "Could not load OCR result.";
        setError(message);
        if (!options.silent) toast.error(message);
      } finally {
        setIsLoadingResult(false);
      }
    },
    [run?.run_id, session],
  );

  useEffect(() => {
    let mounted = true;

    async function boot() {
      const { data } = await supabase.auth.getSession();
      if (!mounted) return;
      setSession(data.session);
      setIsBooting(false);
    }

    boot();

    return () => {
      mounted = false;
    };
  }, [supabase]);

  useEffect(() => {
    if (!run?.run_id || !session || !isProcessing) return;
    const currentSession = session;
    const currentRunId = run.run_id;
    let cancelled = false;

    async function poll() {
      try {
        const nextRun = await getRun(currentSession, currentRunId);
        if (cancelled) return;
        setRun(nextRun);

        if (nextRun.status === "completed") {
          await loadResult(currentSession, nextRun.run_id, { silent: cancelled });
        }

        if (nextRun.status === "failed") {
          toast.error(extractRunError(nextRun.error) || "OCR run failed.");
        }
      } catch (err) {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Could not refresh run status.";
        setError(message);
      }
    }

    const timeout = window.setTimeout(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timeout);
    };
  }, [isProcessing, loadResult, run, session]);

  function onFileChange(file: File | null) {
    if (!file) return;
    if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
      toast.error("Please upload a JPG, PNG, or WEBP image.");
      return;
    }
    setSelectedFile(file);
    setError(null);
  }

  async function startOcr() {
    if (!session) {
      toast.error("No active session. Please log in again.");
      return;
    }
    if (!selectedFile) {
      toast.error("Choose a scoresheet image first.");
      return;
    }

    setIsUploading(true);
    setError(null);
    setResult(null);
    setSelectedPlayerId(null);

    try {
      const response = await uploadRun(session, selectedFile);
      setRun(response);
      if (response.status === "completed") {
        await loadResult(session, response.run_id);
      } else {
        toast.success("Scoresheet uploaded. OCR is running.");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed.";
      setError(message);
      toast.error(message);
    } finally {
      setIsUploading(false);
    }
  }

  function saveSelectedGame() {
    if (!pendingGame) return;

    const current = readSavedGames();
    const next = [
      pendingGame,
      ...current.filter((game) => game.runId !== pendingGame.runId || game.player.id !== pendingGame.player.id),
    ].slice(0, 30);
    writeSavedGames(next);
    toast.success("Game saved. Review it in Progress and History.");
  }

  if (isBooting) {
    return <Panel className="p-8 text-muted">Loading demo...</Panel>;
  }

  return (
    <div className="grid gap-6 sm:gap-8 lg:grid-cols-[0.9fr_1.1fr]">
      <Panel className="h-fit p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep sm:text-sm">Capture</p>
            <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">Run OCR on a scoresheet</h2>
          </div>
          <StatusBadge status={status} />
        </div>

        <div className="mt-5 sm:mt-6">
          <Stepper
            steps={[
              { label: "Choose a photo", state: stepState(Boolean(selectedFile), !selectedFile) },
              {
                label: isProcessing ? "Reading the sheet..." : "Run the OCR",
                state: stepState(Boolean(result), Boolean(selectedFile) && !result),
              },
              { label: "Pick yourself & save", state: stepState(false, Boolean(result)) },
            ]}
          />
        </div>

        <button
          type="button"
          className="mt-5 flex w-full flex-col items-center justify-center rounded-card border border-dashed border-border bg-elevated px-5 py-8 text-center transition hover:border-primary hover:bg-primary/5 sm:py-10"
          onClick={() => fileInputRef.current?.click()}
        >
          <span className="grid size-12 place-items-center rounded-full bg-primary/15 text-primary-deep">
            <UploadIcon />
          </span>
          {selectedFile ? (
            <>
              <span className="mt-4 max-w-full truncate px-2 text-sm font-semibold text-ink">{selectedFile.name}</span>
              <span className="mt-1 text-xs text-muted">{formatFileSize(selectedFile.size)} · Tap to change the photo</span>
            </>
          ) : (
            <>
              <span className="mt-4 text-sm font-semibold text-ink sm:text-base">Choose a scoresheet photo</span>
              <span className="mt-1 text-xs text-muted sm:text-sm">JPG, PNG, or WEBP. The API upload limit still applies.</span>
            </>
          )}
        </button>
        <input
          ref={fileInputRef}
          className="sr-only"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(event) => onFileChange(event.target.files?.[0] || null)}
        />

        <button
          type="button"
          disabled={!selectedFile || isUploading || isProcessing}
          onClick={startOcr}
          className="mt-4 w-full rounded-field bg-primary px-5 py-3 text-sm font-semibold text-primary-contrast transition hover:bg-primary/85 disabled:opacity-60"
        >
          {isUploading ? "Uploading..." : isProcessing ? "Processing..." : "Start OCR analysis"}
        </button>

        {run?.status === "completed" && !result ? (
          <button
            type="button"
            disabled={isLoadingResult}
            onClick={() => loadResult()}
            className="mt-3 w-full rounded-field border border-primary/40 bg-primary/10 px-5 py-3 text-sm font-semibold text-primary-deep transition hover:bg-primary/20 disabled:opacity-60"
          >
            {isLoadingResult ? "Loading result..." : "Load completed OCR result"}
          </button>
        ) : null}

        {error ? <div className="mt-4 rounded-card bg-danger-soft p-4 text-sm text-danger">{error}</div> : null}

        {run?.run_id ? <p className="mt-4 truncate text-xs text-faint">Run ID: {run.run_id}</p> : null}
      </Panel>

      <Panel className="p-5 sm:p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep sm:text-sm">Your game</p>
            <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">{formatGameTitle(result)}</h2>
            <p className="mt-2 text-sm text-muted">{formatFinalScore(result)}</p>
          </div>
          {result?.validation_warnings?.length ? (
            <span className="self-start rounded-full bg-warning-soft px-3 py-1 text-xs font-semibold text-warning">
              {result.validation_warnings.length} warnings
            </span>
          ) : null}
        </div>

        {players.length > 0 ? (
          <div className="mt-5 grid gap-5 sm:mt-6 sm:gap-6 xl:grid-cols-[0.85fr_1.15fr]">
            <div className="max-h-72 space-y-2 overflow-y-auto pr-1 xl:max-h-[34rem]">
              {players.map((player) => (
                <button
                  key={player.id}
                  type="button"
                  onClick={() => setSelectedPlayerId(player.id)}
                  className={`w-full rounded-card border p-3 text-left transition sm:p-4 ${selectedPlayer?.id === player.id ? "border-primary bg-primary/10" : "border-border bg-surface hover:border-faint"}`}
                >
                  <div className="flex items-center gap-3">
                    <span className="grid size-9 shrink-0 place-items-center rounded-full bg-elevated font-heading text-sm font-bold text-ink">
                      {player.number}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold text-ink">{player.name}</p>
                      <p className="truncate text-xs text-muted">{player.teamName}</p>
                    </div>
                    <span className="shrink-0 rounded-full bg-ink px-3 py-1 text-sm font-bold text-background">{player.totalPoints} pts</span>
                  </div>
                </button>
              ))}
            </div>

            {pendingGame ? (
              <GameDetailCard
                game={pendingGame}
                footer={
                  <button
                    type="button"
                    onClick={saveSelectedGame}
                    className="w-full rounded-field bg-primary px-5 py-3 text-sm font-semibold text-primary-contrast transition hover:bg-primary/85"
                  >
                    Save game to my history
                  </button>
                }
              />
            ) : null}
          </div>
        ) : (
          <div className="mt-6 rounded-card border border-dashed border-border p-8 text-center text-sm text-muted">
            Run the OCR on a scoresheet and your roster will appear here. Pick yourself to see your points and fouls at a glance.
          </div>
        )}
      </Panel>
    </div>
  );
}

type StepState = "done" | "active" | "pending";

function stepState(done: boolean, active: boolean): StepState {
  return done ? "done" : active ? "active" : "pending";
}

function Stepper({ steps }: { steps: { label: string; state: StepState }[] }) {
  return (
    <ol className="space-y-2.5">
      {steps.map((step, index) => (
        <li key={step.label} className="flex items-center gap-3 text-sm">
          <span
            className={`grid size-7 shrink-0 place-items-center rounded-full text-xs font-bold transition ${
              step.state === "done"
                ? "bg-primary text-primary-contrast"
                : step.state === "active"
                  ? "bg-ink text-background"
                  : "bg-elevated text-faint"
            }`}
          >
            {step.state === "done" ? <CheckIcon /> : index + 1}
          </span>
          <span className={step.state === "pending" ? "text-faint" : "text-ink"}>{step.label}</span>
        </li>
      ))}
    </ol>
  );
}

function StatusBadge({ status }: { status: string }) {
  const label = status === "idle" ? "Ready" : status;
  const styles =
    status === "completed"
      ? "bg-success-soft text-success"
      : status === "failed"
        ? "bg-danger-soft text-danger"
        : status === "queued" || status === "pending" || status === "running"
          ? "bg-warning-soft text-warning"
          : "bg-elevated text-muted";

  return <span className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${styles}`}>{label}</span>;
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="size-5" aria-hidden="true">
      <path d="M12 16V4" />
      <path d="M7 9l5-5 5 5" />
      <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="size-3.5" aria-hidden="true">
      <path d="M5 13l4 4 10-10" />
    </svg>
  );
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function extractRunError(error: unknown) {
  if (!error) return null;
  if (typeof error === "string") return error;
  if (typeof error === "object" && "message" in error && typeof error.message === "string") return error.message;
  return null;
}
