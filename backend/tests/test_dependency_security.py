from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1] / "app"


def test_cryptography_pkcs7_decrypt_surface_is_not_used() -> None:
    prohibited = (
        "cryptography.hazmat.primitives.serialization.pkcs7",
        "pkcs7_decrypt_der",
        "pkcs7_decrypt_pem",
        "pkcs7_decrypt_smime",
    )

    findings: list[str] = []
    for path in APP_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for marker in prohibited:
            if marker in source:
                findings.append(f"{path.relative_to(APP_ROOT)}: {marker}")

    assert findings == [], (
        "PYSEC-2026-3552 is temporarily ignored only because GoreeCloud Contacts does "
        "not use cryptography's affected PKCS#7 EnvelopedData decryption APIs. Remove "
        "the audit exception before introducing any prohibited API. Findings: "
        + ", ".join(findings)
    )
