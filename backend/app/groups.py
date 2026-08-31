"""CardDAV-backed contact grouping helpers.

Groups are derived from vCard CATEGORIES so Radicale remains the authoritative
contact store. No second groups database is introduced.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import ContactSummary


@dataclass(frozen=True, slots=True)
class ContactGroup:
    name: str
    count: int


def _normalized_group(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def summarize_groups(contacts: list[ContactSummary]) -> list[ContactGroup]:
    display_names: dict[str, str] = {}
    counts: dict[str, int] = {}

    for contact in contacts:
        seen_for_contact: set[str] = set()
        for raw_category in contact.categories:
            display_name = " ".join(raw_category.strip().split())
            normalized = _normalized_group(display_name)
            if not normalized or normalized in seen_for_contact:
                continue
            display_names.setdefault(normalized, display_name)
            counts[normalized] = counts.get(normalized, 0) + 1
            seen_for_contact.add(normalized)

    return [
        ContactGroup(name=display_names[key], count=counts[key])
        for key in sorted(counts, key=lambda item: display_names[item].casefold())
    ]


def filter_contacts_by_group(
    contacts: list[ContactSummary], category: str | None
) -> list[ContactSummary]:
    if category is None:
        return contacts

    normalized = _normalized_group(category)
    if not normalized:
        return contacts

    return [
        contact
        for contact in contacts
        if any(_normalized_group(value) == normalized for value in contact.categories)
    ]
