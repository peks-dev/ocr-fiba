import { createClient } from "@/lib/supabase/server";
import { siteConfig } from "@/lib/env";

const apiExample = `curl -X POST "${siteConfig.apiBaseUrl}/v1/runs/upload" \\
  -H "Authorization: Bearer ocr_live_xxxxx" \\
  -F "file=@dataset/sheet-002/Panteras-vs-mambas.jpg"`;

const pollExample = `curl "${siteConfig.apiBaseUrl}/v1/runs/{run_id}" \\
  -H "Authorization: Bearer ocr_live_xxxxx"`;

const resultExample = `curl "${siteConfig.apiBaseUrl}/v1/runs/{run_id}/result" \\
  -H "Authorization: Bearer ocr_live_xxxxx"`;

const mcpExample = `{
  "mcpServers": {
    "fiba-ocr": {
      "url": "http://localhost:8001/mcp",
      "headers": {
        "Authorization": "Bearer ocr_live_xxxxx"
      }
    }
  }
}`;

function CodeBlock({ children }: { children: string }) {
  return <pre className="overflow-x-auto rounded-3xl border border-slate-200 bg-slate-950 p-5 text-sm leading-6 text-emerald-100 shadow-sm dark:border-slate-800"><code>{children}</code></pre>;
}

export default async function QuickstartPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <article className="space-y-8">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.22em] text-emerald-500">Quickstart</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950 dark:text-white">Use your OCR API key locally</h1>
        <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600 dark:text-slate-300">
          Signed in as <span className="font-semibold text-slate-900 dark:text-white">{user?.email}</span>. Generate a key in the dashboard, copy it once, then use it with the local API and MCP server.
        </p>
      </div>

      <section className="grid gap-5 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <h2 className="text-2xl font-semibold text-slate-950 dark:text-white">1. Start local services</h2>
        <CodeBlock>{`# API
uv run ocr-api

# MCP HTTP server, when validating MCP locally
uv run python mcp_server.py`}</CodeBlock>
      </section>

      <section className="grid gap-5 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <h2 className="text-2xl font-semibold text-slate-950 dark:text-white">2. Submit a scoresheet</h2>
        <CodeBlock>{apiExample}</CodeBlock>
      </section>

      <section className="grid gap-5 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <h2 className="text-2xl font-semibold text-slate-950 dark:text-white">3. Poll and fetch result</h2>
        <CodeBlock>{pollExample}</CodeBlock>
        <CodeBlock>{resultExample}</CodeBlock>
      </section>

      <section className="grid gap-5 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <h2 className="text-2xl font-semibold text-slate-950 dark:text-white">4. MCP local config</h2>
        <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">Use the generated API key as the bearer token for local MCP smoke testing.</p>
        <CodeBlock>{mcpExample}</CodeBlock>
      </section>
    </article>
  );
}
