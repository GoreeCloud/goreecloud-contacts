# GoreeCloud Contacts — Feature Roadmap

**Status:** Active roadmap control  
**As of:** September 10, 2026  
**Authoritative project record:** `Project Specification — Contacts`  
**Canonical repository:** `GoreeCloud/goreecloud-contacts`  
**Drive control:** `GoreeCloud/Feature Roadmap/GoreeCloud Contacts/FEATURE-ROADMAP.docx`

## Purpose

This file is the repository-side feature roadmap control for GoreeCloud Contacts. It records current planned and recommended feature work without replacing the authoritative project record, Radicale/CardDAV authority, repository implementation evidence, release gates, or GoreeCloud Tasks Management.

This roadmap and the Drive-side `FEATURE-ROADMAP.docx` must remain materially synchronized. No feature is complete, production-approved, or Stable solely because it appears here; lifecycle claims require applicable exact-revision implementation, validation, review, target-environment, recovery, release, and production evidence.

Current Development checkpoint: Contacts remains a web Development application at source version `0.5.0` with Radicale/CardDAV as the sole authoritative contact store. Draft PR #34 (`feature/contacts-glaze-v1.3-foundation`) exact source head `17369a83a586b71783c43b809550800f369ffbe8` passed Platform Contract `34542118740` / #60 and Continuous Integration `34542118164` / #192. That head stages a bounded GLAZE UI V1.3 / `1.3.0` foundation at exact Stable integration anchor `fc7cc91d2eace8da2371371c2855c24cbcb326a1` without activating it; the live browser root/source mapping remains V1.1 / `1.1.0`, GLAZE remains `applicable-migration-required`, and overall conformance remains `nonconformant`.

## Status vocabulary

- **Validated development foundation** — exact-revision Development source/runtime CI exists, but downstream production/Stable acceptance is not implied.
- **Active Development** — implementation is present or being advanced on the current stack, with additional review or acceptance still open.
- **Planned** — required product work is not established as current implementation.
- **Blocked on prerequisite** — a required authority, safety, recovery, or platform prerequisite must exist before the capability may advance to production acceptance.
- **Ongoing control** — governance or safety obligation that continuously applies.

## Roadmap

