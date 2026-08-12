from app.models import PostalAddress, StructuredName
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
    assert contact.favorite is False
    assert contact.has_photo is False


def test_parse_expanded_vcard_fields() -> None:
    raw = """BEGIN:VCARD
VERSION:4.0
UID:test-contact-expanded-001
FN:Dr. Jordan Quinn Example Jr.
N:Example;Jordan;Quinn;Dr.;Jr.
EMAIL;TYPE=home:jordan@example.test
TEL;TYPE=cell:+1-555-0100
ORG:GoreeCloud
TITLE:Test Contact
ADR;TYPE=home:;;123 Test Street;Birmingham;AL;35203;USA
BDAY:1990-08-12
URL:https://example.test/profile
NOTE:Line one\\nLine two\\, with comma
CATEGORIES:Family,Emergency\\,Contacts
X-GOREECLOUD-FAVORITE:TRUE
PHOTO;VALUE=uri:data:image/png;base64,AAAA
END:VCARD
"""

    contact = parse_vcard(
        raw,
        href="/addressbooks/test/contact-expanded-001.vcf",
        etag='"expanded-etag"',
    )

    assert contact.structured_name == StructuredName(
        family_name="Example",
        given_name="Jordan",
        additional_names="Quinn",
        honorific_prefixes="Dr.",
        honorific_suffixes="Jr.",
    )
    assert contact.organization == "GoreeCloud"
    assert contact.title == "Test Contact"
    assert contact.addresses == [
        PostalAddress(
            types=["home"],
            street_address="123 Test Street",
            locality="Birmingham",
            region="AL",
            postal_code="35203",
            country="USA",
        )
    ]
    assert contact.birthday == "1990-08-12"
    assert contact.websites == ["https://example.test/profile"]
    assert contact.note == "Line one\nLine two, with comma"
    assert contact.categories == ["Family", "Emergency,Contacts"]
    assert contact.favorite is True
    assert contact.has_photo is True
    assert contact.photo == "data:image/png;base64,AAAA"


def test_structured_name_falls_back_when_fn_is_missing() -> None:
    raw = """BEGIN:VCARD
VERSION:4.0
UID:test-contact-name-fallback
N:Example;Jordan;Quinn;Dr.;Jr.
END:VCARD
"""

    contact = parse_vcard(
        raw,
        href="/addressbooks/test/name-fallback.vcf",
        etag=None,
    )

    assert contact.formatted_name == "Dr. Jordan Quinn Example Jr."


def test_build_vcard_round_trip() -> None:
    raw = build_vcard(
        uid="test-contact-002",
        formatted_name="Taylor, Example",
        structured_name=StructuredName(
            family_name="Example",
            given_name="Taylor",
            honorific_prefixes="Mx.",
        ),
        emails=["taylor@example.test", "other@example.test"],
        phones=["+1-555-0199"],
        organization="GoreeCloud",
        title="Synthetic Contact",
        addresses=[
            PostalAddress(
                types=["home"],
                street_address="456 Example Ave",
                locality="Montgomery",
                region="AL",
                postal_code="36104",
                country="USA",
            )
        ],
        birthday="1995-02-03",
        websites=["https://example.test/taylor"],
        note="Synthetic note, with punctuation; and a second line\nfor testing.",
        categories=["Family", "Test,Group"],
        favorite=True,
        photo="data:image/png;base64,BBBB",
    )

    assert "\r\n" in raw
    assert "FN:Taylor\\, Example" in raw
    assert "N:Example;Taylor;;Mx.;" in raw
    assert "ADR;TYPE=home:;;456 Example Ave;Montgomery;AL;36104;USA" in raw
    assert "X-GOREECLOUD-FAVORITE:TRUE" in raw

    contact = parse_vcard(
        raw,
        href="/addressbooks/test/contact-002.vcf",
        etag='"etag-002"',
    )

    assert contact.uid == "test-contact-002"
    assert contact.formatted_name == "Taylor, Example"
    assert contact.structured_name.family_name == "Example"
    assert contact.structured_name.given_name == "Taylor"
    assert contact.emails == ["taylor@example.test", "other@example.test"]
    assert contact.phones == ["+1-555-0199"]
    assert contact.organization == "GoreeCloud"
    assert contact.title == "Synthetic Contact"
    assert contact.addresses[0].locality == "Montgomery"
    assert contact.birthday == "1995-02-03"
    assert contact.websites == ["https://example.test/taylor"]
    assert contact.note == "Synthetic note, with punctuation; and a second line\nfor testing."
    assert contact.categories == ["Family", "Test,Group"]
    assert contact.favorite is True
    assert contact.has_photo is True
