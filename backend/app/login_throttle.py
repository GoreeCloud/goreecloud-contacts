from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import sqlite3
from threading import Lock
from time import monotonic, time
from typing import Protocol


@dataclass(frozen=True)
class LoginThrottleDecision:
    allowed: bool
    retry_after_seconds: int = 0


class LoginThrottleProtocol(Protocol):
    def check(self, key: str, *, now: float | None = None) -> LoginThrottleDecision: ...

    def reset(self, key: str) -> None: ...


class LoginThrottle:
    """Process-local sign-in throttle for development and isolated testing."""

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
        normalized_key = _normalize_key(key)

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
            self._attempts.pop(_normalize_key(key), None)


class SqliteLoginThrottle:
    """Shared privacy-minimal sign-in throttle suitable for multiple workers.

    The normalized username is reduced to a one-way SHA-256 digest before SQLite
    persistence. No password, session token, contact data, request body, or client
    address is retained by this store.
    """

    def __init__(
        self,
        *,
        max_attempts: int,
        window_seconds: int,
        database_path: str,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be at least 1")
        if not database_path.strip():
            raise ValueError("SQLite login throttle database path is required.")

        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.database_path = Path(database_path).expanduser()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @staticmethod
    def _identity_digest(key: str) -> str:
        return sha256(_normalize_key(key).encode("utf-8")).hexdigest()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=5.0,
            isolation_level=None,
        )
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS login_throttle_attempts (
                    identity_digest TEXT NOT NULL,
                    attempted_at REAL NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS login_throttle_identity_time_idx
                ON login_throttle_attempts(identity_digest, attempted_at)
                """
            )
        self._tighten_permissions()

    def _tighten_permissions(self) -> None:
        for path in (
            self.database_path,
            Path(f"{self.database_path}-wal"),
            Path(f"{self.database_path}-shm"),
        ):
            if path.exists():
                path.chmod(0o600)

    def check(self, key: str, *, now: float | None = None) -> LoginThrottleDecision:
        current = time() if now is None else now
        cutoff = current - self.window_seconds
        digest = self._identity_digest(key)

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    "DELETE FROM login_throttle_attempts WHERE attempted_at <= ?",
                    (cutoff,),
                )
                rows = connection.execute(
                    """
                    SELECT attempted_at
                    FROM login_throttle_attempts
                    WHERE identity_digest = ?
                    ORDER BY attempted_at ASC
                    """,
                    (digest,),
                ).fetchall()

                if len(rows) >= self.max_attempts:
                    oldest = float(rows[0][0])
                    retry_after = max(1, int(self.window_seconds - (current - oldest)))
                    connection.commit()
                    return LoginThrottleDecision(False, retry_after)

                connection.execute(
                    """
                    INSERT INTO login_throttle_attempts(identity_digest, attempted_at)
                    VALUES (?, ?)
                    """,
                    (digest, current),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

        self._tighten_permissions()
        return LoginThrottleDecision(True)

    def reset(self, key: str) -> None:
        digest = self._identity_digest(key)
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM login_throttle_attempts WHERE identity_digest = ?",
                (digest,),
            )
        self._tighten_permissions()


def _normalize_key(key: str) -> str:
    normalized = key.strip().casefold()
    if not normalized:
        raise ValueError("Login throttle identity is required.")
    return normalized


def create_login_throttle(
    *,
    backend: str,
    max_attempts: int,
    window_seconds: int,
    database_path: str,
) -> LoginThrottleProtocol:
    normalized_backend = backend.strip().casefold()
    if normalized_backend == "memory":
        return LoginThrottle(
            max_attempts=max_attempts,
            window_seconds=window_seconds,
        )
    if normalized_backend == "sqlite":
        return SqliteLoginThrottle(
            max_attempts=max_attempts,
            window_seconds=window_seconds,
            database_path=database_path,
        )
    raise ValueError("Login throttle backend must follow SESSION_STORE_BACKEND.")