| ID | Feature / obligation | Priority | Current state |
| --- | --- | --- | --- |
| FR-001 | Reconcile and maintain every current planned or recommended GoreeCloud Contacts feature against the authoritative Project Specification, current repository/runtime evidence, Radicale/DAV records, and applicable GoreeCloud requirements. | High | Ongoing control |
| FR-002 | Move actionable feature obligations into GoreeCloud Tasks Management when required, preserving priority, dependency, owner, lifecycle, and evidence disposition. | High | Ongoing control |
| FR-003 | Do not mark features implemented, complete, cancelled, production-approved, or superseded without authoritative evidence and synchronized repository/Drive roadmap updates. | High | Ongoing control |
| FR-010 | Preserve Radicale/CardDAV as the sole authoritative contact store and maintain standards-based CardDAV/vCard interoperability without introducing a competing application-only contact database. | High | Validated development foundation; ongoing architecture invariant |
| FR-011 | Maintain per-user Radicale-backed authentication, address-book isolation, protected same-origin CardDAV targeting, opaque/shared session behavior, and fail-closed authorization across all protected contact operations. | High | Active Development foundation; target-environment Identity/session/worker/recovery acceptance remains open |
| FR-012 | Preserve ETag/precondition-protected conditional contact writes, explicit write-safety gating, conflict surfacing, and user-reviewed mutation semantics rather than silently forcing stale writes. | High | Validated development foundation; production write acceptance remains gated |
| FR-013 | Continue first-party contact-model capabilities including structured names, organizations/titles, multiple email/phone/address values, birthdays, websites, notes, categories/favorites, photo references, contact groups, public profiles, search, and detail/edit workflows while preserving vCard portability. | High | Active Development foundations exist; broader product/device acceptance remains open |
| FR-014 | Keep duplicate detection and merge user-reviewed, conflict-safe, ETag-aware, and preservation-oriented; do not authorize unattended production-family merges from planning examples. | High | Active Development source exists in consolidated stack; isolated live acceptance and production-family use remain unapproved |
| FR-015 | Preserve raw single-contact and full-address-book VCF export plus bounded vCard 3.0/4.0 preview/import so standards-based portability and source properties are retained without application lock-in. | High | Validated Development foundation; production portability/recovery acceptance remains open |
| FR-016 | Complete deliberate GLAZE UI V1.3 / `1.3.0` migration from the live V1.1 root, then earn whole-application rendered, interaction, accessibility, responsive/form-factor, representative-device/browser, performance, resilience, rollback, and Human Visual Excellence acceptance. | High | Active Development — PR #34 stages V1.3 without activating it; live root remains V1.1 and `applicable-migration-required` |
| FR-017 | Preserve purpose-built Mobile, Tablet, Desktop, and Wide Desktop compositions, visible keyboard focus, touch/reachability behavior, Reduced Motion/Transparency, Increased Contrast, forced-colors resilience, and task-appropriate density through the V1.3 migration. | High | Existing form-factor/accessibility source foundations; current V1.3 acceptance must be re-earned |
| FR-018 | Maintain canonical Contacts application identity and generate browser, future Android, Linux/Debian, launcher, package, release, repository, and documentation derivatives from one approved master rather than independent artwork. | Medium | Canonical web/source identity foundation exists; native package derivatives remain future work |
| FR-019 | Maintain privacy-minimized browser/security controls, abuse throttling, security headers, bounded errors/logging, credential separation, and multi-worker shared state without treating source hardening as accepted Privacy Shield or Wardveil authority. | High | Active Development source/production-shaped CI exists; platform-system and target-environment acceptance remain blocked |
| FR-020 | Integrate and independently validate GoreeCloud Manager, Privacy Shield, Wardveil Security, Everkeep, GoreeCloud Mesh, and GoreeCloud Identity while preserving Radicale/CardDAV authority and least privilege. | High | Blocked/acceptance incomplete for all listed platform systems |
| FR-021 | Protect authoritative Radicale contact collections plus required Contacts configuration/session state through governed backup, clean-target restore, key/secret recovery, rollback, and Everkeep acceptance; keep VCF/CardDAV portability available independently of the UI. | High | Blocked on recovery/continuity acceptance |
| FR-022 | Validate production publication architecture for `contacts.goreecloud.com`, including private DNS/Caddy/NetBird/firewall boundaries, TLS/cookies/CSRF, multi-worker behavior, monitoring/alerts, request/log limits, secret/key rotation, DAVx5 coexistence, and controlled production-family onboarding. | High | Planned production gate; application hostname is not production published/approved |
| FR-023 | Build a native GoreeCloud Android Contacts APK only through a dedicated architecture, permission, CardDAV, identity, Glaze, signing/update, accessibility, and release milestone while retaining the same authoritative contact model. | Medium | Planned future package; no current Android implementation or distribution claim |
| FR-024 | Build a Debian-native Linux Contacts package only through a dedicated desktop architecture, CardDAV, Glaze, packaging/signing/update/rollback, desktop-integration, accessibility, and release milestone. | Medium | Planned future package; no current Debian-native implementation or distribution claim |
| FR-025 | Complete representative browser/mobile acceptance, dependency and production-image validation, backup/restore/rollback evidence, controlled signing/provenance, Release Candidate qualification, production approval, and Stable qualification against the exact release revision before production-family contact use. | High | Planned release gate; current CI is Development evidence only |

## Sequencing and authority rules

1. Preserve Radicale/CardDAV, per-user isolation, ETag conflict protection, raw portability, and write-safety boundaries while user-facing capabilities advance.
2. Finish the deliberate V1.3 root/source migration before claiming current GLAZE UI conformance; staged V1.3 source is not application acceptance.
3. Keep duplicate merge, public-profile, group, VCF, and other contact mutations user-authorized and conflict-safe; production-family data remains out of Development testing until separately approved.
4. Complete Privacy Shield, Wardveil Security, Everkeep, Identity, Mesh, and Manager integration independently; source-local safeguards or CI do not manufacture those authorities.
5. Validate target-environment session persistence, secrets/key lifecycle, private publication, monitoring, backup/restore, rollback, DAVx5 coexistence, and representative browser behavior before production approval.
6. Treat Android APK and Debian-native packaging as separate future native-client milestones with independent platform acceptance and canonical identity derivatives.
7. Bind Release Candidate, production, and Stable claims to the exact accepted revision, controlled signing/provenance, recovery evidence, representative interaction/accessibility evidence, and explicit production approval.

## Reconciliation rule

At each material feature change, reconcile this roadmap against the authoritative Project Specification, current repository and runtime state, Contacts/Radicale/DAV records, applicable platform-system requirements, the Drive-side roadmap, and GoreeCloud Tasks Management. Missing obligations, stale status, duplicated work, roadmap drift, or undocumented disposition changes are defects to correct.
