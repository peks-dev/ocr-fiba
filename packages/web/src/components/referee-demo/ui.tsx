import Link from "next/link";

import type { IssueSeverity } from "./types";

export function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`rounded-panel border border-border bg-surface shadow-sm ${className}`}>{children}</section>;
}

export function EmptyState({
  title,
  description,
  ctaHref,
  ctaLabel,
}: {
  title: string;
  description: string;
  ctaHref?: string;
  ctaLabel?: string;
}) {
  return (
    <div className="rounded-card border border-dashed border-border p-8 text-center sm:p-10">
      <p className="text-base font-semibold text-ink">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted">{description}</p>
      {ctaHref && ctaLabel ? (
        <Link
          href={ctaHref}
          className="mt-5 inline-block rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-contrast transition hover:bg-primary/85"
        >
          {ctaLabel}
        </Link>
      ) : null}
    </div>
  );
}

export function SeverityChip({ severity }: { severity: IssueSeverity }) {
  const styles: Record<IssueSeverity, string> = {
    critical: "bg-danger-soft text-danger",
    high: "bg-danger-soft text-danger",
    medium: "bg-warning-soft text-warning",
    low: "bg-elevated text-muted",
  };
  const label: Record<IssueSeverity, string> = {
    critical: "Crítico",
    high: "Por cuadrar",
    medium: "Revisar",
    low: "Menor",
  };
  return <span className={`rounded-full px-3 py-1 text-xs font-semibold ${styles[severity]}`}>{label[severity]}</span>;
}

export function StatusBanner({ status, blockingCount }: { status: "cuadrada" | "con_observaciones"; blockingCount: number }) {
  if (status === "cuadrada") {
    return (
      <div className="flex items-center gap-3 rounded-card bg-success-soft px-4 py-3 text-sm font-semibold text-success">
        <CheckIcon />
        Acta cuadrada. Lista para enviar a la liga.
      </div>
    );
  }
  return (
    <div className="flex items-center gap-3 rounded-card bg-warning-soft px-4 py-3 text-sm font-semibold text-warning">
      <AlertIcon />
      {blockingCount} {blockingCount === 1 ? "campo" : "campos"} por cuadrar antes de enviar.
    </div>
  );
}

export function NumberField({
  label,
  value,
  onChange,
  className = "",
  highlighted = false,
}: {
  label: string;
  value: number | null;
  onChange: (value: number | null) => void;
  className?: string;
  highlighted?: boolean;
}) {
  return (
    <label className={`block ${className}`}>
      <span className="text-[0.65rem] font-semibold uppercase tracking-wide text-faint">{label}</span>
      <input
        type="number"
        inputMode="numeric"
        value={value ?? ""}
        onChange={(event) => {
          const raw = event.target.value;
          onChange(raw === "" ? null : Number(raw));
        }}
        className={`mt-1 w-full rounded-field border bg-surface px-3 py-3 text-base text-ink outline-none transition focus:border-primary sm:py-2 sm:text-sm ${highlighted ? "border-warning bg-warning-soft/40" : "border-border"}`}
      />
    </label>
  );
}

export function TextField({
  label,
  value,
  onChange,
  placeholder,
  className = "",
  highlighted = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  highlighted?: boolean;
}) {
  return (
    <label className={`block ${className}`}>
      <span className="text-[0.65rem] font-semibold uppercase tracking-wide text-faint">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className={`mt-1 w-full rounded-field border bg-surface px-3 py-3 text-base text-ink outline-none transition focus:border-primary sm:py-2 sm:text-sm ${highlighted ? "border-warning bg-warning-soft/40" : "border-border"}`}
      />
    </label>
  );
}

export function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="size-4 shrink-0" aria-hidden="true">
      <path d="M5 13l4 4 10-10" />
    </svg>
  );
}

export function AlertIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="size-4 shrink-0" aria-hidden="true">
      <path d="M12 9v4" />
      <path d="M12 17h.01" />
      <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
    </svg>
  );
}
