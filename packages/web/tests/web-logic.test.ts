import assert from "node:assert/strict";
import test from "node:test";

import { findBestRosterNameMatch, normalizePlayerName } from "../src/components/club-demo/name-match";
import type { ClubPlayer } from "../src/components/club-demo/types";
import { validateLeagueSubmissionPayload } from "../src/components/referee-demo/league-validation";
import { DEFAULT_REFEREE_PLUGIN_IDS, REFEREE_PLUGINS } from "../src/components/referee-demo/plugins";
import { applySuggestion, setPlayerFlag, setPlayerPoint } from "../src/components/referee-demo/reconcile-utils";
import { buildSheetSections, firstActionableSection } from "../src/components/referee-demo/sections";
import type { OcrResult } from "../src/components/referee-demo/types";
import { computeReconciliation } from "../src/components/referee-demo/validation";
import { resolveAppOrigin } from "../src/lib/auth/origin";

function headersFrom(entries: Record<string, string>) {
  const lower = new Map(Object.entries(entries).map(([key, value]) => [key.toLowerCase(), value]));
  return {
    get(name: string) {
      return lower.get(name.toLowerCase()) ?? null;
    },
  };
}

test("resolveAppOrigin prioritizes configured site URL, rejects mismatched origin, and supports Vercel env", () => {
  assert.equal(
    resolveAppOrigin(headersFrom({ origin: "https://evil.example", host: "demo.vercel.app" }), {
      NEXT_PUBLIC_SITE_URL: "https://fiba-ocr.vercel.app/invite",
    }),
    "https://fiba-ocr.vercel.app",
  );

  assert.equal(
    resolveAppOrigin(
      headersFrom({
        origin: "https://spoofed.example",
        "x-forwarded-host": "app.example.com",
        "x-forwarded-proto": "https",
      }),
      {},
    ),
    "https://app.example.com",
  );

  assert.equal(
    resolveAppOrigin(headersFrom({}), { VERCEL_PROJECT_PRODUCTION_URL: "ocr-web.vercel.app" }),
    "https://ocr-web.vercel.app",
  );

  assert.equal(resolveAppOrigin(headersFrom({ host: "localhost:3000" }), {}), "http://localhost:3000");
});

test("validateLeagueSubmissionPayload accepts valid payload and rejects malformed input", () => {
  const valid = validateLeagueSubmissionPayload({
    match_id: "referee:run-1:123",
    team_a: "Panteras",
    team_b: "Mambas",
    reconcile_status: "cuadrada",
    warnings_remaining: 0,
    payload_json: "{}",
  });
  assert.equal(valid.ok, true);

  assert.equal(validateLeagueSubmissionPayload(null).ok, false);
  assert.equal(validateLeagueSubmissionPayload({ match_id: "   " }).ok, false);
  assert.equal(validateLeagueSubmissionPayload({ match_id: "x", reconcile_status: "invalid" }).ok, false);
  assert.equal(validateLeagueSubmissionPayload({ match_id: "x", warnings_remaining: -1 }).ok, false);
  assert.equal(validateLeagueSubmissionPayload({ match_id: "x", team_a: 42 }).ok, false);
});

test("REFEREE_PLUGINS includes all 13 core, FIBA, and referee plugins", () => {
  assert.equal(REFEREE_PLUGINS.length, 13);
  for (const requiredId of [
    "core_player_vs_progressive",
    "core_progressive_sequence",
    "core_entry_and_fouls_consistency",
    "core_illegible_marks",
    "core_preprocess_fallback",
  ]) {
    assert.ok(DEFAULT_REFEREE_PLUGIN_IDS.includes(requiredId), `Missing plugin ${requiredId}`);
  }
});

test("computeReconciliation surfaces new engine warnings, preserves warning details, and applies suggestions", () => {
  const sheet: OcrResult = {
    team_a: {
      name: "Panteras",
      players: [{ name: "Ana", number: "7", points: { one_point: 2, two_point: 5, three_point: 1 }, started: false, entered: false }],
    },
    team_b: { name: "Mambas", players: [{ name: "Sofía", number: "9", points: { two_point: 6 } }] },
    footer: {
      final_score: { team_a: 15, team_b: 12 },
      winner: "Mambas",
      quarters: {
        first: { team_a: 4, team_b: 3 },
        second: { team_a: 4, team_b: 3 },
        third: { team_a: 4, team_b: 3 },
        fourth: { team_a: 4, team_b: 3 },
      },
    },
    validation_warnings: [
      {
        type: "player_progressive_mismatch",
        severity: "high",
        field: "team_a.players[0].points",
        message: "Mismatch",
      },
      {
        type: "progressive_sequence_jump",
        severity: "high",
        field: "progressive_score.team_a",
        message: "Jump",
        details: { invalid_jumps: [{ index: 2 }] },
      },
      {
        type: "quarter_sum_mismatch",
        severity: "high",
        field: "footer.final_score.team_a",
        message: "Recomputed client-side",
      },
    ],
  };

  const summary = computeReconciliation(sheet);
  assert.equal(summary.status, "con_observaciones");
  assert.equal(summary.blockingCount, 2); // quarter sum mismatch + winner inconsistent

  const seqIssue = summary.issues.find((issue) => issue.title === "Salto inválido en progresivo");
  assert.ok(seqIssue?.warning?.details);
  assert.equal(
    summary.issues.filter((issue) => issue.source === "engine" && issue.warning?.type === "quarter_sum_mismatch").length,
    0,
  );

  const sections = buildSheetSections(sheet, summary.issues);
  assert.equal(firstActionableSection(sections), "footer_score");

  let updated = sheet;
  for (const issue of summary.issues) {
    if (issue.suggestion) updated = applySuggestion(updated, issue.suggestion);
  }
  updated = setPlayerPoint(updated, "team_a", 0, "tree_point", null);
  updated = setPlayerFlag(updated, "team_a", 0, "started", true);

  assert.equal(updated.team_a?.players?.[0]?.points?.tree_point, null);
  assert.equal("three_point" in (updated.team_a?.players?.[0]?.points || {}), false);
  assert.equal(updated.team_a?.players?.[0]?.entered, true);
  assert.equal(computeReconciliation(updated).blockingCount, 0);
});

test("name-match normalizes diacritics and matches roster names across accent/tilde variants", () => {
  const roster: ClubPlayer[] = [
    { id: "p1", name: "José Peña", number: "8", createdAt: "2026-01-01T00:00:00Z" },
    { id: "p2", name: "Carlos Martínez", number: "11", createdAt: "2026-01-01T00:00:00Z" },
  ];
  assert.equal(normalizePlayerName("José Peña"), "jose pena");
  const match = findBestRosterNameMatch("Jose Pena", roster);
  assert.equal(match?.player.id, "p1");
});
