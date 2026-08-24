import multiprocessing
import sqlite3

from app.login_throttle import LoginThrottle, SqliteLoginThrottle, create_login_throttle


def _sqlite_throttle_process_check(
    database_path: str,
    key: str,
    now: float,
    queue,
) -> None:
    throttle = SqliteLoginThrottle(
        max_attempts=2,
        window_seconds=60,
        database_path=database_path,
    )
    decision = throttle.check(key, now=now)
    queue.put((decision.allowed, decision.retry_after_seconds))


def test_login_throttle_blocks_after_bounded_attempts() -> None:
    throttle = LoginThrottle(max_attempts=3, window_seconds=60)

    assert throttle.check("Alice", now=100).allowed is True
    assert throttle.check("alice", now=101).allowed is True
    assert throttle.check(" ALICE ", now=102).allowed is True

    blocked = throttle.check("alice", now=103)
    assert blocked.allowed is False
    assert blocked.retry_after_seconds == 57


def test_login_throttle_expires_old_attempts() -> None:
    throttle = LoginThrottle(max_attempts=2, window_seconds=10)

    assert throttle.check("alice", now=100).allowed is True
    assert throttle.check("alice", now=101).allowed is True
    assert throttle.check("alice", now=102).allowed is False
    assert throttle.check("alice", now=111).allowed is True


def test_login_throttle_reset_clears_successful_identity() -> None:
    throttle = LoginThrottle(max_attempts=1, window_seconds=60)

    assert throttle.check("alice", now=100).allowed is True
    assert throttle.check("alice", now=101).allowed is False

    throttle.reset("ALICE")
    assert throttle.check("alice", now=102).allowed is True


def test_sqlite_login_throttle_is_shared_across_instances(tmp_path) -> None:
    database_path = tmp_path / "sessions.sqlite3"
    first_worker = SqliteLoginThrottle(
        max_attempts=2,
        window_seconds=60,
        database_path=str(database_path),
    )
    second_worker = SqliteLoginThrottle(
        max_attempts=2,
        window_seconds=60,
        database_path=str(database_path),
    )

    assert first_worker.check("Alice", now=100).allowed is True
    assert second_worker.check(" alice ", now=101).allowed is True

    blocked = first_worker.check("ALICE", now=102)
    assert blocked.allowed is False
    assert blocked.retry_after_seconds == 58


def test_sqlite_login_throttle_is_shared_across_processes(tmp_path) -> None:
    database_path = tmp_path / "sessions.sqlite3"
    SqliteLoginThrottle(
        max_attempts=2,
        window_seconds=60,
        database_path=str(database_path),
    )

    context = multiprocessing.get_context("spawn")
    results = []
    for key, now in (("Alice", 100.0), (" alice ", 101.0), ("ALICE", 102.0)):
        queue = context.Queue()
        process = context.Process(
            target=_sqlite_throttle_process_check,
            args=(str(database_path), key, now, queue),
        )
        process.start()
        process.join(timeout=10)

        assert process.exitcode == 0
        results.append(queue.get(timeout=2))
        queue.close()

    assert results == [(True, 0), (True, 0), (False, 58)]


def test_sqlite_login_throttle_reset_is_shared(tmp_path) -> None:
    database_path = tmp_path / "sessions.sqlite3"
    first_worker = SqliteLoginThrottle(
        max_attempts=1,
        window_seconds=60,
        database_path=str(database_path),
    )
    second_worker = SqliteLoginThrottle(
        max_attempts=1,
        window_seconds=60,
        database_path=str(database_path),
    )

    assert first_worker.check("alice", now=100).allowed is True
    assert second_worker.check("alice", now=101).allowed is False

    second_worker.reset(" ALICE ")
    assert first_worker.check("alice", now=102).allowed is True


def test_sqlite_login_throttle_prunes_expired_attempts(tmp_path) -> None:
    throttle = SqliteLoginThrottle(
        max_attempts=2,
        window_seconds=10,
        database_path=str(tmp_path / "sessions.sqlite3"),
    )

    assert throttle.check("alice", now=100).allowed is True
    assert throttle.check("alice", now=101).allowed is True
    assert throttle.check("alice", now=102).allowed is False
    assert throttle.check("alice", now=111).allowed is True


def test_sqlite_login_throttle_does_not_persist_plaintext_username(tmp_path) -> None:
    database_path = tmp_path / "sessions.sqlite3"
    throttle = SqliteLoginThrottle(
        max_attempts=2,
        window_seconds=60,
        database_path=str(database_path),
    )

    assert throttle.check("PrivateUser", now=100).allowed is True

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT identity_digest FROM login_throttle_attempts"
        ).fetchall()

    assert len(rows) == 1
    assert rows[0][0] != "privateuser"
    assert "privateuser" not in rows[0][0]


def test_create_login_throttle_tracks_session_backend(tmp_path) -> None:
    memory = create_login_throttle(
        backend="memory",
        max_attempts=2,
        window_seconds=60,
        database_path=str(tmp_path / "unused.sqlite3"),
    )
    shared = create_login_throttle(
        backend="sqlite",
        max_attempts=2,
        window_seconds=60,
        database_path=str(tmp_path / "sessions.sqlite3"),
    )

    assert isinstance(memory, LoginThrottle)
    assert isinstance(shared, SqliteLoginThrottle)
