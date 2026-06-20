"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { toast } from "sonner";

import { getRun, getRunResult, uploadRun, type RunRecord } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

import { createGameFromResult, teamName } from "./result-utils";
import { addClubGame, addDetectedPlayersToRoster, readClubStore, writeClubStore } from "./storage";
import type { ClubStore, OcrResult, TeamKey } from "./types";
import { Panel, StatusBadge } from "./ui";

const POLL_INTERVAL_MS = 2200;
const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
const INITIAL_STORE: ClubStore = { clubName: "My Club", roster: [], games: [] };

export function CaptureClient() {
  const supabase = useMemo(() => createClient(), []);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [store, setStore] = useState<ClubStore>(INITIAL_STORE);
  const [session, setSession] = useState<Session | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [run, setRun] = useState<RunRecord | null>(null);
  const [result, setResult] = useState<OcrResult | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<TeamKey>("team_a");
  const [isBooting, setIsBooting] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingResult, setIsLoadingResult] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const status = run?.status || "idle";
  const isProcessing = status === "queued" || status === "pending" || status === "running";
  const previewGame = result && run?.run_id ? createGameFromResult(result, run.run_id, selectedTeam, store.roster) : null;

  const loadResult = useCallback(
    async (currentSession = session, runId = run?.run_id, options: { silent?: boolean } = {}) => {
      if (!currentSession || !runId) return;
      setIsLoadingResult(true);
      setError(null);
      try {
        const nextResult = await getRunResult<OcrResult>(currentSession, runId);
        setResult(nextResult);
        setSelectedTeam("team_a");
        if (!options.silent) toast.success("OCR result loaded. Choose your club team and save the game.");
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
      const [{ data }, nextStore] = await Promise.all([supabase.auth.getSession(), Promise.resolve(readClubStore())]);
      if (!mounted) return;
      setSession(data.session);
      setStore(nextStore);
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
        if (nextRun.status === "completed") await loadResult(currentSession, nextRun.run_id, { silent: cancelled });
        if (nextRun.status === "failed") toast.error(extractRunError(nextRun.error) || "OCR run failed.");
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not refresh run status.");
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
      toast.error("Upload a JPG, PNG, or WEBP image.");
      return;
    }
    setSelectedFile(file);
    setRun(null);
    setResult(null);
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
    try {
      const response = await uploadRun(session, selectedFile);
      setRun(response);
      if (response.status === "completed") await loadResult(session, response.run_id);
      else toast.success("Scoresheet uploaded. OCR is running.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed.";
      setError(message);
      toast.error(message);
    } finally {
      setIsUploading(false);
    }
  }

  function saveGame() {
    if (!previewGame || !result || !run?.run_id) return;
    const rosterUpdate = addDetectedPlayersToRoster(store, previewGame.stats);
    const finalGame = createGameFromResult(result, run.run_id, selectedTeam, rosterUpdate.store.roster);
    const next = addClubGame(rosterUpdate.store, finalGame);
    setStore(next);
    writeClubStore(next);
    toast.success(rosterUpdate.addedCount > 0 ? `Game saved and ${rosterUpdate.addedCount} roster players added from OCR.` : "Game saved to club analysis.");
  }

  if (isBooting) return <Panel className="p-6 text-muted">Loading capture...</Panel>;


  return (
    <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
      <Panel className="h-fit p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep">Capture</p>
            <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">Import a game sheet</h2>
            <p className="mt-2 text-sm leading-6 text-muted">Upload the first scoresheet, choose which side is your club, and the roster will be created from player names automatically.</p>
          </div>
          <StatusBadge status={status} />
        </div>

        <button type="button" className="mt-6 flex min-h-56 w-full flex-col items-center justify-center rounded-card border border-dashed border-border bg-elevated px-5 py-8 text-center transition hover:border-primary hover:bg-primary/5" onClick={() => fileInputRef.current?.click()}>
          <span className="grid size-14 place-items-center rounded-full bg-primary/15 text-primary-deep"><UploadIcon /></span>
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
        <input ref={fileInputRef} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={(event) => onFileChange(event.target.files?.[0] || null)} />

        {error ? <div className="mt-4 rounded-card bg-danger-soft p-4 text-sm text-danger">{error}</div> : null}

        <button type="button" disabled={!selectedFile || isUploading || isProcessing || isLoadingResult} onClick={startOcr} className="mt-5 w-full rounded-field bg-primary px-5 py-3 text-sm font-semibold text-primary-contrast transition hover:bg-primary/85 disabled:opacity-60">
          {isUploading ? "Uploading..." : isProcessing ? "Processing..." : isLoadingResult ? "Loading result..." : "Start OCR import"}
        </button>
      </Panel>

      <Panel className="p-5 sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep">Game preview</p>
        <h2 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">Choose your team</h2>
        {!result ? (
          <div className="mt-6 rounded-card border border-dashed border-border p-8 text-center text-sm text-muted">Run OCR to preview both teams. Saving the chosen side will add its detected players to your roster automatically.</div>
        ) : (
          <div className="mt-5 space-y-5">
            <div className="grid gap-3 sm:grid-cols-2">
              {(["team_a", "team_b"] as TeamKey[]).map((team) => (
                <button key={team} type="button" onClick={() => setSelectedTeam(team)} className={`rounded-card border p-4 text-left transition ${selectedTeam === team ? "border-primary bg-primary/10" : "border-border bg-elevated hover:border-faint"}`}>
                  <p className="text-sm font-semibold text-ink">{teamName(result, team)}</p>
                  <p className="mt-1 text-xs text-muted">{result[team]?.players?.length || 0} detected players</p>
                </button>
              ))}
            </div>

            {previewGame ? (
              <div className="rounded-card border border-border bg-elevated p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-ink">{previewGame.clubTeamName} vs {previewGame.opponent}</p>
                    <p className="mt-1 text-xs text-muted">{previewGame.tournament} · {previewGame.gameDate} · {previewGame.finalScore}</p>
                  </div>
                  <span className="rounded-full bg-surface px-3 py-1 text-xs font-semibold text-muted">{previewGame.stats.filter((stat) => stat.matchedRoster).length}/{previewGame.stats.length} name matches</span>
                </div>
                <div className="mt-4 max-h-80 space-y-2 overflow-y-auto pr-1">
                  {previewGame.stats.map((stat) => (
                    <div key={`${stat.number}:${stat.playerName}`} className="flex items-center justify-between gap-3 rounded-card bg-surface p-3 text-sm">
                      <div className="min-w-0">
                        <p className="truncate font-semibold text-ink">#{stat.number} {stat.playerName}</p>
                        <p className="text-xs text-muted">{stat.matchedRoster ? "Name matched" : "Will be added as new player"} · OCR # {stat.number} · {stat.foulsCount} fouls</p>
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

function extractRunError(error: unknown) {
  if (!error) return "";
  if (typeof error === "string") return error;
  if (typeof error === "object" && "message" in error && typeof error.message === "string") return error.message;
  return "";
}

function formatFileSize(size: number) {
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="size-6" aria-hidden="true">
      <path d="M12 16V4" />
      <path d="m7 9 5-5 5 5" />
      <path d="M20 16.5V19a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2.5" />
    </svg>
  );
}
