from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from threading import RLock


@dataclass(frozen=True, slots=True)
class SessionRecord:
    token: str = field(repr=False)
    username: str
    password: str = field(repr=False)
    expires_at: datetime


class SessionStore:
    """Process-local opaque session storage for the Milestone 3 foundation.

    CardDAV passwords are retained only in server memory for the lifetime of an
    authenticated session. The browser receives only a random opaque token.
    """

    def __init__(self, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("Session TTL must be greater than zero.")

        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, SessionRecord] = {}
        self._lock = RLock()

    def create(self, *, username: str, password: str) -> SessionRecord:
        normalized_username = username.strip()
        if not normalized_username or not password:
            raise ValueError("Username and password are required.")

        now = datetime.now(timezone.utc)
        record = SessionRecord(
            token=token_urlsafe(48),
            username=normalized_username,
            password=password,
            expires_at=now + timedelta(seconds=self.ttl_seconds),
        )

        with self._lock:
            self._prune_locked(now)
            self._sessions[record.token] = record

        return record

    def get(self, token: str | None) -> SessionRecord | None:
        if not token:
            return None

        now = datetime.now(timezone.utc)
        with self._lock:
            self._prune_locked(now)
            return self._sessions.get(token)

    def delete(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()

    def _prune_locked(self, now: datetime) -> None:
        expired = [
            token
            for token, record in self._sessions.items()
            if record.expires_at <= now
        ]
        for token in expired:
            self._sessions.pop(token, None)
