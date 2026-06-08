# web — AGENTS.md

> Domain-specific guidance for AI agents working on `packages/web/`.
> Cross-cutting rules live in [`/AGENTS.md`](../../../AGENTS.md). Read both before editing.

## Context

Next.js 15 dashboard for the FIBA OCR engine. Currently ships a minimal Supabase-authenticated dashboard for managing API keys and a `/docs/quickstart` page. Future DEMO pages (single-player stats, referee helper, club analysis) will live here too.

## Stack

- Next.js 15 (App Router)
- React 19
- Tailwind CSS v4 (`@tailwindcss/postcss`)
- Supabase SSR (`@supabase/ssr`) + `@supabase/supabase-js`
- `sonner` for toast notifications
- TypeScript 5
- ESLint 9 with `eslint-config-next`

## Structure

```text
packages/web/
├── package.json
├── next.config.ts (if present)
└── src/
    ├── app/
    │   ├── layout.tsx              # Root layout + global metadata
    │   ├── page.tsx                # Public landing
    │   ├── globals.css             # Tailwind entry
    │   ├── login/page.tsx          # Login + signup (AuthCard)
    │   ├── auth/callback/route.ts  # Supabase email-confirmation code exchange
    │   ├── dashboard/
    │   │   ├── layout.tsx          # Auth gate: redirects to /login if no user
    │   │   └── api-keys/page.tsx   # ApiKeysPanel
    │   └── docs/
    │       ├── layout.tsx
    │       └── quickstart/         # Public quickstart (does not require login)
    ├── components/
    │   ├── nav.tsx                 # Signed-in navigation (logout via Supabase)
    │   ├── auth-card.tsx           # Email/password signup & login
    │   ├── api-keys-panel.tsx      # Bootstrap / list / delete API keys
    │   └── …
    └── lib/
        ├── api.ts                  # Fetch helpers for the OCR API (bearer)
        ├── env.ts                  # Typed NEXT_PUBLIC_* env access
        ├── site.ts                 # siteConfig (URLs, branding)
        └── supabase/
            ├── server.ts           # createClient (RSC) — cookie-based session
            └── client.ts           # createClient (browser) — for client components
```

## Patterns

### 1. App Router only, RSC by default

- No `pages/` directory.
- Components are server components unless they need state, effects, or browser APIs — then add `'use client'` at the top.
- All Supabase I/O goes through `lib/supabase/server.ts` (RSC) or `lib/supabase/client.ts` (client). **Never** instantiate `createClient` directly in a component or page.

### 2. Auth gate lives in `dashboard/layout.tsx`

`app/dashboard/layout.tsx` is the **only** place that checks for a Supabase user on the server. If `user` is null, it calls `redirect("/login")`. Individual pages under `dashboard/*` do not re-check auth.

```tsx
// src/app/dashboard/layout.tsx — pattern
const supabase = await createClient();
const { data: { user } } = await supabase.auth.getUser();
if (!user) redirect("/login");
```

### 3. API calls go through `lib/api.ts`

Browser-side API calls use the helpers in `lib/api.ts`, which attach the API key as `Authorization: Bearer ocr_...`. The key is supplied by the dashboard UI (loaded server-side in the page that owns the keys list).

### 4. Toasts via `sonner`

UI feedback uses `sonner`. There's a global `AppToaster` mounted in the root layout. To show a toast from a client component:

```tsx
import { toast } from "sonner";
toast.success("API key created");
toast.error(error.message);
```

Follow the same pattern in `components/nav.tsx` (logout).

### 5. Public docs live under `app/docs/*`

The quickstart (`/docs/quickstart`) is intentionally public — no auth. To add a new public doc, create `app/docs/<slug>/page.tsx` and reuse `app/docs/layout.tsx`.

### 6. Avoid infinite re-fetch loops in client effects

A common bug in this app: an effect depending on `session`/`refresh` triggers a request loop. The pattern used in `api-keys-panel.tsx` is:

- Load session and keys **once per mount** with an empty `useEffect` dependency list.
- Refresh on explicit user actions (create/delete), not on focus or session ticks.

## Rules specific to web

- **NEVER** add `pages/`. App Router only.
- **NEVER** put a Supabase client instance at module scope. Always go through `lib/supabase/*`.
- **NEVER** store an API key in localStorage or any client-side storage. The key is fetched per session from the server.
- **NEVER** redirect on the client when the layout already redirects on the server.
- New env vars prefixed with `NEXT_PUBLIC_` must be added to `lib/env.ts` with a typed accessor.
- Components should not block the dashboard render waiting for non-essential data. Use `<Suspense>` with a fallback.

## Auto-invoke skills (per task)

| Task | Skill |
|---|---|
| Adding/editing Next.js code | `next-best-practices` + `vercel-react-best-practices` |
| Performance optimization | `react-performance-optimization` |
| Tailwind / design tokens | `design-tailwind-system` |
| Motion / animation | `design-motion-animation` + the appropriate `library-gsap-*` skill |
| Pre-completion security check (new data surfaces, dynamic URLs, metadata) | `audit-security-implementation` |
| Git operations | `git-commit-creation` |

## References

- `app/dashboard/layout.tsx` — auth gate
- `lib/supabase/server.ts` — RSC Supabase client
- `lib/supabase/client.ts` — browser Supabase client
- `components/api-keys-panel.tsx` — fetch-once pattern for client effects
- `components/nav.tsx` — `signOut` + toast pattern
- `app/docs/quickstart/` — public docs structure
