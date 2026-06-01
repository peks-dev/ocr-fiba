"""
Test: Preprocessing variants for progressive_score section.

Compares multiple preprocessing approaches:
1. ORIGINAL — no preprocessing (just the cropped section)
2. NO-GRID (inpaint) — morphological grid detection + cv2.inpaint
3. INK ISOLATION (HSV) — extract only colored ink on white background

Usage:
    python test_grid_removal.py [sheet_id] [--all]
    
    Default: sheet-007
    --all: test on all sheets (no extraction, just save images)
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from ocr_engine_core.utils.image_utils import load_dotenv
from ocr_engine_core.config.pipeline_config import PipelineConfig
from ocr_engine_core.extractor import Extractor, ExtractionTarget, TARGETS
from ocr_engine_core.providers.base import TokenUsage

DATASET_DIR = Path.cwd() / "dataset"


def remove_grid_lines(
    img: np.ndarray,
    scale: int = 40,
    dilate_px: int = 2,
    inpaint_method: int = cv2.INPAINT_TELEA,
    inpaint_radius: int = 3,
) -> np.ndarray:
    """Remove printed grid lines from a document image using morphological operations.
    
    Algorithm:
    1. Convert to grayscale → adaptive threshold (invert: lines/text = white)
    2. Create horizontal and vertical kernels
    3. MORPH_OPEN with each kernel → isolates only long lines
    4. Combine H+V masks → grid_mask
    5. Dilate mask slightly to cover line edges
    6. Inpaint the masked regions (fill with surrounding background)
    
    Args:
        img: BGR image as numpy array.
        scale: Divisor for kernel length (img_width // scale = kernel width).
        dilate_px: Pixels to dilate the grid mask (covers line edges).
        inpaint_method: cv2.INPAINT_TELEA or cv2.INPAINT_NS.
        inpaint_radius: Radius for inpainting algorithm.
    
    Returns:
        Image with grid lines removed (BGR).
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Adaptive threshold — handles uneven lighting
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 51, 10
    )
    
    # Horizontal lines kernel
    hor_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (img.shape[1] // scale, 1)
    )
    mask_h = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, hor_kernel, iterations=1)
    
    # Vertical lines kernel
    ver_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (1, img.shape[0] // scale)
    )
    mask_v = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, ver_kernel, iterations=1)
    
    # Combine masks
    grid_mask = cv2.add(mask_h, mask_v)
    
    # Dilate to cover line edges
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (dilate_px, dilate_px))
    grid_mask = cv2.dilate(grid_mask, dilate_kernel, iterations=1)
    
    # Inpaint: fill grid regions with surrounding background
    result = cv2.inpaint(img, grid_mask, inpaint_radius, inpaint_method)
    
    return result, grid_mask


