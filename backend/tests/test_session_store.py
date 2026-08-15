import sqlite3
import stat

from cryptography.fernet import Fernet

from app.auth import SqliteSessionStore, create_session_store


def _key() -> str:
    return Fernet.generate_key().decode("ascii")


def test_sqlite_session_survives_store_recreation(tmp_path) -> None:
    database = tmp_path / "sessions.sqlite3"
    key = _key()

    first = SqliteSessionStore(3600, str(database), [key])
    created = first.create(username="test-user", password="test-password")

    second = SqliteSessionStore(3600, str(database), [key])
    restored = second.get(created.token)

    assert restored is not None
    assert restored.username == "test-user"
    assert restored.password == "test-password"
    assert restored.expires_at == created.expires_at


def test_sqlite_session_does_not_store_raw_token_username_or_password(tmp_path) -> None:
    database = tmp_path / "sessions.sqlite3"
    store = SqliteSessionStore(3600, str(database), [_key()])
    created = store.create(username="test-user", password="super-secret-password")

    with sqlite3.connect(database) as connection:
        token_digest, encrypted_credentials = connection.execute(
            "SELECT token_digest, encrypted_credentials FROM sessions"
        ).fetchone()

    assert token_digest != created.token
    assert len(token_digest) == 64
    assert b"test-user" not in encrypted_credentials
    assert b"super-secret-password" not in encrypted_credentials
    assert created.token.encode("utf-8") not in encrypted_credentials


def test_sqlite_session_is_shared_and_revocation_is_visible(tmp_path) -> None:
    database = tmp_path / "sessions.sqlite3"
    key = _key()
    first = SqliteSessionStore(3600, str(database), [key])
    second = SqliteSessionStore(3600, str(database), [key])

    created = first.create(username="test-user", password="test-password")
    assert second.get(created.token) is not None

    second.delete(created.token)
    assert first.get(created.token) is None


def test_sqlite_session_supports_controlled_key_rotation(tmp_path) -> None:
    database = tmp_path / "sessions.sqlite3"
    old_key = _key()
    new_key = _key()

    old_store = SqliteSessionStore(3600, str(database), [old_key])
    old_session = old_store.create(username="old-user", password="old-password")

    rotating_store = SqliteSessionStore(3600, str(database), [new_key, old_key])
    restored_old = rotating_store.get(old_session.token)
    assert restored_old is not None
    assert restored_old.username == "old-user"

    new_session = rotating_store.create(username="new-user", password="new-password")
    old_key_only = SqliteSessionStore(3600, str(database), [old_key])
    assert old_key_only.get(new_session.token) is None
    assert rotating_store.get(new_session.token) is not None


def test_sqlite_session_files_are_owner_only(tmp_path) -> None:
    database = tmp_path / "sessions.sqlite3"
    store = SqliteSessionStore(3600, str(database), [_key()])
    store.create(username="test-user", password="test-password")

    paths = [database, tmp_path / "sessions.sqlite3-wal", tmp_path / "sessions.sqlite3-shm"]
    for path in paths:
        if path.exists():
            assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_session_store_factory_preserves_memory_default_and_supports_sqlite(tmp_path) -> None:
    memory = create_session_store(
        backend="memory",
        ttl_seconds=3600,
        database_path=str(tmp_path / "unused.sqlite3"),
        encryption_keys=[],
    )
    memory_record = memory.create(username="memory-user", password="memory-password")
    assert memory.get(memory_record.token) is not None

    sqlite_store = create_session_store(
        backend="sqlite",
        ttl_seconds=3600,
        database_path=str(tmp_path / "sessions.sqlite3"),
        encryption_keys=[_key()],
    )
    sqlite_record = sqlite_store.create(username="sqlite-user", password="sqlite-password")
    assert sqlite_store.get(sqlite_record.token) is not None
