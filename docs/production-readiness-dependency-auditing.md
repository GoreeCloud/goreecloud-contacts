# Production Readiness — Dependency Vulnerability Auditing

## Status

This increment adds known-vulnerability checks to GoreeCloud Contacts continuous integration so a pull request cannot be considered green solely because application tests, linting, and builds pass.

The audits are detection gates. They do not automatically modify dependencies or approve production deployment.

## Python dependency audit

CI installs `pip-audit==2.10.1` as a pinned audit tool and runs it against the backend project definition.

The audit evaluates the dependency resolution declared by `backend/pyproject.toml` for publicly known Python package vulnerabilities. A reported vulnerability normally produces a non-zero exit status and fails the backend CI job.

The audit is intentionally separate from the GoreeCloud Contacts runtime dependency list. `pip-audit` is a CI/security tool, not an application runtime requirement.

## Current reviewed exception — PYSEC-2026-3552

The first production-readiness audit identified `PYSEC-2026-3552` in `cryptography==49.0.0`.

The advisory affects the PKCS#7 EnvelopedData decryption APIs:

- `pkcs7_decrypt_der`;
- `pkcs7_decrypt_pem`;
- `pkcs7_decrypt_smime`.

The issue can expose a Bleichenbacher oracle when an application repeatedly decrypts attacker-controlled PKCS#7 EnvelopedData and reflects distinguishable failure behavior. The advisory records the affected range as cryptography 44.0.0 through 49.0.0 and identifies 50.0.0 as the fixed version.

At the time this exception was recorded, cryptography 49.0.0 remains the latest stable PyPI release and 50.0.0 is not yet available as a stable release. GoreeCloud Contacts does not use PKCS#7 EnvelopedData decryption. Its session encryption imports and uses Fernet/MultiFernet only.

CI therefore contains one explicit temporary exception:

`--ignore-vuln PYSEC-2026-3552`

This exception is accepted only with the following compensating controls:

1. `backend/tests/test_dependency_security.py` scans the application source and fails if the affected PKCS#7 module or decryption API names are introduced.
2. No application feature may add the affected PKCS#7 decryption surface while this exception exists.
3. The exception must be removed and cryptography upgraded once an appropriate fixed stable release is available and passes the full GoreeCloud Contacts validation suite.
4. Any change to the application cryptography usage requires reevaluation of this exception before merge.
5. No additional vulnerability ID may be added to the ignore list without its own documented exposure analysis and removal condition.

This is a scope-specific risk decision, not a claim that cryptography 49.0.0 is generally free of the advisory.

## Frontend dependency audit

The frontend already uses a committed `package-lock.json` and reproducible `npm ci` installation.

CI runs `npm audit` immediately after installation. The command audits the resolved lockfile dependency tree and returns a failing exit status when known vulnerabilities are reported.

No automatic `npm audit fix` action is used in CI. Dependency changes remain deliberate source changes that can be reviewed and validated through the normal pull-request workflow.

## Why auditing is separate from functional tests

A package can remain API-compatible and allow every GoreeCloud Contacts test to pass while still containing a publicly known vulnerability. Functional validation and dependency-security validation therefore answer different questions:

- tests/lint/build verify intended application behavior and source quality;
- dependency audits verify the current dependency resolution against known vulnerability information.

Both must pass for the source branch to be considered green.

## Network and availability boundary

Both auditing tools depend on current advisory information from external package ecosystems. An audit can therefore fail because:

- a real vulnerability has been newly published;
- the dependency tree cannot be resolved;
- the package/advisory service is unavailable;
- network access required by the audit is unavailable.

For production-readiness CI, failing closed is intentional. A branch should not claim a current clean dependency audit when the audit could not actually complete.

This does not mean every temporary advisory-service outage is an application defect. The failure must be inspected and distinguished from a real vulnerability before retrying or changing the workflow.

## Remediation expectations

When a dependency audit reports a vulnerability:

1. Identify the affected direct or transitive package and advisory.
2. Confirm whether a fixed stable version is actually available.
3. Determine whether the vulnerable functionality is reachable in GoreeCloud Contacts.
4. Prefer upgrading to a supported fixed dependency without weakening GoreeCloud requirements.
5. If no fixed stable release exists and the vulnerable surface is demonstrably unreachable, document a narrow exception with an automated scope guard and explicit removal condition.
6. Re-run backend tests, frontend lint/build, and the dependency audits on the exact resulting commit.

The audit tools must not be used as automatic update mechanisms in CI.

## Scope boundary

These checks cover known vulnerabilities in Python and npm package dependency metadata. They do not replace:

- source-code security review;
- application authentication/authorization testing;
- container image or operating-system package scanning once a deployment image/runtime exists;
- secret scanning;
- target-host patching and security updates;
- reverse-proxy, TLS, network, firewall, and private-publication validation;
- dependency-license review where separately required;
- runtime monitoring or incident response.

The final production image/runtime is not yet approved, so container and operating-system vulnerability scanning remain later deployment-specific gates.

## Acceptance gate

This increment is accepted only after exact-head GitHub Actions proves all of the following on the same commit:

- backend dependency audit passes with only the explicitly documented `PYSEC-2026-3552` exception;
- the PKCS#7 scope-guard test passes;
- backend live-helper syntax validation passes;
- backend tests pass;
- frontend dependency audit passes;
- frontend lint passes;
- frontend production build passes.

Production deployment remains unapproved until the other applicable production-readiness gates have separate evidence.
