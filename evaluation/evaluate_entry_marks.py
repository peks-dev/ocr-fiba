"""
Evaluate player entered/started extraction against ground truth.

Usage:
    python evaluation/evaluate_entry_marks.py [--sheet sheet-002] [--results-dir dataset/results-v2] [--verbose]
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
    "sheet-006", "sheet-007", "sheet-008", "sheet-009", "sheet-010",
]


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
        "players_checked": 0,
        "entered_mismatches": [],
        "started_mismatches": [],
    }

    for team_key in ("team_a", "team_b"):
        gt_players = gt.get(team_key, {}).get("players") or []
        result_players = result.get(team_key, {}).get("players") or []

        for idx, (gt_player, result_player) in enumerate(zip(gt_players, result_players)):
            report["players_checked"] += 1
            for field, bucket in (
                ("entered", "entered_mismatches"),
                ("started", "started_mismatches"),
            ):
                if gt_player.get(field) != result_player.get(field):
                    report[bucket].append({
                        "team": team_key,
                        "player_index": idx,
                        "player_number": gt_player.get("number"),
                        "gt": gt_player.get(field),
                        "result": result_player.get(field),
                    })

    report["total_errors"] = (
        len(report["entered_mismatches"]) + len(report["started_mismatches"])
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate player entry marks")
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

    total_entered = 0
    total_started = 0
    for report in reports:
        if "error" in report:
            print(f"{report['sheet']}: ERROR - {report['error']}")
            continue
        entered = len(report["entered_mismatches"])
        started = len(report["started_mismatches"])
        total_entered += entered
        total_started += started
        print(
            f"{report['sheet']}: total_errors={report['total_errors']} "
            f"(entered={entered}, started={started})"
        )
        if args.verbose:
            for item in report["entered_mismatches"]:
                print(f"  entered {item}")
            for item in report["started_mismatches"]:
                print(f"  started {item}")

    print(
        f"\nTOTAL: total_errors={total_entered + total_started} "
        f"(entered={total_entered}, started={total_started})"
    )


if __name__ == "__main__":
    main()
