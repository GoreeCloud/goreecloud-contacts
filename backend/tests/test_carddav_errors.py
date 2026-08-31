import pytest

from app.carddav import (
    CardDavAuthenticationError,
    CardDavAuthorizationError,
    CardDavConflict,
    CardDavError,
    CardDavNotFound,
)
from app.carddav_errors import carddav_http_exception


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (
            CardDavAuthenticationError("upstream detail that must not matter"),
            401,
            "CardDAV authentication failed.",
        ),
        (
            CardDavAuthorizationError("The selected address book is not authorized for this session."),
            403,
            "The selected address book is not authorized for this session.",
        ),
        (
            CardDavConflict("The contact changed after review."),
            409,
            "The contact changed after review.",
        ),
        (
            CardDavNotFound("CardDAV resource was not found."),
            404,
            "CardDAV resource was not found.",
        ),
    ],
)
def test_controlled_carddav_failures_keep_expected_browser_semantics(
    error: CardDavError,
    expected_status: int,
    expected_detail: str,
) -> None:
    mapped = carddav_http_exception(error)

    assert mapped.status_code == expected_status
    assert mapped.detail == expected_detail


def test_unexpected_carddav_error_is_not_reflected_to_browser() -> None:
    upstream_detail = (
        "CardDAV server https://calendar.example.test/private-user/contacts returned "
        "an implementation-specific parser failure"
    )

    mapped = carddav_http_exception(CardDavError(upstream_detail))

    assert mapped.status_code == 502
    assert mapped.detail == "CardDAV request could not be completed."
    assert "private-user" not in mapped.detail
    assert "calendar.example.test" not in mapped.detail
