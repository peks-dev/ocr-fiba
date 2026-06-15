export type TeamKey = "team_a" | "team_b";
export type RunStatus = "queued" | "pending" | "running" | "completed" | "failed" | "cancelled" | "skipped" | string;

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
  header?: {
    league?: string | null;
    tournament?: string | null;
    date?: string | null;
    time?: string | null;
  } | null;
  team_a?: OcrTeam | null;
  team_b?: OcrTeam | null;
  footer?: {
    final_score?: { team_a?: number | null; team_b?: number | null } | null;
    winner?: string | null;
  } | null;
  validation_warnings?: unknown[] | null;
};

export type ClubPlayer = {
  id: string;
  name: string;
  number: string;
  position?: string;
  createdAt: string;
};

export type ClubGamePlayerStat = {
  playerId?: string;
  playerName: string;
  number: string;
  onePoint: number;
  twoPoint: number;
  threePoint: number;
  totalPoints: number;
  foulsCount: number;
  started: boolean;
  entered: boolean;
  matchedRoster: boolean;
};

export type ClubGame = {
  id: string;
  runId: string;
  savedAt: string;
  gameDate: string;
  tournament: string;
  clubTeamName: string;
  opponent: string;
  finalScore: string;
  resultLabel: "Win" | "Loss" | "Result pending";
  stats: ClubGamePlayerStat[];
};

export type ClubStore = {
  clubName: string;
  roster: ClubPlayer[];
  games: ClubGame[];
};
