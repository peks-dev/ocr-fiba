"""
Excepción base y jerarquía para el OCR Engine.

Toda excepción del engine hereda de OcrEngineError y lleva metadatos
estándar para trazabilidad: código de error, fase del pipeline, provider
involucrado, si es reintentable, y detalles adicionales.

El método to_dict() serializa al formato de respuesta estandarizado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Códigos de error
# ---------------------------------------------------------------------------

class ErrorCode:
    """Catálogo de códigos de error machine-readable."""

    # Configuración
    CONFIG_MISSING_ENV = "CONFIG_MISSING_ENV"
    CONFIG_INVALID_PROVIDER = "CONFIG_INVALID_PROVIDER"
    CONFIG_MISSING_API_KEY = "CONFIG_MISSING_API_KEY"

    # Input
    INPUT_IMAGE_NOT_FOUND = "INPUT_IMAGE_NOT_FOUND"
    INPUT_IMAGE_INVALID = "INPUT_IMAGE_INVALID"
    INPUT_IMAGE_UNREADABLE = "INPUT_IMAGE_UNREADABLE"

    # Pipeline — Cropping
    CROP_SECTION_NOT_FOUND = "CROP_SECTION_NOT_FOUND"
    CROP_INVALID_BOX = "CROP_INVALID_BOX"
    CROP_EMPTY_CROP = "CROP_EMPTY_CROP"
    CROP_LAYOUT_INVALID = "CROP_LAYOUT_INVALID"
    CROP_TEAM_FOULS_NOT_FOUND = "CROP_TEAM_FOULS_NOT_FOUND"

    # Pipeline — Extraction
    EXTRACT_SECTION_MISSING = "EXTRACT_SECTION_MISSING"
    EXTRACT_MARKDOWN_PARSE = "EXTRACT_MARKDOWN_PARSE"
    EXTRACT_INVALID_RESPONSE = "EXTRACT_INVALID_RESPONSE"

    # Provider
    PROVIDER_AUTH = "PROVIDER_AUTH"
    PROVIDER_RATE_LIMIT = "PROVIDER_RATE_LIMIT"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_SERVER_ERROR = "PROVIDER_SERVER_ERROR"
    PROVIDER_CONNECTION = "PROVIDER_CONNECTION"
    PROVIDER_INVALID_RESPONSE = "PROVIDER_INVALID_RESPONSE"
    PROVIDER_EMPTY_RESPONSE = "PROVIDER_EMPTY_RESPONSE"

    # Validación
    VALIDATION_PLUGIN_ERROR = "VALIDATION_PLUGIN_ERROR"


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

@dataclass
class OcrEngineError(Exception):
    """
    Excepción base de todo el OCR Engine.

    Atributos:
        message: Descripción legible del error.
        code: Código machine-readable (ver ErrorCode).
        phase: Fase del pipeline donde ocurrió ("cropping", "extraction", "validation").
        provider: Provider de IA involucrado, si aplica.
        retryable: Si el error es potencialmente recuperable con un reintento.
        details: Diccionario con contexto adicional para debug.
    """

    message: str
    code: str = "UNKNOWN"
    phase: str | None = None
    provider: str | None = None
    retryable: bool = False
    details: dict[str, Any] | None = None

    def __init__(
        self,
        message: str,
        *,
        code: str = "UNKNOWN",
        phase: str | None = None,
        provider: str | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.phase = phase
        self.provider = provider
        self.retryable = retryable
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        """Serializar al formato de respuesta de error estandarizado."""
        error: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.phase:
            error["phase"] = self.phase
        if self.provider:
            error["provider"] = self.provider
        if self.details:
            error["details"] = self.details
        return error

    def __str__(self) -> str:
        parts = [f"[{self.code}]"]
        if self.phase:
            parts.append(f"phase={self.phase}")
        if self.provider:
            parts.append(f"provider={self.provider}")
        parts.append(self.message)
        return " ".join(parts)


# ---------------------------------------------------------------------------
# Errores de configuración
# ---------------------------------------------------------------------------

class ConfigurationError(OcrEngineError):
    """Error en la configuración del pipeline (.env, providers, API keys)."""

    def __init__(
        self,
        message: str,
        *,
        code: str = ErrorCode.CONFIG_MISSING_ENV,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            phase="configuration",
            retryable=False,
            details=details,
        )


# ---------------------------------------------------------------------------
# Errores de input
# ---------------------------------------------------------------------------

class InputError(OcrEngineError):
    """Error con la imagen de entrada (no existe, corrupta, formato inválido)."""

    def __init__(
        self,
        message: str,
        *,
        code: str = ErrorCode.INPUT_IMAGE_NOT_FOUND,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            phase="input",
            retryable=False,
            details=details,
        )


# ---------------------------------------------------------------------------
# Errores del pipeline
# ---------------------------------------------------------------------------

class PipelineError(OcrEngineError):
    """Error genérico durante una fase del pipeline."""


class CroppingError(PipelineError):
    """Error durante la fase de detección y recorte de secciones."""

    def __init__(
        self,
        message: str,
        *,
        code: str = ErrorCode.CROP_SECTION_NOT_FOUND,
        provider: str | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            phase="cropping",
            provider=provider,
            retryable=retryable,
            details=details,
        )


class ExtractionError(PipelineError):
    """Error durante la fase de extracción de datos."""

    def __init__(
        self,
        message: str,
        *,
        code: str = ErrorCode.EXTRACT_INVALID_RESPONSE,
        provider: str | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            phase="extraction",
            provider=provider,
            retryable=retryable,
            details=details,
        )


# ---------------------------------------------------------------------------
# Errores de provider (APIs externas)
# ---------------------------------------------------------------------------

class ProviderError(OcrEngineError):
    """Error originado en un provider de IA externo."""

    def __init__(
        self,
        message: str,
        *,
        code: str = ErrorCode.PROVIDER_SERVER_ERROR,
        provider: str,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            phase="provider",
            provider=provider,
            retryable=retryable,
            details=details,
        )


class ProviderAuthError(ProviderError):
    """Error de autenticación (401/403) — API key inválida o sin permisos."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=ErrorCode.PROVIDER_AUTH,
            provider=provider,
            retryable=False,
            details=details,
        )


