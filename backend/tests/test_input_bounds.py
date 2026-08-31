import pytest
from pydantic import ValidationError

import app.vcf as vcf
from app.duplicate_models import DuplicateMergePreviewRequest, DuplicateMergeRequest
from app.models import ContactWriteRequest
from app.vcf_models import MAX_VCF_RECORDS, VcfImportRequest


def test_contact_write_limits_individual_multi_value_fields() -> None:
    accepted = ContactWriteRequest(
        formatted_name="Bounded Example",
        emails=["a" * 320],
        phones=["1" * 128],
        websites=["h" * 2048],
        categories=["c" * 256],
    )

    assert len(accepted.emails[0]) == 320
    assert len(accepted.phones[0]) == 128
    assert len(accepted.websites[0]) == 2048
    assert len(accepted.categories[0]) == 256

    for field, value in [
        ("emails", ["a" * 321]),
        ("phones", ["1" * 129]),
        ("websites", ["h" * 2049]),
        ("categories", ["c" * 257]),
    ]:
        with pytest.raises(ValidationError):
            ContactWriteRequest(formatted_name="Too Large", **{field: value})


def test_contact_write_limits_photo_reference_length() -> None:
    prefix = "https://example.test/"
    accepted = ContactWriteRequest(
        formatted_name="Photo Bound",
        photo=prefix + "a" * (4096 - len(prefix)),
    )
    assert accepted.photo is not None
    assert len(accepted.photo) == 4096

    with pytest.raises(ValidationError):
        ContactWriteRequest(
            formatted_name="Photo Too Large",
            photo=prefix + "a" * (4097 - len(prefix)),
        )


def test_duplicate_review_limits_resource_identifiers_and_etags() -> None:
    DuplicateMergePreviewRequest(
        address_book_href="/" + "a" * 4095,
        primary_href="/" + "p" * 4095,
        duplicate_href="/" + "d" * 4095,
    )

    with pytest.raises(ValidationError):
        DuplicateMergePreviewRequest(
            address_book_href="/" + "a" * 4096,
            primary_href="/p.vcf",
            duplicate_href="/d.vcf",
        )

    with pytest.raises(ValidationError):
        DuplicateMergeRequest(
            address_book_href="/book/",
            primary_href="/book/p.vcf",
            primary_etag="e" * 1025,
            duplicate_href="/book/d.vcf",
            duplicate_etag='"d"',
            merged=ContactWriteRequest(formatted_name="Merged"),
        )


def test_vcf_import_selection_count_is_bounded() -> None:
    with pytest.raises(ValidationError):
        VcfImportRequest(
            address_book_href="/book/",
            vcf_text="BEGIN:VCARD\nVERSION:4.0\nFN:Example\nEND:VCARD\n",
            selected_indices=[0] * (MAX_VCF_RECORDS + 1),
        )


def test_split_vcards_rejects_files_over_record_limit(monkeypatch) -> None:
    monkeypatch.setattr(vcf, "MAX_VCF_RECORDS", 2)
    card = "BEGIN:VCARD\nVERSION:4.0\nFN:Example\nEND:VCARD\n"

    assert len(vcf.split_vcards(card * 2)) == 2
    with pytest.raises(ValueError, match="at most 2 vCard records"):
        vcf.split_vcards(card * 3)
