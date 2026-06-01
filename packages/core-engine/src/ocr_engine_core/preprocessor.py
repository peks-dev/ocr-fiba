"""
Sheet Preprocessor — Isolate and enhance the FIBA scoresheet from a raw photo.

Detects the sheet contour in the image, corrects perspective distortion,
and applies contrast/sharpness enhancement. This step is critical for
reliable OCR: without it, background clutter and perspective skew degrade
extraction quality significantly.

Migrated from the legacy standalone sheet scanner into pipeline step 0.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance

PADDING_RATIO = 0.03
EXPECTED_ASPECT_RATIO = 1.32


def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect


def _expand_quad(pts: np.ndarray, image_shape: tuple, padding_ratio: float = PADDING_RATIO) -> np.ndarray:
    rect = _order_points(pts)
    center = rect.mean(axis=0)
    expanded = []

    for point in rect:
        vector = point - center
        expanded_point = point + (vector * padding_ratio)
        expanded.append(expanded_point)

    expanded = np.array(expanded, dtype="float32")
    expanded[:, 0] = np.clip(expanded[:, 0], 0, image_shape[1] - 1)
    expanded[:, 1] = np.clip(expanded[:, 1], 0, image_shape[0] - 1)
    return expanded


def _contour_metrics(points: np.ndarray, image_shape: tuple) -> dict[str, float]:
    rect = _order_points(points.astype("float32"))
    image_h, image_w = image_shape[:2]

    width_a = np.linalg.norm(rect[2] - rect[3])
    width_b = np.linalg.norm(rect[1] - rect[0])
    width = max(width_a, width_b)

    height_a = np.linalg.norm(rect[1] - rect[2])
    height_b = np.linalg.norm(rect[0] - rect[3])
    height = max(height_a, height_b)

    x_min = float(np.min(rect[:, 0]))
    x_max = float(np.max(rect[:, 0]))
    y_min = float(np.min(rect[:, 1]))
    y_max = float(np.max(rect[:, 1]))

    border_margin = min(image_w, image_h) * 0.01
    touches = sum(
        (
            x_min <= border_margin,
            y_min <= border_margin,
            x_max >= image_w - 1 - border_margin,
            y_max >= image_h - 1 - border_margin,
        )
    )

    return {
        "aspect": height / width if width else 0.0,
        "coverage": (width * height) / float(image_w * image_h),
        "top": y_min / float(image_h),
        "bottom": y_max / float(image_h),
        "touches": float(touches),
    }


def _score_sheet_candidate(points: np.ndarray, area: float, image_shape: tuple) -> float:
    metrics = _contour_metrics(points, image_shape)
    image_area = float(image_shape[0] * image_shape[1])
    area_ratio = area / image_area

    aspect_score = max(0.0, 1.0 - abs(metrics["aspect"] - EXPECTED_ASPECT_RATIO) / 0.45)
    area_score = min(area_ratio / 0.70, 1.0)
    top_score = max(0.0, 1.0 - metrics["top"] / 0.25)
    bottom_score = min(metrics["bottom"] / 0.88, 1.0)
    border_penalty = metrics["touches"] * 0.35

    # Very large masks usually mean the detector captured the full photo, not the paper.
    full_image_penalty = 1.5 if area_ratio > 0.94 and metrics["touches"] >= 2 else 0.0

    return (
        area_score * 2.0
        + aspect_score * 2.0
        + top_score * 1.2
        + bottom_score * 1.0
        - border_penalty
        - full_image_penalty
    )


def _find_canny_sheet_candidates(gray: np.ndarray, min_area: int) -> list[tuple[np.ndarray, float]]:
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blur, 50, 150)
    edged = cv2.dilate(edged, np.ones((5, 5), np.uint8), iterations=2)
    edged = cv2.erode(edged, np.ones((5, 5), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    candidates = []
    for c in contours[:80]:
        peri = cv2.arcLength(c, True)
        area = cv2.contourArea(c)
        if area <= min_area:
            continue

        for epsilon in (0.02, 0.03, 0.04, 0.05):
            approx = cv2.approxPolyDP(c, epsilon * peri, True)
            if len(approx) == 4:
                candidates.append((approx.reshape(4, 2), area))
                break

    return candidates


def _find_paper_mask_candidates(image: np.ndarray, min_area: int) -> list[tuple[np.ndarray, float]]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0, 0, 80), (179, 95, 255))
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (31, 31))
    open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    candidates = []
    for contour in contours[:10]:
        area = cv2.contourArea(contour)
        if area <= min_area:
            continue

        peri = cv2.arcLength(contour, True)
        quad = None
        for epsilon in (0.02, 0.03, 0.04, 0.05, 0.08):
            approx = cv2.approxPolyDP(contour, epsilon * peri, True)
            if len(approx) == 4:
                quad = approx.reshape(4, 2)
                break

        if quad is None:
            quad = cv2.boxPoints(cv2.minAreaRect(contour))

        candidates.append((quad.astype("float32"), area))

    return candidates


def _select_best_sheet_contour(
    candidates: list[tuple[np.ndarray, float]],
    image_shape: tuple,
) -> np.ndarray | None:
    if not candidates:
        return None

    scored = [
        (_score_sheet_candidate(points, area, image_shape), points)
        for points, area in candidates
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def _find_sheet_contour(gray: np.ndarray, min_area: int) -> np.ndarray | None:
    candidates = _find_canny_sheet_candidates(gray, min_area)
    return _select_best_sheet_contour(candidates, gray.shape)


def _find_best_sheet_contour(
    image: np.ndarray,
    gray: np.ndarray,
    preprocessed_gray: np.ndarray,
    min_area: int,
) -> np.ndarray | None:
    candidates = _find_canny_sheet_candidates(gray, min_area)
    candidates.extend(_find_canny_sheet_candidates(preprocessed_gray, min_area))
    candidates.extend(
        (points, area)
        for points, area in _find_paper_mask_candidates(image, min_area)
        if _contour_metrics(points, image.shape)["touches"] == 0
    )
    return _select_best_sheet_contour(candidates, image.shape)


def _preprocess_for_detection(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    normalized = cv2.normalize(enhanced, None, 0, 255, cv2.NORM_MINMAX)
    return normalized


def _rotate_image(image: np.ndarray, angle: float) -> tuple[np.ndarray, np.ndarray]:
    height, width = image.shape[:2]
    center = (width / 2.0, height / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated, matrix


def _apply_inverse_rotation(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    inverse = cv2.invertAffineTransform(matrix)
    transformed = cv2.transform(points.reshape(-1, 1, 2).astype(np.float32), inverse)
    return transformed.reshape(-1, 2)


def _estimate_rotation_angle(gray: np.ndarray, min_area: int) -> float:
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blur, 50, 150)
    edged = cv2.dilate(edged, np.ones((5, 5), np.uint8), iterations=2)
    edged = cv2.erode(edged, np.ones((5, 5), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for contour in contours[:50]:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        rect = cv2.minAreaRect(contour)
        (_, _), (width, height), angle = rect
        if width <= 0 or height <= 0:
            continue

        if width < height:
            corrected = angle - 90
        else:
            corrected = angle

        if abs(corrected) > 45:
            continue

        return corrected

    return 0.0


def preprocess_sheet(image_path: Path, output_path: Path) -> Path:
    """
    Isolate the FIBA scoresheet from a raw photo and enhance it.

    Steps:
    1. Detect the sheet contour (4-point quadrilateral)
    2. Correct perspective distortion (warp to rectangle)
    3. Enhance contrast and sharpness

    Args:
        image_path: Path to the raw photo containing a FIBA scoresheet.
        output_path: Where to save the preprocessed image.

    Returns:
        Path to the preprocessed image.

    Raises:
        ValueError: If the sheet contour cannot be detected.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"No se pudo abrir la imagen: {image_path}")

    orig = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    min_area = max(1_000_000, int(img.shape[0] * img.shape[1] * 0.08))

    preprocessed = _preprocess_for_detection(gray)
    chosen = _find_best_sheet_contour(img, gray, preprocessed, min_area)
    if chosen is None:
        chosen = _find_sheet_contour(preprocessed, min_area)
        if chosen is None:
            angle = _estimate_rotation_angle(preprocessed, min_area)
            if abs(angle) >= 3:
                rotated_gray, rotation_matrix = _rotate_image(preprocessed, angle)
                rotated_chosen = _find_sheet_contour(rotated_gray, min_area)
                if rotated_chosen is not None:
                    chosen = _apply_inverse_rotation(rotated_chosen, rotation_matrix)

    if chosen is None:
        raise ValueError("No se pudo detectar un contorno de 4 puntos para la hoja")

    rect = _expand_quad(chosen, img.shape)
    tl, tr, br, bl = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_w = int(max(width_a, width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_h = int(max(height_a, height_b))

    dst = np.array(
        [
            [0, 0],
            [max_w - 1, 0],
            [max_w - 1, max_h - 1],
            [0, max_h - 1],
        ],
        dtype="float32",
    )

    matrix = cv2.getPerspectiveTransform(rect, dst)
    warp = cv2.warpPerspective(orig, matrix, (max_w, max_h))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), warp, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

    pil = Image.open(output_path)
    pil = ImageEnhance.Contrast(pil).enhance(1.08)
    pil = ImageEnhance.Sharpness(pil).enhance(1.15)
    pil.save(output_path, quality=95)

    return output_path