class ProviderRateLimitError(ProviderError):
    """Rate limit excedido (429) — reintentable con backoff."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=ErrorCode.PROVIDER_RATE_LIMIT,
            provider=provider,
            retryable=True,
            details=details,
        )


class ProviderTimeoutError(ProviderError):
    """Timeout en la llamada al provider — reintentable."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=ErrorCode.PROVIDER_TIMEOUT,
            provider=provider,
            retryable=True,
            details=details,
        )


class ProviderServerError(ProviderError):
    """Error del lado del servidor (5xx) — reintentable."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=ErrorCode.PROVIDER_SERVER_ERROR,
            provider=provider,
            retryable=True,
            details=details,
        )


class ProviderConnectionError(ProviderError):
    """Error de conexión (DNS, network unreachable) — reintentable."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=ErrorCode.PROVIDER_CONNECTION,
            provider=provider,
            retryable=True,
            details=details,
        )


class ProviderInvalidResponseError(ProviderError):
    """El provider devolvió una respuesta que no se puede interpretar."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=ErrorCode.PROVIDER_INVALID_RESPONSE,
            provider=provider,
            retryable=False,
            details=details,
        )


# ---------------------------------------------------------------------------
# Errores de validación
# ---------------------------------------------------------------------------

class ValidationEngineError(OcrEngineError):
    """Error interno del motor de validación."""

    def __init__(
        self,
        message: str,
        *,
        code: str = ErrorCode.VALIDATION_PLUGIN_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            phase="validation",
            retryable=False,
            details=details,
        )