from typing import Literal

from pydantic import BaseModel, Field

from .models import ContactDetail, ContactSummary, ContactWriteRequest


class DuplicateSignal(BaseModel):
    kind: Literal["uid", "email", "phone", "name", "organization", "title"]
    value: str


class DuplicateCandidate(BaseModel):
    left: ContactSummary
    right: ContactSummary
    score: int = Field(ge=0, le=100)
    confidence: Literal["high", "medium", "low"]
    signals: list[DuplicateSignal] = Field(default_factory=list)


class DuplicateScanResponse(BaseModel):
    candidate_count: int
    candidates: list[DuplicateCandidate] = Field(default_factory=list)


class DuplicateMergePreviewRequest(BaseModel):
    address_book_href: str = Field(min_length=1)
    primary_href: str = Field(min_length=1)
    duplicate_href: str = Field(min_length=1)


class DuplicateFieldConflict(BaseModel):
    field: str
    primary_value: str
    duplicate_value: str


class DuplicateMergePreviewResponse(BaseModel):
    primary: ContactDetail
    duplicate: ContactDetail
    proposed: ContactWriteRequest
    conflicts: list[DuplicateFieldConflict] = Field(default_factory=list)
    passthrough_properties_preserved: bool = True


class DuplicateMergeRequest(BaseModel):
    address_book_href: str = Field(min_length=1)
    primary_href: str = Field(min_length=1)
    primary_etag: str = Field(min_length=1)
    duplicate_href: str = Field(min_length=1)
    duplicate_etag: str = Field(min_length=1)
    merged: ContactWriteRequest


class DuplicateMergeResponse(BaseModel):
    merged: ContactDetail
    deleted_href: str
