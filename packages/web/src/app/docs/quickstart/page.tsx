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
  return <pre className="overflow-x-auto rounded-card bg-inverse p-4 text-sm leading-6 text-inverse-foreground shadow-sm sm:p-5"><code>{children}</code></pre>;
}

export default async function QuickstartPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <article className="space-y-6 sm:space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary-deep sm:text-sm">Quickstart</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Use your OCR API key locally</h1>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-muted sm:text-base sm:leading-7">
          Signed in as <span className="font-semibold text-ink">{user?.email}</span>. Generate a key in the dashboard, copy it once, then use it with the local API and MCP server.
        </p>
      </div>

      <section className="grid gap-5 rounded-panel border border-border bg-surface p-5 shadow-sm sm:p-6">
        <h2 className="text-xl font-semibold text-ink sm:text-2xl">1. Start local services</h2>
        <CodeBlock>{`# API
uv run ocr-api

# MCP HTTP server, when validating MCP locally
uv run python mcp_server.py`}</CodeBlock>
      </section>

      <section className="grid gap-5 rounded-panel border border-border bg-surface p-5 shadow-sm sm:p-6">
        <h2 className="text-xl font-semibold text-ink sm:text-2xl">2. Submit a scoresheet</h2>
        <CodeBlock>{apiExample}</CodeBlock>
      </section>

      <section className="grid gap-5 rounded-panel border border-border bg-surface p-5 shadow-sm sm:p-6">
        <h2 className="text-xl font-semibold text-ink sm:text-2xl">3. Poll and fetch result</h2>
        <CodeBlock>{pollExample}</CodeBlock>
        <CodeBlock>{resultExample}</CodeBlock>
      </section>

      <section className="grid gap-5 rounded-panel border border-border bg-surface p-5 shadow-sm sm:p-6">
        <h2 className="text-xl font-semibold text-ink sm:text-2xl">4. MCP local config</h2>
        <p className="text-sm leading-6 text-muted">Use the generated API key as the bearer token for local MCP smoke testing.</p>
        <CodeBlock>{mcpExample}</CodeBlock>
      </section>
    </article>
  );
}
