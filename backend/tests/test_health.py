from fastapi.testclient import TestClient

import app.main as main


client = TestClient(main.app)


def test_health_compatibility_and_liveness() -> None:
    compatibility = client.get("/api/health")
    liveness = client.get("/api/health/live")

    for response in (compatibility, liveness):
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "goreecloud-contacts-backend"


def test_readiness_passes_only_when_session_store_and_carddav_are_ready(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "carddav_base_url", "https://dav.example.test")
    monkeypatch.setattr(main.session_store, "healthcheck", lambda: True)

    async def carddav_ready(*_args) -> bool:
        return True

    monkeypatch.setattr(main, "carddav_transport_ready", carddav_ready)

    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "goreecloud-contacts-backend",
        "checks": {"session_store": "ok", "carddav": "ok"},
    }


def test_readiness_fails_when_session_store_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "carddav_base_url", "https://dav.example.test")
    monkeypatch.setattr(main.session_store, "healthcheck", lambda: False)

    async def carddav_ready(*_args) -> bool:
        return True

    monkeypatch.setattr(main, "carddav_transport_ready", carddav_ready)

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"] == {
        "session_store": "unavailable",
        "carddav": "ok",
    }


def test_readiness_fails_when_carddav_is_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "carddav_base_url", "")
    monkeypatch.setattr(main.session_store, "healthcheck", lambda: True)

    async def must_not_probe(*_args) -> bool:
        raise AssertionError("CardDAV probe must not run when CardDAV is not configured")

    monkeypatch.setattr(main, "carddav_transport_ready", must_not_probe)

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == {
        "session_store": "ok",
        "carddav": "not_configured",
    }


def test_readiness_fails_when_carddav_transport_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "carddav_base_url", "https://dav.example.test")
    monkeypatch.setattr(main.session_store, "healthcheck", lambda: True)

    async def carddav_unavailable(*_args) -> bool:
        return False

    monkeypatch.setattr(main, "carddav_transport_ready", carddav_unavailable)

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == {
        "session_store": "ok",
        "carddav": "unavailable",
    }
    assert set(response.json()) == {"status", "service", "checks"}
