from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass(frozen=True)
class LoginThrottleDecision:
    allowed: bool
    retry_after_seconds: int = 0


class LoginThrottle:
    """Bound repeated sign-in attempts without retaining credentials or contact data."""

    def __init__(self, *, max_attempts: int, window_seconds: int) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be at least 1")
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, *, now: float | None = None) -> LoginThrottleDecision:
        current = monotonic() if now is None else now
        cutoff = current - self.window_seconds
        normalized_key = key.strip().casefold()

        with self._lock:
            attempts = self._attempts[normalized_key]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()

            if len(attempts) >= self.max_attempts:
                retry_after = max(1, int(self.window_seconds - (current - attempts[0])))
                return LoginThrottleDecision(False, retry_after)

            attempts.append(current)
            return LoginThrottleDecision(True)

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key.strip().casefold(), None)
