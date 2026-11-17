"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";

import { readDraft, writeDraft } from "./draft";
import { applySuggestion, gameTitle } from "./reconcile-utils";
import { computeReconciliation } from "./validation";
import { buildSheetSections, firstActionableSection, nextSectionId, type SheetSectionId } from "./sections";
import { ReconcileSectionEditor } from "./reconcile-sections";
import { DEFAULT_REFEREE_PLUGIN_IDS, pluginLabel } from "./plugins";
import type { OcrResult, Suggestion } from "./types";
import { EmptyState, Panel, StatusBanner } from "./ui";

const DEFAULT_BASE_PATH = "/test/referee";

export function ReconcileClient({ basePath = DEFAULT_BASE_PATH }: { basePath?: string }) {
  const [runId, setRunId] = useState<string | null>(null);
  const [result, setResult] = useState<OcrResult | null>(null);
  const [activeSectionId, setActiveSectionId] = useState<SheetSectionId | null>(null);
  const [validationPlugins, setValidationPlugins] = useState<string[]>(DEFAULT_REFEREE_PLUGIN_IDS);
  const [isBooting, setIsBooting] = useState(true);

  useEffect(() => {
    const draft = readDraft();
    if (draft) {
      setRunId(draft.runId);
      setResult(draft.result);
      setValidationPlugins(draft.validationPlugins?.length ? draft.validationPlugins : pluginsFromWarnings(draft.result));
    }
    setIsBooting(false);
  }, []);

  const summary = useMemo(() => (result ? computeReconciliation(result) : null), [result]);
  const sections = useMemo(() => (result && summary ? buildSheetSections(result, summary.issues) : []), [result, summary]);

  useEffect(() => {
    if (!result || !summary || activeSectionId) return;
    setActiveSectionId(firstActionableSection(buildSheetSections(result, summary.issues)));
  }, [activeSectionId, result, summary]);

  function update(next: OcrResult) {
    setResult(next);
    if (runId) writeDraft(runId, next, validationPlugins);
  }

  function onApply(suggestion: Suggestion) {
    if (!result) return;
    update(applySuggestion(result, suggestion));
    toast.success("Sugerencia aplicada.");
  }

  if (isBooting) return <Panel className="p-6 text-muted">Cargando acta...</Panel>;

  if (!result || !runId || !summary || !activeSectionId) {
    return (
      <Panel className="p-5 sm:p-6">
        <EmptyState
          title="No hay un acta en curso"
          description="Captura y extrae primero un acta. Luego podrás cuadrar los campos aquí."
          ctaHref={`${basePath}/capture`}
          ctaLabel="Ir a Capturar acta"
        />
      </Panel>
    );
  }

  const activeSection = sections.find((section) => section.id === activeSectionId) || sections[0];
  const nextId = nextSectionId(sections, activeSection.id);
  const reviewedCount = sections.filter((section) => section.issues.length === 0).length;

  return (
    <div className="mx-auto max-w-3xl space-y-4 pb-28 sm:space-y-6 sm:pb-0">
      <Panel className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18em] text-primary-deep">Corregir acta</p>
            <h2 className="mt-1 truncate text-lg font-semibold text-ink sm:text-2xl">{gameTitle(result)}</h2>
            <p className="mt-1 text-xs text-muted">
              {summary.totalCount === 0
                ? "No quedan observaciones. Puedes enviar el acta."
                : `${summary.totalCount} ${summary.totalCount === 1 ? "observación" : "observaciones"} · revisadas ${reviewedCount}/${sections.length} secciones`}
            </p>
          </div>
          <span className="shrink-0 rounded-full bg-elevated px-3 py-1 text-xs font-semibold text-muted">
            Paso 2/3
          </span>
        </div>
        <div className="mt-4">
          <StatusBanner status={summary.status} blockingCount={summary.blockingCount} />
        </div>
        {result.confidence ? <ConfidenceSummaryBar confidence={result.confidence} /> : null}
        <div className="mt-4 rounded-card border border-border bg-elevated p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-faint">Plugins usados en esta revisión</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {validationPlugins.map((plugin) => (
              <span key={plugin} className="rounded-full bg-surface px-3 py-1 text-xs font-semibold text-muted">
                {pluginLabel(plugin)}
              </span>
            ))}
          </div>
        </div>
      </Panel>

      <nav className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0" aria-label="Secciones del acta">
        {sections.map((section) => {
          const active = section.id === activeSection.id;
          const count = section.issues.length;
          return (
            <button
              key={section.id}
              type="button"
              onClick={() => setActiveSectionId(section.id)}
              className={`shrink-0 rounded-full border px-4 py-2 text-sm font-semibold transition ${
                active
                  ? "border-primary bg-primary text-primary-contrast"
                  : count > 0
                    ? "border-warning/40 bg-warning-soft text-warning"
                    : "border-border bg-surface text-muted"
              }`}
            >
              {section.shortLabel}
              {count > 0 ? <span className="ml-2 rounded-full bg-surface/80 px-2 py-0.5 text-xs text-ink">{count}</span> : null}
            </button>
          );
        })}
      </nav>

      <Panel className="p-4 sm:p-6">
        <div className="mb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-deep">Sección activa</p>
          <h3 className="mt-1 text-xl font-semibold text-ink">{activeSection.label}</h3>
          <p className="mt-1 text-sm text-muted">{activeSection.description}</p>
        </div>

        <ReconcileSectionEditor sectionId={activeSection.id} result={result} issues={activeSection.issues} onChange={update} />

        {activeSection.issues.some((issue) => issue.suggestion) ? (
          <div className="mt-5 space-y-2">
            {activeSection.issues.map((issue) =>
              issue.suggestion ? (
                <button
                  key={`${issue.id}-suggestion`}
                  type="button"
                  onClick={() => onApply(issue.suggestion!)}
                  className="w-full rounded-field bg-primary px-4 py-3 text-sm font-semibold text-primary-contrast transition hover:bg-primary/85"
                >
                  {issue.suggestion.label}
                </button>
              ) : null,
            )}
          </div>
        ) : null}
      </Panel>

      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-surface/95 p-4 shadow-2xl backdrop-blur sm:static sm:border-0 sm:bg-transparent sm:p-0 sm:shadow-none">
        {summary.blockingCount === 0 ? (
          <Link
            href={`${basePath}/submit`}
            className="block w-full rounded-field bg-ink px-5 py-3 text-center text-sm font-semibold text-background transition hover:bg-ink/85"
          >
            Enviar a la liga →
          </Link>
        ) : nextId ? (
          <button
            type="button"
            onClick={() => setActiveSectionId(nextId)}
            className="w-full rounded-field bg-ink px-5 py-3 text-sm font-semibold text-background transition hover:bg-ink/85"
          >
            Revisar siguiente sección →
          </button>
        ) : (
          <Link
            href={`${basePath}/submit`}
            className="block w-full rounded-field bg-warning px-5 py-3 text-center text-sm font-semibold text-background transition hover:opacity-90"
          >
            Enviar con observaciones →
          </Link>
        )}
      </div>
    </div>
  );
}


