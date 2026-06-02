import { Suspense } from "react";

import { AuthCard } from "@/components/auth-card";

export default function LoginPage() {
  return (
    <main className="grid min-h-screen lg:grid-cols-[1.1fr_0.9fr]">
      <section className="flex items-center justify-center px-6 py-12">
        <Suspense fallback={<div className="text-slate-500">Loading...</div>}>
          <AuthCard />
        </Suspense>
      </section>
      <section className="relative hidden overflow-hidden border-l border-slate-200 bg-slate-950 text-white lg:block dark:border-slate-800">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(52,211,153,0.30),transparent_32rem),radial-gradient(circle_at_80%_10%,rgba(56,189,248,0.18),transparent_26rem)]" />
        <div className="relative flex h-full flex-col justify-between p-12">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-emerald-300">Local-first beta</p>
            <h2 className="mt-6 max-w-lg text-5xl font-semibold tracking-tight">Turn FIBA scoresheets into structured data.</h2>
            <p className="mt-6 max-w-md text-lg leading-8 text-slate-300">
              This minimal dashboard validates signup, account provisioning, API key generation, and service auth before deployment.
            </p>
          </div>
          <div className="grid gap-4 rounded-3xl border border-white/10 bg-white/10 p-6 backdrop-blur">
            {[
              "Supabase Auth creates the beta user session",
              "Database trigger provisions the account row",
              "FastAPI issues hashed OCR API keys",
              "Quickstart documents API and MCP usage",
            ].map((item) => (
              <div className="flex items-center gap-3" key={item}>
                <span className="size-2 rounded-full bg-emerald-300" />
                <span className="text-sm text-slate-200">{item}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
