"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const BASE_PATH = "/dashboard/demos/single-player";

const tabs = [
  { href: `${BASE_PATH}/capture`, label: "Capture game" },
  { href: `${BASE_PATH}/progress`, label: "Progress" },
  { href: `${BASE_PATH}/history`, label: "History" },
];

export function DemoTabs() {
  const pathname = usePathname();

  return (
    <nav className="-mx-1 mt-5 flex gap-2 overflow-x-auto px-1 pb-1 sm:mt-6">
      {tabs.map((tab) => {
        const isActive = pathname.startsWith(tab.href);
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
