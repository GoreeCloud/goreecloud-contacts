from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from .models import ContactDetail
from .vcard import parse_vcard


@dataclass(frozen=True, slots=True)
class VCardInspection:
    raw: str
    version: str
    contact: ContactDetail
    warnings: list[str]


def _unfold(raw: str) -> list[str]:
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    unfolded: list[str] = []
    for line in normalized.split("\n"):
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def _property_name_value(line: str) -> tuple[str, str] | None:
    if ":" not in line:
        return None
    left, value = line.split(":", 1)
    name = left.split(";", 1)[0].rsplit(".", 1)[-1].upper()
    return name, value.strip()


def split_vcards(raw: str) -> list[str]:
    normalized = raw.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    records: list[str] = []
    current: list[str] | None = None

    for line_number, line in enumerate(normalized.split("\n"), start=1):
        marker = line.strip().upper()
        if current is None:
            if not marker:
                continue
            if marker != "BEGIN:VCARD":
                raise ValueError(
                    f"Unexpected content outside a vCard at line {line_number}. "
                    "VCF files must contain BEGIN:VCARD ... END:VCARD records."
                )
            current = ["BEGIN:VCARD"]
            continue

        if marker == "BEGIN:VCARD":
            raise ValueError(
                f"Nested BEGIN:VCARD found at line {line_number}; the VCF file is malformed."
            )

        current.append(line)
        if marker == "END:VCARD":
            records.append("\r\n".join(current) + "\r\n")
            current = None

    if current is not None:
        raise ValueError("A vCard record is missing its END:VCARD marker.")
    if not records:
        raise ValueError("No vCard records were found in the supplied VCF content.")
    return records


def inspect_vcard(raw: str, *, index: int = 0) -> VCardInspection:
    versions: list[str] = []
    for line in _unfold(raw):
        item = _property_name_value(line)
        if item is not None and item[0] == "VERSION":
            versions.append(item[1])

    if len(versions) != 1:
        raise ValueError("Each imported vCard must contain exactly one VERSION property.")

    version = versions[0]
    if version not in {"3.0", "4.0"}:
        raise ValueError(
            f"Unsupported vCard version {version!r}. Phase 4B accepts vCard 3.0 and 4.0."
        )

    contact = parse_vcard(raw, href=f"import-preview://{index}", etag=None)
    if contact.formatted_name == "Unnamed contact":
        raise ValueError("Imported vCards must contain FN or enough N data to derive a name.")

    warnings: list[str] = []
    if not contact.uid:
        warnings.append("No UID was supplied; GoreeCloud will generate one during import.")
    if contact.photo and contact.photo.casefold().startswith("data:image/"):
        warnings.append(
            "Embedded photo data may not round-trip losslessly through the current "
            "Radicale/vobject storage path."
        )

    return VCardInspection(raw=raw, version=version, contact=contact, warnings=warnings)


def ensure_vcard_uid(raw: str, uid: str | None = None) -> tuple[str, str]:
    inspection = inspect_vcard(raw)
    if inspection.contact.uid:
        return normalize_vcard_record(raw), inspection.contact.uid

    generated_uid = uid or str(uuid4())
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    output: list[str] = []
    inserted = False
    for line in normalized.split("\n"):
        if line.strip().upper() == "END:VCARD" and not inserted:
            output.append(f"UID:{generated_uid}")
            inserted = True
        output.append(line)

    if not inserted:
        raise ValueError("Cannot add a UID because END:VCARD is missing.")
    return "\r\n".join(output).rstrip("\r\n") + "\r\n", generated_uid


def normalize_vcard_record(raw: str) -> str:
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    return normalized.replace("\n", "\r\n") + "\r\n"
