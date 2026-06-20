import { createClient as createSupabaseClient } from "@supabase/supabase-js";

import { siteConfig } from "@/lib/env";

export function createAdminClient() {
  const supabaseUrl = process.env.SUPABASE_URL || siteConfig.supabaseUrl;
  const serviceKey = process.env.SUPABASE_SERVICE_KEY;

  if (!supabaseUrl || !serviceKey) {
    throw new Error("Missing SUPABASE_URL/NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_KEY");
  }

  return createSupabaseClient(supabaseUrl, serviceKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}
