import { Nav } from "@/components/nav";
import { requireAdminAccount } from "@/lib/auth/account";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, account } = await requireAdminAccount();

  return (
    <div className="min-h-screen">
      <Nav email={user.email} role={account.role} assignedDemo={account.assigned_demo} />
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-10">{children}</main>
    </div>
  );
}
