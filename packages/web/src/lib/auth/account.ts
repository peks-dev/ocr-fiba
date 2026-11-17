import { redirect } from "next/navigation";

import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";

export const DEMOS = ["referee", "player", "club"] as const;
export type AssignedDemo = (typeof DEMOS)[number];
export type AccountRole = "admin" | "tester";

export type Account = {
  id: string;
  supabase_user_id: string | null;
  email: string;
  role: AccountRole;
  status: string;
  assigned_demo: AssignedDemo | null;
  invited_by: string | null;
  invited_at: string | null;
  accepted_at: string | null;
};

export type CurrentUserAccount = {
  user: { id: string; email?: string };
  account: Account;
};

export type AccountLookupResult =
  | { state: "ok"; current: CurrentUserAccount }
  | { state: "unauthenticated" }
  | { state: "missing" }
  | { state: "inactive" };

export type DemoApiAccessResult =
  | { ok: true; current: CurrentUserAccount }
  | { ok: false; status: 401 | 403; error: string };

export const demoHomePaths: Record<AssignedDemo, string> = {
  referee: "/test/referee",
  player: "/test/player",
  club: "/test/club",
};


export function isAssignedDemo(value: string | null | undefined): value is AssignedDemo {
  return DEMOS.includes(value as AssignedDemo);
}

export function destinationForAccount(account: Pick<Account, "role" | "assigned_demo">) {
  if (account.role === "admin") return "/admin";
  if (account.assigned_demo && isAssignedDemo(account.assigned_demo)) return demoHomePaths[account.assigned_demo];
  return "/login?error=No%20demo%20assigned";
}

export async function lookupCurrentUserAccount(): Promise<AccountLookupResult> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) return { state: "unauthenticated" };

  const { data: account, error } = await supabase
    .from("accounts")
    .select("id,supabase_user_id,email,role,status,assigned_demo,invited_by,invited_at,accepted_at")
    .eq("supabase_user_id", user.id)
    .single();

  if (error || !account) return { state: "missing" };
  if (account.status !== "active") return { state: "inactive" };

  return {
    state: "ok",
    current: { user: { id: user.id, email: user.email }, account: account as Account },
  };
}

export async function getCurrentUserAccount(): Promise<CurrentUserAccount | null> {
  const result = await lookupCurrentUserAccount();
  return result.state === "ok" ? result.current : null;
}

export async function requireCurrentUserAccount() {
  const result = await lookupCurrentUserAccount();
  if (result.state === "inactive") redirect("/login?error=Account%20inactive");
  if (result.state === "missing") redirect("/login?error=Account%20not%20provisioned");
  if (result.state !== "ok") redirect("/login");
  return result.current;
}

export async function authorizeDemoApiAccess(demo: AssignedDemo): Promise<DemoApiAccessResult> {
  const result = await lookupCurrentUserAccount();
  if (result.state === "unauthenticated") {
    return { ok: false, status: 401, error: "No autenticado." };
  }
  if (result.state === "inactive") {
    return { ok: false, status: 403, error: "Tu cuenta está inactiva." };
  }
  if (result.state !== "ok") {
    return { ok: false, status: 403, error: "Tu cuenta aún no está aprovisionada." };
  }
  const { account } = result.current;
  if (account.role !== "admin" && account.assigned_demo !== demo) {
    return { ok: false, status: 403, error: "No tienes acceso a esta demo." };
  }
  return { ok: true, current: result.current };
}

export async function requireAdminAccount() {
  const current = await requireCurrentUserAccount();
  if (current.account.role !== "admin") redirect(destinationForAccount(current.account));
  return current;
}

export async function requireDemoAccess(demo: AssignedDemo) {
  const current = await requireCurrentUserAccount();
  if (current.account.role === "admin") return current;
  if (current.account.assigned_demo !== demo) redirect(destinationForAccount(current.account));
  return current;
}

export async function markCurrentAccountAccepted(userId: string) {
  const admin = createAdminClient();
  const now = new Date().toISOString();

  const { data: existing } = await admin
    .from("accounts")
    .select("id,email,role,status,assigned_demo,accepted_at")
    .eq("supabase_user_id", userId)
    .maybeSingle();

  if (!existing || existing.status !== "active") return null;

  const account = existing.accepted_at
    ? existing
    : (
        await admin
          .from("accounts")
          .update({ accepted_at: now })
          .eq("supabase_user_id", userId)
          .select("id,email,role,status,assigned_demo,accepted_at")
          .maybeSingle()
      ).data || existing;

  if (account.email) {
    await admin
      .from("admin_invitations")
      .update({ status: "accepted", accepted_at: account.accepted_at || now, invited_user_id: userId, updated_at: now })
      .eq("email", account.email)
      .eq("status", "invited");
  }

  return account as Pick<Account, "id" | "email" | "role" | "assigned_demo"> | null;
}
