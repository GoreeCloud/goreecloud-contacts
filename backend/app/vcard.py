from .models import ContactSummary


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
    return (
        value.replace(r"\n", "\n")
        .replace(r"\N", "\n")
        .replace(r"\,", ",")
        .replace(r"\;", ";")
        .replace(r"\\", "\\")
    )


def _escape(value: str) -> str:
    return (
        value.replace("\\", r"\\")
        .replace("\r\n", r"\n")
        .replace("\r", r"\n")
        .replace("\n", r"\n")
        .replace(";", r"\;")
        .replace(",", r"\,")
    )


def _property(line: str) -> tuple[str, str] | None:
    if ":" not in line:
        return None

    left, value = line.split(":", 1)
    name = left.split(";", 1)[0].upper()
    return name, _unescape(value.strip())


def parse_vcard(raw: str, *, href: str, etag: str | None) -> ContactSummary:
    uid: str | None = None
    formatted_name: str | None = None
    structured_name: str | None = None
    emails: list[str] = []
    phones: list[str] = []

    for line in _unfold(raw):
        item = _property(line)
        if item is None:
            continue

        name, value = item

        if name == "UID" and not uid:
            uid = value
        elif name == "FN" and not formatted_name:
            formatted_name = value
        elif name == "N" and not structured_name:
            parts = [part for part in value.split(";") if part]
            structured_name = " ".join(reversed(parts[:2])).strip() or None
        elif name == "EMAIL" and value:
            emails.append(value)
        elif name == "TEL" and value:
            phones.append(value)

    return ContactSummary(
        href=href,
        etag=etag,
        uid=uid,
        formatted_name=formatted_name or structured_name or "Unnamed contact",
        emails=emails,
        phones=phones,
    )


def build_vcard(
    *,
    uid: str,
    formatted_name: str,
    emails: list[str],
    phones: list[str],
) -> str:
    lines = [
        "BEGIN:VCARD",
        "VERSION:4.0",
        f"UID:{_escape(uid)}",
        f"FN:{_escape(formatted_name.strip())}",
    ]

    lines.extend(f"EMAIL:{_escape(value.strip())}" for value in emails if value.strip())
    lines.extend(f"TEL:{_escape(value.strip())}" for value in phones if value.strip())
    lines.append("END:VCARD")

    return "\r\n".join(lines) + "\r\n"
