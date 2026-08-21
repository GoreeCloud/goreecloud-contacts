from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.browser_security import BROWSER_SECURITY_HEADERS, BrowserSecurityHeadersMiddleware


def _client() -> TestClient:
    application = FastAPI()

    @application.get("/")
    async def index():
        return {"status": "ok"}

    application.add_middleware(BrowserSecurityHeadersMiddleware)
    return TestClient(application)


def test_browser_security_headers_apply_to_every_response() -> None:
    response = _client().get("/")

    assert response.status_code == 200
    for name, value in BROWSER_SECURITY_HEADERS.items():
        assert response.headers[name] == value


def test_content_security_policy_is_same_origin_and_fail_closed() -> None:
    response = _client().get("/")
    policy = response.headers["Content-Security-Policy"]

    assert "default-src 'self'" in policy
    assert "connect-src 'self'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "object-src 'none'" in policy
    assert "script-src 'self'" in policy
    assert "style-src 'self'" in policy
    assert "worker-src 'none'" in policy
    assert "http:" not in policy
    assert "https:" not in policy
    assert "'unsafe-inline'" not in policy
    assert "'unsafe-eval'" not in policy


def test_browser_policy_disables_sensitive_browser_features() -> None:
    response = _client().get("/")

    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert response.headers["Permissions-Policy"] == (
        "camera=(), geolocation=(), microphone=(), payment=(), usb=()"
    )
