"""
Binarize a FIBA scoresheet section image for OCR testing.

Standalone utility — not part of the main pipeline.
Applies adaptive thresholding to produce a clean black-and-white image
that may improve OCR extraction on difficult sections.

Usage:
    python binarize_image.py <input_image> [output_image] [--method adaptive|otsu]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from ocr_engine_core.utils.image_utils import read_image, write_png


def binarize_adaptive(image_path: Path, output_path: Path, block_size: int = 15, c: int = 10) -> Path:
    """Binarize using adaptive Gaussian thresholding.

    Good for images with uneven lighting — computes threshold
    per-region using a Gaussian-weighted window.
    """
    img = read_image(image_path)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Adaptive threshold — Gaussian weighted, binary inverse
    # (ink is dark on light paper, so THRESH_BINARY_INV makes ink=white on black)
    # Then invert back to black ink on white paper for OCR
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, block_size, c
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_png(output_path, binary)
    print(f"Binarizada (adaptive, block={block_size}, C={c}): {output_path}")
    return output_path


def binarize_otsu(image_path: Path, output_path: Path) -> Path:
    """Binarize using Otsu's global threshold.

    Good for images with even lighting and strong contrast.
    Automatically finds the optimal global threshold.
    """
    img = read_image(image_path)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Otsu's threshold
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_png(output_path, binary)
    print(f"Binarizada (otsu): {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Binarize a FIBA section image for OCR testing")
    parser.add_argument("input", type=Path, help="Input image path")
    parser.add_argument("output", nargs="?", type=Path, default=None,
                        help="Output path (default: <input>-binarizada.png)")
    parser.add_argument("--method", choices=["adaptive", "otsu", "both"], default="both",
                        help="Binarization method (default: both)")
    parser.add_argument("--block-size", type=int, default=15,
                        help="Adaptive threshold block size (odd, default: 15)")
    parser.add_argument("--c", type=int, default=10,
                        help="Adaptive threshold C constant (default: 10)")
    args = parser.parse_args()

    input_path = args.input
    if not input_path.exists():
        print(f"Error: no existe {input_path}")
        return

    if args.method in ("adaptive", "both"):
        out = args.output or input_path.with_name(f"{input_path.stem}-adaptive.png")
        binarize_adaptive(input_path, out, block_size=args.block_size, c=args.c)

    if args.method in ("otsu", "both"):
        out = args.output or input_path.with_name(f"{input_path.stem}-otsu.png")
        binarize_otsu(input_path, out)


if __name__ == "__main__":
    main()
