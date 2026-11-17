"""
Evaluate individual player foul extraction against ground truth.

This focuses only on players[].fouls, separating:
- exact code mismatches (P vs P1 matters)
- family mismatches (P vs P1 does not matter)
- list length/alignment mismatches

Usage:
    python evaluation/evaluate_player_fouls.py [--sheet sheet-004] [--verbose]
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


def _foul_family(value: Any) -> str:
    token = str(value).strip().lower()
    if token and token[0] in {"p", "t", "u", "d", "c", "b"}:
        return token[0]
    return token


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
        "foul_slots_checked": 0,
        "exact_mismatches": [],
        "family_mismatches": [],
        "length_mismatches": [],
    }

    for team_key in ("team_a", "team_b"):
        gt_players = gt.get(team_key, {}).get("players") or []
        result_players = result.get(team_key, {}).get("players") or []

        for idx, (gt_player, result_player) in enumerate(zip(gt_players, result_players)):
            report["players_checked"] += 1
            gt_fouls = gt_player.get("fouls") or []
            result_fouls = result_player.get("fouls") or []

            if len(gt_fouls) != len(result_fouls):
                report["length_mismatches"].append({
                    "team": team_key,
                    "player_index": idx,
                    "player_number": gt_player.get("number"),
                    "gt": gt_fouls,
                    "result": result_fouls,
                })
                continue

            for foul_idx, (gt_foul, result_foul) in enumerate(zip(gt_fouls, result_fouls)):
                report["foul_slots_checked"] += 1
                if gt_foul != result_foul:
                    entry = {
                        "team": team_key,
                        "player_index": idx,
                        "player_number": gt_player.get("number"),
                        "foul_index": foul_idx,
                        "gt": gt_foul,
                        "result": result_foul,
                    }
                    report["exact_mismatches"].append(entry)
                    if _foul_family(gt_foul) != _foul_family(result_foul):
                        report["family_mismatches"].append(entry)

    exact_errors = len(report["exact_mismatches"]) + len(report["length_mismatches"])
    family_errors = len(report["family_mismatches"]) + len(report["length_mismatches"])
    report["exact_errors"] = exact_errors
    report["family_errors"] = family_errors
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate individual player fouls")
    parser.add_argument("--sheet", help="Only evaluate one sheet, e.g. sheet-004")
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

    total_exact = 0
    total_family = 0
    total_length = 0
    total_code = 0

    for report in reports:
        if "error" in report:
            print(f"{report['sheet']}: ERROR - {report['error']}")
            continue

        exact_code = len(report["exact_mismatches"])
        family_code = len(report["family_mismatches"])
        length = len(report["length_mismatches"])
        total_exact += report["exact_errors"]
        total_family += report["family_errors"]
        total_length += length
        total_code += exact_code

        print(
            f"{report['sheet']}: exact_errors={report['exact_errors']} "
            f"(code={exact_code}, length={length}) | family_errors={report['family_errors']} "
            f"(family_code={family_code}, length={length})"
        )

        if args.verbose:
            for item in report["length_mismatches"]:
                print(f"  length {item}")
            for item in report["exact_mismatches"]:
                print(f"  code   {item}")

    print(
        f"\nTOTAL: exact_errors={total_exact} "
        f"(code={total_code}, length={total_length}) | family_errors={total_family}"
    )


if __name__ == "__main__":
    main()
