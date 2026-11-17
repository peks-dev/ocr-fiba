"use client";

import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { UploadIcon, formatFileSize } from "@/components/ocr-capture-ui";
import { useOcrRunCapture } from "@/lib/use-ocr-run-capture";

import { createGameFromResult, teamName } from "./result-utils";
import { addClubGame, addDetectedPlayersToRoster, readClubStore, writeClubStore } from "./storage";
import type { ClubStore, OcrResult, TeamKey } from "./types";
import { Panel, StatusBadge } from "./ui";

const INITIAL_STORE: ClubStore = { clubName: "My Club", roster: [], games: [] };

export function CaptureClient() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [store, setStore] = useState<ClubStore>(INITIAL_STORE);
  const [selectedTeam, setSelectedTeam] = useState<TeamKey>("team_a");

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
  } = useOcrRunCapture<OcrResult>({
    onResultLoaded: ({ silent }) => {
      setSelectedTeam("team_a");
      if (!silent) toast.success("OCR result loaded. Choose your club team and save the game.");
    },
  });

  useEffect(() => {
    setStore(readClubStore());
  }, []);

  const previewGame = result && run?.run_id ? createGameFromResult(result, run.run_id, selectedTeam, store.roster) : null;

  function saveGame() {
    if (!previewGame || !result || !run?.run_id) return;
    const rosterUpdate = addDetectedPlayersToRoster(store, previewGame.stats);
    const finalGame = createGameFromResult(result, run.run_id, selectedTeam, rosterUpdate.store.roster);
    const next = addClubGame(rosterUpdate.store, finalGame);
    setStore(next);
    writeClubStore(next);
    toast.success(
      rosterUpdate.addedCount > 0
        ? `Game saved and ${rosterUpdate.addedCount} roster players added from OCR.`
        : "Game saved to club analysis.",
    );
  }

  if (isBooting) return <Panel className="p-6 text-muted">Loading capture...</Panel>;

  return (
    <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
      <Panel className="h-fit p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep">Capture</p>
            <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">Import a game sheet</h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              Upload the first scoresheet, choose which side is your club, and the roster will be created from player names automatically.
            </p>
          </div>
          <StatusBadge status={status} />
        </div>

        <button
          type="button"
          className="mt-6 flex min-h-56 w-full flex-col items-center justify-center rounded-card border border-dashed border-border bg-elevated px-5 py-8 text-center transition hover:border-primary hover:bg-primary/5"
          onClick={() => fileInputRef.current?.click()}
        >
          <span className="grid size-14 place-items-center rounded-full bg-primary/15 text-primary-deep">
            <UploadIcon />
          </span>
          {selectedFile ? (
            <>
              <span className="mt-4 max-w-full truncate px-2 text-base font-semibold text-ink">{selectedFile.name}</span>
              <span className="mt-1 text-sm text-muted">{formatFileSize(selectedFile.size)} · Tap to change</span>
            </>
          ) : (
            <>
              <span className="mt-4 text-base font-semibold text-ink">Choose scoresheet image</span>
              <span className="mt-1 text-sm text-muted">JPG, PNG, or WEBP.</span>
            </>
          )}
        </button>
        <input
          ref={fileInputRef}
          className="sr-only"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          onChange={(event) => onFileChange(event.target.files?.[0] || null)}
        />

        {error ? <div className="mt-4 rounded-card bg-danger-soft p-4 text-sm text-danger">{error}</div> : null}

        {pollStopped ? (
          <button
            type="button"
            onClick={retryPolling}
            className="mt-4 w-full rounded-field border border-warning/40 bg-warning-soft px-5 py-3 text-sm font-semibold text-warning transition hover:opacity-90"
          >
            Retry status check
          </button>
        ) : null}

        <button
          type="button"
          disabled={!selectedFile || isUploading || isProcessing || isLoadingResult}
          onClick={() => startOcr()}
          className="mt-5 w-full rounded-field bg-primary px-5 py-3 text-sm font-semibold text-primary-contrast transition hover:bg-primary/85 disabled:opacity-60"
        >
          {isUploading ? "Uploading..." : isProcessing ? "Processing..." : isLoadingResult ? "Loading result..." : "Start OCR import"}
        </button>
      </Panel>

      <Panel className="p-5 sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep">Game preview</p>
        <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">Choose your team</h2>
        {!result ? (
          <div className="mt-6 rounded-card border border-dashed border-border p-8 text-center text-sm text-muted">
            Run OCR to preview both teams. Saving the chosen side will add its detected players to your roster automatically.
          </div>
        ) : (
          <div className="mt-5 space-y-5">
            <div className="grid gap-3 sm:grid-cols-2">
              {(["team_a", "team_b"] as TeamKey[]).map((team) => (
                <button
                  key={team}
                  type="button"
                  onClick={() => setSelectedTeam(team)}
                  className={`rounded-card border p-4 text-left transition ${
                    selectedTeam === team ? "border-primary bg-primary/10" : "border-border bg-elevated hover:border-faint"
                  }`}
                >
                  <p className="text-sm font-semibold text-ink">{teamName(result, team)}</p>
                  <p className="mt-1 text-xs text-muted">{result[team]?.players?.length || 0} detected players</p>
                </button>
              ))}
            </div>

            {previewGame ? (
              <div className="rounded-card border border-border bg-elevated p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-ink">
                      {previewGame.clubTeamName} vs {previewGame.opponent}
                    </p>
                    <p className="mt-1 text-xs text-muted">
                      {previewGame.tournament} · {previewGame.gameDate} · {previewGame.finalScore}
                    </p>
                  </div>
                  <span className="rounded-full bg-surface px-3 py-1 text-xs font-semibold text-muted">
                    {previewGame.stats.filter((stat) => stat.matchedRoster).length}/{previewGame.stats.length} name matches
                  </span>
                </div>
                <div className="mt-4 max-h-80 space-y-2 overflow-y-auto pr-1">
                  {previewGame.stats.map((stat) => (
                    <div key={`${stat.number}:${stat.playerName}`} className="flex items-center justify-between gap-3 rounded-card bg-surface p-3 text-sm">
                      <div className="min-w-0">
                        <p className="truncate font-semibold text-ink">
                          #{stat.number} {stat.playerName}
                        </p>
                        <p className="text-xs text-muted">
                          {stat.matchedRoster ? "Name matched" : "Will be added as new player"} · OCR # {stat.number} · {stat.foulsCount} fouls
                        </p>
                      </div>
                      <span className="text-lg font-black text-ink">{stat.totalPoints}</span>
                    </div>
                  ))}
                </div>
                <button type="button" onClick={saveGame} className="mt-4 w-full rounded-field bg-ink px-5 py-3 text-sm font-semibold text-background transition hover:bg-ink/85">
                  Save game and update roster
                </button>
              </div>
            ) : null}
          </div>
        )}
      </Panel>
    </div>
  );
}
