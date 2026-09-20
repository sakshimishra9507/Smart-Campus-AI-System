"""Model and provider configuration.

Configuration is deliberately provider-neutral. Concrete provider adapters can
map these fields to their SDK/API without leaking provider details elsewhere.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Pricing:
    """Optional per-1M-token pricing used only for local cost estimates."""

    input_per_million: float = 0.0
    output_per_million: float = 0.0

    def __post_init__(self) -> None:
        if self.input_per_million < 0 or self.output_per_million < 0:
            raise ValueError("Pricing values cannot be negative.")


@dataclass(frozen=True)
class ModelConfig:
    """Provider-neutral model runtime settings."""

    provider_name: str
    model_name: str
    temperature: float = 0.0
    max_output_tokens: int = 2048
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_backoff_seconds: float = 0.5
    max_total_tokens: Optional[int] = None
    pricing: Pricing = Pricing()

    def __post_init__(self) -> None:
        if not self.provider_name.strip() or not self.model_name.strip():
            raise ValueError("provider_name and model_name are required.")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0 and 2.")
        if self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive.")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative.")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds cannot be negative.")
        if self.max_total_tokens is not None and self.max_total_tokens <= 0:
            raise ValueError("max_total_tokens must be positive when provided.")
