"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const BASE_PATH = "/dashboard/demos/referee";

const steps = [
  { href: `${BASE_PATH}/capture`, label: "Captura", step: "1" },
  { href: `${BASE_PATH}/reconcile`, label: "Corrige", step: "2" },
  { href: `${BASE_PATH}/submit`, label: "Envía", step: "3" },
];

export function DemoTabs() {
  const pathname = usePathname();

  return (
    <nav className="mt-5" aria-label="Flujo de cierre de acta">
      <ol className="grid grid-cols-3 gap-2">
        {steps.map((tab) => {
          const isActive = pathname.startsWith(tab.href);
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
      <Link href={`${BASE_PATH}/league`} className="mt-3 inline-block text-xs font-semibold text-inverse-foreground/70 underline underline-offset-4">
        Ver vista de liga
      </Link>
    </nav>
  );
}
