import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "platform-systems.json"
MANDATORY_SYSTEMS = {"glaze_ui", "wardveil_security", "privacy_shield", "everkeep"}
ACCEPTED_STATES = {"implemented-source-runtime-ci", "accepted"}


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_declares_native_contacts_and_all_mandatory_systems() -> None:
    data = load_manifest()
    assert data["application"] == "GoreeCloud Contacts"
    assert data["native_application"] is True
    assert set(data["systems"]) == MANDATORY_SYSTEMS
    assert all(data["systems"][name]["required"] is True for name in MANDATORY_SYSTEMS)


def test_manifest_evidence_paths_exist() -> None:
    data = load_manifest()
    for system in data["systems"].values():
        assert system["evidence"], "every mandatory system must name source-controlled evidence"
        for relative_path in system["evidence"]:
            assert (ROOT / relative_path).exists(), f"missing evidence path: {relative_path}"


def test_stable_gate_fails_closed_until_every_system_is_accepted() -> None:
    data = load_manifest()
    all_accepted = all(
        system["state"] in ACCEPTED_STATES for system in data["systems"].values()
    )
    assert data["stable_allowed"] is all_accepted
    assert data["stable_allowed"] is False
