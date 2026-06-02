"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { toast } from "sonner";

import { createClient } from "@/lib/supabase/client";

const links = [
  { href: "/dashboard/api-keys", label: "Dashboard" },
  { href: "/docs/quickstart", label: "Quickstart" },
];

export function Nav({ email }: { email?: string }) {
  const pathname = usePathname();
  const router = useRouter();

  async function logout() {
    const supabase = createClient();
    const { error } = await supabase.auth.signOut();
    if (error) {
      toast.error(error.message);
      return;
    }
    toast.success("Logged out successfully.");
    router.push("/login");
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/85 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/80">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/dashboard/api-keys" className="flex items-center gap-3 font-semibold text-slate-950 dark:text-white">
          <span className="grid size-9 place-items-center rounded-2xl bg-emerald-400 text-slate-950">OCR</span>
          <span>FIBA OCR</span>
        </Link>
        <nav className="hidden items-center gap-2 md:flex">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`rounded-full px-4 py-2 text-sm font-medium transition ${pathname === link.href ? "bg-slate-950 text-white dark:bg-white dark:text-slate-950" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-900"}`}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          {email ? <span className="hidden max-w-48 truncate text-sm text-slate-500 lg:inline">{email}</span> : null}
          <button className="rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:text-slate-200 dark:hover:bg-slate-900" onClick={logout} type="button">
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
