from app.vcard import parse_vcard


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
