from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path

import httpx
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_milestone4_phase4c_live.py"
SPEC = importlib.util.spec_from_file_location("phase4c_live_helper", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
phase4c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(phase4c)


def test_api_base_url_defaults_to_loopback_targets() -> None:
    assert (
        phase4c._validate_api_base_url(
            "http://127.0.0.1:8000/",
            allow_non_loopback=False,
        )
        == "http://127.0.0.1:8000"
    )
    assert (
        phase4c._validate_api_base_url(
            "http://localhost:8000",
            allow_non_loopback=False,
        )
        == "http://localhost:8000"
    )
    assert (
        phase4c._validate_api_base_url(
            "http://[::1]:8000",
            allow_non_loopback=False,
        )
        == "http://[::1]:8000"
    )


def test_api_base_url_refuses_remote_target_without_explicit_override() -> None:
    with pytest.raises(phase4c.ValidationFailure, match="non-loopback"):
        phase4c._validate_api_base_url(
            "https://contacts-test.example.test",
            allow_non_loopback=False,
        )

    assert (
        phase4c._validate_api_base_url(
            "https://contacts-test.example.test",
            allow_non_loopback=True,
        )
        == "https://contacts-test.example.test"
    )


def test_api_base_url_refuses_embedded_secrets_and_non_root_metadata() -> None:
    rejected = [
        "https://user:password@example.test",
        "https://example.test/api",
        "https://example.test?token=secret",
        "https://example.test#fragment",
    ]

    for value in rejected:
        with pytest.raises(phase4c.ValidationFailure):
            phase4c._validate_api_base_url(value, allow_non_loopback=True)


def test_cleanup_scope_allows_only_retained_and_known_fixture_uids() -> None:
    safe_contacts = [
        {"formatted_name": phase4c.JORDAN_NAME, "uid": phase4c.JORDAN_UID},
        {"formatted_name": phase4c.DUPLICATE_NAME, "uid": phase4c.PRIMARY_UID},
        {"formatted_name": phase4c.DUPLICATE_NAME, "uid": phase4c.DUPLICATE_UID},
    ]
    phase4c._validate_cleanup_scope(safe_contacts)

    with pytest.raises(phase4c.ValidationFailure, match="Cleanup refused"):
        phase4c._validate_cleanup_scope(
            safe_contacts
            + [{"formatted_name": "Unexpected Contact", "uid": "unexpected-contact-001"}]
        )


def test_final_session_ttl_requires_restored_eight_hour_value() -> None:
    now = datetime(2026, 8, 15, 6, 0, tzinfo=timezone.utc)
    phase4c._validate_restored_session_ttl(
        {
            "expires_at": (
                now + timedelta(seconds=phase4c.FINAL_SESSION_TTL_SECONDS)
            ).isoformat()
        },
        now=now,
    )

    with pytest.raises(phase4c.ValidationFailure, match="28,800-second"):
        phase4c._validate_restored_session_ttl(
            {"expires_at": (now + timedelta(hours=1)).isoformat()},
            now=now,
        )


def test_service_validation_refuses_production_environment() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/health":
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "service": "goreecloud-contacts-backend",
                    "environment": "production",
                },
            )
        return httpx.Response(
            200,
            json={"configured": True, "read_only": True, "write_enabled": False},
        )

    with httpx.Client(
        base_url="http://127.0.0.1:8000",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(phase4c.ValidationFailure, match="refuses backend environment"):
            phase4c._validate_service(client, require_write=False)
