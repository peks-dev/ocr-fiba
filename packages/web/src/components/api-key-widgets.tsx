"use client";

import { toast } from "sonner";

export function KeyStatusChip({ status }: { status: string }) {
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
        status === "active" ? "bg-success-soft text-success" : "bg-elevated text-muted"
      }`}
    >
      {status}
    </span>
  );
}

export function NewApiKeyBanner({
  apiKey,
  helperText,
  onDismiss,
}: {
  apiKey: string;
  helperText: string;
  onDismiss: () => void;
}) {
  return (
    <div className="rounded-panel border border-success/30 bg-success-soft p-5 text-ink shadow-sm sm:p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-success">Save this key now</p>
          <p className="mt-2 text-sm text-muted">{helperText}</p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-contrast transition hover:bg-primary/85"
              type="button"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(apiKey);
                  toast.success("API key copied to clipboard.");
                } catch {
                  toast.error("Could not copy automatically. Copy the key manually below.");
                }
              }}
            >
              Copy key
            </button>
          </div>
        </div>
        <button className="self-start text-sm font-semibold text-ink underline" onClick={onDismiss} type="button">
          Dismiss
        </button>
      </div>
      <code className="mt-4 block overflow-x-auto rounded-card bg-surface p-4 text-sm text-ink">{apiKey}</code>
    </div>
  );
}
