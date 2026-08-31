from app.groups import filter_contacts_by_group, summarize_groups
from app.models import ContactSummary


def contact(name: str, *categories: str) -> ContactSummary:
    return ContactSummary(
        href=f"/{name}.vcf",
        formatted_name=name,
        categories=list(categories),
    )


def test_summarize_groups_deduplicates_case_and_whitespace_per_contact():
    groups = summarize_groups(
        [
            contact("Ada", "Family", " family ", "Friends"),
            contact("Grace", "FAMILY", "Work"),
            contact("Linus", "work"),
        ]
    )

    assert [(group.name, group.count) for group in groups] == [
        ("Family", 2),
        ("Friends", 1),
        ("Work", 2),
    ]


def test_filter_contacts_by_group_is_case_insensitive_and_exact():
    contacts = [
        contact("Ada", "Family"),
        contact("Grace", "Family Friends"),
        contact("Linus", "Work"),
    ]

    filtered = filter_contacts_by_group(contacts, " family ")

    assert [value.formatted_name for value in filtered] == ["Ada"]


def test_empty_group_filter_preserves_full_contact_list():
    contacts = [contact("Ada", "Family"), contact("Linus", "Work")]

    assert filter_contacts_by_group(contacts, None) is contacts
    assert filter_contacts_by_group(contacts, "   ") is contacts


def test_empty_categories_do_not_create_groups():
    groups = summarize_groups([contact("Ada", "", "   ")])

    assert groups == []
