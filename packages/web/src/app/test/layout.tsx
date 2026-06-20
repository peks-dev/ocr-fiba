import { Nav } from "@/components/nav";
import { requireCurrentUserAccount } from "@/lib/auth/account";

export default async function TestLayout({ children }: { children: React.ReactNode }) {
  const { user, account } = await requireCurrentUserAccount();

  return (
    <div className="min-h-screen">
      <Nav email={user.email} role={account.role} assignedDemo={account.assigned_demo} />
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-10">{children}</main>
    </div>
  );
}
