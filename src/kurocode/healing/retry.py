"""
src/kurocode/healing/retry.py — Smart Retry Policy with Exponential Backoff.
"""

from __future__ import annotations

import random
import time
from typing import Any, Callable, Optional


class RetryPolicy:
    """Configurable retry logic with exponential backoff and jitter."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 30.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        """Calculates sleep delay for a given attempt index (0-based)."""
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        if self.jitter:
            delay += random.uniform(0, self.initial_delay * 0.5)
        return min(delay, self.max_delay)

    def execute_with_retry(
        self,
        func: Callable[[], Any],
        is_retryable_fn: Optional[Callable[[Exception], bool]] = None,
        on_retry_fn: Optional[Callable[[int, Exception, float], None]] = None,
    ) -> Any:
        """Executes a callable with automatic retries on failure."""
        last_exception = None
        for attempt in range(self.max_attempts):
            try:
                return func()
            except Exception as exc:
                last_exception = exc
                if attempt == self.max_attempts - 1:
                    raise
                if is_retryable_fn and not is_retryable_fn(exc):
                    raise
                delay = self.calculate_delay(attempt)
                if on_retry_fn:
                    on_retry_fn(attempt + 1, exc, delay)
                time.sleep(delay)
        if last_exception:
            raise last_exception


__all__ = ["RetryPolicy"]
