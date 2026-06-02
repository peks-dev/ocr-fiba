import { NextResponse, type NextRequest } from "next/server";

import { createClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get("code");
  const next = getSafeNextPath(requestUrl.searchParams.get("next"));

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      return NextResponse.redirect(new URL(next, requestUrl.origin));
    }

    const loginUrl = new URL("/login", requestUrl.origin);
    loginUrl.searchParams.set("error", error.message);
    return NextResponse.redirect(loginUrl);
  }

  const loginUrl = new URL("/login", requestUrl.origin);
  loginUrl.searchParams.set("error", "Missing confirmation code. Please log in again.");
  return NextResponse.redirect(loginUrl);
}


function getSafeNextPath(value: string | null) {
  if (!value || !value.startsWith("/")) {
    return "/dashboard/api-keys";
  }

  // Disallow protocol-relative URLs like //evil.example.com.
  if (value.startsWith("//")) {
    return "/dashboard/api-keys";
  }

  return value;
}
