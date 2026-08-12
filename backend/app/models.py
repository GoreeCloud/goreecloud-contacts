from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


class CardDavStatusResponse(BaseModel):
    configured: bool
    read_only: bool
    write_enabled: bool


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


class ContactWriteRequest(BaseModel):
    formatted_name: str = Field(min_length=1, max_length=512)
    emails: list[str] = Field(default_factory=list, max_length=50)
    phones: list[str] = Field(default_factory=list, max_length=50)


class ContactDeleteResponse(BaseModel):
    deleted: bool
    href: str
