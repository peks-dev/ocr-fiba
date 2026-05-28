"""
CV-based Progressive Score Extraction — Isolated test script (v2).

Uses Computer Vision instead of OCR to detect marked cells.
Key insight: running_scores are PRE-PRINTED (1,2,3...150), so we only
need to detect which rows have ink marks, not read the numbers.

Strategy:
1. Find row positions using contour detection of printed numbers
2. Generate regular grid from detected positions
3. Separate red ink (team_a) from black ink (team_b) by HSV color
4. For each row, check if there's ink in the team column
5. running_score = row index (known)
6. Extract dorsals via OCR on individual cell ROIs
7. Compute points = running_score[i] - running_score[i-1]

Usage:
    python cv-progressive-score.py <image_path> [--gt <ground_truth.json>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Row detection
# ---------------------------------------------------------------------------

def detect_row_positions(img: np.ndarray) -> list[tuple[int, int]]:
    """Detect row Y positions by finding printed number contours.

    Scans the team_b running_score column for printed number blobs,
    then generates a regular grid covering all rows from 1 to max.

    Returns list of (y1, y2) for each row (1-indexed: row 0 = running_score 1).
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Use the team_b number column (right-center of image)
    num_x1 = int(w * 0.60)
    num_x2 = int(w * 0.72)

    # Binarize
    binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    roi = binary[:, num_x1:num_x2]

    # Find contours
    contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter for number-like blobs
    blob_ys = []
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cv2.contourArea(c)
        if 5 < ch < 30 and 3 < cw < 25 and area > 15:
            blob_ys.append(y + ch // 2)

    if not blob_ys:
        # Fallback: use entire image height divided by expected rows
        print("  No number blobs found, using fallback row detection", file=sys.stderr)
        n_rows = 56  # typical FIBA sheet
        cell_h = h / n_rows
        return [(int(i * cell_h), int((i + 1) * cell_h)) for i in range(n_rows)]

    # Sort and deduplicate
    blob_ys = sorted(set(blob_ys))

    # Group nearby Ys (within 10px = same row)
    groups = []
    current = [blob_ys[0]]
    for y in blob_ys[1:]:
        if y - current[-1] <= 10:
            current.append(y)
        else:
            groups.append(int(np.mean(current)))
            current = [y]
    groups.append(int(np.mean(current)))

    print(f"  Detected {len(groups)} row positions from contours", file=sys.stderr)

    # Calculate median spacing
    if len(groups) < 2:
        cell_h = h / 56
        return [(int(i * cell_h), int((i + 1) * cell_h)) for i in range(56)]

    spacings = [groups[i + 1] - groups[i] for i in range(len(groups) - 1)]
    median_spacing = int(np.median(spacings))

    # Filter outlier spacings and recalculate
    clean_spacings = [s for s in spacings if abs(s - median_spacing) < median_spacing * 0.6]
    if clean_spacings:
        median_spacing = int(np.median(clean_spacings))

    print(f"  Median spacing: {median_spacing}px", file=sys.stderr)

    # Generate regular grid from first detected row to last
    y_first = groups[0]
    y_last = groups[-1]
    n_detected = len(groups)
    n_total = round((y_last - y_first) / median_spacing) + 1

    # Extend: some rows before first detected and after last
    # First row is typically rs=1, check if y_first is close to top
    y_start = y_first % median_spacing  # align to grid
    if y_start < median_spacing // 2:
        y_start = y_first - (y_first % median_spacing)
    else:
        y_start = y_first

    # Generate all rows
    rows = []
    y = y_start
    while y + median_spacing <= h:
        rows.append((y, y + median_spacing))
        y += median_spacing
        if len(rows) > 160:  # safety limit
            break

    print(f"  Generated {len(rows)} regular rows", file=sys.stderr)
    return rows


# ---------------------------------------------------------------------------
# Ink detection
# ---------------------------------------------------------------------------

def create_ink_masks(img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Create masks for red ink (team_a) and black ink (team_b + dorsals)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Red ink mask (team_a) — handles both hue ranges
    mask_red1 = cv2.inRange(hsv, (0, 60, 60), (10, 255, 255))
    mask_red2 = cv2.inRange(hsv, (170, 60, 60), (180, 255, 255))
    red_mask = mask_red1 | mask_red2

    # Black/dark ink mask
    black_mask = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)[1]
    # Remove red from black mask
    black_mask = black_mask & ~red_mask

    return red_mask, black_mask


def cell_has_ink(mask: np.ndarray, x1: int, x2: int, y1: int, y2: int,
                 threshold: float = 0.003) -> bool:
    """Check if a cell has enough ink to be considered marked."""
    cell = mask[max(0, y1):y2, max(0, x1):x2]
    if cell.size == 0:
        return False
    return np.count_nonzero(cell) / cell.size > threshold


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract_progressive_score(image_path: Path) -> dict:
    """Extract progressive score using CV for cell detection."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")

    h, w = img.shape[:2]

    # 1. Detect rows
    print("Detecting rows...", file=sys.stderr)
    rows = detect_row_positions(img)

    # 2. Create ink masks
    print("Creating ink masks...", file=sys.stderr)
    red_mask, black_mask = create_ink_masks(img)

    # 3. Column boundaries
    # Dorsal column: left portion
    dorsal_x1 = int(w * 0.0)
    dorsal_x2 = int(w * 0.15)
    # Team A running score column: where red ink is
    team_a_x1 = int(w * 0.15)
    team_a_x2 = int(w * 0.50)
    # Team B running score column: right portion
    team_b_x1 = int(w * 0.50)
    team_b_x2 = int(w * 0.85)

    # 4. Scan each row for marks
    team_a_events = []
    team_b_events = []

    print("Scanning rows for marks...", file=sys.stderr)
    for i, (y1, y2) in enumerate(rows):
        running_score = i + 1

        # Team A: check for red ink in team_a column
        if cell_has_ink(red_mask, team_a_x1, team_a_x2, y1, y2):
            team_a_events.append({
                "period": None,
                "player_number": None,
                "points": None,
                "running_score": running_score,
                "_row": (y1, y2),
            })

        # Team B: check for black ink in team_b column
        if cell_has_ink(black_mask, team_b_x1, team_b_x2, y1, y2):
            team_b_events.append({
                "period": None,
                "player_number": None,
                "points": None,
                "running_score": running_score,
                "_row": (y1, y2),
            })

    print(f"Team A: {len(team_a_events)} marked rows", file=sys.stderr)
    print(f"Team B: {len(team_b_events)} marked rows", file=sys.stderr)

    # 5. Compute points
    for events in [team_a_events, team_b_events]:
        prev_rs = 0
        for e in events:
            rs = e["running_score"]
            diff = rs - prev_rs
            if 1 <= diff <= 3:
                e["points"] = diff
            prev_rs = rs

    # Clean internal fields
    def clean(events):
        return [{k: v for k, v in e.items() if not k.startswith("_")} for e in events]

    return {
        "team_a": clean(team_a_events),
        "team_b": clean(team_b_events),
    }


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(result: dict, gt_path: Path) -> None:
    """Compare against ground truth."""
    gt = json.loads(gt_path.read_text())
    gt_ps = gt["progressive_score"]

    total_match = 0
    total_fields = 0

    for team in ["team_a", "team_b"]:
        events = result.get(team, [])
        gt_events = gt_ps.get(team, [])

        rs_match = 0
        pts_match = 0
        total = min(len(events), len(gt_events))

        print(f"\n=== {team} ===")
        print(f"Events: {len(events)} (GT: {len(gt_events)})")

        for i in range(total):
            e = events[i]
            g = gt_events[i]
            rs_ok = e["running_score"] == g["running_score"]
            pts_ok = e.get("points") == g.get("points")

            if rs_ok:
                rs_match += 1
            if pts_ok:
                pts_match += 1

            if not rs_ok or not pts_ok:
                rs_s = "✓" if rs_ok else "✗"
                pts_s = "✓" if pts_ok else "✗"
                print(f"  [{i}] rs:{rs_s} {e['running_score']:>3} (GT={g['running_score']:>3})  "
                      f"pts:{pts_s} {e.get('points', '?'):>2} (GT={g['points']:>2})")

        if total > 0:
            print(f"  Running_score: {rs_match}/{total} ({rs_match / total * 100:.1f}%)")
            print(f"  Points: {pts_match}/{total} ({pts_match / total * 100:.1f}%)")
            total_match += rs_match + pts_match
            total_fields += total * 2

    if total_fields > 0:
        print(f"\n=== TOTAL: {total_match}/{total_fields} ({total_match / total_fields * 100:.1f}%) ===")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="CV-based progressive score extraction")
    parser.add_argument("image", type=Path, help="Progressive score crop image")
    parser.add_argument("--gt", type=Path, default=None, help="Ground truth JSON")
    args = parser.parse_args()

    if not args.image.exists():
        print(f"Error: {args.image} not found")
        return

    result = extract_progressive_score(args.image)

    # Output JSON
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Evaluate
    if args.gt and args.gt.exists():
        evaluate(result, args.gt)


if __name__ == "__main__":
    main()
