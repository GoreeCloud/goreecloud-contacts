import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings, fastapi_documentation_options
from app.main import app, settings
from app.security import configured_frontend_origin, normalize_origin


_TEST_FERNET_KEY = Fernet.generate_key().decode("ascii")


def _production_settings(**overrides) -> Settings:
    values = {
        "app_env": "production",
        "frontend_origin": "https://contacts.goreecloud.com",
        "carddav_base_url": "https://calendar.goreecloud.com",
        "session_cookie_secure": True,
        "csrf_origin_check_enabled": True,
        "session_store_backend": "sqlite",
        "session_db_path": "/data/sessions.sqlite3",
        "session_encryption_keys": _TEST_FERNET_KEY,
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


def test_app_environment_normalizes_supported_values() -> None:
    development = Settings(_env_file=None, app_env=" DEVELOPMENT ")
    test = Settings(_env_file=None, app_env="Test")
    production = _production_settings(app_env=" PRODUCTION ")

    assert development.app_env == "development"
    assert test.app_env == "test"
    assert production.app_env == "production"
    assert development.is_production is False
    assert test.is_production is False
    assert production.is_production is True


@pytest.mark.parametrize("value", ["prod", "prodution", "staging", "local", ""])
def test_unknown_app_environment_fails_closed(value: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None, app_env=value)

    assert "app_env" in str(exc_info.value)


def test_production_configuration_accepts_secure_https_boundaries() -> None:
    configured = _production_settings(frontend_origin="https://CONTACTS.goreecloud.com/")

    assert configured.session_cookie_secure is True
    assert configured.csrf_origin_check_enabled is True
    assert configured.frontend_origin == "https://contacts.goreecloud.com"
    assert configured.session_store_backend == "sqlite"
    assert configured.session_encryption_key_list == [_TEST_FERNET_KEY]


def test_production_configuration_accepts_file_based_encryption_secret(tmp_path) -> None:
    secret_path = tmp_path / "session-encryption-keys"
    secret_path.write_text(_TEST_FERNET_KEY + "\n", encoding="utf-8")

    configured = _production_settings(
        session_encryption_keys="",
        session_encryption_keys_file=str(secret_path),
    )

    assert configured.session_encryption_key_list == [_TEST_FERNET_KEY]


def test_encryption_secret_sources_are_mutually_exclusive(tmp_path) -> None:
    secret_path = tmp_path / "session-encryption-keys"
    secret_path.write_text(_TEST_FERNET_KEY, encoding="utf-8")

    with pytest.raises(ValidationError, match="Configure only one"):
        _production_settings(session_encryption_keys_file=str(secret_path))


def test_production_encryption_secret_file_must_be_readable() -> None:
    with pytest.raises(ValidationError, match="readable secret file"):
        _production_settings(
            session_encryption_keys="",
            session_encryption_keys_file="/missing/goreecloud-contacts-session-key",
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"session_cookie_secure": False}, "SESSION_COOKIE_SECURE=true"),
        ({"csrf_origin_check_enabled": False}, "CSRF_ORIGIN_CHECK_ENABLED=true"),
        ({"frontend_origin": "http://contacts.goreecloud.com"}, "HTTPS FRONTEND_ORIGIN"),
        ({"carddav_base_url": ""}, "CARDDAV_BASE_URL to be configured"),
        ({"carddav_base_url": "http://calendar.goreecloud.com"}, "HTTPS CARDDAV_BASE_URL"),
        ({"session_store_backend": "memory"}, "SESSION_STORE_BACKEND=sqlite"),
        ({"session_encryption_keys": ""}, "SESSION_ENCRYPTION_KEYS"),
        ({"session_db_path": "sessions.sqlite3"}, "SESSION_DB_PATH to be an absolute path"),
        ({"session_encryption_keys_file": "relative/secret"}, "absolute path"),
    ],
)
def test_production_configuration_fails_closed(overrides, message) -> None:
    with pytest.raises(ValidationError, match=message):
        _production_settings(**overrides)


def test_api_documentation_is_enabled_only_outside_production() -> None:
    development = Settings(_env_file=None, app_env="development")
    test = Settings(_env_file=None, app_env="test")
    production = _production_settings()

    assert development.api_documentation_enabled is True
    assert test.api_documentation_enabled is True
    assert production.api_documentation_enabled is False


def test_documentation_route_configuration_matches_environment_policy() -> None:
    development_app = FastAPI(
        **fastapi_documentation_options(
            Settings(_env_file=None, app_env="development").api_documentation_enabled
        )
    )
    production_app = FastAPI(
        **fastapi_documentation_options(_production_settings().api_documentation_enabled)
    )

    with TestClient(development_app) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200
        assert client.get("/openapi.json").status_code == 200

    with TestClient(production_app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404


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
