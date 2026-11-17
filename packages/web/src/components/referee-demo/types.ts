// Shared types for the Arbitros Helper demo (DEMO 2).
// The OcrResult shape mirrors the engine output (see core-engine output_builder).

export type RunStatus = "queued" | "pending" | "running" | "completed" | "failed" | "cancelled" | "skipped" | string;

export type TeamKey = "team_a" | "team_b";

export type QuarterKey = "first" | "second" | "third" | "fourth" | "extra";

export type IssueSeverity = "critical" | "high" | "medium" | "low";

export type ValidationWarning = {
  type?: string;
  severity?: IssueSeverity | string;
  message?: string;
  field?: string;
  details?: Record<string, unknown> | null;
  plugin?: string;
};

export type PlayerPoints = {
  one_point?: number | null;
  two_point?: number | null;
  tree_point?: number | null;
  three_point?: number | null;
};

export type OcrPlayer = {
  name?: string | null;
  number?: string | number | null;
  points?: PlayerPoints | null;
  fouls?: unknown[] | null;
  entered?: boolean | null;
  started?: boolean | null;
};

export type OcrTeam = {
  name?: string | null;
  captain?: string | null;
  team_fouls_quarters?: (number | null)[] | null;
  players?: OcrPlayer[] | null;
};

export type ProgressiveEvent = {
  player_number?: string | number | null;
  running_score?: number | null;
  points?: number | null;
  period?: number | null;
};

export type QuarterScore = { team_a?: number | null; team_b?: number | null } | null;

export type OcrFooter = {
  final_score?: { team_a?: number | null; team_b?: number | null } | null;
  winner?: string | null;
  quarters?: Partial<Record<QuarterKey, QuarterScore>> | null;
} | null;

export type ConfidenceLevel = "high" | "medium" | "low";

export type ConfidenceSectionKey = "header" | "team_a" | "team_b" | "progressive_score" | "footer";

export type ConfidenceSummary = {
  score?: number | null;
  level?: ConfidenceLevel | string | null;
  sections?: Partial<Record<ConfidenceSectionKey, number>> | null;
  warning_counts?: Partial<Record<IssueSeverity, number>> | null;
};

export type OcrResult = {
  match_status?: string | null;
  header?: {
    league?: string | null;
    tournament?: string | null;
    date?: string | null;
    time?: string | null;
    gender?: string | null;
    first_judge?: string | null;
    second_judge?: string | null;
  } | null;
  team_a?: OcrTeam | null;
  team_b?: OcrTeam | null;
  progressive_score?: Partial<Record<TeamKey, ProgressiveEvent[]>> | null;
  footer?: OcrFooter;
  validation_warnings?: ValidationWarning[] | null;
  confidence?: ConfidenceSummary | null;
  meta?: Record<string, unknown> | null;
};

// A structured, serialisable suggestion the referee can apply with one click.
export type Suggestion =
  | { kind: "set_final_score"; team: TeamKey; value: number; label: string }
  | { kind: "set_winner"; winner: string; label: string };

// An actionable reconciliation issue computed live from the editable result.
export type ReconcileIssue = {
  id: string;
  severity: IssueSeverity;
  title: string;
  message: string;
  field?: string;
  // "engine" issues come from validation_warnings; "live" issues are recomputed
  // client-side after every edit.
  source: "live" | "engine";
  suggestion?: Suggestion;
  warning?: ValidationWarning;
};

export type ReconcileSummary = {
  issues: ReconcileIssue[];
  blockingCount: number; // critical + high + required-empty
  totalCount: number;
  status: "cuadrada" | "con_observaciones";
};

// Working draft handed off between capture → reconcile → submit (sessionStorage).
export type RefereeDraft = {
  runId: string;
  result: OcrResult;
  updatedAt: string;
  validationPlugins?: string[];
};

// What we send to the league (Airtable) via the server proxy.
export type LeagueSubmissionPayload = {
  match_id: string;
  league: string;
  tournament: string;
  game_date: string;
  team_a: string;
  team_b: string;
  final_score: string;
  winner: string;
  reconcile_status: "cuadrada" | "con_observaciones";
  warnings_remaining: number;
  source_run_id: string;
  payload_json: string;
};

// What we read back from the league view.
export type LeagueRecord = {
  id: string;
  submittedAt: string | null;
  fields: Partial<LeagueSubmissionPayload>;
};
