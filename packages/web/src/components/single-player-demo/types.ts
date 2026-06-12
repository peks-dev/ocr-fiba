export type RunStatus = "queued" | "pending" | "running" | "completed" | "failed" | "cancelled" | "skipped" | string;

export type OcrRun = {
  success?: boolean;
  run_id: string;
  status: RunStatus;
  created_at?: string;
  updated_at?: string;
  error?: { message?: string; code?: string } | string | null;
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
  players?: OcrPlayer[] | null;
};

export type OcrResult = {
  match_status?: string | null;
  header?: {
    league?: string | null;
    tournament?: string | null;
    date?: string | null;
    time?: string | null;
    gender?: string | null;
  } | null;
  team_a?: OcrTeam | null;
  team_b?: OcrTeam | null;
  footer?: {
    final_score?: { team_a?: number | null; team_b?: number | null } | null;
    winner?: string | null;
    quarters?: Record<string, { team_a?: number | null; team_b?: number | null } | null> | null;
  } | null;
  validation_warnings?: unknown[] | null;
};

export type DemoPlayer = {
  id: string;
  teamKey: "team_a" | "team_b";
  teamName: string;
  name: string;
  number: string;
  onePoint: number;
  twoPoint: number;
  threePoint: number;
  totalPoints: number;
  foulsCount: number;
  started: boolean;
  entered: boolean;
};

export type SavedSinglePlayerGame = {
  id: string;
  savedAt: string;
  runId: string;
  player: DemoPlayer;
  opponent: string;
  teamName: string;
  gameDate: string;
  tournament: string;
  finalScore: string;
  resultLabel: string;
};
