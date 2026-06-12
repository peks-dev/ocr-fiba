import { ApiKeysPanel } from "@/components/api-keys-panel";

export default function ApiKeysPage() {
  return (
    <div className="space-y-6 sm:space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary-deep sm:text-sm">Dashboard</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Manage API access</h1>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-muted sm:text-base sm:leading-7">
          Create and delete API keys for local FastAPI testing. Use these keys with <code className="rounded bg-elevated px-1.5 py-0.5">Authorization: Bearer</code> on OCR run endpoints.
        </p>
      </div>
      <ApiKeysPanel />
    </div>
  );
}
