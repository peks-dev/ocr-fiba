"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Session } from "@supabase/supabase-js";
import { toast } from "sonner";

import { getRun, getRunResult, uploadRun, type RunRecord } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

import { writeDraft } from "./draft";
import { DEFAULT_REFEREE_PLUGIN_IDS, REFEREE_PLUGINS } from "./plugins";
import type { OcrResult } from "./types";
import { Panel } from "./ui";

const POLL_INTERVAL_MS = 2200;
const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
const DEFAULT_BASE_PATH = "/test/referee";

export function CaptureClient({ basePath = DEFAULT_BASE_PATH }: { basePath?: string }) {
  const router = useRouter();
  const supabase = useMemo(() => createClient(), []);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedPlugins, setSelectedPlugins] = useState<string[]>(DEFAULT_REFEREE_PLUGIN_IDS);
  const [run, setRun] = useState<RunRecord | null>(null);
  const [isBooting, setIsBooting] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingResult, setIsLoadingResult] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const status = run?.status || "idle";
  const isProcessing = status === "queued" || status === "pending" || status === "running";

  const loadResult = useCallback(
    async (currentSession = session, runId = run?.run_id) => {
      if (!currentSession || !runId) return;
      setIsLoadingResult(true);
      setError(null);
      try {
        const nextResult = await getRunResult<OcrResult>(currentSession, runId);
        writeDraft(runId, nextResult, selectedPlugins);
        toast.success("Acta extraída. Vamos a corregirla.");
        router.push(`${basePath}/reconcile`);
      } catch (err) {
        const message = err instanceof Error ? err.message : "No se pudo cargar el resultado del OCR.";
        setError(message);
        toast.error(message);
      } finally {
        setIsLoadingResult(false);
      }
    },
    [basePath, router, run?.run_id, selectedPlugins, session],
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
        if (nextRun.status === "completed") await loadResult(currentSession, nextRun.run_id);
        if (nextRun.status === "failed") toast.error(extractRunError(nextRun.error) || "El OCR falló.");
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "No se pudo refrescar el estado del run.");
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
      toast.error("Sube una imagen JPG, PNG o WEBP.");
      return;
    }
    setSelectedFile(file);
    setRun(null);
    setError(null);
  }

  async function startOcr() {
    if (!session) {
      toast.error("No hay sesión activa. Inicia sesión de nuevo.");
      return;
    }
    if (!selectedFile) {
      toast.error("Elige primero una imagen del acta.");
      return;
    }
    if (selectedPlugins.length === 0) {
      toast.error("Activa al menos un plugin de revisión.");
      return;
    }
    setIsUploading(true);
    setError(null);
    try {
      const response = await uploadRun(session, selectedFile, { validationPlugins: selectedPlugins });
      setRun(response);
      if (response.status === "completed") await loadResult(session, response.run_id);
      else toast.success("Acta subida. Estoy leyendo la hoja.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "La subida falló.";
      setError(message);
      toast.error(message);
    } finally {
      setIsUploading(false);
    }
  }

  function togglePlugin(pluginId: string) {
    setSelectedPlugins((current) =>
      current.includes(pluginId) ? current.filter((id) => id !== pluginId) : [...current, pluginId],
    );
  }

  if (isBooting) return <Panel className="p-6 text-muted">Cargando demo...</Panel>;

  return (
    <div className="mx-auto max-w-xl pb-24 sm:pb-0">
      <Panel className="p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18em] text-primary-deep">Paso 1/3 · Capturar</p>
            <h2 className="mt-2 text-2xl font-semibold text-ink">Toma foto del acta</h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              Sube la hoja FIBA completa. Cuando el motor termine, te llevo directo a corregir las secciones que necesiten revisión.
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
              <span className="mt-1 text-sm text-muted">{formatFileSize(selectedFile.size)} · Toca para cambiar</span>
            </>
          ) : (
            <>
              <span className="mt-4 text-base font-semibold text-ink">Tomar foto o elegir imagen</span>
              <span className="mt-1 text-sm text-muted">JPG, PNG o WEBP.</span>
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

        <div className="mt-5 rounded-card border border-border bg-surface p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-ink">Plugins de revisión</p>
              <p className="mt-1 text-xs leading-5 text-muted">Elige qué reglas usará el motor para marcar pendientes de cierre.</p>
            </div>
            <span className="shrink-0 rounded-full bg-primary/15 px-3 py-1 text-xs font-semibold text-primary-deep">
              {selectedPlugins.length}/{REFEREE_PLUGINS.length}
            </span>
          </div>
          <div className="mt-3 grid gap-2">
            {REFEREE_PLUGINS.map((plugin) => {
              const checked = selectedPlugins.includes(plugin.id);
              return (
                <label
                  key={plugin.id}
                  className={`flex items-start gap-3 rounded-card border p-3 transition ${checked ? "border-primary bg-primary/5" : "border-border bg-elevated"}`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => togglePlugin(plugin.id)}
                    disabled={isUploading || isProcessing}
                    className="mt-1 size-4 accent-[var(--color-primary)]"
                  />
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-ink">{plugin.label}</span>
                    <span className="mt-0.5 block text-xs leading-5 text-muted">{plugin.description}</span>
                  </span>
                </label>
              );
            })}
          </div>
        </div>

        <button
          type="button"
          disabled={!selectedFile || selectedPlugins.length === 0 || isUploading || isProcessing || isLoadingResult}
          onClick={startOcr}
          className="mt-4 w-full rounded-field bg-primary px-5 py-4 text-base font-semibold text-primary-contrast transition hover:bg-primary/85 disabled:opacity-60"
        >
          {buttonLabel({ isUploading, isProcessing, isLoadingResult })}
        </button>

        {isProcessing || isLoadingResult ? (
          <div className="mt-4 rounded-card bg-warning-soft p-4 text-sm font-semibold text-warning">
            {isLoadingResult ? "Preparando el asistente de corrección..." : "Leyendo secciones y validando inconsistencias..."}
          </div>
        ) : null}

        {run?.status === "completed" ? (
          <button
            type="button"
            disabled={isLoadingResult}
            onClick={() => loadResult()}
            className="mt-3 w-full rounded-field border border-primary/40 bg-primary/10 px-5 py-3 text-sm font-semibold text-primary-deep transition hover:bg-primary/20 disabled:opacity-60"
          >
            {isLoadingResult ? "Cargando resultado..." : "Continuar a corregir"}
          </button>
        ) : null}

        {error ? <div className="mt-4 rounded-card bg-danger-soft p-4 text-sm text-danger">{error}</div> : null}
        {run?.run_id ? <p className="mt-4 truncate text-xs text-faint">Run ID: {run.run_id}</p> : null}
      </Panel>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const label = status === "idle" ? "Listo" : status;
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

function buttonLabel({ isUploading, isProcessing, isLoadingResult }: { isUploading: boolean; isProcessing: boolean; isLoadingResult: boolean }) {
  if (isUploading) return "Subiendo acta...";
  if (isLoadingResult) return "Abriendo corrección...";
  if (isProcessing) return "Procesando OCR...";
  return "Leer acta";
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="size-6" aria-hidden="true">
      <path d="M12 16V4" />
      <path d="M7 9l5-5 5 5" />
      <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
    </svg>
  );
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function extractRunError(error: unknown): string | null {
  if (!error) return null;
  if (typeof error === "string") return error;
  if (typeof error === "object" && "message" in error && typeof error.message === "string") return error.message;
  return null;
}
