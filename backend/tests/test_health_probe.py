import asyncio

import httpx

import app.health as health


class FakeAsyncClient:
    def __init__(self, *, status_code: int | None = None, error: Exception | None = None):
        self.status_code = status_code
        self.error = error
        self.request_call = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def request(self, method, url, **kwargs):
        self.request_call = (method, url, kwargs)
        if self.error is not None:
            raise self.error
        assert self.status_code is not None
        return httpx.Response(self.status_code)


def _install_client(monkeypatch, fake: FakeAsyncClient) -> None:
    monkeypatch.setattr(
        health.httpx,
        "AsyncClient",
        lambda **_kwargs: fake,
    )


def test_carddav_probe_accepts_auth_required_response_without_credentials(monkeypatch) -> None:
    fake = FakeAsyncClient(status_code=401)
    _install_client(monkeypatch, fake)

    ready = asyncio.run(
        health.carddav_transport_ready("https://dav.example.test", 15.0)
    )

    assert ready is True
    method, url, kwargs = fake.request_call
    assert method == "PROPFIND"
    assert url == "https://dav.example.test"
    assert "Authorization" not in kwargs["headers"]
    assert kwargs["headers"]["Depth"] == "0"


def test_carddav_probe_accepts_success_and_rejects_endpoint_or_server_failures(monkeypatch) -> None:
    for status_code, expected in [(207, True), (403, True), (404, False), (405, False), (500, False)]:
        fake = FakeAsyncClient(status_code=status_code)
        _install_client(monkeypatch, fake)
        assert (
            asyncio.run(
                health.carddav_transport_ready("https://dav.example.test", 15.0)
            )
            is expected
        )


def test_carddav_probe_fails_closed_on_transport_error(monkeypatch) -> None:
    request = httpx.Request("PROPFIND", "https://dav.example.test")
    fake = FakeAsyncClient(error=httpx.ConnectError("unreachable", request=request))
    _install_client(monkeypatch, fake)

    assert (
        asyncio.run(
            health.carddav_transport_ready("https://dav.example.test", 15.0)
        )
        is False
    )


def test_carddav_probe_rejects_missing_configuration() -> None:
    assert asyncio.run(health.carddav_transport_ready("", 15.0)) is False
