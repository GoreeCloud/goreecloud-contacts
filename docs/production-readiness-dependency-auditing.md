# Production Readiness — Dependency Vulnerability Auditing

## Status

This increment adds known-vulnerability checks to GoreeCloud Contacts continuous integration so a pull request cannot be considered green solely because application tests, linting, and builds pass.

The audits are detection gates. They do not automatically modify dependencies, suppress advisories, or approve production deployment.

## Python dependency audit

CI installs `pip-audit==2.10.1` as a pinned audit tool and runs it against the backend project definition.

The audit evaluates the dependency resolution declared by `backend/pyproject.toml` for publicly known Python package vulnerabilities. A reported vulnerability produces a non-zero exit status and fails the backend CI job.

The audit is intentionally separate from the GoreeCloud Contacts runtime dependency list. `pip-audit` is a CI/security tool, not an application runtime requirement.

No vulnerability IDs are ignored by default. If a future advisory cannot immediately be remediated, any proposed exception must be reviewed and documented separately with the affected package, advisory identifier, exposure analysis, compensating controls, remediation plan, and removal condition. The CI workflow must not silently suppress findings.

## Frontend dependency audit

The frontend already uses a committed `package-lock.json` and reproducible `npm ci` installation.

CI now runs `npm audit` immediately after installation. The command audits the resolved lockfile dependency tree and returns a failing exit status when known vulnerabilities are reported.

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
2. Confirm whether a fixed version is available.
3. Prefer upgrading to a supported fixed dependency without weakening GoreeCloud requirements.
4. Re-run backend tests, frontend lint/build, and the dependency audits on the exact resulting commit.
5. Record any unavoidable exception explicitly rather than adding an undocumented ignore rule.

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

- backend dependency audit passes;
- backend live-helper syntax validation passes;
- backend tests pass;
- frontend dependency audit passes;
- frontend lint passes;
- frontend production build passes.

Production deployment remains unapproved until the other applicable production-readiness gates have separate evidence.
