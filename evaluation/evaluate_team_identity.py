"""
Evaluate team/player identity extraction against ground truth.

Focuses on team.name, captain, players[].name, and players[].number.

Usage:
    python evaluation/evaluate_team_identity.py [--sheet sheet-005] [--results-dir dataset/results-v2] [--verbose]
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


def _norm(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    return value


def evaluate_sheet(sheet_id: str) -> dict[str, Any]:
    gt_path = DATASET_DIR / sheet_id / "ground_truth.json"
    result_path = RESULTS_DIR / sheet_id / "result.json"

    if not gt_path.exists():
        return {"sheet": sheet_id, "error": "ground_truth.json not found"}
    if not result_path.exists():
        return {"sheet": sheet_id, "error": "result.json not found"}

    gt = json.loads(gt_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))

    report: dict[str, Any] = {
        "sheet": sheet_id,
        "team_name_mismatches": [],
        "captain_mismatches": [],
        "player_name_mismatches": [],
        "player_number_mismatches": [],
    }

    for team_key in ("team_a", "team_b"):
        gt_team = gt.get(team_key, {})
        result_team = result.get(team_key, {})

        if _norm(gt_team.get("name")) != _norm(result_team.get("name")):
            report["team_name_mismatches"].append({
                "team": team_key,
                "gt": gt_team.get("name"),
                "result": result_team.get("name"),
            })

        if _norm(gt_team.get("captain")) != _norm(result_team.get("captain")):
            report["captain_mismatches"].append({
                "team": team_key,
                "gt": gt_team.get("captain"),
                "result": result_team.get("captain"),
            })

        gt_players = gt_team.get("players") or []
        result_players = result_team.get("players") or []
        for idx, (gt_player, result_player) in enumerate(zip(gt_players, result_players)):
            if _norm(gt_player.get("name")) != _norm(result_player.get("name")):
                report["player_name_mismatches"].append({
                    "team": team_key,
                    "player_index": idx,
                    "player_number": gt_player.get("number"),
                    "gt": gt_player.get("name"),
                    "result": result_player.get("name"),
                })
            if _norm(gt_player.get("number")) != _norm(result_player.get("number")):
                report["player_number_mismatches"].append({
                    "team": team_key,
                    "player_index": idx,
                    "gt_name": gt_player.get("name"),
                    "gt": gt_player.get("number"),
                    "result": result_player.get("number"),
                })

    report["total_errors"] = sum(
        len(report[key])
        for key in (
            "team_name_mismatches",
            "captain_mismatches",
            "player_name_mismatches",
            "player_number_mismatches",
        )
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate team/player identity")
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

    totals = {
        "team_name_mismatches": 0,
        "captain_mismatches": 0,
        "player_name_mismatches": 0,
        "player_number_mismatches": 0,
    }
    for report in reports:
        if "error" in report:
            print(f"{report['sheet']}: ERROR - {report['error']}")
            continue
        for key in totals:
            totals[key] += len(report[key])
        print(
            f"{report['sheet']}: total={report['total_errors']} "
            f"(team={len(report['team_name_mismatches'])}, "
            f"captain={len(report['captain_mismatches'])}, "
            f"names={len(report['player_name_mismatches'])}, "
            f"numbers={len(report['player_number_mismatches'])})"
        )
        if args.verbose:
            for key in totals:
                for item in report[key]:
                    print(f"  {key.removesuffix('_mismatches')} {item}")

    total = sum(totals.values())
    print(
        f"\nTOTAL: total={total} "
        f"(team={totals['team_name_mismatches']}, "
        f"captain={totals['captain_mismatches']}, "
        f"names={totals['player_name_mismatches']}, "
        f"numbers={totals['player_number_mismatches']})"
    )


if __name__ == "__main__":
    main()
