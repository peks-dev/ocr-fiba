export const siteConfig = {
  apiBaseUrl: process.env.NEXT_PUBLIC_OCR_API_URL || "http://localhost:8000",
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL || "",
  supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "",
};

export function assertBrowserEnv() {
  if (!siteConfig.supabaseUrl || !siteConfig.supabaseAnonKey) {
    throw new Error("Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY");
  }
}
