import pytest

from app.vcf import ensure_vcard_uid, inspect_vcard, split_vcards


def test_split_vcards_preserves_unknown_properties() -> None:
    raw = """BEGIN:VCARD
VERSION:4.0
UID:first-001
FN:First Example
X-EXAMPLE-UNKNOWN:keep-me
END:VCARD
BEGIN:VCARD
VERSION:3.0
UID:second-002
FN:Second Example
EMAIL:second@example.test
END:VCARD
"""

    records = split_vcards(raw)

    assert len(records) == 2
    assert "X-EXAMPLE-UNKNOWN:keep-me" in records[0]
    assert inspect_vcard(records[0]).version == "4.0"
    assert inspect_vcard(records[1]).version == "3.0"


def test_inspect_vcard_rejects_unsupported_version() -> None:
    raw = """BEGIN:VCARD
VERSION:2.1
FN:Legacy Example
END:VCARD
"""

    with pytest.raises(ValueError, match="accepts vCard 3.0 and 4.0"):
        inspect_vcard(raw)


def test_missing_uid_is_warned_and_generated_without_dropping_unknown_fields() -> None:
    raw = """BEGIN:VCARD
VERSION:4.0
FN:No UID Example
X-EXAMPLE-UNKNOWN:preserve-this
END:VCARD
"""

    inspection = inspect_vcard(raw)
    assert inspection.contact.uid is None
    assert inspection.warnings

    prepared, uid = ensure_vcard_uid(raw, "generated-test-uid")

    assert uid == "generated-test-uid"
    assert "UID:generated-test-uid" in prepared
    assert "X-EXAMPLE-UNKNOWN:preserve-this" in prepared


def test_split_vcards_rejects_content_outside_records() -> None:
    raw = """not-a-vcard
BEGIN:VCARD
VERSION:4.0
FN:Example
END:VCARD
"""

    with pytest.raises(ValueError, match="outside a vCard"):
        split_vcards(raw)
