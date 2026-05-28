"""Shared image and environment utilities."""

from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path

import cv2
import numpy as np


def encode_file(path: Path) -> str:
    """Encode a file to base64 ASCII string."""
    return base64.b64encode(path.read_bytes()).decode("ascii")


def guess_mime_type(path: Path) -> str:
    """Guess MIME type from filename, defaulting to image/jpeg."""
    mime_type, _ = mimetypes.guess_type(path.name)
    return mime_type or "image/jpeg"


def read_image(path: Path) -> np.ndarray:
    """Read an image using OpenCV (color mode)."""
    buffer = np.frombuffer(path.read_bytes(), dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"No se pudo abrir la imagen: {path}")
    return image


def write_png(path: Path, image: np.ndarray) -> None:
    """Write an image as PNG."""
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError(f"No se pudo codificar el recorte: {path.name}")
    path.write_bytes(encoded.tobytes())


def load_dotenv(path: Path) -> None:
    """Load environment variables from a .env file (does not override existing)."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# ---------------------------------------------------------------------------
# API key resolution
# ---------------------------------------------------------------------------

INTERFAZE_API_KEY_ENV_NAMES = ("INTERFAZE_API_KEY", "INTERFAZE_KEY")
GEMINI_API_KEY_ENV_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
GLM_API_KEY_ENV_NAMES = ("GLM_API_KEY", "ZAI_API_KEY")
DOCSTRANGE_API_KEY_ENV_NAMES = ("DOCSTRANGE_API_KEY",)
QUBRID_API_KEY_ENV_NAMES = ("QUBRID_API_KEY",)
OPENROUTER_API_KEY_ENV_NAMES = ("OPENROUTER_API_KEY",)


def get_api_key(api_key_env: str | None, detector: str) -> str | None:
    """Resolve an API key from environment variables."""
    if api_key_env:
        return os.environ.get(api_key_env)
    if detector == "gemini":
        names = GEMINI_API_KEY_ENV_NAMES
    elif detector == "glm":
        names = GLM_API_KEY_ENV_NAMES
    elif detector == "docstrange":
        names = DOCSTRANGE_API_KEY_ENV_NAMES
    elif detector == "qubrid":
        names = QUBRID_API_KEY_ENV_NAMES
    elif detector == "openrouter":
        names = OPENROUTER_API_KEY_ENV_NAMES
    else:
        names = INTERFAZE_API_KEY_ENV_NAMES
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None
