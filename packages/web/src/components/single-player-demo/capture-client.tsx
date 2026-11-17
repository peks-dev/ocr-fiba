"use client";

import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { CheckIcon, RunStatusBadge, UploadIcon, formatFileSize } from "@/components/ocr-capture-ui";
import { useOcrRunCapture } from "@/lib/use-ocr-run-capture";

import { createSavedGame, extractPlayers, formatFinalScore, formatGameTitle } from "./result-utils";
import { readSavedGames, writeSavedGames } from "./storage";
import type { OcrResult } from "./types";
import { GameDetailCard, Panel } from "./ui";

export function CaptureClient() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);

  const {
    isBooting,
    selectedFile,
    run,
    result,
    status,
    isProcessing,
    isUploading,
    isLoadingResult,
    error,
    pollStopped,
    onFileChange,
    retryPolling,
    startOcr,
    loadResult,
  } = useOcrRunCapture<OcrResult>({
    onResultLoaded: ({ silent }) => {
      setSelectedPlayerId(null);
      if (!silent) {
        toast.success("OCR result loaded. Pick yourself from the roster to see your game.");
      }
    },
  });

  const players = useMemo(() => extractPlayers(result), [result]);
  const selectedPlayer = players.find((player) => player.id === selectedPlayerId) || players[0] || null;
  const pendingGame = useMemo(
    () => (result && run?.run_id && selectedPlayer ? createSavedGame(result, run.run_id, selectedPlayer) : null),
    [result, run?.run_id, selectedPlayer],
  );

  async function handleStartOcr() {
    setSelectedPlayerId(null);
    await startOcr();
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
          <RunStatusBadge status={status} idleLabel="Ready" />
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
            <UploadIcon className="size-5" />
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
          onClick={handleStartOcr}
          className="mt-4 w-full rounded-field bg-primary px-5 py-3 text-sm font-semibold text-primary-contrast transition hover:bg-primary/85 disabled:opacity-60"
        >
          {isUploading ? "Uploading..." : isProcessing ? "Processing..." : "Start OCR analysis"}
        </button>

        {pollStopped ? (
          <button
            type="button"
            onClick={retryPolling}
            className="mt-3 w-full rounded-field border border-warning/40 bg-warning-soft px-5 py-3 text-sm font-semibold text-warning transition hover:opacity-90"
          >
            Retry status check
          </button>
        ) : null}

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
