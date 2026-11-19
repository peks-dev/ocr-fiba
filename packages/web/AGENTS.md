# web — AGENTS.md

> Local guardrails for `packages/web/` (`web`).
> Read [`/AGENTS.md`](../../AGENTS.md) and [`/docs/codebase/adapters-and-web.md`](../../docs/codebase/adapters-and-web.md) before modifying code here.

## Context & Stack

Next.js 15 App Router + React 19 + Tailwind CSS v4 + `@supabase/ssr` + `sonner` + TypeScript 5. Separates `/admin` (invites + API key management), `/test/{player,referee,club}` invite-only demos, `/api/league/submissions` (server-side Airtable proxy), and authenticated `/docs/quickstart`. Calls `ocr-engine-api` over HTTPS via `src/lib/api.ts`.

## Local Verification

```bash
npm --prefix packages/web run lint
npm --prefix packages/web test
npm --prefix packages/web run build
```

## Non-Negotiable Rules (`NEVER`)

- **NEVER** add `pages/` routes; App Router (`src/app/`) only.
- **NEVER** instantiate Supabase `createClient` directly inside components; use `src/lib/supabase/{server,client,admin,middleware}.ts`.
- **NEVER** store `ocr_live_` keys or `SUPABASE_SERVICE_KEY` / `AIRTABLE_TOKEN` in client storage or `NEXT_PUBLIC_*` env vars.
- **NEVER** duplicate layout auth checks inside individual pages under `/admin/*` or `/test/{demo}/*` (layouts call `requireAdminAccount()` / `requireDemoAccess()`).
- **NEVER** trigger client `useEffect` loops depending on unstable session objects; fetch once on mount and refresh explicitly on mutations.

## Pointers

- Web architecture & auth gates: [`docs/codebase/adapters-and-web.md`](../../docs/codebase/adapters-and-web.md)
- Local setup & Vercel deploy: [`packages/web/README.md`](./README.md) · [`docs/DEPLOYMENT.md`](../../docs/DEPLOYMENT.md)
