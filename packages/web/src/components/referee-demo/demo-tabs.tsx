"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const DEFAULT_BASE_PATH = "/test/referee";

export function DemoTabs({ basePath = DEFAULT_BASE_PATH }: { basePath?: string }) {
  const pathname = usePathname();
  const [currentPathname, setCurrentPathname] = useState<string | null>(null);
  const steps = [
    { href: `${basePath}/capture`, label: "Captura", step: "1" },
    { href: `${basePath}/reconcile`, label: "Corrige", step: "2" },
    { href: `${basePath}/submit`, label: "Envía", step: "3" },
  ];

  useEffect(() => {
    setCurrentPathname(pathname);
  }, [pathname]);

  return (
    <nav className="mt-5" aria-label="Flujo de cierre de acta">
      <ol className="grid grid-cols-3 gap-2">
        {steps.map((tab) => {
          const isActive = Boolean(currentPathname?.startsWith(tab.href));
          return (
            <li key={tab.href}>
              <Link
                href={tab.href}
                className={`flex items-center justify-center gap-2 rounded-full px-3 py-2 text-xs font-semibold transition sm:text-sm ${
                  isActive ? "bg-primary text-primary-contrast" : "bg-inverse-foreground/10 text-inverse-foreground/85 hover:bg-inverse-foreground/20"
                }`}
              >
                <span className="grid size-5 place-items-center rounded-full bg-inverse-foreground/15 text-[0.65rem]">{tab.step}</span>
                {tab.label}
              </Link>
            </li>
          );
        })}
      </ol>
      <Link href={`${basePath}/league`} className="mt-3 inline-block text-xs font-semibold text-inverse-foreground/70 underline underline-offset-4">
        Ver vista de liga
      </Link>
    </nav>
  );
}
