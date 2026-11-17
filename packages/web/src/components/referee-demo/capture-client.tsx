"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { RunStatusBadge, UploadIcon, formatFileSize } from "@/components/ocr-capture-ui";
import { useOcrRunCapture } from "@/lib/use-ocr-run-capture";

import { writeDraft } from "./draft";
import { DEFAULT_REFEREE_PLUGIN_IDS, REFEREE_PLUGINS } from "./plugins";
import type { OcrResult } from "./types";
import { Panel } from "./ui";

const DEFAULT_BASE_PATH = "/test/referee";

export function CaptureClient({ basePath = DEFAULT_BASE_PATH }: { basePath?: string }) {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedPlugins, setSelectedPlugins] = useState<string[]>(DEFAULT_REFEREE_PLUGIN_IDS);

  const {
    isBooting,
    selectedFile,
    run,
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
    messages: {
      invalidFileType: "Sube una imagen JPG, PNG o WEBP.",
      noSession: "No hay sesión activa. Inicia sesión de nuevo.",
      noFileSelected: "Elige primero una imagen del acta.",
      uploadStarted: "Acta subida. Estoy leyendo la hoja.",
      uploadFailed: "La subida falló.",
      runFailed: "El OCR falló.",
      pollFailed: "No se pudo refrescar el estado del run.",
      resultFailed: "No se pudo cargar el resultado del OCR.",
    },
    onResultLoaded: ({ runId, result }) => {
      writeDraft(runId, result, selectedPlugins);
      toast.success("Acta extraída. Vamos a corregirla.");
      router.push(`${basePath}/reconcile`);
    },
  });

  async function handleStartOcr() {
    if (selectedPlugins.length === 0) {
      toast.error("Activa al menos un plugin de revisión.");
      return;
    }
    await startOcr({ validationPlugins: selectedPlugins });
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
          <RunStatusBadge status={status} idleLabel="Listo" />
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
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2">
                      <span className="block text-sm font-semibold text-ink">{plugin.label}</span>
                      <span className="rounded-full bg-surface px-2 py-0.5 text-[0.65rem] font-semibold text-muted">{plugin.category}</span>
                    </span>
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
          onClick={handleStartOcr}
          className="mt-4 w-full rounded-field bg-primary px-5 py-4 text-base font-semibold text-primary-contrast transition hover:bg-primary/85 disabled:opacity-60"
        >
          {buttonLabel({ isUploading, isProcessing, isLoadingResult })}
        </button>

        {isProcessing || isLoadingResult ? (
          <div className="mt-4 rounded-card bg-warning-soft p-4 text-sm font-semibold text-warning">
            {isLoadingResult ? "Preparando el asistente de corrección..." : "Leyendo secciones y validando inconsistencias..."}
          </div>
        ) : null}

        {pollStopped ? (
          <button
            type="button"
            onClick={retryPolling}
            className="mt-3 w-full rounded-field border border-warning/40 bg-warning-soft px-5 py-3 text-sm font-semibold text-warning transition hover:opacity-90"
          >
            Reintentar comprobación de estado
          </button>
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

function buttonLabel({ isUploading, isProcessing, isLoadingResult }: { isUploading: boolean; isProcessing: boolean; isLoadingResult: boolean }) {
  if (isUploading) return "Subiendo acta...";
  if (isLoadingResult) return "Abriendo corrección...";
  if (isProcessing) return "Procesando OCR...";
  return "Leer acta";
}
