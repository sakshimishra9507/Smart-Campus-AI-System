"""Usage and local cost-estimation tracking."""

from dataclasses import dataclass
from threading import Lock

from .config import Pricing
from .models import Usage


@dataclass(frozen=True)
class UsageSnapshot:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


class UsageTracker:
    def __init__(self) -> None:
        self._lock = Lock()
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._total_tokens = 0
        self._estimated_cost_usd = 0.0

    def record(self, usage: Usage, pricing: Pricing) -> None:
        cost = (
            usage.prompt_tokens * pricing.input_per_million
            + usage.completion_tokens * pricing.output_per_million
        ) / 1_000_000
        with self._lock:
            self._prompt_tokens += usage.prompt_tokens
            self._completion_tokens += usage.completion_tokens
            self._total_tokens += usage.total_tokens
            self._estimated_cost_usd += cost

    def snapshot(self) -> UsageSnapshot:
        with self._lock:
            return UsageSnapshot(
                self._prompt_tokens,
                self._completion_tokens,
                self._total_tokens,
                self._estimated_cost_usd,
            )
