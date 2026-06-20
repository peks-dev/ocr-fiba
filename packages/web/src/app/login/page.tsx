import { Suspense } from "react";

import { AuthCard } from "@/components/auth-card";

const flowSteps = [
  "Admin sends a Supabase invitation",
  "Tester creates a password from the invite link",
  "Account role and assigned demo gate access",
  "The demo runs OCR without exposing API keys",
];

export default function LoginPage() {
  return (
    <main className="grid min-h-screen lg:grid-cols-[1.05fr_0.95fr]">
      <section className="flex flex-col items-center justify-center gap-8 px-4 py-10 sm:px-6 sm:py-12">
        <div className="flex w-full max-w-md items-center gap-3 lg:hidden">
          <span className="grid size-10 place-items-center rounded-card bg-primary font-heading text-sm font-semibold text-primary-contrast">OCR</span>
          <div>
            <p className="font-heading font-semibold text-ink">FIBA OCR</p>
            <p className="text-xs text-muted">Turn scoresheets into structured data</p>
          </div>
        </div>

        <Suspense fallback={<div className="text-muted">Loading...</div>}>
          <AuthCard />
        </Suspense>
      </section>

      <section className="relative hidden overflow-hidden border-l border-border bg-inverse text-inverse-foreground lg:block">
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(circle at 30% 20%, color-mix(in oklab, var(--color-primary) 30%, transparent), transparent 32rem), radial-gradient(circle at 80% 10%, color-mix(in oklab, var(--color-accent) 18%, transparent), transparent 26rem)",
          }}
        />
        <div className="relative flex h-full flex-col justify-between p-12">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-primary">Local-first beta</p>
            <h2 className="mt-6 max-w-lg text-4xl font-semibold tracking-tight xl:text-5xl">Turn FIBA scoresheets into structured data.</h2>
            <p className="mt-6 max-w-md text-lg leading-8 text-inverse-foreground/75">
              This invite-only beta gives each tester access to one assigned demo while keeping admin controls separate.
            </p>
          </div>
          <div className="grid gap-4 rounded-panel border border-inverse-foreground/10 bg-inverse-foreground/10 p-6 backdrop-blur">
            {flowSteps.map((item) => (
              <div className="flex items-center gap-3" key={item}>
                <span className="size-2 rounded-full bg-primary" />
                <span className="text-sm text-inverse-foreground/85">{item}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
