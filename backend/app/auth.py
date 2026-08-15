from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from secrets import token_urlsafe
import sqlite3
from threading import RLock
from typing import Protocol

from cryptography.fernet import Fernet, InvalidToken, MultiFernet


@dataclass(frozen=True, slots=True)
class SessionRecord:
    token: str = field(repr=False)
    username: str
    password: str = field(repr=False)
    expires_at: datetime


class SessionStoreProtocol(Protocol):
    ttl_seconds: int

    def create(self, *, username: str, password: str) -> SessionRecord: ...

    def get(self, token: str | None) -> SessionRecord | None: ...

    def delete(self, token: str | None) -> None: ...

    def clear(self) -> None: ...


class SessionStore:
    """Process-local opaque session storage for development and isolated testing."""

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


class SqliteSessionStore:
    """Shared encrypted session storage suitable for multiple backend workers.

    Browser session tokens are never stored in plaintext. CardDAV usernames and
    passwords are encrypted together with MultiFernet before persistence. The
    encryption key material must be supplied separately from the database and source
    control.
    """

    def __init__(
        self,
        ttl_seconds: int,
        database_path: str,
        encryption_keys: list[str],
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("Session TTL must be greater than zero.")
        if not database_path.strip():
            raise ValueError("SQLite session database path is required.")
        if not encryption_keys:
            raise ValueError("At least one session encryption key is required.")

        self.ttl_seconds = ttl_seconds
        self.database_path = Path(database_path).expanduser()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            fernets = [Fernet(key.strip().encode("ascii")) for key in encryption_keys]
        except (ValueError, UnicodeEncodeError) as exc:
            raise ValueError("SESSION_ENCRYPTION_KEYS contains an invalid Fernet key.") from exc

        self._cipher = MultiFernet(fernets)
        self._initialize()

    @staticmethod
    def _token_digest(token: str) -> str:
        return sha256(token.encode("utf-8")).hexdigest()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=5.0,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token_digest TEXT PRIMARY KEY,
                    encrypted_credentials BLOB NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS sessions_expires_at_idx ON sessions(expires_at)"
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

    @staticmethod
    def _expiration_text(expires_at: datetime) -> str:
        return expires_at.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _parse_expiration(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _prune(self, connection: sqlite3.Connection, now: datetime) -> None:
        connection.execute(
            "DELETE FROM sessions WHERE expires_at <= ?",
            (self._expiration_text(now),),
        )

    def _encrypt_credentials(self, username: str, password: str) -> bytes:
        payload = json.dumps(
            {"username": username, "password": password},
            separators=(",", ":"),
        ).encode("utf-8")
        return self._cipher.encrypt(payload)

    def _decrypt_credentials(self, encrypted_credentials: bytes) -> tuple[str, str] | None:
        try:
            payload = json.loads(self._cipher.decrypt(encrypted_credentials).decode("utf-8"))
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError):
            return None

        username = payload.get("username") if isinstance(payload, dict) else None
        password = payload.get("password") if isinstance(payload, dict) else None
        if not isinstance(username, str) or not username.strip():
            return None
        if not isinstance(password, str) or not password:
            return None
        return username, password

    def create(self, *, username: str, password: str) -> SessionRecord:
        normalized_username = username.strip()
        if not normalized_username or not password:
            raise ValueError("Username and password are required.")

        now = datetime.now(timezone.utc)
        token = token_urlsafe(48)
        record = SessionRecord(
            token=token,
            username=normalized_username,
            password=password,
            expires_at=now + timedelta(seconds=self.ttl_seconds),
        )
        encrypted_credentials = self._encrypt_credentials(normalized_username, password)

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                self._prune(connection, now)
                connection.execute(
                    """
                    INSERT INTO sessions (
                        token_digest,
                        encrypted_credentials,
                        expires_at
                    ) VALUES (?, ?, ?)
                    """,
                    (
                        self._token_digest(token),
                        encrypted_credentials,
                        self._expiration_text(record.expires_at),
                    ),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

        self._tighten_permissions()
        return record

    def get(self, token: str | None) -> SessionRecord | None:
        if not token:
            return None

        now = datetime.now(timezone.utc)
        digest = self._token_digest(token)
        with self._connect() as connection:
            self._prune(connection, now)
            row = connection.execute(
                """
                SELECT encrypted_credentials, expires_at
                FROM sessions
                WHERE token_digest = ?
                """,
                (digest,),
            ).fetchone()

        if row is None:
            return None

        expires_at = self._parse_expiration(row["expires_at"])
        if expires_at <= now:
            self.delete(token)
            return None

        credentials = self._decrypt_credentials(row["encrypted_credentials"])
        if credentials is None:
            return None
        username, password = credentials

        return SessionRecord(
            token=token,
            username=username,
            password=password,
            expires_at=expires_at,
        )

    def delete(self, token: str | None) -> None:
        if not token:
            return
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE token_digest = ?",
                (self._token_digest(token),),
            )
        self._tighten_permissions()

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions")
        self._tighten_permissions()


def create_session_store(
    *,
    backend: str,
    ttl_seconds: int,
    database_path: str,
    encryption_keys: list[str],
) -> SessionStoreProtocol:
    normalized_backend = backend.strip().casefold()
    if normalized_backend == "memory":
        return SessionStore(ttl_seconds=ttl_seconds)
    if normalized_backend == "sqlite":
        return SqliteSessionStore(
            ttl_seconds=ttl_seconds,
            database_path=database_path,
            encryption_keys=encryption_keys,
        )
    raise ValueError("SESSION_STORE_BACKEND must be either 'memory' or 'sqlite'.")
