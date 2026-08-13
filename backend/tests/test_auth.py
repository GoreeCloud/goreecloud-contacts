from fastapi.testclient import TestClient

from app.auth import SessionStore
from app.carddav import CardDavAuthenticationError, CardDavClient
from app.main import app, session_store, settings
from app.models import AddressBook, ContactDetail, PostalAddress, StructuredName


def test_session_record_repr_does_not_expose_secrets() -> None:
    store = SessionStore(ttl_seconds=60)
    record = store.create(username="test-user", password="super-secret-password")

    representation = repr(record)
    assert "super-secret-password" not in representation
    assert record.token not in representation
    assert "test-user" in representation


def test_login_session_and_logout(monkeypatch) -> None:
    session_store.clear()
    monkeypatch.setattr(settings, "carddav_base_url", "https://carddav.example.test")
    monkeypatch.setattr(settings, "session_cookie_secure", False)

    async def discover_address_books(self) -> list[AddressBook]:
        assert self.username == "test-user"
        assert self.password == "test-password"
        return [AddressBook(href="/test-user/contacts/", display_name="Contacts")]

    monkeypatch.setattr(CardDavClient, "discover_address_books", discover_address_books)

    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login",
            json={"username": "test-user", "password": "test-password"},
        )

        assert login.status_code == 200
        assert login.json()["authenticated"] is True
        assert login.json()["username"] == "test-user"
        assert "test-password" not in login.text

        set_cookie = login.headers["set-cookie"]
        assert "HttpOnly" in set_cookie
        assert "SameSite=strict" in set_cookie

        current = client.get("/api/auth/session")
        assert current.status_code == 200
        assert current.json()["authenticated"] is True
        assert current.json()["username"] == "test-user"

        books = client.get("/api/carddav/address-books")
        assert books.status_code == 200
        assert books.json()[0]["href"] == "/test-user/contacts/"

        logout = client.post("/api/auth/logout")
        assert logout.status_code == 200
        assert logout.json() == {
            "authenticated": False,
            "username": None,
            "expires_at": None,
        }

        after_logout = client.get("/api/carddav/address-books")
        assert after_logout.status_code == 401

    session_store.clear()


def test_authenticated_contact_detail_route(monkeypatch) -> None:
    session_store.clear()
    monkeypatch.setattr(settings, "carddav_base_url", "https://carddav.example.test")
    monkeypatch.setattr(settings, "session_cookie_secure", False)

    async def discover_address_books(self) -> list[AddressBook]:
        return [AddressBook(href="/test-user/contacts/", display_name="Contacts")]

    async def get_contact(self, href: str) -> ContactDetail:
        assert self.username == "test-user"
        assert self.password == "test-password"
        assert href == "/test-user/contacts/contact-001.vcf"
        return ContactDetail(
            href=href,
            etag='"etag-001"',
            uid="contact-001",
            formatted_name="Jordan Example",
            structured_name=StructuredName(
                family_name="Example",
                given_name="Jordan",
            ),
            emails=["jordan@example.test"],
            phones=["+1-555-0100"],
            organization="GoreeCloud",
            title="Synthetic Contact",
            addresses=[
                PostalAddress(
                    types=["home"],
                    street_address="123 Test Street",
                    locality="Birmingham",
                    region="AL",
                    postal_code="35203",
                    country="USA",
                )
            ],
            birthday="1990-08-12",
            websites=["https://example.test/jordan"],
            note="Synthetic detail",
            categories=["Test"],
            favorite=True,
        )

    monkeypatch.setattr(CardDavClient, "discover_address_books", discover_address_books)
    monkeypatch.setattr(CardDavClient, "get_contact", get_contact)

    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login",
            json={"username": "test-user", "password": "test-password"},
        )
        assert login.status_code == 200

        detail = client.get(
            "/api/carddav/contact",
            params={"href": "/test-user/contacts/contact-001.vcf"},
        )

        assert detail.status_code == 200
        payload = detail.json()
        assert payload["structured_name"]["given_name"] == "Jordan"
        assert payload["organization"] == "GoreeCloud"
        assert payload["addresses"][0]["locality"] == "Birmingham"
        assert payload["favorite"] is True
        assert payload["photo"] is None

    session_store.clear()


def test_login_rejects_invalid_carddav_credentials(monkeypatch) -> None:
    session_store.clear()
    monkeypatch.setattr(settings, "carddav_base_url", "https://carddav.example.test")

    async def reject_credentials(self) -> list[AddressBook]:
        raise CardDavAuthenticationError("CardDAV authentication failed.")

    monkeypatch.setattr(CardDavClient, "discover_address_books", reject_credentials)

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "test-user", "password": "wrong-password"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == (
            "Unable to sign in with the supplied CardDAV credentials."
        )
        assert client.get("/api/auth/session").json()["authenticated"] is False

    session_store.clear()


def test_carddav_routes_require_authenticated_session() -> None:
    session_store.clear()

    with TestClient(app) as client:
        address_books = client.get("/api/carddav/address-books")
        detail = client.get(
            "/api/carddav/contact",
            params={"href": "/test-user/contacts/contact-001.vcf"},
        )

    assert address_books.status_code == 401
    assert address_books.json()["detail"] == "Authentication is required."
    assert detail.status_code == 401
    assert detail.json()["detail"] == "Authentication is required."
