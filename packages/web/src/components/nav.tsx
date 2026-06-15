"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { toast } from "sonner";

import { createClient } from "@/lib/supabase/client";

const links = [
  { href: "/dashboard/api-keys", label: "Dashboard" },
  { href: "/dashboard/demos/single-player", label: "Single Player" },
  { href: "/dashboard/demos/referee", label: "Arbitros" },
  { href: "/dashboard/demos/club", label: "Club" },
  { href: "/docs/quickstart", label: "Quickstart" },
];

export function Nav({ email }: { email?: string }) {
  const pathname = usePathname();
  const router = useRouter();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  useEffect(() => {
    setIsMenuOpen(false);
  }, [pathname]);

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

  function isActive(href: string) {
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-surface/85 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <Link href="/dashboard/api-keys" className="flex items-center gap-3 font-heading font-semibold text-ink">
          <span className="grid size-9 place-items-center rounded-card bg-primary text-sm text-primary-contrast">OCR</span>
          <span>FIBA OCR</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`rounded-full px-4 py-2 text-sm font-medium transition ${isActive(link.href) ? "bg-ink text-background" : "text-muted hover:bg-elevated hover:text-ink"}`}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {email ? <span className="hidden max-w-48 truncate text-sm text-muted lg:inline">{email}</span> : null}
          <button
            className="hidden rounded-full border border-border px-4 py-2 text-sm font-semibold text-ink transition hover:bg-elevated md:inline-flex"
            onClick={logout}
            type="button"
          >
            Logout
          </button>
          <button
            type="button"
            className="grid size-10 place-items-center rounded-full border border-border text-ink transition hover:bg-elevated md:hidden"
            aria-expanded={isMenuOpen}
            aria-label={isMenuOpen ? "Close menu" : "Open menu"}
            onClick={() => setIsMenuOpen((open) => !open)}
          >
            <MenuIcon open={isMenuOpen} />
          </button>
        </div>
      </div>

      {isMenuOpen ? (
        <nav className="border-t border-border bg-surface px-4 pb-5 pt-3 md:hidden">
          <div className="space-y-1">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`block rounded-card px-4 py-3 text-sm font-medium transition ${isActive(link.href) ? "bg-ink text-background" : "text-muted hover:bg-elevated hover:text-ink"}`}
              >
                {link.label}
              </Link>
            ))}
          </div>
          <div className="mt-4 border-t border-border pt-4">
            {email ? <p className="truncate px-4 text-xs text-faint">{email}</p> : null}
            <button
              className="mt-3 w-full rounded-card border border-border px-4 py-3 text-sm font-semibold text-ink transition hover:bg-elevated"
              onClick={logout}
              type="button"
            >
              Logout
            </button>
          </div>
        </nav>
      ) : null}
    </header>
  );
}

function MenuIcon({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="size-5" aria-hidden="true">
      {open ? (
        <>
          <path d="M6 6l12 12" />
          <path d="M18 6L6 18" />
        </>
      ) : (
        <>
          <path d="M4 7h16" />
          <path d="M4 12h16" />
          <path d="M4 17h16" />
        </>
      )}
    </svg>
  );
}
