from app.duplicates import (
    detect_duplicate_candidates,
    merge_vcard_preserving_passthrough,
    propose_duplicate_merge,
)
from app.models import ContactDetail, ContactSummary, PublicProfile


def test_duplicate_detection_uses_normalized_email_and_phone() -> None:
    contacts = [
        ContactSummary(
            href="/book/a.vcf",
            formatted_name="Jordan Example",
            emails=["Jordan@Example.test"],
            phones=["+1 (555) 0100"],
        ),
        ContactSummary(
            href="/book/b.vcf",
            formatted_name="J. Example",
            emails=["jordan@example.test"],
            phones=["1-555-0100"],
        ),
    ]

    candidates = detect_duplicate_candidates(contacts)

    assert len(candidates) == 1
    assert candidates[0].confidence == "high"
    assert candidates[0].score == 100
    assert {signal.kind for signal in candidates[0].signals} == {"email", "phone"}


def test_duplicate_detection_marks_name_only_as_low_confidence() -> None:
    contacts = [
        ContactSummary(href="/book/a.vcf", formatted_name="Same Person"),
        ContactSummary(href="/book/b.vcf", formatted_name="same person"),
    ]

    candidates = detect_duplicate_candidates(contacts)

    assert len(candidates) == 1
    assert candidates[0].confidence == "low"
    assert candidates[0].score == 30


def test_merge_proposal_unions_multi_value_fields_and_reports_scalar_conflicts() -> None:
    primary = ContactDetail(
        href="/book/a.vcf",
        etag='"a"',
        uid="primary-uid",
        formatted_name="Jordan Example",
        emails=["jordan@example.test"],
        organization="Primary Org",
        categories=["Family"],
        favorite=False,
        public_profiles=[
            PublicProfile(platform="github", url="https://github.com/jordan-example")
        ],
    )
    duplicate = ContactDetail(
        href="/book/b.vcf",
        etag='"b"',
        uid="duplicate-uid",
        formatted_name="Jordan Example",
        emails=["JORDAN@example.test", "jordan.work@example.test"],
        phones=["+1-555-0100"],
        organization="Other Org",
        categories=["family", "Test"],
        favorite=True,
        public_profiles=[
            PublicProfile(platform="github", url="https://github.com/jordan-example"),
            PublicProfile(platform="linkedin", url="https://www.linkedin.com/in/jordan-example"),
        ],
    )

    proposal = propose_duplicate_merge(primary, duplicate)

    assert proposal.payload.emails == [
        "jordan@example.test",
        "jordan.work@example.test",
    ]
    assert proposal.payload.phones == ["+1-555-0100"]
    assert proposal.payload.categories == ["Family", "Test"]
    assert proposal.payload.public_profiles == [
        PublicProfile(platform="github", url="https://github.com/jordan-example"),
        PublicProfile(platform="linkedin", url="https://www.linkedin.com/in/jordan-example"),
    ]
    assert proposal.payload.favorite is True
    assert proposal.payload.organization == "Primary Org"
    assert [conflict.field for conflict in proposal.conflicts] == ["organization"]


def test_raw_merge_preserves_primary_uid_version_unknown_properties_and_profiles() -> None:
    primary_raw = """BEGIN:VCARD
VERSION:3.0
UID:primary-uid
FN:Primary Person
EMAIL:primary@example.test
URL;TYPE=profile;X-GOREECLOUD-PLATFORM=github:https://github.com/primary-person
X-PRIMARY:keep-primary
END:VCARD
"""
    duplicate_raw = """BEGIN:VCARD
VERSION:4.0
UID:duplicate-uid
FN:Duplicate Person
TEL:+1-555-0100
URL;TYPE=profile;X-GOREECLOUD-PLATFORM=linkedin:https://www.linkedin.com/in/duplicate-person
X-DUPLICATE:keep-duplicate
X-PRIMARY:keep-primary
END:VCARD
"""
    primary = ContactDetail(
        href="/book/a.vcf",
        uid="primary-uid",
        formatted_name="Primary Person",
        emails=["primary@example.test"],
        public_profiles=[
            PublicProfile(platform="github", url="https://github.com/primary-person")
        ],
    )
    duplicate = ContactDetail(
        href="/book/b.vcf",
        uid="duplicate-uid",
        formatted_name="Duplicate Person",
        phones=["+1-555-0100"],
        public_profiles=[
            PublicProfile(
                platform="linkedin",
                url="https://www.linkedin.com/in/duplicate-person",
            )
        ],
    )
    proposal = propose_duplicate_merge(primary, duplicate)

    merged = merge_vcard_preserving_passthrough(
        primary_raw,
        duplicate_raw,
        primary_uid="primary-uid",
        payload=proposal.payload,
    )

    assert "VERSION:3.0\r\n" in merged
    assert "UID:primary-uid\r\n" in merged
    assert "UID:duplicate-uid" not in merged
    assert "EMAIL:primary@example.test\r\n" in merged
    assert "TEL:+1-555-0100\r\n" in merged
    assert "URL;TYPE=profile;X-GOREECLOUD-PLATFORM=github:https://github.com/primary-person\r\n" in merged
    assert "URL;TYPE=profile;X-GOREECLOUD-PLATFORM=linkedin:https://www.linkedin.com/in/duplicate-person\r\n" in merged
    assert "X-PRIMARY:keep-primary\r\n" in merged
    assert "X-DUPLICATE:keep-duplicate\r\n" in merged
    assert merged.count("X-PRIMARY:keep-primary") == 1
