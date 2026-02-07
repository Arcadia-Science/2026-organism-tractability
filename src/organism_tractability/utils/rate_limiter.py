"""Centralized rate limiting and retry utilities for API clients.

This module provides:
- RateLimiter: Proactive time-based throttling (X requests per second)
- ConcurrencyLimiter: Maximum concurrent requests using a semaphore
- retry_with_backoff: Pre-configured tenacity decorator with exponential backoff and jitter
"""

import logging
import time
from threading import Lock, Semaphore

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """Thread-safe proactive rate limiter that enforces delays between calls.

    Use this to stay under API rate limits by adding delays before each request,
    rather than waiting to hit the limit and then backing off.

    This class is thread-safe: multiple threads can call wait() concurrently,
    and the rate limit will be correctly enforced across all threads.

    Example:
        limiter = RateLimiter(calls_per_second=3)  # 3 requests per second

        def make_request():
            limiter.wait()  # Blocks if needed to respect rate limit
            return requests.get(url)
    """

    def __init__(self, calls_per_second: float):
        """Initialize the rate limiter.

        Args:
            calls_per_second: Maximum number of calls allowed per second.
        """
        if calls_per_second <= 0:
            raise ValueError("calls_per_second must be positive")
        self.min_interval = 1.0 / calls_per_second
        self._last_call = 0.0
        self._lock = Lock()

    def wait(self) -> None:
        """Block until enough time has passed since the last call.

        This method is thread-safe. When multiple threads call wait(),
        they will be serialized and each will wait the appropriate amount
        of time to respect the rate limit.
        """
        with self._lock:
            now = time.time()
            wait_time = self.min_interval - (now - self._last_call)
            if wait_time > 0:
                time.sleep(wait_time)
            self._last_call = time.time()


class ConcurrencyLimiter:
    """Limits concurrent requests using a semaphore.

    Use this for APIs that limit the number of simultaneous requests
    (e.g., Firecrawl allows max 5 concurrent requests).

    Example:
        limiter = ConcurrencyLimiter(max_concurrent=5)

        def make_request():
            with limiter:
                return requests.get(url)
    """

    def __init__(self, max_concurrent: int):
        """Initialize the concurrency limiter.

        Args:
            max_concurrent: Maximum number of concurrent requests allowed.
        """
        if max_concurrent <= 0:
            raise ValueError("max_concurrent must be positive")
        self._semaphore = Semaphore(max_concurrent)

    def __enter__(self):
        """Acquire the semaphore before making a request."""
        self._semaphore.acquire()
        return self

    def __exit__(self, *args):
        """Release the semaphore after the request completes."""
        self._semaphore.release()


def retry_with_backoff(
    max_attempts: int = 5,
    min_wait: float = 1.0,
    max_wait: float = 60.0,
    retry_on: tuple = (requests.RequestException, requests.HTTPError),
):
    """Create a retry decorator with random exponential backoff.

    Uses jitter (randomized delays) to prevent thundering herd problems
    when multiple requests fail and retry simultaneously.

    Args:
        max_attempts: Maximum number of retry attempts (default: 5).
        min_wait: Minimum wait time in seconds (default: 1.0).
        max_wait: Maximum wait time in seconds (default: 60.0).
        retry_on: Tuple of exception types to retry on.

    Returns:
        A tenacity retry decorator.

    Example:
        @retry_with_backoff(max_attempts=3)
        def make_request():
            return requests.get(url)
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_random_exponential(min=min_wait, max=max_wait),
        retry=retry_if_exception_type(retry_on),
        reraise=True,
    )
