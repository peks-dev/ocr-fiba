import { createBrowserClient } from "@supabase/ssr";

import { assertBrowserEnv, siteConfig } from "@/lib/env";

export function createClient() {
  assertBrowserEnv();
  return createBrowserClient(siteConfig.supabaseUrl, siteConfig.supabaseAnonKey);
}
