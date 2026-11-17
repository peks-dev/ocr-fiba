import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

import { siteConfig } from "@/lib/env";

type MiddlewareAccount = {
  role: "admin" | "tester" | string;
  assigned_demo: "referee" | "player" | "club" | null;
  status?: string;
};

function matchesPrefix(path: string, prefix: string): boolean {
  return path === prefix || path.startsWith(`${prefix}/`);
}

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  if (!siteConfig.supabaseUrl || !siteConfig.supabaseAnonKey) {
    return supabaseResponse;
  }

  const supabase = createServerClient(siteConfig.supabaseUrl, siteConfig.supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        supabaseResponse = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => {
          supabaseResponse.cookies.set(name, value, options);
        });
      },
    },
  });

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const path = request.nextUrl.pathname;
  const isProtected =
    matchesPrefix(path, "/docs") || matchesPrefix(path, "/admin") || matchesPrefix(path, "/test");
  const isAuthPage = path === "/login";

  if (isProtected && !user) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", path);
    return NextResponse.redirect(url);
  }

  if (isAuthPage && user) {
    const account = await getAccountForUser(supabase, user.id);
    const destination = account && account.status === "active" ? destinationForMiddlewareAccount(account) : "/login";
    if (destination !== "/login") {
      const url = request.nextUrl.clone();
      url.pathname = destination;
      url.search = "";
      return NextResponse.redirect(url);
    }
  }

  return supabaseResponse;
}

async function getAccountForUser(supabase: ReturnType<typeof createServerClient>, userId: string) {
  const { data } = await supabase
    .from("accounts")
    .select("role,assigned_demo,status")
    .eq("supabase_user_id", userId)
    .maybeSingle();

  return data as MiddlewareAccount | null;
}

function destinationForMiddlewareAccount(account: MiddlewareAccount) {
  if (account.status && account.status !== "active") return "/login";
  if (account.role === "admin") return "/admin";
  if (account.assigned_demo === "referee") return "/test/referee";
  if (account.assigned_demo === "club") return "/test/club";
  if (account.assigned_demo === "player") return "/test/player";
  return "/login";
}
