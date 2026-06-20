"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const DEFAULT_BASE_PATH = "/test/player";

export function DemoTabs({ basePath = DEFAULT_BASE_PATH }: { basePath?: string }) {
  const pathname = usePathname();
  const [currentPathname, setCurrentPathname] = useState<string | null>(null);
  const tabs = [
    { href: `${basePath}/capture`, label: "Capture game" },
    { href: `${basePath}/progress`, label: "Progress" },
    { href: `${basePath}/history`, label: "History" },
  ];

  useEffect(() => {
    setCurrentPathname(pathname);
  }, [pathname]);

  return (
    <nav className="-mx-1 mt-5 flex gap-2 overflow-x-auto px-1 pb-1 sm:mt-6">
      {tabs.map((tab) => {
        const isActive = Boolean(currentPathname?.startsWith(tab.href));
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`shrink-0 rounded-full px-4 py-2 text-sm font-semibold transition ${isActive ? "bg-primary text-primary-contrast" : "bg-inverse-foreground/10 text-inverse-foreground/85 hover:bg-inverse-foreground/20"}`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
