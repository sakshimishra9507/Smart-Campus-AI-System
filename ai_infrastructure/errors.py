"""Errors used by the provider-agnostic LLM layer."""


class LLMError(Exception):
    """Base class for expected LLM infrastructure errors."""


class TransientLLMError(LLMError):
    """An error that may succeed when retried."""


class LLMTimeoutError(TransientLLMError):
    """A provider call exceeded the configured timeout."""


class InvalidLLMResponseError(LLMError):
    """The provider returned a response that violates the request contract."""


class TokenLimitExceededError(LLMError):
    """The returned usage exceeded the configured token budget."""


class RetryExhaustedError(LLMError):
    """All configured retry attempts failed."""

    def __init__(self, message: str, last_error: Exception | None = None) -> None:
        super().__init__(message)
        self.last_error = last_error
