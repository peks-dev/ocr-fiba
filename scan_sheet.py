from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageEnhance


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
PADDING_RATIO = 0.03


def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect


def expand_quad(pts, image_shape, padding_ratio=PADDING_RATIO):
    rect = order_points(pts)
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


def find_sheet_contour(gray, min_area):
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blur, 50, 150)
    edged = cv2.dilate(edged, np.ones((5, 5), np.uint8), iterations=2)
    edged = cv2.erode(edged, np.ones((5, 5), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for c in contours[:50]:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        area = cv2.contourArea(c)

        if len(approx) == 4 and area > min_area:
            return approx.reshape(4, 2)

    return None


def preprocess_for_detection(gray):
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    normalized = cv2.normalize(enhanced, None, 0, 255, cv2.NORM_MINMAX)
    return normalized


def rotate_image(image, angle):
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


def apply_inverse_rotation(points, matrix):
    inverse = cv2.invertAffineTransform(matrix)
    transformed = cv2.transform(points.reshape(-1, 1, 2).astype(np.float32), inverse)
    return transformed.reshape(-1, 2)


def estimate_rotation_angle(gray, min_area):
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


def scan_sheet(input_path, output_path):
    img = cv2.imread(str(input_path))
    if img is None:
        raise ValueError(f"No se pudo abrir la imagen: {input_path}")

    orig = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    min_area = max(1_000_000, int(img.shape[0] * img.shape[1] * 0.08))

    chosen = find_sheet_contour(gray, min_area)
    if chosen is None:
        preprocessed = preprocess_for_detection(gray)
        chosen = find_sheet_contour(preprocessed, min_area)
        if chosen is None:
            angle = estimate_rotation_angle(preprocessed, min_area)
            if abs(angle) >= 3:
                rotated_gray, rotation_matrix = rotate_image(preprocessed, angle)
                rotated_chosen = find_sheet_contour(rotated_gray, min_area)
                if rotated_chosen is not None:
                    chosen = apply_inverse_rotation(rotated_chosen, rotation_matrix)

    if chosen is None:
        raise ValueError("No se pudo detectar un contorno de 4 puntos para la hoja")

    rect = expand_quad(chosen, img.shape)
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

    cv2.imwrite(str(output_path), warp, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

    pil = Image.open(output_path)
    pil = ImageEnhance.Contrast(pil).enhance(1.08)
    pil = ImageEnhance.Sharpness(pil).enhance(1.15)
    pil.save(output_path, quality=95)


def build_output_path(input_path):
    suffix = input_path.suffix if input_path.suffix else ".jpg"
    return OUTPUT_DIR / f"{input_path.stem}-recortada{suffix}"


def main():
    if len(sys.argv) != 2:
        print("Uso: python scan_sheet.py imagen.jpg")
        sys.exit(1)

    input_arg = Path(sys.argv[1])
    input_path = input_arg if input_arg.is_absolute() else BASE_DIR / input_arg

    if not input_path.exists():
        print(f"No existe la imagen: {input_path}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = build_output_path(input_path)

    scan_sheet(input_path, output_path)
    print(f"Guardado en: {output_path}")


if __name__ == "__main__":
    main()
