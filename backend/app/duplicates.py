from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import unicodedata

from .duplicate_models import DuplicateCandidate, DuplicateFieldConflict, DuplicateSignal
from .models import (
    ContactDetail,
    ContactSummary,
    ContactWriteRequest,
    PostalAddress,
    PublicProfile,
    StructuredName,
)
from .vcard import build_vcard


_SUPPORTED_PROPERTIES = {
    "BEGIN",
    "END",
    "VERSION",
    "UID",
    "FN",
    "N",
    "EMAIL",
    "TEL",
    "ORG",
    "TITLE",
    "ADR",
    "BDAY",
    "URL",
    "NOTE",
    "CATEGORIES",
    "PHOTO",
    "X-GOREECLOUD-FAVORITE",
}


@dataclass(frozen=True, slots=True)
class MergeProposal:
    payload: ContactWriteRequest
    conflicts: list[DuplicateFieldConflict]


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    cleaned = "".join(character if character.isalnum() else " " for character in normalized)
    return " ".join(cleaned.split())


def _normalize_email(value: str) -> str:
    return unicodedata.normalize("NFKC", value.strip()).casefold()


def _normalize_phone(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    return digits if len(digits) >= 7 else ""


def _stable_union(values: Iterable[str], *, key) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized_value = value.strip()
        if not normalized_value:
            continue
        identity = key(normalized_value)
        if not identity or identity in seen:
            continue
        seen.add(identity)
        result.append(normalized_value)
    return result


def _address_key(address: PostalAddress) -> tuple[str, ...]:
    return (
        ",".join(sorted(_normalize_text(item) for item in address.types if item.strip())),
        _normalize_text(address.po_box),
        _normalize_text(address.extended_address),
        _normalize_text(address.street_address),
        _normalize_text(address.locality),
        _normalize_text(address.region),
        _normalize_text(address.postal_code),
        _normalize_text(address.country),
    )


def _stable_address_union(addresses: Iterable[PostalAddress]) -> list[PostalAddress]:
    result: list[PostalAddress] = []
    seen: set[tuple[str, ...]] = set()
    for address in addresses:
        identity = _address_key(address)
        if not any(identity) or identity in seen:
            continue
        seen.add(identity)
        result.append(address)
    return result


def _profile_key(profile: PublicProfile) -> tuple[str, str]:
    return (profile.platform.casefold(), profile.url.casefold())


def _stable_profile_union(profiles: Iterable[PublicProfile]) -> list[PublicProfile]:
    result: list[PublicProfile] = []
    seen: set[tuple[str, str]] = set()
    for profile in profiles:
        identity = _profile_key(profile)
        if identity in seen:
            continue
        seen.add(identity)
        result.append(profile)
    return result


def detect_duplicate_candidates(contacts: list[ContactSummary]) -> list[DuplicateCandidate]:
    candidates: list[DuplicateCandidate] = []

    for left_index, left in enumerate(contacts):
        for right in contacts[left_index + 1 :]:
            signals: list[DuplicateSignal] = []
            score = 0

            if left.uid and right.uid and left.uid.strip() == right.uid.strip():
                signals.append(DuplicateSignal(kind="uid", value=left.uid.strip()))
                score += 100

            left_emails = {
                _normalize_email(value): value
                for value in left.emails
                if _normalize_email(value)
            }
            right_emails = {
                _normalize_email(value): value
                for value in right.emails
                if _normalize_email(value)
            }
            shared_emails = sorted(set(left_emails) & set(right_emails))
            if shared_emails:
                score += 80
                signals.extend(
                    DuplicateSignal(kind="email", value=left_emails[value])
                    for value in shared_emails
                )

            left_phones = {
                _normalize_phone(value): value
                for value in left.phones
                if _normalize_phone(value)
            }
            right_phones = {
                _normalize_phone(value): value
                for value in right.phones
                if _normalize_phone(value)
            }
            shared_phones = sorted(set(left_phones) & set(right_phones))
            if shared_phones:
                score += 80
                signals.extend(
                    DuplicateSignal(kind="phone", value=left_phones[value])
                    for value in shared_phones
                )

            left_name = _normalize_text(left.formatted_name)
            right_name = _normalize_text(right.formatted_name)
            same_name = bool(
                left_name
                and left_name == right_name
                and left_name != "unnamed contact"
            )
            if same_name:
                score += 30
                signals.append(DuplicateSignal(kind="name", value=left.formatted_name))

                left_org = _normalize_text(left.organization)
                right_org = _normalize_text(right.organization)
                if left_org and left_org == right_org:
                    score += 20
                    signals.append(
                        DuplicateSignal(
                            kind="organization",
                            value=left.organization or "",
                        )
                    )

                left_title = _normalize_text(left.title)
                right_title = _normalize_text(right.title)
                if left_title and left_title == right_title:
                    score += 10
                    signals.append(DuplicateSignal(kind="title", value=left.title or ""))

            if not signals:
                continue

            score = min(score, 100)
            strong = any(
                signal.kind in {"uid", "email", "phone"}
                for signal in signals
            )
            supporting = any(
                signal.kind in {"organization", "title"}
                for signal in signals
            )
            confidence = "high" if strong else "medium" if supporting else "low"

            candidates.append(
                DuplicateCandidate(
                    left=left,
                    right=right,
                    score=score,
                    confidence=confidence,
                    signals=signals,
                )
            )

    return sorted(
        candidates,
        key=lambda item: (
            -item.score,
            item.left.formatted_name.casefold(),
            item.right.formatted_name.casefold(),
            item.left.href,
            item.right.href,
        ),
    )


def _choose_scalar(
    field: str,
    primary: str | None,
    duplicate: str | None,
    conflicts: list[DuplicateFieldConflict],
    *,
    normalize=_normalize_text,
) -> str | None:
    primary_value = primary.strip() if primary and primary.strip() else None
    duplicate_value = duplicate.strip() if duplicate and duplicate.strip() else None

    if (
        primary_value
        and duplicate_value
        and normalize(primary_value) != normalize(duplicate_value)
    ):
        conflicts.append(
            DuplicateFieldConflict(
                field=field,
                primary_value=primary_value,
                duplicate_value=duplicate_value,
            )
        )

    return primary_value or duplicate_value


def _merge_structured_name(
    primary: StructuredName,
    duplicate: StructuredName,
    conflicts: list[DuplicateFieldConflict],
) -> StructuredName:
    values: dict[str, str] = {}
    for field in (
        "family_name",
        "given_name",
        "additional_names",
        "honorific_prefixes",
        "honorific_suffixes",
    ):
        values[field] = (
            _choose_scalar(
                f"structured_name.{field}",
                getattr(primary, field),
                getattr(duplicate, field),
                conflicts,
            )
            or ""
        )
    return StructuredName(**values)


def propose_duplicate_merge(
    primary: ContactDetail,
    duplicate: ContactDetail,
) -> MergeProposal:
    conflicts: list[DuplicateFieldConflict] = []

    formatted_name = _choose_scalar(
        "formatted_name",
        primary.formatted_name,
        duplicate.formatted_name,
        conflicts,
    ) or "Merged contact"
    structured_name = _merge_structured_name(
        primary.structured_name,
        duplicate.structured_name,
        conflicts,
    )

    organization = _choose_scalar(
        "organization",
        primary.organization,
        duplicate.organization,
        conflicts,
    )
    title = _choose_scalar("title", primary.title, duplicate.title, conflicts)
    birthday = _choose_scalar(
        "birthday",
        primary.birthday,
        duplicate.birthday,
        conflicts,
        normalize=lambda value: value.strip(),
    )
    note = _choose_scalar(
        "note",
        primary.note,
        duplicate.note,
        conflicts,
        normalize=lambda value: value.strip(),
    )
    photo = _choose_scalar(
        "photo",
        primary.photo,
        duplicate.photo,
        conflicts,
        normalize=lambda value: value.strip(),
    )

    payload = ContactWriteRequest(
        formatted_name=formatted_name,
        structured_name=structured_name,
        emails=_stable_union(
            [*primary.emails, *duplicate.emails],
            key=_normalize_email,
        ),
        phones=_stable_union(
            [*primary.phones, *duplicate.phones],
            key=lambda value: _normalize_phone(value) or _normalize_text(value),
        ),
        organization=organization,
        title=title,
        addresses=_stable_address_union(
            [*primary.addresses, *duplicate.addresses]
        ),
        birthday=birthday,
        websites=_stable_union(
            [*primary.websites, *duplicate.websites],
            key=lambda value: value.casefold(),
        ),
        public_profiles=_stable_profile_union(
            [*primary.public_profiles, *duplicate.public_profiles]
        ),
        note=note,
        categories=_stable_union(
            [*primary.categories, *duplicate.categories],
            key=_normalize_text,
        ),
        favorite=primary.favorite or duplicate.favorite,
        photo=photo,
    )
    return MergeProposal(payload=payload, conflicts=conflicts)


def _unfold(raw: str) -> list[str]:
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    unfolded: list[str] = []
    for line in normalized.split("\n"):
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def _property_name(line: str) -> str | None:
    if ":" not in line:
        return None
    left = line.split(":", 1)[0]
    return left.split(";", 1)[0].rsplit(".", 1)[-1].upper()


def _vcard_version(raw: str) -> str:
    for line in _unfold(raw):
        if _property_name(line) == "VERSION":
            return line.split(":", 1)[1].strip() or "4.0"
    return "4.0"


def _passthrough_lines(raw: str) -> list[str]:
    lines: list[str] = []
    for line in _unfold(raw):
        stripped = line.strip("\r\n")
        if not stripped:
            continue
        name = _property_name(stripped)
        if name is None or name in _SUPPORTED_PROPERTIES:
            continue
        lines.append(stripped)
    return lines


def merge_vcard_preserving_passthrough(
    primary_raw: str,
    duplicate_raw: str,
    *,
    primary_uid: str,
    payload: ContactWriteRequest,
) -> str:
    merged = build_vcard(
        uid=primary_uid,
        formatted_name=payload.formatted_name,
        structured_name=payload.structured_name,
        emails=payload.emails,
        phones=payload.phones,
        organization=payload.organization,
        title=payload.title,
        addresses=payload.addresses,
        birthday=payload.birthday,
        websites=payload.websites,
        public_profiles=payload.public_profiles,
        note=payload.note,
        categories=payload.categories,
        favorite=payload.favorite,
        photo=payload.photo,
    )

    version = _vcard_version(primary_raw)
    output = merged.replace(
        "VERSION:4.0\r\n",
        f"VERSION:{version}\r\n",
        1,
    )

    passthrough: list[str] = []
    seen: set[str] = set()
    for line in [
        *_passthrough_lines(primary_raw),
        *_passthrough_lines(duplicate_raw),
    ]:
        if line in seen:
            continue
        seen.add(line)
        passthrough.append(line)

    if not passthrough:
        return output

    marker = "END:VCARD\r\n"
    if marker not in output:
        raise ValueError("Merged vCard is missing END:VCARD.")
    return output.replace(
        marker,
        "".join(f"{line}\r\n" for line in passthrough) + marker,
        1,
    )
