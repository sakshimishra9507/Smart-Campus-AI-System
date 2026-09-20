"""LLM orchestration: retries, timeout, validation, logging, and usage tracking."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import json
import logging
import time
from typing import Any

from .config import ModelConfig
from .errors import (
    InvalidLLMResponseError,
    LLMTimeoutError,
    RetryExhaustedError,
    TokenLimitExceededError,
    TransientLLMError,
)
from .models import LLMRequest, LLMResponse, Message, ToolDefinition
from .providers import LLMProvider
from .usage import UsageTracker

logger = logging.getLogger(__name__)


class LLMService:
    """Provider-independent gateway for model calls.

    Tool definitions are passed to the provider as data. This service has no
    command runner, subprocess access, shell access, or tool execution path.
    """

    def __init__(
        self,
        provider: LLMProvider,
        config: ModelConfig,
        usage_tracker: UsageTracker | None = None,
    ) -> None:
        self.provider = provider
        self.config = config
        self.usage_tracker = usage_tracker or UsageTracker()

    def complete(
        self,
        messages: list[Message] | tuple[Message, ...],
        *,
        response_format: str = "text",
        response_schema: dict[str, Any] | None = None,
        tools: list[ToolDefinition] | tuple[ToolDefinition, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> LLMResponse:
        request = LLMRequest(
            messages=tuple(messages),
            model=self.config.model_name,
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_output_tokens,
            response_format=response_format,  # type: ignore[arg-type]
            response_schema=response_schema,
            tools=tuple(tools),
            metadata=metadata or {},
        )

        last_error: Exception | None = None
        attempts = self.config.max_retries + 1
        for attempt in range(1, attempts + 1):
            started = time.monotonic()
            try:
                logger.info(
                    "LLM request provider=%s model=%s attempt=%d/%d",
                    self.config.provider_name,
                    self.config.model_name,
                    attempt,
                    attempts,
                )
                response = self._call_with_timeout(request)
                self._validate_response(request, response)
                self.usage_tracker.record(response.usage, self.config.pricing)
                logger.info(
                    "LLM response request_id=%s tokens=%d latency_ms=%d",
                    response.request_id,
                    response.usage.total_tokens,
                    int((time.monotonic() - started) * 1000),
                )
                return response
            except (TransientLLMError, LLMTimeoutError) as exc:
                last_error = exc
                logger.warning("Transient LLM failure on attempt %d: %s", attempt, exc)
                if attempt < attempts:
                    time.sleep(self.config.retry_backoff_seconds * attempt)
            except Exception:
                logger.exception("Non-retryable LLM failure")
                raise

        raise RetryExhaustedError(
            f"LLM request failed after {attempts} attempts.",
            last_error=last_error,
        )

    def _call_with_timeout(self, request: LLMRequest) -> LLMResponse:
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="llm-call")
        future = executor.submit(self.provider.complete, request)
        try:
            return future.result(timeout=self.config.timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise LLMTimeoutError(
                f"LLM provider exceeded {self.config.timeout_seconds}s timeout."
            ) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _validate_response(self, request: LLMRequest, response: LLMResponse) -> None:
        if not isinstance(response, LLMResponse):
            raise InvalidLLMResponseError("Provider must return LLMResponse.")
        if self.config.max_total_tokens is not None and (
            response.usage.total_tokens > self.config.max_total_tokens
        ):
            raise TokenLimitExceededError(
                f"Response used {response.usage.total_tokens} tokens; "
                f"budget is {self.config.max_total_tokens}."
            )
        if request.response_format == "json":
            if response.structured_output is None:
                try:
                    parsed = json.loads(response.content)
                except json.JSONDecodeError as exc:
                    raise InvalidLLMResponseError(
                        "Expected a JSON response but received invalid JSON."
                    ) from exc
                if not isinstance(parsed, dict):
                    raise InvalidLLMResponseError("Structured output must be a JSON object.")
            elif not isinstance(response.structured_output, dict):
                raise InvalidLLMResponseError("structured_output must be a mapping.")