function ConfidenceSummaryBar({ confidence }: { confidence: NonNullable<OcrResult["confidence"]> }) {
  const score = typeof confidence.score === "number" ? Math.round(confidence.score * 100) : null;
  const level = confidence.level;
  const levelLabel = level === "high" ? "Alta" : level === "medium" ? "Media" : "Baja";
  const pillStyle =
    level === "high"
      ? "bg-success-soft text-success"
      : level === "medium"
        ? "bg-warning-soft text-warning"
        : "bg-danger-soft text-danger";

  const sectionLabels: { key: keyof NonNullable<NonNullable<OcrResult["confidence"]>["sections"]>; label: string }[] = [
    { key: "header", label: "Datos" },
    { key: "team_a", label: "Eq. A" },
    { key: "team_b", label: "Eq. B" },
    { key: "progressive_score", label: "Progresivo" },
    { key: "footer", label: "Cierre" },
  ];

  return (
    <div className="mt-3 rounded-card border border-border bg-elevated p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-faint">Confianza de extracción</p>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${pillStyle}`}>
          {score !== null ? `${score}% · ` : ""}
          {levelLabel}
        </span>
      </div>
      {confidence.sections ? (
        <div className="mt-2 flex flex-wrap gap-2">
          {sectionLabels.map(({ key, label }) => {
            const value = confidence.sections?.[key];
            if (typeof value !== "number") return null;
            return (
              <span key={key} className="rounded-full bg-surface px-2.5 py-1 text-xs text-muted">
                {label}: <strong className="text-ink">{Math.round(value * 100)}%</strong>
              </span>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function pluginsFromWarnings(result: OcrResult): string[] {
  const plugins = Array.from(
    new Set((result.validation_warnings || []).map((warning) => warning.plugin).filter((plugin): plugin is string => Boolean(plugin))),
  );
  return plugins.length ? plugins : DEFAULT_REFEREE_PLUGIN_IDS;
}
