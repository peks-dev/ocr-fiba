import { teamName } from "./validation";
import type { OcrResult, ReconcileIssue, TeamKey } from "./types";

export type SheetSectionId =
  | "footer_score"
  | "team_a_roster"
  | "team_b_roster"
  | "team_a_fouls"
  | "team_b_fouls"
  | "progressive_score_a"
  | "progressive_score_b"
  | "header";

export type SheetSection = {
  id: SheetSectionId;
  label: string;
  shortLabel: string;
  description: string;
  issues: ReconcileIssue[];
};

const SECTION_ORDER: SheetSectionId[] = [
  "footer_score",
  "team_a_roster",
  "team_b_roster",
  "progressive_score_a",
  "progressive_score_b",
  "team_a_fouls",
  "team_b_fouls",
  "header",
];

export function buildSheetSections(result: OcrResult, issues: ReconcileIssue[]): SheetSection[] {
  const grouped = new Map<SheetSectionId, ReconcileIssue[]>();
  for (const id of SECTION_ORDER) grouped.set(id, []);

  for (const issue of issues) {
    grouped.get(sectionFromIssue(issue))?.push(issue);
  }

  return SECTION_ORDER.map((id) => ({ ...sectionMeta(id, result), issues: grouped.get(id) || [] }));
}

export function firstActionableSection(sections: SheetSection[]): SheetSectionId {
  const withIssues = sections
    .filter((section) => section.issues.length > 0)
    .sort((a, b) => sectionWeight(b.issues) - sectionWeight(a.issues));
  return withIssues[0]?.id || "footer_score";
}

export function nextSectionId(sections: SheetSection[], current: SheetSectionId): SheetSectionId | null {
  const currentIndex = sections.findIndex((section) => section.id === current);
  const nextWithIssues = sections.slice(currentIndex + 1).find((section) => section.issues.length > 0);
  if (nextWithIssues) return nextWithIssues.id;
  return sections.find((section) => section.issues.length > 0 && section.id !== current)?.id || null;
}

export function sectionHasFieldIssue(issues: ReconcileIssue[], fieldPrefix: string): boolean {
  return issues.some((issue) => {
    const field = issue.field || "";
    return field === fieldPrefix || field.startsWith(`${fieldPrefix}.`) || field.startsWith(`${fieldPrefix}[`) || fieldPrefix.startsWith(field);
  });
}

export function teamForSection(sectionId: SheetSectionId): TeamKey | null {
  if (sectionId === "team_a_roster" || sectionId === "team_a_fouls" || sectionId === "progressive_score_a") return "team_a";
  if (sectionId === "team_b_roster" || sectionId === "team_b_fouls" || sectionId === "progressive_score_b") return "team_b";
  return null;
}

function sectionFromIssue(issue: ReconcileIssue): SheetSectionId {
  const field = issue.field || "";
  if (field.startsWith("footer.")) return "footer_score";
  if (field.startsWith("header.")) return "header";
  if (field.startsWith("progressive_score.team_a")) return "progressive_score_a";
  if (field.startsWith("progressive_score.team_b")) return "progressive_score_b";
  if (field.startsWith("team_a.team_fouls_quarters")) return "team_a_fouls";
  if (field.startsWith("team_b.team_fouls_quarters")) return "team_b_fouls";
  if (field.startsWith("team_a.players")) return "team_a_roster";
  if (field.startsWith("team_b.players")) return "team_b_roster";
  if (field.startsWith("team_a.")) return "team_a_roster";
  if (field.startsWith("team_b.")) return "team_b_roster";
  return "footer_score";
}

function sectionMeta(id: SheetSectionId, result: OcrResult): Omit<SheetSection, "issues"> {
  const teamA = teamName(result, "team_a");
  const teamB = teamName(result, "team_b");
  switch (id) {
    case "footer_score":
      return { id, label: "Marcador y cierre", shortLabel: "Marcador", description: "Marcador final, ganador y puntos por cuarto." };
    case "team_a_roster":
      return { id, label: `Jugadores · ${teamA}`, shortLabel: "Jug. A", description: "Dorsales, nombres, puntos y faltas de jugadores." };
    case "team_b_roster":
      return { id, label: `Jugadores · ${teamB}`, shortLabel: "Jug. B", description: "Dorsales, nombres, puntos y faltas de jugadores." };
    case "team_a_fouls":
      return { id, label: `Faltas equipo · ${teamA}`, shortLabel: "Faltas A", description: "Faltas de equipo por cuarto." };
    case "team_b_fouls":
      return { id, label: `Faltas equipo · ${teamB}`, shortLabel: "Faltas B", description: "Faltas de equipo por cuarto." };
    case "progressive_score_a":
      return { id, label: `Progresivo · ${teamA}`, shortLabel: "Prog. A", description: "Eventos de anotación detectados en el marcador progresivo." };
    case "progressive_score_b":
      return { id, label: `Progresivo · ${teamB}`, shortLabel: "Prog. B", description: "Eventos de anotación detectados en el marcador progresivo." };
    case "header":
      return { id, label: "Datos del partido", shortLabel: "Datos", description: "Liga, torneo, fecha, hora y árbitros." };
  }
}

function sectionWeight(issues: ReconcileIssue[]): number {
  return issues.reduce((acc, issue) => acc + severityWeight(issue.severity), 0);
}

function severityWeight(severity: ReconcileIssue["severity"]): number {
  return { critical: 4, high: 3, medium: 2, low: 1 }[severity];
}
