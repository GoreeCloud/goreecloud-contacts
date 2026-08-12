from app.vcard import build_vcard, parse_vcard


def test_parse_vcard_summary() -> None:
    raw = """BEGIN:VCARD
VERSION:4.0
UID:test-contact-001
FN:Jordan Example
EMAIL;TYPE=home:jordan@example.test
TEL;TYPE=cell:+1-555-0100
END:VCARD
"""

    contact = parse_vcard(
        raw,
        href="/addressbooks/test/contact-001.vcf",
        etag='"test-etag"',
    )

    assert contact.uid == "test-contact-001"
    assert contact.formatted_name == "Jordan Example"
    assert contact.emails == ["jordan@example.test"]
    assert contact.phones == ["+1-555-0100"]


def test_build_vcard_round_trip() -> None:
    raw = build_vcard(
        uid="test-contact-002",
        formatted_name="Taylor, Example",
        emails=["taylor@example.test", "other@example.test"],
        phones=["+1-555-0199"],
    )

    assert "\r\n" in raw
    assert "FN:Taylor\\, Example" in raw

    contact = parse_vcard(
        raw,
        href="/addressbooks/test/contact-002.vcf",
        etag='"etag-002"',
    )

    assert contact.uid == "test-contact-002"
    assert contact.formatted_name == "Taylor, Example"
    assert contact.emails == ["taylor@example.test", "other@example.test"]
    assert contact.phones == ["+1-555-0199"]
