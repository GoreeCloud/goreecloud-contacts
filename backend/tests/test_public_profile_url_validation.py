import pytest
from pydantic import ValidationError

from app.models import PublicProfile


def test_public_profile_requires_a_real_hostname() -> None:
    with pytest.raises(ValidationError, match="valid host"):
        PublicProfile(platform="example", url="https://:443/profile")

    with pytest.raises(ValidationError, match="valid host"):
        PublicProfile(platform="example", url="https://exa mple.test/profile")


def test_public_profile_rejects_malformed_explicit_port() -> None:
    with pytest.raises(ValidationError, match="valid port"):
        PublicProfile(platform="example", url="https://example.test:not-a-port/profile")


def test_public_profile_keeps_valid_explicit_ports() -> None:
    profile = PublicProfile(
        platform="example",
        url="https://example.test:8443/profile",
    )

    assert profile.url == "https://example.test:8443/profile"
