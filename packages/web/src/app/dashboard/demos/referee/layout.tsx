import type { Metadata } from "next";

import { DemoTabs } from "@/components/referee-demo/demo-tabs";

export const metadata: Metadata = {
  title: "Arbitros Helper · FIBA OCR",
  description: "Cierra el acta del partido: extrae con OCR, cuadra los campos y envía datos estructurados a la liga.",
};

export default function RefereeDemoLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="space-y-4 sm:space-y-8">
      <section className="overflow-hidden rounded-panel border border-border bg-inverse text-inverse-foreground shadow-sm">
        <div className="relative p-4 sm:p-8">
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(circle at 85% 0%, color-mix(in oklab, var(--color-primary) 22%, transparent), transparent 24rem)",
            }}
          />
          <div className="relative">
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-primary sm:text-xs">Arbitros Helper · Demo</p>
            <h1 className="mt-2 max-w-3xl text-2xl font-semibold tracking-tight sm:mt-3 sm:text-3xl md:text-4xl">
              Cierra el acta y envíala a la liga.
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-inverse-foreground/75 sm:mt-3">
              Sube la hoja, revisa solo las secciones problemáticas y manda los datos estructurados en minutos.
            </p>
            <DemoTabs />
          </div>
        </div>
      </section>
      {children}
    </div>
  );
}
