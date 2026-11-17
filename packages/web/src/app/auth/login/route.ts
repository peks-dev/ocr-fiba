import { NextResponse, type NextRequest } from "next/server";

import { destinationForAccount } from "@/lib/auth/account";
import { createClient } from "@/lib/supabase/server";

type LoginPayload = {
  email?: unknown;
  password?: unknown;
  next?: unknown;
};

export async function POST(request: NextRequest) {
  let payload: LoginPayload;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid login request." }, { status: 400 });
  }

  const email = typeof payload.email === "string" ? payload.email.trim() : "";
  const password = typeof payload.password === "string" ? payload.password : "";
  const next = getSafeNextPath(typeof payload.next === "string" ? payload.next : null);

  if (!email || !password) {
    return NextResponse.json({ error: "Email and password are required." }, { status: 400 });
  }

  const supabase = await createClient();
  const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });

  if (signInError) {
    return NextResponse.json({ error: signInError.message }, { status: 401 });
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Login succeeded but session could not be verified." }, { status: 401 });
  }

  const { data: account } = await supabase
    .from("accounts")
    .select("role,assigned_demo,status")
    .eq("supabase_user_id", user.id)
    .maybeSingle();

  if (!account) {
    await supabase.auth.signOut();
    return NextResponse.json({ error: "Your product account is not ready yet. Ask the admin to verify your invite." }, { status: 403 });
  }

  if (account.status !== "active") {
    await supabase.auth.signOut();
    return NextResponse.json({ error: "This account is inactive. Contact an administrator." }, { status: 403 });
  }

  return NextResponse.json({ destination: next || destinationForAccount(account) });
}

function getSafeNextPath(value: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return null;
  return value;
}
