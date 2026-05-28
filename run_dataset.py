"""
Batch runner: process the entire FIBA scoresheet dataset through the pipeline.

Usage:
    python run_dataset.py [--skip SHEET_ID ...]

Outputs are organized under dataset/results/<sheet-xxx>/ with:
  - <stem>-recortada.jpg   (preprocessed sheet image)
  - *.png                   (section crops: header, team_a, team_b, etc.)
  - boxes.json, fouls_boxes.json
  - result.json             (final extracted + validated JSON)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from helpers.image_utils import load_dotenv
from config.pipeline_config import PipelineConfig
from core.pipeline import FibaOcrPipeline
from core.exceptions import OcrEngineError

DATASET_DIR = Path(__file__).resolve().parent / "dataset"
RESULTS_DIR = DATASET_DIR / "results"

# Sheets to process (sheet-006 excluded — no usable image)
ALL_SHEETS = [
    "sheet-001",
    "sheet-002",
    "sheet-003",
    "sheet-004",
    "sheet-005",
    "sheet-007",
    "sheet-008",
    "sheet-009",
    "sheet-010",
]


def find_image(sheet_dir: Path) -> Path | None:
    """Find the .jpg image inside a sheet directory."""
    imgs = sorted(sheet_dir.glob("*.jpg"))
    return imgs[0] if imgs else None


def main():
    parser = argparse.ArgumentParser(description="Run OCR pipeline on the full dataset")
    parser.add_argument(
        "--skip",
        nargs="*",
        default=[],
        help="Sheet IDs to skip (e.g. --skip sheet-003 sheet-008)",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Only process these sheet IDs (e.g. --only sheet-010)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Override results directory (e.g. --output-dir results-new)",
    )
    parser.add_argument(
        "--run-layout",
        action="store_true",
        help="Guardar cada hoja en layout auditable runs/{run_id}/",
    )
    parser.add_argument(
        "--runs-dir",
        type=str,
        default=None,
        help="Directorio base para --run-layout (default: dataset/runs)",
    )
    parser.add_argument(
        "--grid-removal",
        choices=["inpaint", "handwriting"],
        default=None,
        help="Enable grid line removal on progressive_score section. "
             "'inpaint': morphological + cv2.inpaint. "
             "'handwriting': grid removal + restore handwritten marks.",
    )
    parser.add_argument(
        "--gamma",
        type=float,
        default=None,
        help="Gamma correction value (e.g. 0.7 to darken overexposed images). "
             "Default: 0.7 (enabled). Use --gamma 1.0 to disable.",
    )
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parent / ".env")

    sheets = args.only if args.only else [s for s in ALL_SHEETS if s not in args.skip]

    if args.run_layout and args.output_dir:
        print("Error: --output-dir no se puede combinar con --run-layout. Usa --runs-dir.", file=sys.stderr)
        sys.exit(1)

    results_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR
    runs_dir = Path(args.runs_dir) if args.runs_dir else DATASET_DIR / "runs"

    config = PipelineConfig(
        cropper_provider="openrouter",
        cropper_model="google/gemini-3-flash-preview",
        extractor_provider="docstrange",
        extractor_model="nanonets-ocr-3",
        validation_plugins="all",
        grid_removal=args.grid_removal or False,
        gamma=args.gamma if args.gamma is not None else 0.7,
    )

    pipeline = FibaOcrPipeline(config)

    total_start = time.monotonic()
    results_summary: list[dict] = []

    for sheet_id in sheets:
        sheet_dir = DATASET_DIR / sheet_id
        image_path = find_image(sheet_dir)

        if image_path is None:
            print(f"\n⚠ {sheet_id}: no se encontró imagen, saltando...", file=sys.stderr)
            continue

        output_dir = None if args.run_layout else results_dir / sheet_id
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"  {sheet_id}: {image_path.name}", file=sys.stderr)
        if args.run_layout:
            print(f"  Runs dir: {runs_dir}", file=sys.stderr)
        else:
            print(f"  Output: {output_dir}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

        try:
            result = pipeline.process(
                image_path,
                output_dir=output_dir,
                runs_dir=runs_dir,
                use_run_layout=args.run_layout,
            )
            if args.run_layout:
                run_context = pipeline.last_context
                result_path = run_context.result_path if run_context else None
            else:
                result_path = output_dir / "result.json"
                pipeline.save_result(result, result_path)

            status = result.get("match_status", "unknown")
            warnings = len(result.get("validation_warnings", []))
            results_summary.append({
                "sheet": sheet_id,
                "image": image_path.name,
                "status": status,
                "warnings": warnings,
                "result_path": str(result_path) if result_path else None,
            })
            print(f"  ✓ {sheet_id}: {status} ({warnings} warnings)", file=sys.stderr)

        except OcrEngineError as exc:
            results_summary.append({
                "sheet": sheet_id,
                "image": image_path.name,
                "status": "error",
                "error": str(exc),
            })
            print(f"  ✗ {sheet_id}: ERROR — {exc}", file=sys.stderr)

    elapsed = time.monotonic() - total_start

    # Print summary
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  RESUMEN — {len(results_summary)} hojas procesadas en {elapsed:.1f}s", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    for r in results_summary:
        if r["status"] == "error":
            print(f"  ✗ {r['sheet']}: ERROR — {r['error']}", file=sys.stderr)
        else:
            print(f"  {'✓' if r['status'] == 'success' else '⚠'} {r['sheet']}: {r['status']} ({r['warnings']} warnings)", file=sys.stderr)

    success_count = sum(1 for r in results_summary if r["status"] == "success")
    review_count = sum(1 for r in results_summary if r["status"] == "needs_review")
    error_count = sum(1 for r in results_summary if r["status"] == "error")
    print(f"\n  success: {success_count} | needs_review: {review_count} | error: {error_count}", file=sys.stderr)


if __name__ == "__main__":
    main()
