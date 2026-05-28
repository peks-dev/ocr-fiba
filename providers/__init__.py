"""
Provider factory — centralized creation of ModelProvider instances.
"""

from __future__ import annotations

from typing import Literal

from .base import ModelProvider
from .docstrange import DocstrangeProvider
from .gemini import GeminiProvider
from .glm import GlmProvider
from .interfaze import InterfazeProvider
from .openrouter import OpenrouterProvider
from .qubrid import QubridProvider

ProviderType = Literal["interfaze", "gemini", "glm", "docstrange", "qubrid", "openrouter"]


def create_provider(
    provider_type: ProviderType,
    model_name: str,
    api_key: str,
    **kwargs,
) -> ModelProvider:
    """Create a ModelProvider instance from configuration.

    Extra kwargs are passed to the provider constructor (e.g. reasoning for OpenRouter).
    """
    if provider_type == "interfaze":
        return InterfazeProvider(model_name, api_key)
    elif provider_type == "gemini":
        return GeminiProvider(model_name, api_key)
    elif provider_type == "glm":
        return GlmProvider(model_name, api_key)
    elif provider_type == "docstrange":
        return DocstrangeProvider(model_name, api_key)
    elif provider_type == "qubrid":
        return QubridProvider(model_name, api_key)
    elif provider_type == "openrouter":
        return OpenrouterProvider(model_name, api_key, **kwargs)
    raise ValueError(f"Proveedor no soportado: {provider_type}")


__all__ = ["create_provider", "ProviderType", "ModelProvider"]
