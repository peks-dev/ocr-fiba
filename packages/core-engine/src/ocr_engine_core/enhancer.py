"""
Enhancer — Image preprocessing phase for FIBA section crops.

Applies three enhancement passes:
1. CLAHE (Contrast Limited Adaptive Histogram Equalization) on L channel
   of LAB color space — improves local contrast for faint handwritten marks
   without altering colors (preserves red/blue ink distinction).
2. Grid line removal on the progressive_score section (optional, 2 modes):
   - "inpaint": morphological grid detection + cv2.inpaint
   - "handwriting": grid removal + restore handwritten marks via HSV + morphology
3. Unsharp mask sharpening on all section images to make handwritten
   marks crisper before extraction.

The enhancer modifies images IN-PLACE in the sections directory,
so the extractor always works with enhanced images.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from ocr_engine_core.utils.image_utils import read_image, write_png


# Section images to enhance (all cropped PNGs)
SECTION_IMAGES = [
    "header.png",
    "team_a.png",
    "team_b.png",
    "team_a_fouls.png",
    "team_b_fouls.png",
    "progressive_score.png",
    "footer.png",
]

# Sections that need grid line removal before sharpening
GRID_REMOVAL_SECTIONS = {"progressive_score"}

# Sections that benefit from gamma correction (darkening overexposed handwritten digits)
# Only progressive_score — gamma on other sections causes regressions (header dates, team names)
GAMMA_SECTIONS = {"progressive_score"}

# Upscale thresholds for dense progressive_score crops. The model misses rows
# when handwritten marks occupy too much of the available row height; upscaling
# increases visual separation without changing document semantics.
PROGRESSIVE_MIN_WIDTH = 1000
PROGRESSIVE_MIN_AREA = 2_400_000
PROGRESSIVE_UPSCALE_FACTOR = 1.35

# CLAHE parameters (applied to all sections)
CLAHE_CLIP_LIMIT = 1.5
CLAHE_TILE_SIZE = 8


def _apply_gamma(
    img: np.ndarray,
    gamma: float = 0.7,
) -> np.ndarray:
    """Apply gamma correction to an image via LUT.

    Gamma < 1 darkens the image (enhances faint marks on bright backgrounds).
    Gamma > 1 brightens the image (enhances details in dark regions).
    Gamma = 1 leaves the image unchanged.

    For FIBA scoresheets, gamma=0.7 is used because photos tend to be
    overexposed — darkening slightly makes handwritten marks more visible
    against the white paper background.

    Args:
        img: BGR image as numpy array.
        gamma: Gamma value. <1 darkens, >1 brightens.

    Returns:
        Gamma-corrected BGR image as numpy array.
    """
    lookup = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)]).astype(np.uint8)
    return cv2.LUT(img, lookup)


def _apply_clahe(
    img: np.ndarray,
    clip_limit: float = CLAHE_CLIP_LIMIT,
    tile_size: int = CLAHE_TILE_SIZE,
) -> np.ndarray:
    """Apply CLAHE on the L channel of LAB color space.

    CLAHE (Contrast Limited Adaptive Histogram Equalization) improves local
    contrast without amplifying noise. Applying it on the L channel of LAB
    preserves color information (critical for distinguishing red vs blue ink
    on FIBA scoresheets).

    Args:
        img: BGR image as numpy array.
        clip_limit: Contrast limit for CLAHE. Higher = more contrast
            enhancement but risk of noise amplification. 1.5 is conservative.
        tile_size: Size of the grid for histogram equalization.

    Returns:
        CLAHE-enhanced BGR image as numpy array.
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    l_clahe = clahe.apply(l)
    lab_clahe = cv2.merge([l_clahe, a, b])
    return cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)


def _remove_grid_lines(
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

    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 51, 10
    )

    hor_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (img.shape[1] // scale, 1)
    )
    mask_h = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, hor_kernel, iterations=1)

    ver_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (1, img.shape[0] // scale)
    )
    mask_v = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, ver_kernel, iterations=1)

    grid_mask = cv2.add(mask_h, mask_v)

    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (dilate_px, dilate_px))
    grid_mask = cv2.dilate(grid_mask, dilate_kernel, iterations=1)

    result = cv2.inpaint(img, grid_mask, inpaint_radius, inpaint_method)
    return result


