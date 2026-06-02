import { ApiKeysPanel } from "@/components/api-keys-panel";

export default function ApiKeysPage() {
  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.22em] text-emerald-500">Dashboard</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950 dark:text-white">Manage API access</h1>
        <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600 dark:text-slate-300">
          Create and delete API keys for local FastAPI testing. Use these keys with <code className="rounded bg-slate-100 px-1.5 py-0.5 dark:bg-slate-900">Authorization: Bearer</code> on OCR run endpoints.
        </p>
      </div>
      <ApiKeysPanel />
    </div>
  );
}
