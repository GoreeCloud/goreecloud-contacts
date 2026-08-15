import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import app, settings
from app.security import configured_frontend_origin, normalize_origin


def _production_settings(**overrides) -> Settings:
    values = {
        "app_env": "production",
        "frontend_origin": "https://contacts.goreecloud.com",
        "carddav_base_url": "https://dav.goreecloud.com",
        "session_cookie_secure": True,
        "csrf_origin_check_enabled": True,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_origin_normalization_rejects_non_origins_and_credentials() -> None:
    assert normalize_origin("https://CONTACTS.goreecloud.com") == (
        "https://contacts.goreecloud.com"
    )
    assert normalize_origin("null") is None
    assert normalize_origin("javascript:alert(1)") is None
    assert normalize_origin("https://user:pass@contacts.goreecloud.com") is None
    assert configured_frontend_origin("https://contacts.goreecloud.com/app") is None


def test_production_configuration_accepts_secure_https_boundaries() -> None:
    configured = _production_settings()

    assert configured.session_cookie_secure is True
    assert configured.csrf_origin_check_enabled is True
    assert configured.frontend_origin == "https://contacts.goreecloud.com"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"session_cookie_secure": False}, "SESSION_COOKIE_SECURE=true"),
        ({"csrf_origin_check_enabled": False}, "CSRF_ORIGIN_CHECK_ENABLED=true"),
        ({"frontend_origin": "http://contacts.goreecloud.com"}, "HTTPS FRONTEND_ORIGIN"),
        ({"carddav_base_url": ""}, "CARDDAV_BASE_URL to be configured"),
        ({"carddav_base_url": "http://dav.goreecloud.com"}, "HTTPS CARDDAV_BASE_URL"),
    ],
)
def test_production_configuration_fails_closed(overrides, message) -> None:
    with pytest.raises(ValidationError, match=message):
        _production_settings(**overrides)


def test_csrf_origin_check_rejects_missing_and_cross_origin_mutations(monkeypatch) -> None:
    monkeypatch.setattr(settings, "csrf_origin_check_enabled", True)
    monkeypatch.setattr(settings, "frontend_origin", "https://contacts.goreecloud.com")

    with TestClient(app) as client:
        missing = client.post("/api/auth/logout")
        hostile = client.post(
            "/api/auth/logout",
            headers={"Origin": "https://attacker.example"},
        )
        lookalike = client.post(
            "/api/auth/logout",
            headers={"Origin": "https://contacts.goreecloud.com.attacker.example"},
        )

    assert missing.status_code == 403
    assert hostile.status_code == 403
    assert lookalike.status_code == 403
    assert missing.json() == {"detail": "Request origin is not allowed."}


def test_csrf_origin_check_accepts_exact_origin_and_referer_fallback(monkeypatch) -> None:
    monkeypatch.setattr(settings, "csrf_origin_check_enabled", True)
    monkeypatch.setattr(settings, "frontend_origin", "https://contacts.goreecloud.com")

    with TestClient(app) as client:
        origin = client.post(
            "/api/auth/logout",
            headers={"Origin": "https://contacts.goreecloud.com"},
        )
        referer = client.post(
            "/api/auth/logout",
            headers={"Referer": "https://contacts.goreecloud.com/settings/profile"},
        )
        health = client.get("/api/health")

    assert origin.status_code == 200
    assert referer.status_code == 200
    assert health.status_code == 200
