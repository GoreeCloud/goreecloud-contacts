from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


class CardDavStatusResponse(BaseModel):
    configured: bool
    read_only: bool = True


class AddressBook(BaseModel):
    href: str
    display_name: str


class ContactSummary(BaseModel):
    href: str
    etag: str | None = None
    uid: str | None = None
    formatted_name: str
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
