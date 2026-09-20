"""LLM provider abstraction.

Application code depends on LLMProvider, not on an OpenAI/Anthropic/etc. SDK.
Provider adapters should implement this interface in their own integration
modules. No provider implementation in this layer may execute arbitrary tools.
"""

from abc import ABC, abstractmethod

from .models import LLMRequest, LLMResponse


class LLMProvider(ABC):
    """Minimal contract every LLM provider adapter must implement."""

    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return a provider-neutral response for a request."""
        raise NotImplementedError