def _remove_grid_protect_handwriting(
    img: np.ndarray,
    scale: int = 40,
    dilate_px: int = 2,
    inpaint_method: int = cv2.INPAINT_TELEA,
    inpaint_radius: int = 3,
    saturation_min: int = 45,
    value_min: int = 50,
    short_line_max: int = 30,
) -> np.ndarray:
    """Remove grid lines via inpainting, protect only handwritten marks.

    FIBA scoresheets have both black and colored (red/blue) grid lines.
    Standard inpainting erases marks crossing grid lines; simple HSV ink
    protection also restores colored grid lines. This variant distinguishes
    handwriting from grid lines by morphology: handwriting is short/thick,
    grid lines are long/thin.

    Algorithm:
    1. Detect all colored pixels via HSV (saturation + value thresholds)
    2. Remove long thin structures from the ink mask (morphological opening)
       → eliminates colored grid lines while keeping handwritten marks
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
    short_h = cv2.getStructuringElement(cv2.MORPH_RECT, (short_line_max, 1))
    mask_h = cv2.morphologyEx(colored_mask, cv2.MORPH_OPEN, short_h, iterations=1)

    short_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, short_line_max))
    mask_v = cv2.morphologyEx(colored_mask, cv2.MORPH_OPEN, short_v, iterations=1)

    handwriting_mask = cv2.add(mask_h, mask_v)

    # Dilate handwriting mask to protect full stroke width
    protect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    handwriting_mask = cv2.dilate(handwriting_mask, protect_kernel, iterations=1)

    # Step 3: Standard grid removal via inpainting
    inpainted = _remove_grid_lines(
        img, scale=scale, dilate_px=dilate_px,
        inpaint_method=inpaint_method, inpaint_radius=inpaint_radius,
    )

    # Step 4: Restore original pixels only where handwriting was detected
    result = inpainted.copy()
    result[handwriting_mask > 0] = img[handwriting_mask > 0]

    return result


def _enhance_image(img: np.ndarray) -> np.ndarray:
    """Apply unsharp mask sharpening to a single image.

    Uses Gaussian blur subtraction:
        sharpened = original + alpha * (original - blurred)
    with alpha=0.8 and sigma=1. This makes thin handwritten strokes
    crisper without amplifying noise or altering the overall appearance.

    Args:
        img: BGR image as numpy array.

    Returns:
        Enhanced BGR image as numpy array.
    """
    gaussian = cv2.GaussianBlur(img, (0, 0), sigmaX=1)
    alpha = 0.8
    sharpened = cv2.addWeighted(img, 1 + alpha, gaussian, -alpha, 0)
    sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
    return sharpened


def _upscale_dense_progressive_score(
    img: np.ndarray,
    min_width: int = PROGRESSIVE_MIN_WIDTH,
    min_area: int = PROGRESSIVE_MIN_AREA,
    factor: float = PROGRESSIVE_UPSCALE_FACTOR,
) -> tuple[np.ndarray, bool]:
    """Upscale dense progressive_score crops before OCR.

    The threshold is intentionally conservative: it targets the known failure
    mode where the crop is too narrow/dense (e.g. sheet-007) while leaving
    already large crops unchanged.
    """
    height, width = img.shape[:2]
    if width >= min_width and width * height >= min_area:
        return img, False

    new_width = int(round(width * factor))
    new_height = int(round(height * factor))
    upscaled = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
    return upscaled, True


def _normalize_grid_mode(mode: str | bool) -> str:
    """Normalize grid_removal config value to a string mode."""
    if mode is False or mode == "off":
        return "off"
    if mode is True or mode == "inpaint":
        return "inpaint"
    if mode == "handwriting":
        return "handwriting"
    raise ValueError(f"Unknown grid_removal mode: {mode!r}. Use False, 'inpaint', or 'handwriting'.")


def enhance_sections(
    sections_dir: Path,
    grid_removal: str | bool = False,
    gamma: float | None = 0.7,
) -> list[str]:
    """Apply gamma correction, grid removal, and sharpening to all section images.

    Enhancement order:
    0. Gamma correction (optional, darkens overexposed images)
    1. CLAHE contrast enhancement (all sections)
    2. Grid line removal (specific sections, when enabled)
    3. Unsharp mask sharpening (all sections)

    Images are modified IN-PLACE (overwritten with enhanced version).

    Args:
        sections_dir: Directory containing cropped section PNGs.
        grid_removal: Grid removal mode:
            False / "off" — no grid removal (default)
            True / "inpaint" — morphological grid detection + cv2.inpaint
            "handwriting" — grid removal + restore handwritten marks
        gamma: Gamma correction value. None or 1.0 disables gamma.
            0.7 darkens (recommended for overexposed FIBA photos).

    Returns:
        List of enhanced image names.
    """
    mode = _normalize_grid_mode(grid_removal)

    enhanced = []
    for image_name in SECTION_IMAGES:
        image_path = sections_dir / image_name
        if not image_path.exists():
            continue

        try:
            img = read_image(image_path)
        except ValueError:
            continue

        # Step 0: Gamma correction (only for sections that benefit from it)
        section_key = image_name.replace(".png", "")
        if section_key == "progressive_score":
            img, _ = _upscale_dense_progressive_score(img)

        if gamma is not None and gamma != 1.0 and section_key in GAMMA_SECTIONS:
            img = _apply_gamma(img, gamma=gamma)

        # Step 1: CLAHE contrast enhancement (all sections)
        img = _apply_clahe(img)

        # Step 2: Grid removal for specific sections
        if section_key in GRID_REMOVAL_SECTIONS and mode != "off":
            if mode == "inpaint":
                img = _remove_grid_lines(img)
            elif mode == "handwriting":
                img = _remove_grid_protect_handwriting(img)

        # Step 3: Sharpening for all sections
        enhanced_img = _enhance_image(img)
        write_png(image_path, enhanced_img)
        enhanced.append(image_name)

    return enhanced
