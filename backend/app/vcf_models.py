from pydantic import BaseModel, Field


MAX_VCF_IMPORT_CHARS = 5_000_000


class VcfImportPreviewRequest(BaseModel):
    vcf_text: str = Field(min_length=1, max_length=MAX_VCF_IMPORT_CHARS)


class VcfImportPreviewItem(BaseModel):
    index: int
    valid: bool
    version: str | None = None
    uid: str | None = None
    formatted_name: str | None = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class VcfImportPreviewResponse(BaseModel):
    total: int
    valid: int
    invalid: int
    items: list[VcfImportPreviewItem]


class VcfImportRequest(BaseModel):
    address_book_href: str = Field(min_length=1, max_length=4096)
    vcf_text: str = Field(min_length=1, max_length=MAX_VCF_IMPORT_CHARS)
    selected_indices: list[int] | None = Field(default=None, max_length=5000)


class VcfImportResultItem(BaseModel):
    index: int
    href: str
    etag: str | None = None
    uid: str | None = None
    formatted_name: str


class VcfImportResponse(BaseModel):
    imported_count: int
    items: list[VcfImportResultItem]
