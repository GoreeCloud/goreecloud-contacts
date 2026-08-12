from __future__ import annotations

import re

from .models import ContactDetail, PostalAddress, StructuredName


_PARAM_TOKEN = re.compile(r"^[A-Za-z0-9-]+$")


def _unfold(raw: str) -> list[str]:
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    unfolded: list[str] = []

    for line in normalized.split("\n"):
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)

    return unfolded


def _unescape(value: str) -> str:
    output: list[str] = []
    index = 0

    while index < len(value):
        character = value[index]
        if character != "\\" or index + 1 >= len(value):
            output.append(character)
            index += 1
            continue

        escaped = value[index + 1]
        if escaped in {"n", "N"}:
            output.append("\n")
        elif escaped in {"\\", ",", ";"}:
            output.append(escaped)
        else:
            output.extend(("\\", escaped))
        index += 2

    return "".join(output)


def _escape(value: str) -> str:
    return (
        value.replace("\\", r"\\")
        .replace("\r\n", r"\n")
        .replace("\r", r"\n")
        .replace("\n", r"\n")
        .replace(";", r"\;")
        .replace(",", r"\,")
    )


def _split_escaped(value: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    escaped = False

    for character in value:
        if escaped:
            current.extend(("\\", character))
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character == delimiter:
            parts.append("".join(current))
            current = []
            continue
        current.append(character)

    if escaped:
        current.append("\\")
    parts.append("".join(current))
    return parts


def _property(line: str) -> tuple[str, dict[str, list[str]], str] | None:
    if ":" not in line:
        return None

    left, raw_value = line.split(":", 1)
    pieces = left.split(";")
    name = pieces[0].rsplit(".", 1)[-1].upper()
    params: dict[str, list[str]] = {}

    for piece in pieces[1:]:
        if "=" not in piece:
            continue
        key, value = piece.split("=", 1)
        params.setdefault(key.upper(), []).extend(
            item.strip('"') for item in value.split(",") if item.strip('"')
        )

    return name, params, raw_value.strip()


def _types(params: dict[str, list[str]]) -> list[str]:
    return [value.casefold() for value in params.get("TYPE", []) if value]


def _structured_name(raw_value: str) -> StructuredName:
    parts = _split_escaped(raw_value, ";")
    parts.extend([""] * (5 - len(parts)))
    return StructuredName(
        family_name=_unescape(parts[0]),
        given_name=_unescape(parts[1]),
        additional_names=_unescape(parts[2]),
        honorific_prefixes=_unescape(parts[3]),
        honorific_suffixes=_unescape(parts[4]),
    )


def _display_name_from_structured(name: StructuredName) -> str | None:
    parts = [
        name.honorific_prefixes,
        name.given_name,
        name.additional_names,
        name.family_name,
        name.honorific_suffixes,
    ]
    display_name = " ".join(part.strip() for part in parts if part.strip())
    return display_name or None


def _postal_address(raw_value: str, params: dict[str, list[str]]) -> PostalAddress:
    parts = _split_escaped(raw_value, ";")
    parts.extend([""] * (7 - len(parts)))
    return PostalAddress(
        types=_types(params),
        po_box=_unescape(parts[0]),
        extended_address=_unescape(parts[1]),
        street_address=_unescape(parts[2]),
        locality=_unescape(parts[3]),
        region=_unescape(parts[4]),
        postal_code=_unescape(parts[5]),
        country=_unescape(parts[6]),
    )


def _photo_uri_compat(raw_value: str) -> str:
    """Normalize the known Radicale/vobject data-URI escaping defect on reads.

    RFC 6350 PHOTO values are URIs, so the semicolon separating a data URI's
    media type from the ``base64`` marker must not be backslash-escaped.
    Some Radicale/vobject combinations rewrite it as ``\\;`` (and may escape
    the following comma).  GoreeCloud continues to emit standards-compliant
    vCard 4.0 and tolerates only this narrow server-side rewrite when reading.
    """

    normalized = raw_value.strip()
    if not normalized.casefold().startswith("data:image/"):
        return normalized

    return re.sub(
        r"^(data:image/[^,]*?)\\;base64\\?,",
        r"\1;base64,",
        normalized,
        count=1,
        flags=re.IGNORECASE,
    )


def parse_vcard(raw: str, *, href: str, etag: str | None) -> ContactDetail:
    uid: str | None = None
    formatted_name: str | None = None
    structured_name = StructuredName()
    emails: list[str] = []
    phones: list[str] = []
    organization: str | None = None
    title: str | None = None
    addresses: list[PostalAddress] = []
    birthday: str | None = None
    websites: list[str] = []
    note: str | None = None
    categories: list[str] = []
    favorite = False
    photo: str | None = None

    for line in _unfold(raw):
        item = _property(line)
        if item is None:
            continue

        name, params, raw_value = item

        if name == "UID" and not uid:
            uid = _unescape(raw_value)
        elif name == "FN" and not formatted_name:
            formatted_name = _unescape(raw_value)
        elif name == "N":
            structured_name = _structured_name(raw_value)
        elif name == "EMAIL" and raw_value:
            emails.append(_unescape(raw_value))
        elif name == "TEL" and raw_value:
            phones.append(_unescape(raw_value))
        elif name == "ORG" and not organization:
            organization = _unescape(raw_value) or None
        elif name == "TITLE" and not title:
            title = _unescape(raw_value) or None
        elif name == "ADR" and raw_value:
            addresses.append(_postal_address(raw_value, params))
        elif name == "BDAY" and not birthday:
            birthday = raw_value or None
        elif name == "URL" and raw_value:
            websites.append(raw_value)
        elif name == "NOTE" and not note:
            note = _unescape(raw_value) or None
        elif name == "CATEGORIES" and raw_value:
            categories.extend(
                _unescape(value)
                for value in _split_escaped(raw_value, ",")
                if _unescape(value)
            )
        elif name == "X-GOREECLOUD-FAVORITE":
            favorite = raw_value.strip().casefold() in {"1", "true", "yes"}
        elif name == "PHOTO" and not photo and raw_value:
            photo = _photo_uri_compat(raw_value)

    return ContactDetail(
        href=href,
        etag=etag,
        uid=uid,
        formatted_name=(
            formatted_name
            or _display_name_from_structured(structured_name)
            or "Unnamed contact"
        ),
        structured_name=structured_name,
        emails=emails,
        phones=phones,
        organization=organization,
        title=title,
        addresses=addresses,
        birthday=birthday,
        websites=websites,
        note=note,
        categories=categories,
        favorite=favorite,
        has_photo=photo is not None,
        photo=photo,
    )


def _parameterized_property(name: str, types: list[str], value: str) -> str:
    safe_types = [item for item in types if _PARAM_TOKEN.fullmatch(item)]
    parameter = f";TYPE={','.join(safe_types)}" if safe_types else ""
    return f"{name}{parameter}:{value}"


def _uri_value(value: str) -> str:
    normalized = value.strip()
    if "\r" in normalized or "\n" in normalized:
        raise ValueError("vCard URI values cannot contain line breaks.")
    return normalized


def build_vcard(
    *,
    uid: str,
    formatted_name: str,
    structured_name: StructuredName | None = None,
    emails: list[str],
    phones: list[str],
    organization: str | None = None,
    title: str | None = None,
    addresses: list[PostalAddress] | None = None,
    birthday: str | None = None,
    websites: list[str] | None = None,
    note: str | None = None,
    categories: list[str] | None = None,
    favorite: bool = False,
    photo: str | None = None,
) -> str:
    structured_name = structured_name or StructuredName()
    addresses = addresses or []
    websites = websites or []
    categories = categories or []

    lines = [
        "BEGIN:VCARD",
        "VERSION:4.0",
        f"UID:{_escape(uid)}",
        f"FN:{_escape(formatted_name.strip())}",
    ]

    name_parts = [
        structured_name.family_name,
        structured_name.given_name,
        structured_name.additional_names,
        structured_name.honorific_prefixes,
        structured_name.honorific_suffixes,
    ]
    if any(part.strip() for part in name_parts):
        lines.append("N:" + ";".join(_escape(part.strip()) for part in name_parts))

    lines.extend(f"EMAIL:{_escape(value.strip())}" for value in emails if value.strip())
    lines.extend(f"TEL:{_escape(value.strip())}" for value in phones if value.strip())

    if organization and organization.strip():
        lines.append(f"ORG:{_escape(organization.strip())}")
    if title and title.strip():
        lines.append(f"TITLE:{_escape(title.strip())}")

    for address in addresses:
        address_parts = [
            address.po_box,
            address.extended_address,
            address.street_address,
            address.locality,
            address.region,
            address.postal_code,
            address.country,
        ]
        if not any(part.strip() for part in address_parts):
            continue
        value = ";".join(_escape(part.strip()) for part in address_parts)
        lines.append(_parameterized_property("ADR", address.types, value))

    if birthday and birthday.strip():
        lines.append(f"BDAY:{_uri_value(birthday)}")
    lines.extend(f"URL:{_uri_value(value)}" for value in websites if value.strip())
    if note and note.strip():
        lines.append(f"NOTE:{_escape(note.strip())}")

    normalized_categories = [value.strip() for value in categories if value.strip()]
    if normalized_categories:
        lines.append(
            "CATEGORIES:" + ",".join(_escape(value) for value in normalized_categories)
        )
    if favorite:
        lines.append("X-GOREECLOUD-FAVORITE:TRUE")
    if photo and photo.strip():
        lines.append(f"PHOTO;VALUE=uri:{_uri_value(photo)}")

    lines.append("END:VCARD")
    return "\r\n".join(lines) + "\r\n"
