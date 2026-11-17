import { revalidatePath } from "next/cache";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { DEMOS, requireAdminAccount, type AssignedDemo } from "@/lib/auth/account";
import { resolveAppOrigin } from "@/lib/auth/origin";
import { createAdminClient } from "@/lib/supabase/admin";

const demoLabels: Record<AssignedDemo, string> = {
  referee: "Referee helper",
  player: "Single player",
  club: "Club analysis",
};

export default async function AdminPage({ searchParams }: { searchParams: Promise<{ error?: string; invited?: string }> }) {
  const [{ account }, params] = await Promise.all([requireAdminAccount(), searchParams]);
  const admin = createAdminClient();
  const [{ data: invitations }, { data: accounts }] = await Promise.all([
    admin
      .from("admin_invitations")
      .select("id,email,assigned_demo,status,created_at,accepted_at,error_message")
      .order("created_at", { ascending: false })
      .limit(25),
    admin
      .from("accounts")
      .select("id,email,role,assigned_demo,created_at,accepted_at")
      .order("created_at", { ascending: false })
      .limit(25),
  ]);

  return (
    <div className="space-y-8">
      <section className="rounded-panel border border-border bg-surface p-6 shadow-sm sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary-deep">Admin</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Demo access control</h1>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-muted sm:text-base sm:leading-7">
          Invite testers with Supabase native invitations and assign exactly one demo before they accept access.
        </p>
        <p className="mt-3 text-xs text-faint">Signed in as admin account {account.email}</p>
      </section>

      {params.error ? <p className="rounded-field bg-danger-soft p-3 text-sm text-danger">{params.error}</p> : null}
      {params.invited ? <p className="rounded-field bg-success-soft p-3 text-sm text-success">Invitation sent to {params.invited}.</p> : null}

      <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <form action={inviteTester} className="rounded-panel border border-border bg-surface p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-ink">Invite tester</h2>
          <p className="mt-2 text-sm leading-6 text-muted">Supabase sends the password setup email. The selected demo is stored in Auth metadata and product tables.</p>

          <label className="mt-6 block text-sm font-medium text-ink">
            Email
            <input name="email" type="email" required placeholder="tester@example.com" className="mt-2 w-full rounded-field border border-border bg-surface px-4 py-3 text-ink outline-none transition placeholder:text-faint focus:border-primary focus:ring-4 focus:ring-primary/15" />
          </label>

          <label className="mt-4 block text-sm font-medium text-ink">
            Assigned demo
            <select name="assigned_demo" required defaultValue="player" className="mt-2 w-full rounded-field border border-border bg-surface px-4 py-3 text-ink outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/15">
              {DEMOS.map((demo) => (
                <option key={demo} value={demo}>{demoLabels[demo]}</option>
              ))}
            </select>
          </label>

          <button type="submit" className="mt-6 w-full rounded-field bg-primary px-5 py-3 font-semibold text-primary-contrast transition hover:bg-primary/85">
            Send Supabase invite
          </button>
        </form>

        <div className="rounded-panel border border-border bg-surface p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-ink">Recent invitations</h2>
          <div className="mt-5 space-y-3">
            {(invitations || []).length === 0 ? <p className="text-sm text-muted">No invitations yet.</p> : null}
            {(invitations || []).map((invitation) => (
              <div key={invitation.id} className="rounded-card border border-border bg-elevated p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-semibold text-ink">{invitation.email}</p>
                  <span className="rounded-full bg-surface px-3 py-1 text-xs font-semibold text-muted">{invitation.status}</span>
                </div>
                <p className="mt-1 text-sm text-muted">{demoLabels[invitation.assigned_demo as AssignedDemo]} · {new Date(invitation.created_at).toLocaleString()}</p>
                {invitation.error_message ? <p className="mt-2 text-xs text-danger">{invitation.error_message}</p> : null}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-panel border border-border bg-surface p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-ink">Recent accounts</h2>
        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-faint">
              <tr>
                <th className="border-b border-border py-3 pr-4">Email</th>
                <th className="border-b border-border py-3 pr-4">Role</th>
                <th className="border-b border-border py-3 pr-4">Demo</th>
                <th className="border-b border-border py-3 pr-4">Accepted</th>
              </tr>
            </thead>
            <tbody>
              {(accounts || []).map((item) => (
                <tr key={item.id} className="border-b border-border/60">
                  <td className="py-3 pr-4 text-ink">{item.email}</td>
                  <td className="py-3 pr-4 text-muted">{item.role}</td>
                  <td className="py-3 pr-4 text-muted">{item.assigned_demo || "—"}</td>
                  <td className="py-3 pr-4 text-muted">{item.accepted_at ? new Date(item.accepted_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

async function inviteTester(formData: FormData) {
  "use server";

  const { account } = await requireAdminAccount();
  const email = String(formData.get("email") || "").trim().toLowerCase();
  const assignedDemo = String(formData.get("assigned_demo") || "") as AssignedDemo;

  if (!email || !DEMOS.includes(assignedDemo)) {
    return redirectWithMessage("Invalid email or demo.");
  }

  const requestHeaders = await headers();
  const origin = resolveAppOrigin(requestHeaders);
  const admin = createAdminClient();
  const now = new Date().toISOString();

  const { data: invitation } = await admin
    .from("admin_invitations")
    .insert({ email, assigned_demo: assignedDemo, status: "invited", invited_by: account.id, created_at: now, updated_at: now })
    .select("id")
    .single();

  const { error } = await admin.auth.admin.inviteUserByEmail(email, {
    data: {
      role: "tester",
      assigned_demo: assignedDemo,
      invited_by: account.id,
      invitation_id: invitation?.id,
    },
    redirectTo: `${origin}/auth/invite`,
  });

  if (error) {
    if (invitation?.id) {
      await admin.from("admin_invitations").update({ status: "failed", error_message: error.message, updated_at: new Date().toISOString() }).eq("id", invitation.id);
    }
    return redirectWithMessage("Could not send invitation. Check Supabase Auth settings or whether the user already exists.");
  }

  revalidatePath("/admin");
  return redirectWithMessage(undefined, email);
}

function redirectWithMessage(error?: string, invited?: string): never {
  const params = new URLSearchParams();
  if (error) params.set("error", error);
  if (invited) params.set("invited", invited);
  redirect(`/admin?${params.toString()}`);
}
