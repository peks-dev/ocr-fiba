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

# Single source of truth: provider name → candidate env var names (in priority
# order). Both image utilities and PipelineConfig resolve keys through this.
PROVIDER_API_KEY_ENV_NAMES: dict[str, tuple[str, ...]] = {
    "interfaze": ("INTERFAZE_API_KEY", "INTERFAZE_KEY"),
    "gemini": ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_GENAI_API_KEY"),
    "glm": ("GLM_API_KEY", "ZAI_API_KEY"),
    "docstrange": ("DOCSTRANGE_API_KEY",),
    "qubrid": ("QUBRID_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY",),
}

# Provider used when an unknown detector name is given (matches legacy behavior).
_DEFAULT_PROVIDER = "interfaze"


def env_names_for_provider(provider: str) -> tuple[str, ...]:
    """Candidate env var names for a provider (falls back to the default)."""
    return PROVIDER_API_KEY_ENV_NAMES.get(
        provider, PROVIDER_API_KEY_ENV_NAMES[_DEFAULT_PROVIDER]
    )


def resolve_provider_api_key(provider: str) -> str | None:
    """Resolve a provider's API key from its candidate env vars."""
    for name in env_names_for_provider(provider):
        value = os.environ.get(name)
        if value:
            return value
    return None


def get_api_key(api_key_env: str | None, detector: str) -> str | None:
    """Resolve an API key from environment variables.

    If ``api_key_env`` is given it takes precedence; otherwise the provider's
    canonical env var names are tried in order.
    """
    if api_key_env:
        return os.environ.get(api_key_env)
    return resolve_provider_api_key(detector)
