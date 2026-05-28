"""
Evaluate OCR pipeline results against ground truth for all sheets.

Compares every field and produces a detailed report with:
- Per-field match/mismatch
- Per-section accuracy percentages
- Global summary

Usage:
    python evaluation/evaluate_dataset.py [--sheet SHEET_ID] [--results-dir dataset/results]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DATASET_DIR = Path(__file__).resolve().parents[1] / "dataset"
RESULTS_DIR = DATASET_DIR / "results"

ALL_SHEETS = [
    "sheet-001", "sheet-002", "sheet-003", "sheet-004", "sheet-005",
    "sheet-007", "sheet-008", "sheet-009", "sheet-010",
]


def compare_values(gt_val: Any, result_val: Any, path: str, diffs: list[dict]) -> bool:
    """Recursively compare two values, collecting diffs.

    Note: extra keys in result that are not in GT are recorded as
    'extra_in_result' but do NOT count as mismatches for accuracy
    calculation. The GT defines the expected contract; extra output
    fields are acceptable.
    """
    if gt_val is None and result_val is None:
        return True
    if gt_val is None:
        diffs.append({"path": path, "gt": None, "result": result_val, "type": "missing_in_gt"})
        return False
    if result_val is None:
        diffs.append({"path": path, "gt": gt_val, "result": None, "type": "missing_in_result"})
        return False

    if type(gt_val) != type(result_val):
        # Try numeric comparison
        try:
            if float(gt_val) == float(result_val):
                return True
        except (ValueError, TypeError):
            pass
        diffs.append({"path": path, "gt": gt_val, "result": result_val, "type": "type_mismatch"})
        return False

    if isinstance(gt_val, dict):
        # Only check keys that exist in GT (extra keys in result are informational)
        all_match = True
        for k in sorted(gt_val.keys()):
            child_path = f"{path}.{k}" if path else k
            if k not in result_val:
                diffs.append({"path": child_path, "gt": gt_val[k], "result": "<MISSING>", "type": "missing_in_result"})
                all_match = False
            else:
                if not compare_values(gt_val[k], result_val[k], child_path, diffs):
                    all_match = False
        # Record extra keys in result (informational, not a mismatch)
        for k in sorted(result_val.keys()):
            if k not in gt_val:
                child_path = f"{path}.{k}" if path else k
                diffs.append({"path": child_path, "gt": "<MISSING>", "result": result_val[k], "type": "extra_in_result"})
        return all_match

    if isinstance(gt_val, list):
        # For lists of dicts (players, progressive entries), compare by index
        if len(gt_val) != len(result_val):
            diffs.append({"path": f"{path}._length", "gt": len(gt_val), "result": len(result_val), "type": "list_length"})
            # Compare up to the shorter length
            shorter = min(len(gt_val), len(result_val))
            for i in range(shorter):
                compare_values(gt_val[i], result_val[i], f"{path}[{i}]", diffs)
            return False
        all_match = True
        for i in range(len(gt_val)):
            if not compare_values(gt_val[i], result_val[i], f"{path}[{i}]", diffs):
                all_match = False
        return all_match

    # Scalar comparison — normalize strings
    if isinstance(gt_val, str) and isinstance(result_val, str):
        gt_norm = gt_val.strip().lower()
        r_norm = result_val.strip().lower()
        if gt_norm == r_norm:
            return True
        # Numeric string comparison
        try:
            if float(gt_norm) == float(r_norm):
                return True
        except ValueError:
            pass
        diffs.append({"path": path, "gt": gt_val, "result": result_val, "type": "value_mismatch"})
        return False

    if gt_val == result_val:
        return True

    diffs.append({"path": path, "gt": gt_val, "result": result_val, "type": "value_mismatch"})
    return False


def count_fields(obj: Any) -> int:
    """Count scalar fields in a nested structure."""
    if isinstance(obj, dict):
        return sum(count_fields(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(count_fields(item) for item in obj)
    return 1


def count_matches(gt_val: Any, result_val: Any) -> int:
    """Count matching scalar fields recursively."""
    if gt_val is None and result_val is None:
        return 1
    if gt_val is None or result_val is None:
        return 0
    if type(gt_val) != type(result_val):
        try:
            return 1 if float(gt_val) == float(result_val) else 0
        except (ValueError, TypeError):
            return 0

    if isinstance(gt_val, dict):
        matches = 0
        for k in gt_val.keys():
            if k in result_val:
                matches += count_matches(gt_val[k], result_val[k])
        return matches

    if isinstance(gt_val, list):
        matches = 0
        for gt_item, result_item in zip(gt_val, result_val):
            matches += count_matches(gt_item, result_item)
        return matches

    if isinstance(gt_val, str) and isinstance(result_val, str):
        gt_norm = gt_val.strip().lower()
        r_norm = result_val.strip().lower()
        if gt_norm == r_norm:
            return 1
        try:
            return 1 if float(gt_norm) == float(r_norm) else 0
        except ValueError:
            return 0

    return 1 if gt_val == result_val else 0


def evaluate_sheet(sheet_id: str) -> dict:
    """Evaluate a single sheet."""
    gt_path = DATASET_DIR / sheet_id / "ground_truth.json"
    result_path = RESULTS_DIR / sheet_id / "result.json"

    if not gt_path.exists():
        return {"sheet": sheet_id, "error": "ground_truth.json not found"}
    if not result_path.exists():
        return {"sheet": sheet_id, "error": "result.json not found"}

    gt = json.loads(gt_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))

    sections = ["header", "team_a", "team_b", "progressive_score", "footer"]
    report = {
        "sheet": sheet_id,
        "match_status": result.get("match_status"),
        "sections": {},
        "total_fields": 0,
        "total_matches": 0,
        "mismatches": [],
    }

    for section in sections:
        gt_section = gt.get(section, {})
        result_section = result.get(section, {})
        diffs: list[dict] = []
        compare_values(gt_section, result_section, section, diffs)

        field_count = count_fields(gt_section)
        match_count = count_matches(gt_section, result_section)
        accuracy = (match_count / field_count * 100) if field_count > 0 else 100.0

        mismatch_diffs = [d for d in diffs if d.get("type") != "extra_in_result"]
        report["sections"][section] = {
            "total_fields": field_count,
            "matches": match_count,
            "accuracy_pct": round(accuracy, 1),
            "mismatches": mismatch_diffs,
        }
        report["total_fields"] += field_count
        report["total_matches"] += match_count
        report["mismatches"].extend(mismatch_diffs)

    total_fields = report["total_fields"]
    total_matches = report["total_matches"]
    report["overall_accuracy"] = round(total_matches / total_fields * 100, 1) if total_fields > 0 else 100.0
    report["total_mismatches"] = len(report["mismatches"])

    return report


def print_mismatches(mismatches: list[dict], max_items: int = 15):
    """Print mismatch details grouped by type."""
    by_type: dict[str, list[dict]] = {}
    for diff in mismatches:
        by_type.setdefault(diff["type"], []).append(diff)

    for diff_type, items in by_type.items():
        print(f"    [{diff_type}] ({len(items)}):")
        for diff in items[:max_items]:
            print(f"      {diff['path']}: GT={diff['gt']!r} → RESULT={diff['result']!r}")
        if len(items) > max_items:
            print(f"      ... and {len(items) - max_items} more")


def main():
    parser = argparse.ArgumentParser(description="Evaluate OCR dataset results")
    parser.add_argument("--sheet", help="Evaluate only one sheet")
    parser.add_argument("--results-dir", default=None, help="Override results directory")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed mismatches")
    args = parser.parse_args()

    global RESULTS_DIR
    if args.results_dir:
        RESULTS_DIR = Path(args.results_dir)
        if not RESULTS_DIR.is_absolute():
            RESULTS_DIR = Path(__file__).resolve().parents[1] / RESULTS_DIR

    sheets = [args.sheet] if args.sheet else ALL_SHEETS
    reports = [evaluate_sheet(sheet) for sheet in sheets]

    if args.json:
        print(json.dumps(reports, indent=2, ensure_ascii=False))
        return

    total_fields = 0
    total_matches = 0
    total_mismatches = 0

    for report in reports:
        if "error" in report:
            print(f"ERROR {report['sheet']}: {report['error']}", file=sys.stderr)
            continue

        total_fields += report["total_fields"]
        total_matches += report["total_matches"]
        total_mismatches += report["total_mismatches"]

        print(f"\n{'='*60}")
        print(f"  {report['sheet']} — status: {report['match_status']}")
        print(f"  Overall: {report['total_matches']}/{report['total_fields']} fields match ({report['overall_accuracy']}%)")
        print(f"{'='*60}")

        for section, sr in report["sections"].items():
            status = "✓" if sr["accuracy_pct"] == 100.0 else "✗"
            print(f"\n  {status} {section}: {sr['matches']}/{sr['total_fields']} ({sr['accuracy_pct']}%)")
            if sr["mismatches"]:
                if args.verbose:
                    print_mismatches(sr["mismatches"])
                else:
                    # Summary by type
                    by_type: dict[str, int] = {}
                    for diff in sr["mismatches"]:
                        by_type[diff["type"]] = by_type.get(diff["type"], 0) + 1
                    summary = ", ".join(f"{k}:{v}" for k, v in by_type.items())
                    print(f"    mismatches: {summary}")

    if len(reports) > 1:
        print(f"\n{'='*60}")
        print("  GLOBAL SUMMARY")
        print(f"{'='*60}")
        print(f"  Sheets evaluated: {len([r for r in reports if 'error' not in r])}")
        print(f"  Total fields: {total_fields}")
        print(f"  Total matches: {total_matches}")
        print(f"  Total mismatches: {total_mismatches}")
        print(f"  Overall accuracy: {total_matches / total_fields * 100:.1f}%")

        # Per-sheet summary table
        print(f"\n  {'Sheet':<12} {'Status':<15} {'Accuracy':>10} {'Mismatches':>12}")
        print(f"  {'-'*12} {'-'*15} {'-'*10} {'-'*12}")
        for report in reports:
            if "error" in report:
                continue
            print(f"  {report['sheet']:<12} {report['match_status']:<15} {report['overall_accuracy']:>9.1f}% {report['total_mismatches']:>12}")

        # Per-section accuracy table
        print(f"\n  Per-section accuracy:")
        sections = ["header", "team_a", "team_b", "progressive_score", "footer"]
        header = f"  {'Sheet':<12}"
        for s in sections:
            header += f" {s:>17}"
        print(header)
        print(f"  {'-'*12}" + " " + " ".join("-"*17 for _ in sections))
        for report in reports:
            if "error" in report:
                continue
            row = f"  {report['sheet']:<12}"
            for s in sections:
                sr = report["sections"].get(s, {})
                row += f" {sr.get('accuracy_pct', 0):>16.1f}%"
            print(row)

        # Average per-section
        row = f"  {'AVERAGE':<12}"
        for s in sections:
            accs = [r["sections"][s]["accuracy_pct"] for r in reports if "error" not in r and s in r["sections"]]
            avg = sum(accs) / len(accs) if accs else 0
            row += f" {avg:>16.1f}%"
        print(row)


if __name__ == "__main__":
    main()
