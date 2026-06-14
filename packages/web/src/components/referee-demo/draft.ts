// Working-acta handoff between capture → reconcile → submit, via sessionStorage.
// The draft holds the editable OCR result for the current run.

import type { OcrResult, RefereeDraft } from "./types";

export const REFEREE_DRAFT_KEY = "fiba-ocr:referee-demo:draft:v1";

export function readDraft(): RefereeDraft | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(REFEREE_DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<RefereeDraft>;
    if (!parsed || typeof parsed.runId !== "string" || !parsed.result) return null;
    return {
      runId: parsed.runId,
      result: parsed.result as OcrResult,
      updatedAt: parsed.updatedAt || "",
      validationPlugins: Array.isArray(parsed.validationPlugins) ? parsed.validationPlugins.filter((plugin): plugin is string => typeof plugin === "string") : undefined,
    };
  } catch {
    return null;
  }
}

export function writeDraft(runId: string, result: OcrResult, validationPlugins?: string[]): void {
  if (typeof window === "undefined") return;
  const draft: RefereeDraft = { runId, result, updatedAt: new Date().toISOString(), validationPlugins };
  window.sessionStorage.setItem(REFEREE_DRAFT_KEY, JSON.stringify(draft));
}

export function clearDraft(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(REFEREE_DRAFT_KEY);
}
