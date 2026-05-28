"""
Evaluate progressive_score extraction against ground truth.

Reports running_score set accuracy and player_number accuracy for matched
running scores. This avoids noisy index-cascade diffs.

Usage:
    python evaluation/evaluate_progressive_score.py [--sheet sheet-007] [--results-dir dataset/results-v2] [--verbose]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DATASET_DIR = Path(__file__).resolve().parents[1] / "dataset"
RESULTS_DIR = DATASET_DIR / "results"

ALL_SHEETS = [
    "sheet-001", "sheet-002", "sheet-003", "sheet-004", "sheet-005",
    "sheet-007", "sheet-008", "sheet-009", "sheet-010",
]


def _events_by_running_score(events: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    result = {}
    for event in events:
        rs = event.get("running_score")
        if isinstance(rs, int):
            result[rs] = event
    return result


def evaluate_sheet(sheet_id: str) -> dict[str, Any]:
    gt_path = DATASET_DIR / sheet_id / "ground_truth.json"
    result_path = RESULTS_DIR / sheet_id / "result.json"

    if not gt_path.exists():
        return {"sheet": sheet_id, "error": "ground_truth.json not found"}
    if not result_path.exists():
        return {"sheet": sheet_id, "error": "result.json not found"}

    gt = json.loads(gt_path.read_text(encoding="utf-8")).get("progressive_score", {})
    result = json.loads(result_path.read_text(encoding="utf-8")).get("progressive_score", {})

    report: dict[str, Any] = {"sheet": sheet_id, "teams": {}}
    for team_key in ("team_a", "team_b"):
        gt_events = gt.get(team_key) or []
        result_events = result.get(team_key) or []
        gt_by_rs = _events_by_running_score(gt_events)
        result_by_rs = _events_by_running_score(result_events)

        gt_rs = set(gt_by_rs)
        result_rs = set(result_by_rs)
        matched_rs = gt_rs & result_rs

        player_mismatches = []
        for rs in sorted(matched_rs):
            gt_player = gt_by_rs[rs].get("player_number")
            result_player = result_by_rs[rs].get("player_number")
            if str(gt_player) != str(result_player):
                player_mismatches.append({
                    "running_score": rs,
                    "gt": gt_player,
                    "result": result_player,
                })

        report["teams"][team_key] = {
            "gt_count": len(gt_events),
            "result_count": len(result_events),
            "matched_running_scores": len(matched_rs),
            "missing_running_scores": sorted(gt_rs - result_rs),
            "extra_running_scores": sorted(result_rs - gt_rs),
            "player_mismatches": player_mismatches,
            "player_matches": len(matched_rs) - len(player_mismatches),
        }

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate progressive_score extraction")
    parser.add_argument("--sheet", help="Only evaluate one sheet")
    parser.add_argument("--results-dir", default=None, help="Override results directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print mismatch details")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    global RESULTS_DIR
    if args.results_dir:
        RESULTS_DIR = Path(args.results_dir)
        if not RESULTS_DIR.is_absolute():
            RESULTS_DIR = Path(__file__).resolve().parents[1] / RESULTS_DIR

    sheets = [args.sheet] if args.sheet else ALL_SHEETS
    reports = [evaluate_sheet(sheet_id) for sheet_id in sheets]

    if args.json:
        print(json.dumps(reports, indent=2, ensure_ascii=False))
        return

    total_gt = total_rs = total_player_matches = total_player_compared = 0
    for report in reports:
        if "error" in report:
            print(f"{report['sheet']}: ERROR - {report['error']}")
            continue
        print(report["sheet"])
        for team_key, team_report in report["teams"].items():
            gt_count = team_report["gt_count"]
            matched = team_report["matched_running_scores"]
            compared = matched
            player_matches = team_report["player_matches"]
            total_gt += gt_count
            total_rs += matched
            total_player_matches += player_matches
            total_player_compared += compared
            print(
                f"  {team_key}: rs={matched}/{gt_count} "
                f"players={player_matches}/{compared} "
                f"missing={len(team_report['missing_running_scores'])} "
                f"extra={len(team_report['extra_running_scores'])}"
            )
            if args.verbose:
                if team_report["missing_running_scores"]:
                    print(f"    missing_rs={team_report['missing_running_scores']}")
                if team_report["extra_running_scores"]:
                    print(f"    extra_rs={team_report['extra_running_scores']}")
                for item in team_report["player_mismatches"]:
                    print(f"    player rs={item['running_score']}: GT={item['gt']} RESULT={item['result']}")

    print(
        f"\nTOTAL: rs={total_rs}/{total_gt} "
        f"players={total_player_matches}/{total_player_compared}"
    )


if __name__ == "__main__":
    main()
