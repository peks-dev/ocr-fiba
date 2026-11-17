"""
Evaluate player points extraction against ground truth.

Usage:
    python evaluation/evaluate_player_points.py [--sheet sheet-002] [--results-dir dataset/results-v2] [--verbose]
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

POINT_FIELDS = ["one_point", "two_point", "tree_point"]


def evaluate_sheet(sheet_id: str) -> dict[str, Any]:
    gt_path = DATASET_DIR / sheet_id / "ground_truth.json"
    result_path = RESULTS_DIR / sheet_id / "result.json"

    if not gt_path.exists():
        return {"sheet": sheet_id, "error": "ground_truth.json not found"}
    if not result_path.exists():
        return {"sheet": sheet_id, "error": "result.json not found"}

    gt = json.loads(gt_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))

    mismatches = []
    for team_key in ("team_a", "team_b"):
        gt_players = gt.get(team_key, {}).get("players") or []
        result_players = result.get(team_key, {}).get("players") or []
        for idx, (gt_player, result_player) in enumerate(zip(gt_players, result_players)):
            gt_points = gt_player.get("points") or {}
            result_points = result_player.get("points") or {}
            for field in POINT_FIELDS:
                if gt_points.get(field) != result_points.get(field):
                    mismatches.append({
                        "team": team_key,
                        "player_index": idx,
                        "player_number": gt_player.get("number"),
                        "player_name": gt_player.get("name"),
                        "field": field,
                        "gt": gt_points.get(field),
                        "result": result_points.get(field),
                    })

    return {
        "sheet": sheet_id,
        "mismatches": mismatches,
        "total_errors": len(mismatches),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate player points")
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

    total = 0
    by_field = {field: 0 for field in POINT_FIELDS}
    for report in reports:
        if "error" in report:
            print(f"{report['sheet']}: ERROR - {report['error']}")
            continue
        total += report["total_errors"]
        for item in report["mismatches"]:
            by_field[item["field"]] += 1
        print(f"{report['sheet']}: total={report['total_errors']}")
        if args.verbose:
            for item in report["mismatches"]:
                print(
                    f"  {item['team']}[{item['player_index']}] "
                    f"#{item['player_number']} {item['field']}: "
                    f"GT={item['gt']!r} RESULT={item['result']!r} "
                    f"name={item['player_name']!r}"
                )

    field_summary = ", ".join(f"{field}={count}" for field, count in by_field.items() if count)
    print(f"\nTOTAL: total={total}" + (f" ({field_summary})" if field_summary else ""))


if __name__ == "__main__":
    main()
