from app.login_throttle import LoginThrottle


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
