import type { Metadata } from "next";

import { DemoTabs } from "@/components/club-demo/demo-tabs";

export const metadata: Metadata = {
  title: "Club Analysis Tracker · FIBA OCR",
  description: "Track roster performance from FIBA scoresheets and discover player trends over time.",
};

export default function ClubDemoLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="space-y-6 sm:space-y-8">
      <section className="overflow-hidden rounded-panel border border-border bg-inverse text-inverse-foreground shadow-sm">
        <div className="relative p-5 sm:p-8">
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(circle at 82% 0%, color-mix(in oklab, var(--color-primary) 24%, transparent), transparent 24rem), radial-gradient(circle at 10% 20%, color-mix(in oklab, var(--color-accent) 14%, transparent), transparent 20rem)",
            }}
          />
          <div className="relative">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Club Analysis Tracker · Demo</p>
            <h1 className="mt-3 max-w-3xl text-2xl font-semibold tracking-tight sm:text-3xl md:text-4xl">
              Turn game sheets into a roster performance dashboard.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-inverse-foreground/75">
              Import a first FIBA scoresheet to create the roster from player names automatically, then track who is scoring, trending up, or staying consistent across games.
            </p>
            <DemoTabs />
          </div>
        </div>
      </section>
      {children}
    </div>
  );
}
