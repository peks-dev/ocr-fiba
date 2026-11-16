# packages/web

Next.js 15 App Router UI for the FIBA OCR engine: invite-only login, admin invitations and API keys, and tester demos. The browser talks to the public OCR API over HTTP and authenticates run requests with the signed-in Supabase session JWT. Service-to-service clients use `ocr_live_` keys instead.

## Local development

```bash
cp .env.local.example .env.local
npm install
npm run dev
# → http://localhost:3000
```

## Deploy on Vercel

This package is designed to build as a standalone Next.js app in the monorepo. In the Vercel project:

1. Set **Root Directory** to `packages/web`.
2. Leave the build command as the default (`npm run build` / Next.js preset). No `vercel.json` is required.
3. Configure the environment variables below. Then deploy.

After the first successful deploy, copy the production URL (for example `https://<project>.vercel.app`) and set `OCR_CORS_ORIGINS` on the Cloud Run API to that origin (comma-separated if you also include preview URLs). `parse_cors_origins` already accepts a list. `scripts/deploy_cloudrun.sh` passes `OCR_CORS_ORIGINS` through when the variable is set; Cloud Build image deploys do not change env vars, so this is a one-time (or occasional) service update.

### Required environment variables

| Name | Where | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Browser + server | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Browser + server | Legacy anon key. Alternative: `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` |
| `NEXT_PUBLIC_OCR_API_URL` | Browser + server | Production API: `https://ocr-api-676774806036.us-central1.run.app` |
| `SUPABASE_SERVICE_KEY` | Server only | Service-role key for admin/invite server routes. Never prefix with `NEXT_PUBLIC_`. |

### Optional environment variables

| Name | Where | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Browser + server | Used if `NEXT_PUBLIC_SUPABASE_ANON_KEY` is unset |
| `AIRTABLE_TOKEN` | Server only | Referee league view. The route returns a friendly error if unset. |
| `AIRTABLE_BASE_ID` | Server only | Same as above |
| `AIRTABLE_LEAGUE_TABLE` | Server only | Same as above |
| `SUPABASE_URL` | Server only | Optional override of the public Supabase URL for the admin client |

Do not add `OCR_ENGINE_API_KEY` or raw `ocr_live_` keys to the Vercel project. Testers and admins use their session JWT; keys are issued in the admin panel for MCP or other service clients.