def isolate_colored_ink(
    img: np.ndarray,
    saturation_min: int = 45,
    value_min: int = 50,
    dilate_px: int = 2,
    background: tuple[int, int, int] = (255, 255, 255),
) -> np.ndarray:
    """Extract only colored ink (red/blue handwriting) onto a clean background.
    
    FIBA scoresheets use black/gray printed grids with red and blue handwritten
    marks. This function isolates the colored ink pixels and places them on a
    uniform background, completely eliminating the printed grid.
    
    Algorithm:
    1. Convert to HSV
    2. Detect colored pixels: saturation > threshold AND value > threshold
       This catches red, blue, and any colored pen marks but NOT black/gray print
    3. Dilate the ink mask slightly to preserve full stroke width
    4. Create output image: background color everywhere, original pixels where ink
    
    Args:
        img: BGR image as numpy array.
        saturation_min: Min HSV saturation to consider as "ink" (0-255).
        value_min: Min HSV value/brightness to consider as "ink" (0-255).
        dilate_px: Pixels to dilate the ink mask (preserves stroke edges).
        background: BGR color for the background (default: white).
    
    Returns:
        Image with only colored ink on clean background (BGR).
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    
    ink_mask = (
        (saturation >= saturation_min) & (value >= value_min)
    ).astype(np.uint8) * 255
    
    if dilate_px > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (dilate_px * 2 + 1, dilate_px * 2 + 1))
        ink_mask = cv2.dilate(ink_mask, kernel, iterations=1)
    
    result = np.full_like(img, background, dtype=np.uint8)
    result[ink_mask > 0] = img[ink_mask > 0]
    
    return result, ink_mask


def remove_grid_protect_ink(
    img: np.ndarray,
    scale: int = 40,
    dilate_px: int = 2,
    inpaint_method: int = cv2.INPAINT_TELEA,
    inpaint_radius: int = 3,
    saturation_min: int = 45,
    value_min: int = 50,
    ink_dilate_px: int = 3,
) -> np.ndarray:
    """Remove grid lines via inpainting but restore colored ink pixels afterward.
    
    Hybrid approach: standard morphological grid removal + inpainting, but
    colored ink pixels (red/blue handwriting) are restored from the original
    image after inpainting. This preserves marks that cross grid lines while
    still removing the grid structure.
    
    Algorithm:
    1. Detect colored ink via HSV (same as isolate_colored_ink)
    2. Dilate ink mask to protect full stroke width
    3. Run standard grid removal (morphological + inpaint)
    4. Restore original pixels where ink mask is active
    
    Args:
        img: BGR image as numpy array.
        scale: Divisor for kernel length (img_width // scale = kernel width).
        dilate_px: Pixels to dilate the grid mask.
        inpaint_method: cv2.INPAINT_TELEA or cv2.INPAINT_NS.
        inpaint_radius: Radius for inpainting algorithm.
        saturation_min: Min HSV saturation to consider as "ink" (0-255).
        value_min: Min HSV value/brightness to consider as "ink" (0-255).
        ink_dilate_px: Pixels to dilate the ink protection mask.
    
    Returns:
        Image with grid removed but colored ink preserved (BGR).
    """
    # Step 1: Detect colored ink
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    ink_mask = (
        (hsv[:, :, 1] >= saturation_min) & (hsv[:, :, 2] >= value_min)
    ).astype(np.uint8) * 255
    
    # Dilate ink mask to protect full stroke width
    if ink_dilate_px > 0:
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (ink_dilate_px * 2 + 1, ink_dilate_px * 2 + 1)
        )
        ink_mask = cv2.dilate(ink_mask, kernel, iterations=1)
    
    # Step 2: Standard grid removal via inpainting
    inpainted, grid_mask = remove_grid_lines(
        img, scale=scale, dilate_px=dilate_px,
        inpaint_method=inpaint_method, inpaint_radius=inpaint_radius,
    )
    
    # Step 3: Restore original pixels where ink was detected
    result = inpainted.copy()
    result[ink_mask > 0] = img[ink_mask > 0]
    
    return result, grid_mask, ink_mask


def remove_grid_protect_handwriting(
    img: np.ndarray,
    scale: int = 40,
    dilate_px: int = 2,
    inpaint_method: int = cv2.INPAINT_TELEA,
    inpaint_radius: int = 3,
    saturation_min: int = 45,
    value_min: int = 50,
    short_line_max: int = 30,
) -> np.ndarray:
    """Remove grid lines via inpainting, protect only handwritten marks (not colored grid lines).
    
    The key insight: FIBA scoresheets have BOTH black and colored (red/blue) grid
    lines. Simple HSV ink protection also restores the colored grid lines, undoing
    the grid removal. This variant distinguishes handwriting from grid lines by
    morphology: handwriting is short/thick, grid lines are long/thin.
    
    Algorithm:
    1. Detect all colored pixels via HSV (saturation + value thresholds)
    2. Remove long thin structures from the ink mask (morphological opening)
       → This eliminates colored grid lines while keeping handwritten marks
    3. Run standard grid removal (morphological + inpaint)
    4. Restore original pixels where handwriting mask is active
    
    Args:
        img: BGR image as numpy array.
        scale: Divisor for kernel length for grid detection.
        dilate_px: Pixels to dilate the grid mask.
        inpaint_method: cv2.INPAINT_TELEA or cv2.INPAINT_NS.
        inpaint_radius: Radius for inpainting algorithm.
        saturation_min: Min HSV saturation to consider as "ink" (0-255).
        value_min: Min HSV value/brightness to consider as "ink" (0-255).
        short_line_max: Max length (px) for a structure to be considered
            handwriting. Lines longer than this are treated as grid.
    
    Returns:
        Image with grid removed, only handwritten marks preserved (BGR).
    """
    # Step 1: Detect all colored pixels
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    colored_mask = (
        (hsv[:, :, 1] >= saturation_min) & (hsv[:, :, 2] >= value_min)
    ).astype(np.uint8) * 255
    
    # Step 2: Remove long thin structures (grid lines) from the ink mask
    # Use morphological opening with a short kernel — this removes long lines
    # but keeps short thick marks (handwritten numbers, check marks, etc.)
    # Horizontal short kernel: removes long horizontal colored grid lines
    short_h = cv2.getStructuringElement(cv2.MORPH_RECT, (short_line_max, 1))
    mask_h = cv2.morphologyEx(colored_mask, cv2.MORPH_OPEN, short_h, iterations=1)
    
    # Vertical short kernel: removes long vertical colored grid lines
    short_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, short_line_max))
    mask_v = cv2.morphologyEx(colored_mask, cv2.MORPH_OPEN, short_v, iterations=1)
    
    # Handwriting = colored pixels that are NOT long lines
    # (i.e., short/thick structures that survived the opening)
    handwriting_mask = cv2.add(mask_h, mask_v)
    
    # Dilate handwriting mask to protect full stroke width
    protect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    handwriting_mask = cv2.dilate(handwriting_mask, protect_kernel, iterations=1)
    
    # Step 3: Standard grid removal via inpainting
    inpainted, grid_mask = remove_grid_lines(
        img, scale=scale, dilate_px=dilate_px,
        inpaint_method=inpaint_method, inpaint_radius=inpaint_radius,
    )
    
    # Step 4: Restore original pixels only where handwriting was detected
    result = inpainted.copy()
    result[handwriting_mask > 0] = img[handwriting_mask > 0]
    
    return result, grid_mask, handwriting_mask


def extract_progressive_score(image_path: Path, api_key: str) -> dict:
    """Run nanonets extraction on a progressive_score image."""
    from ocr_engine_core.providers import create_provider, ProviderType
    
    provider = create_provider(
        "docstrange",
        "nanonets-ocr-3",
        api_key,
    )
    
    # Find the progressive_score target
    target = None
    for t in TARGETS:
        if t.name == "progressive_score":
            target = t
            break
    
    if target is None:
        raise ValueError("progressive_score target not found")
    
    result, usage = provider.structured_completion(
        image_path=image_path,
        prompt=target.prompt,
        schema=__import__("schemas").load_schema("progressive_score", provider="docstrange"),
        max_tokens=6000,
        agentic_mode=True,
    )
    
    return result


def compare_with_gt(result: dict, gt_path: Path) -> dict:
    """Compare extraction result against ground truth."""
    gt = json.loads(gt_path.read_text(encoding="utf-8"))
    gt_ps = gt.get("progressive_score", {})
    gt_a = gt_ps.get("team_a", [])
    gt_b = gt_ps.get("team_b", [])
    
    a = result.get("team_a", [])
    b = result.get("team_b", [])
    
    a_correct = 0
    for i, gt_e in enumerate(gt_a):
        if i < len(a):
            e = a[i]
            pn_match = str(e.get("player_number", "")) == str(gt_e.get("player_number", ""))
            rs_match = e.get("running_score") == gt_e.get("running_score")
            if pn_match and rs_match:
                a_correct += 1
    
    b_correct = 0
    for i, gt_e in enumerate(gt_b):
        if i < len(b):
            e = b[i]
            pn_match = str(e.get("player_number", "")) == str(gt_e.get("player_number", ""))
            rs_match = e.get("running_score") == gt_e.get("running_score")
            if pn_match and rs_match:
                b_correct += 1
    
    return {
        "team_a_correct": a_correct,
        "team_a_total": len(gt_a),
        "team_a_pct": a_correct / len(gt_a) * 100 if gt_a else 0,
        "team_b_correct": b_correct,
        "team_b_total": len(gt_b),
        "team_b_pct": b_correct / len(gt_b) * 100 if gt_b else 0,
    }


def main():
    load_dotenv(Path.cwd() / ".env")
    
    # Parse args
    test_all = "--all" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--all"]
    sheet_id = args[0] if args else "sheet-007"
    
    api_key = os.environ.get("DOCSTRANGE_API_KEY", "")
    
    sheets = [
        "sheet-001", "sheet-002", "sheet-003", "sheet-004", "sheet-005",
        "sheet-007", "sheet-008", "sheet-009", "sheet-010",
    ] if test_all else [sheet_id]
    
    for sheet_id in sheets:
        # Use the existing cropped section image (from results-new, which has no grid removal)
        section_img = DATASET_DIR / "results-new" / sheet_id / "progressive_score.png"
        if not section_img.exists():
            print(f"{sheet_id}: image not found at {section_img}")
            continue
        
        gt_path = DATASET_DIR / sheet_id / "ground_truth.json"
        
        print(f"\nProcessing: {section_img}")
        img = cv2.imread(str(section_img))
        print(f"Image size: {img.shape}")
        
        # Apply preprocessing variants
        cleaned_inpaint, grid_mask = remove_grid_lines(img)
        cleaned_ink, ink_mask = isolate_colored_ink(img)
        cleaned_hybrid, grid_mask2, ink_mask2 = remove_grid_protect_ink(img)
        cleaned_handwriting, grid_mask3, hw_mask = remove_grid_protect_handwriting(img)
        
        # Save outputs
        out_dir = Path(f"/tmp/ink-isolation-test/{sheet_id}")
        out_dir.mkdir(parents=True, exist_ok=True)
        
        cv2.imwrite(str(out_dir / "original.png"), img)
        cv2.imwrite(str(out_dir / "no_grid_inpaint.png"), cleaned_inpaint)
        cv2.imwrite(str(out_dir / "ink_isolation.png"), cleaned_ink)
        cv2.imwrite(str(out_dir / "hybrid_grid_ink.png"), cleaned_hybrid)
        cv2.imwrite(str(out_dir / "handwriting_protect.png"), cleaned_handwriting)
        cv2.imwrite(str(out_dir / "ink_mask.png"), ink_mask)
        cv2.imwrite(str(out_dir / "grid_mask.png"), grid_mask)
        cv2.imwrite(str(out_dir / "hw_mask.png"), hw_mask)
        print(f"Saved: {out_dir}/")
        
        if test_all:
            # Just save images, no extraction (too slow for all sheets)
            continue
        
        # Extract from all versions
        print("\n=== Extracting from ORIGINAL ===")
        result_orig = extract_progressive_score(section_img, api_key)
        
        inpaint_path = out_dir / "no_grid_inpaint.png"
        print("\n=== Extracting from NO-GRID (inpaint) ===")
        result_inpaint = extract_progressive_score(inpaint_path, api_key)
        
        ink_path = out_dir / "ink_isolation.png"
        print("\n=== Extracting from INK ISOLATION (HSV) ===")
        result_ink = extract_progressive_score(ink_path, api_key)
        
        hybrid_path = out_dir / "hybrid_grid_ink.png"
        print("\n=== Extracting from HYBRID (grid removal + ink protection) ===")
        result_hybrid = extract_progressive_score(hybrid_path, api_key)
        
        hw_path = out_dir / "handwriting_protect.png"
        print("\n=== Extracting from HANDWRITING PROTECT (grid + handwriting mask) ===")
        result_handwriting = extract_progressive_score(hw_path, api_key)
        
        # Compare with ground truth
        print("\n" + "=" * 60)
        print("COMPARISON vs GROUND TRUTH")
        print("=" * 60)
        
        for label, result in [
            ("ORIGINAL", result_orig),
            ("NO-GRID (inpaint)", result_inpaint),
            ("INK ISOLATION (HSV)", result_ink),
            ("HYBRID (grid+ink)", result_hybrid),
            ("HANDWRITING PROTECT", result_handwriting),
        ]:
            a = result.get("team_a", [])
            b = result.get("team_b", [])
            
            if gt_path.exists():
                cmp = compare_with_gt(result, gt_path)
                print(f"\n--- {label} ---")
                print(f"  Team A: {cmp['team_a_correct']}/{cmp['team_a_total']} correct ({cmp['team_a_pct']:.0f}%)")
                print(f"  Team B: {cmp['team_b_correct']}/{cmp['team_b_total']} correct ({cmp['team_b_pct']:.0f}%)")
            else:
                print(f"\n--- {label} ---")
                print(f"  Team A: {len(a)} entries, Team B: {len(b)} entries")
            
            for e in a[:5]:
                pn = e.get("player_number")
                rs = e.get("running_score")
                print(f"    dor={str(pn):>4} rs={str(rs):>3}")
            if len(a) > 5:
                print(f"    ... ({len(a)} total)")
        
        # Save results
        with open(out_dir / "result_original.json", "w") as f:
            json.dump(result_orig, f, indent=2, ensure_ascii=False)
        with open(out_dir / "result_no_grid_inpaint.json", "w") as f:
            json.dump(result_inpaint, f, indent=2, ensure_ascii=False)
        with open(out_dir / "result_ink_isolation.json", "w") as f:
            json.dump(result_ink, f, indent=2, ensure_ascii=False)
        with open(out_dir / "result_hybrid.json", "w") as f:
            json.dump(result_hybrid, f, indent=2, ensure_ascii=False)
        with open(out_dir / "result_handwriting.json", "w") as f:
            json.dump(result_handwriting, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to {out_dir}/")


if __name__ == "__main__":
    main()
