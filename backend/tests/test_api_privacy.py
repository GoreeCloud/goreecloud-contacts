from fastapi.testclient import TestClient

import app.main as main


client = TestClient(main.app)


def _assert_privacy_headers(response) -> None:
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["expires"] == "0"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_api_success_responses_are_not_cacheable() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    _assert_privacy_headers(response)


def test_api_auth_state_responses_are_not_cacheable() -> None:
    response = client.get("/api/auth/session")

    assert response.status_code == 200
    _assert_privacy_headers(response)


def test_api_error_responses_are_not_cacheable() -> None:
    response = client.get("/api/carddav/address-books")

    assert response.status_code == 401
    _assert_privacy_headers(response)


def test_csrf_rejections_receive_same_privacy_headers(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "csrf_origin_check_enabled", True)
    monkeypatch.setattr(main.settings, "frontend_origin", "https://contacts.goreecloud.com")

    response = client.post(
        "/api/auth/logout",
        headers={"Origin": "https://attacker.example"},
    )

    assert response.status_code == 403
    _assert_privacy_headers(response)


def test_non_api_routes_do_not_receive_api_cache_policy() -> None:
    response = client.get("/definitely-not-an-api-route")

    assert response.status_code == 404
    assert "cache-control" not in response.headers
