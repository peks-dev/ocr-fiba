# packages/web

Next.js 15 App Router UI for the FIBA OCR Engine: invite-only login, admin invitations and API key management, and role-gated tester demos (`/test/player`, `/test/referee`, `/test/club`). Browser OCR calls send the user's Supabase session JWT over HTTPS to `NEXT_PUBLIC_OCR_API_URL`.

For auth gates, route structure, and Vercel deployment + CORS follow-up details, see:
- [Adapters and Web (`docs/codebase/adapters-and-web.md`)](../../docs/codebase/adapters-and-web.md#3-web-app-packagesweb-nextjs-15-app-router)
- [Deployment and Operations (`docs/DEPLOYMENT.md`)](../../docs/DEPLOYMENT.md#3-web-app-on-vercel-packagesweb)

## Local development

```bash
cp .env.local.example .env.local   # fill Supabase and API URL values
npm install
npm run dev
# -> http://localhost:3000
```

## Lint, test, and build

```bash
npm --prefix packages/web run lint
npm --prefix packages/web test
npm --prefix packages/web run build
```

## Key environment variables

- **Required:** `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` (or `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`), `NEXT_PUBLIC_OCR_API_URL`, `SUPABASE_SERVICE_KEY` (server-only).
- **Optional:** `NEXT_PUBLIC_SITE_URL`, `AIRTABLE_TOKEN`, `AIRTABLE_BASE_ID`, `AIRTABLE_LEAGUE_TABLE` (server-only, used by `/api/league/submissions`).

Never add `OCR_ENGINE_API_KEY` or `ocr_live_` keys to Vercel or browser storage.
