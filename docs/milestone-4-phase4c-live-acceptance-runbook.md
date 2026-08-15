# Milestone 4 Phase 4C — Isolated Live Acceptance Runbook

## Purpose

This runbook defines the controlled live acceptance sequence for GoreeCloud Contacts duplicate detection and user-reviewed merge.

It does not authorize production contact testing or production deployment. Radicale/CardDAV remains authoritative, production-family contacts remain outside the Phase 4C test scope, and the live helper is limited to the isolated `goreecloud-contacts-test` identity, the `GoreeCloud Contacts Test` address book, the retained Jordan Example fixture, and two fixed disposable Phase 4C fixture UIDs.

The acceptance helper is:

`backend/scripts/validate_milestone4_phase4c_live.py`

Run commands from the `backend` directory with the project virtual environment active. The helper prompts for the isolated CardDAV test password with `getpass`; do not place the password in shell history, environment examples, documentation, GitHub, or command-line arguments.

## Preconditions

Before beginning:

- use only the isolated `goreecloud-contacts-test` identity;
- confirm the backend is a development/test environment, not production;
- confirm `GoreeCloud Contacts Test` is the intended address book;
- confirm Jordan Example is the only retained contact before seeding;
- keep reusable credentials out of source control and ordinary logs;
- do not point the helper at a production service;
- do not use production-family contact data.

The helper defaults to `http://127.0.0.1:8000` and refuses non-loopback targets unless `--allow-non-loopback` is supplied explicitly. Even with that override, a backend that reports `prod` or `production` as its environment is refused.

## Normal acceptance sequence

### 1. Baseline — read-only

Required state:

- `CARDDAV_WRITE_ENABLED=false`
- normal protected test configuration loaded

Run:

```bash
python scripts/validate_milestone4_phase4c_live.py --stage baseline
```

The stage verifies:

- backend health;
- non-production environment;
- CardDAV configuration;
- write gate disabled;
- isolated Radicale-backed login;
- expected test address book discovery;
- Jordan Example is the only retained contact;
- duplicate scan is clean;
- the merge endpoint remains blocked while writes are disabled.

### 2. Seed — controlled synthetic write

Temporarily set `CARDDAV_WRITE_ENABLED=true` in the protected local test configuration and restart the backend so the change is active.

Run:

```bash
python scripts/validate_milestone4_phase4c_live.py --stage seed
```

The stage previews and imports exactly two known disposable vCard fixtures. After success, the isolated address book should contain Jordan Example plus the two Phase 4C test contacts.

Immediately restore `CARDDAV_WRITE_ENABLED=false`, restart the backend, and continue to review.

### 3. Review — read-only

Required state:

- `CARDDAV_WRITE_ENABLED=false`

Run:

```bash
python scripts/validate_milestone4_phase4c_live.py --stage review
```

The stage verifies:

- the seeded pair is detected as a high-confidence candidate;
- email, phone, and name signals are present;
- complementary fields are unioned in preview;
- organization and title conflicts are surfaced for user review;
- the selected primary contact remains the proposed survivor;
- a valid reviewed merge still returns the write-gate rejection while writes are disabled.

After review succeeds, enable `CARDDAV_WRITE_ENABLED=true` only for the controlled write stage and restart the backend.

### 4. Write — stale review, reviewed merge, portability, cleanup

Required state:

- `CARDDAV_WRITE_ENABLED=true`
- only Jordan Example and the two fixed Phase 4C fixture UIDs are expected in the isolated address book

Run:

```bash
python scripts/validate_milestone4_phase4c_live.py --stage write
```

The stage verifies:

- stale duplicate ETag rejection occurs before the survivor changes;
- the disposable duplicate fixture can be restored after the stale-ETag test;
- a fresh reviewed merge retains the selected primary UID;
- the explicit scalar conflict choice is applied;
- complementary emails remain in the merged survivor;
- the superseded duplicate resource is no longer readable after a successful merge;
- raw export retains the tested `X-GOREECLOUD-PHASE4C` passthrough properties from both source vCards;
- the merged disposable survivor is removed;
- Jordan Example is again the only retained contact.

After success, restore:

- `CARDDAV_WRITE_ENABLED=false`
- `SESSION_TTL_SECONDS=28800`

Restart the backend and run the final stage.

### 5. Final — restored safety state

Required state:

- `CARDDAV_WRITE_ENABLED=false`
- `SESSION_TTL_SECONDS=28800`

Run:

```bash
python scripts/validate_milestone4_phase4c_live.py --stage final
```

The stage verifies:

- write gate disabled;
- isolated login still works;
- the newly issued session expires approximately 28,800 seconds after authentication;
- Jordan Example is the only retained contact;
- duplicate scan is clean.

A successful final stage is API-level evidence that the helper-visible safety state was restored. Production-representative browser acceptance remains a separate requirement.

## Recovery after an interrupted write stage

If `seed` or `write` stops after disposable fixtures may have been created, do not manually delete arbitrary contacts and do not continue with a partially understood address-book state.

Keep `CARDDAV_WRITE_ENABLED=true` only long enough to run the fixture-scoped cleanup stage:

```bash
python scripts/validate_milestone4_phase4c_live.py --stage cleanup
```

Cleanup is intentionally narrow:

- Jordan Example must still be present and unchanged;
- every contact in the address book must have either the Jordan UID or one of the two fixed Phase 4C fixture UIDs;
- any unexpected contact causes cleanup to fail before mutation;
- only the two known Phase 4C fixture UIDs may be deleted;
- each deletion requires the current returned ETag;
- cleanup must end with Jordan Example as the only retained contact.

After cleanup, restore `CARDDAV_WRITE_ENABLED=false` and `SESSION_TTL_SECONDS=28800`, restart the backend, and run `--stage final`.

## Approved non-loopback isolated test backend

The helper should normally run against loopback. If a separately approved isolated test backend is intentionally used, the target must be explicit:

```bash
python scripts/validate_milestone4_phase4c_live.py \
  --api-base-url https://approved-isolated-test.example.test \
  --allow-non-loopback \
  --stage baseline
```

The override does not bypass production-environment refusal, test-identity restrictions, address-book checks, write-gate checks, or fixture cleanup restrictions.

Do not embed a username, password, token, query string, fragment, or API subpath in `--api-base-url`.

## Evidence to record

Phase 4C should not be marked complete merely because the helper exists or automated tests pass. Record the actual acceptance evidence after execution, including:

- branch/commit tested;
- date and time of the live test;
- isolated test identity and address-book name, without reusable credentials;
- baseline stage result;
- seed stage result;
- review stage result;
- stale-ETag rejection result;
- reviewed merge result and retained survivor UID;
- raw passthrough export result;
- cleanup result;
- final write-gate state;
- final 28,800-second session TTL evidence;
- final one-contact Jordan Example baseline;
- final clean duplicate scan;
- browser confirmation that the application is again in read-only safety mode;
- exact-head CI result.

## Completion boundary

Phase 4C remains incomplete until automated validation, exact-head CI, isolated live acceptance, cleanup, restored safety state, browser acceptance, documentation reconciliation, and final review are all complete.

This runbook does not approve production-family contact use, private-service publication, production deployment, backup/recovery acceptance, DAVx5 coexistence, or any other separate production-readiness gate.
