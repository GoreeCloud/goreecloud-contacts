from datetime import datetime
import re
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, SecretStr, field_validator


MAX_RESOURCE_HREF_CHARS = 4096
MAX_ETAG_CHARS = 1024

ContactEmail = Annotated[str, Field(min_length=1, max_length=320)]
ContactPhone = Annotated[str, Field(min_length=1, max_length=128)]
ContactWebsite = Annotated[str, Field(min_length=1, max_length=2048)]
ContactCategory = Annotated[str, Field(min_length=1, max_length=256)]

_PROFILE_PLATFORM_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


class ReadinessChecks(BaseModel):
    session_store: Literal["ok", "unavailable"]
    carddav: Literal["ok", "not_configured", "unavailable"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    service: str
    checks: ReadinessChecks


class CardDavStatusResponse(BaseModel):
    configured: bool
    read_only: bool
    write_enabled: bool


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=256)
    password: SecretStr = Field(min_length=1, max_length=4096)


class AuthSessionResponse(BaseModel):
    authenticated: bool
    username: str | None = None
    expires_at: datetime | None = None


class AddressBook(BaseModel):
    href: str
    display_name: str


class StructuredName(BaseModel):
    family_name: str = Field(default="", max_length=512)
    given_name: str = Field(default="", max_length=512)
    additional_names: str = Field(default="", max_length=512)
    honorific_prefixes: str = Field(default="", max_length=512)
    honorific_suffixes: str = Field(default="", max_length=512)


class PostalAddress(BaseModel):
    types: list[str] = Field(default_factory=list, max_length=20)
    po_box: str = Field(default="", max_length=512)
    extended_address: str = Field(default="", max_length=1024)
    street_address: str = Field(default="", max_length=2048)
    locality: str = Field(default="", max_length=512)
    region: str = Field(default="", max_length=512)
    postal_code: str = Field(default="", max_length=128)
    country: str = Field(default="", max_length=512)


class PublicProfile(BaseModel):
    """A user-entered public profile carried in a portable vCard URL property."""

    platform: str = Field(min_length=1, max_length=64)
    url: str = Field(min_length=1, max_length=2048)

    @field_validator("platform")
    @classmethod
    def normalize_platform(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not _PROFILE_PLATFORM_RE.fullmatch(normalized):
            raise ValueError(
                "Public profile platform must be a lowercase-compatible slug using letters, "
                "numbers, and hyphens."
            )
        return normalized

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        normalized = value.strip()
        parsed = urlparse(normalized)
        if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Public profile URLs must use HTTP or HTTPS.")
        return normalized


class ContactSummary(BaseModel):
    href: str
    etag: str | None = None
    uid: str | None = None
    formatted_name: str
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    organization: str | None = None
    title: str | None = None
    categories: list[str] = Field(default_factory=list)
    favorite: bool = False
    has_photo: bool = False


class ContactGroupSummary(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    count: int = Field(ge=1)


class ContactDetail(ContactSummary):
    structured_name: StructuredName = Field(default_factory=StructuredName)
    addresses: list[PostalAddress] = Field(default_factory=list)
    birthday: str | None = None
    websites: list[str] = Field(default_factory=list)
    public_profiles: list[PublicProfile] = Field(default_factory=list)
    note: str | None = None
    photo: str | None = None


class ContactWriteRequest(BaseModel):
    formatted_name: str = Field(min_length=1, max_length=512)
    structured_name: StructuredName = Field(default_factory=StructuredName)
    emails: list[ContactEmail] = Field(default_factory=list, max_length=50)
    phones: list[ContactPhone] = Field(default_factory=list, max_length=50)
    organization: str | None = Field(default=None, max_length=1024)
    title: str | None = Field(default=None, max_length=1024)
    addresses: list[PostalAddress] = Field(default_factory=list, max_length=20)
    birthday: str | None = Field(default=None, max_length=64)
    websites: list[ContactWebsite] = Field(default_factory=list, max_length=50)
    public_profiles: list[PublicProfile] = Field(default_factory=list, max_length=50)
    note: str | None = Field(default=None, max_length=10000)
    categories: list[ContactCategory] = Field(default_factory=list, max_length=100)
    favorite: bool = False
    photo: str | None = Field(default=None, max_length=4096)

    @field_validator("photo")
    @classmethod
    def validate_photo_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None

        parsed = urlparse(normalized)
        if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
            raise ValueError(
                "Phase 4A photo writes require an HTTP(S) URI reference. Embedded data "
                "URIs are not accepted because the current Radicale/vobject storage path "
                "does not preserve them losslessly."
            )

        return normalized


class ContactDeleteResponse(BaseModel):
    deleted: bool
    href: str
