import Link from "next/link";

import { RunStatusBadge } from "@/components/ocr-capture-ui";

export function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`rounded-panel border border-border bg-surface shadow-sm ${className}`}>{children}</section>;
}

export function EmptyState({ title, description, ctaHref, ctaLabel }: { title: string; description: string; ctaHref?: string; ctaLabel?: string }) {
  const safeHref = ctaHref?.startsWith("/") ? ctaHref : undefined;
  return (
    <div className="rounded-card border border-dashed border-border p-8 text-center sm:p-10">
      <p className="text-base font-semibold text-ink">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">{description}</p>
      {safeHref && ctaLabel ? (
        <Link href={safeHref} className="mt-5 inline-block rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-contrast transition hover:bg-primary/85">
          {ctaLabel}
        </Link>
      ) : null}
    </div>
  );
}

export function ResultChip({ label }: { label: string }) {
  const styles = label === "Win" ? "bg-success-soft text-success" : label === "Loss" ? "bg-danger-soft text-danger" : "bg-elevated text-muted";
  return <span className={`rounded-full px-3 py-1 text-xs font-semibold ${styles}`}>{label}</span>;
}

export function MiniStat({ label, value, hint }: { label: string; value: number | string; hint?: string }) {
  return (
    <div className="rounded-card border border-border bg-elevated p-4">
      <p className="text-2xl font-black text-ink sm:text-3xl">{value}</p>
      <p className="mt-1 text-[0.65rem] font-semibold uppercase tracking-wide text-faint">{label}</p>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return <RunStatusBadge status={status} idleLabel={status} capitalize={false} />;
}
