import type { Metadata } from "next";

import { DemoTabs } from "@/components/single-player-demo/demo-tabs";

export const metadata: Metadata = {
  title: "Single Player Improve · FIBA OCR",
  description: "Capture games from FIBA scoresheets and track your personal progress over time.",
};

export default function SinglePlayerDemoLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="space-y-6 sm:space-y-8">
      <section className="overflow-hidden rounded-panel border border-border bg-inverse text-inverse-foreground shadow-sm">
        <div className="relative p-5 sm:p-8">
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(circle at 85% 0%, color-mix(in oklab, var(--color-primary) 22%, transparent), transparent 24rem)",
            }}
          />
          <div className="relative">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Single Player Improve · Demo</p>
            <h1 className="mt-3 max-w-3xl text-2xl font-semibold tracking-tight sm:text-3xl md:text-4xl">
              Understand your game, one scoresheet at a time.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-inverse-foreground/75">
              Capture your games from FIBA scoresheets, see your points and fouls at a glance, and follow your averages
              over time to find out if you are improving and what to work on next.
            </p>
            <DemoTabs />
          </div>
        </div>
      </section>
      {children}
    </div>
  );
}
