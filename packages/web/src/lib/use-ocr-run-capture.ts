"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { toast } from "sonner";

import { getRun, getRunResult, uploadRun, type RunRecord } from "@/lib/api";
import { ACCEPTED_IMAGE_TYPES, extractRunError } from "@/components/ocr-capture-ui";
import { useSupabaseSession } from "@/lib/supabase/use-session";

const POLL_INTERVAL_MS = 2200;
const MAX_CONSECUTIVE_POLL_ERRORS = 4;

export type CaptureMessages = {
  invalidFileType: string;
  noSession: string;
  noFileSelected: string;
  uploadStarted: string;
  uploadFailed: string;
  runFailed: string;
  pollFailed: string;
  resultFailed: string;
};

const DEFAULT_MESSAGES: CaptureMessages = {
  invalidFileType: "Please upload a JPG, PNG, or WEBP image.",
  noSession: "No active session. Please log in again.",
  noFileSelected: "Choose a scoresheet image first.",
  uploadStarted: "Scoresheet uploaded. OCR is running.",
  uploadFailed: "Upload failed.",
  runFailed: "OCR run failed.",
  pollFailed: "Could not refresh run status.",
  resultFailed: "Could not load OCR result.",
};

export function useOcrRunCapture<TResult>(options?: {
  messages?: Partial<CaptureMessages>;
  onResultLoaded?: (payload: { runId: string; result: TResult; silent?: boolean }) => void;
}) {
  const { session, isBooting } = useSupabaseSession();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [run, setRun] = useState<RunRecord | null>(null);
  const [result, setResult] = useState<TResult | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingResult, setIsLoadingResult] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pollTick, setPollTick] = useState(0);
  const [pollStopped, setPollStopped] = useState(false);

  const pollFailuresRef = useRef(0);
  const onResultLoadedRef = useRef(options?.onResultLoaded);
  onResultLoadedRef.current = options?.onResultLoaded;

  const messages: CaptureMessages = {
    ...DEFAULT_MESSAGES,
    ...(options?.messages || {}),
  };
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  const status = run?.status || "idle";
  const isProcessing = status === "queued" || status === "pending" || status === "running";

  const loadResult = useCallback(
    async (
      currentSession: Session | null = session,
      runId: string | undefined = run?.run_id,
      loadOptions: { silent?: boolean } = {},
    ) => {
      if (!currentSession || !runId) return null;
      setIsLoadingResult(true);
      setError(null);
      try {
        const nextResult = await getRunResult<TResult>(currentSession, runId);
        setResult(nextResult);
        onResultLoadedRef.current?.({ runId, result: nextResult, silent: loadOptions.silent });
        return nextResult;
      } catch (err) {
        const message = err instanceof Error ? err.message : messagesRef.current.resultFailed;
        setError(message);
        if (!loadOptions.silent) toast.error(message);
        return null;
      } finally {
        setIsLoadingResult(false);
      }
    },
    [run?.run_id, session],
  );

  useEffect(() => {
    if (!run?.run_id || !session || !isProcessing || pollStopped) return;
    const currentSession = session;
    const currentRunId = run.run_id;
    let cancelled = false;

    const failureAttempt = pollFailuresRef.current;
    const delayMs = failureAttempt > 0 ? POLL_INTERVAL_MS * (failureAttempt + 1) : POLL_INTERVAL_MS;

    async function poll() {
      try {
        const nextRun = await getRun(currentSession, currentRunId);
        if (cancelled) return;
        pollFailuresRef.current = 0;
        setError(null);
        setRun(nextRun);

        if (nextRun.status === "completed") {
          await loadResult(currentSession, nextRun.run_id, { silent: cancelled });
        } else if (nextRun.status === "failed") {
          toast.error(extractRunError(nextRun.error) || messagesRef.current.runFailed);
        }
      } catch (err) {
        if (cancelled) return;
        pollFailuresRef.current += 1;
        const message = err instanceof Error ? err.message : messagesRef.current.pollFailed;
        setError(message);
        if (pollFailuresRef.current >= MAX_CONSECUTIVE_POLL_ERRORS) {
          setPollStopped(true);
          toast.error(message);
        } else {
          setPollTick((tick) => tick + 1);
        }
      }
    }

    const timeout = window.setTimeout(poll, delayMs);
    return () => {
      cancelled = true;
      window.clearTimeout(timeout);
    };
  }, [isProcessing, loadResult, pollStopped, pollTick, run, session]);

  function onFileChange(file: File | null) {
    if (!file) return;
    if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
      toast.error(messagesRef.current.invalidFileType);
      return;
    }
    pollFailuresRef.current = 0;
    setPollStopped(false);
    setSelectedFile(file);
    setRun(null);
    setResult(null);
    setError(null);
  }

  function retryPolling() {
    pollFailuresRef.current = 0;
    setPollStopped(false);
    setError(null);
    setPollTick((tick) => tick + 1);
  }

  async function startOcr(uploadOptions?: { validationPlugins?: string[] | "all" }) {
    if (!session) {
      toast.error(messagesRef.current.noSession);
      return null;
    }
    if (!selectedFile) {
      toast.error(messagesRef.current.noFileSelected);
      return null;
    }

    pollFailuresRef.current = 0;
    setPollStopped(false);
    setIsUploading(true);
    setError(null);
    setResult(null);

    try {
      const response = await uploadRun(session, selectedFile, uploadOptions);
      setRun(response);
      if (response.status === "completed") {
        await loadResult(session, response.run_id);
      } else {
        toast.success(messagesRef.current.uploadStarted);
      }
      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : messagesRef.current.uploadFailed;
      setError(message);
      toast.error(message);
      return null;
    } finally {
      setIsUploading(false);
    }
  }

  return {
    session,
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
  };
}
