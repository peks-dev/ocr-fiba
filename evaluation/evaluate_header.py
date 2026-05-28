"""
Evaluate header extraction against ground truth.

Usage:
    python evaluation/evaluate_header.py [--sheet sheet-008] [--results-dir dataset/results-v2] [--verbose]
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


FIELDS = ["league", "tournament", "date", "time", "gender", "first_judge", "second_judge"]


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

    gt = json.loads(gt_path.read_text(encoding="utf-8")).get("header", {})
    result = json.loads(result_path.read_text(encoding="utf-8")).get("header", {})

    mismatches = []
    for field in FIELDS:
        if _norm(gt.get(field)) != _norm(result.get(field)):
            mismatches.append({
                "field": field,
                "gt": gt.get(field),
                "result": result.get(field),
            })

    return {
        "sheet": sheet_id,
        "mismatches": mismatches,
        "total_errors": len(mismatches),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate header extraction")
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
    by_field = {field: 0 for field in FIELDS}
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
                print(f"  {item['field']}: GT={item['gt']!r} RESULT={item['result']!r}")

    field_summary = ", ".join(f"{field}={count}" for field, count in by_field.items() if count)
    print(f"\nTOTAL: total={total}" + (f" ({field_summary})" if field_summary else ""))


if __name__ == "__main__":
    main()
