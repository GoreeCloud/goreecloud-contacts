# GoreeCloud Contacts — GLAZE UI V1.1 Source Migration

## Status

Development source migration candidate. This document does not claim rendered acceptance, accessibility acceptance, representative-device acceptance, platform-system acceptance, production approval, or Stable qualification.

## Design-system authority

- Product: GLAZE UI V1.1
- Machine version currently pinned by this development branch: `1.1.0`
- Authoritative repository: `GoreeCloud/goreecloud-glaze-ui`
- Historical Stable source revision used for this migration: `15cc76d2bcd4065552dc31c77145b63f34d9e7b2`
- Authoritative contract: `GLAZE_UI_V1_1.md`
- Historical Stable web entrypoint: `css/glaze-v1.1.0.css`

This branch originally migrated against immutable Stable `1.1.0`. That release now has a known import-closure defect in its published web source graph. Corrective `1.1.1` is still an unmerged Release Candidate and is not yet a Stable authority that Contacts may silently adopt. The existing `1.1.0` source work therefore remains development evidence only. Contacts must re-pin to a corrected immutable Stable release and repeat applicable exact-revision validation before GLAZE acceptance can advance.

Upstream Stable promotion alone never makes Contacts conformant; downstream application-specific exact-revision evidence is still required.

## Migration approach

Contacts retains the earlier 1.4 form-factor and refinement files as historical structural implementation evidence while loading `frontend/src/glaze-v1.1.css` last as the current migration layer. The V1.1 layer is therefore authoritative when old compatibility tokens or material rules conflict, subject to the corrected-Stable re-pin requirement above.

The migration layer:

- activates `data-glaze-version="1.1"` at the document root;
- declares the Standard optical density profile;
- adopts the V1 structural canvas, text, line, focus, and protected semantic roles;
- adopts the V1.1 Deep Teal + Soft Amber atmospheric identity from the currently pinned historical source revision;
- adopts the 8 / 16 / 24 / 32 px optical geometry references plus capsule geometry;
- enforces the V1.1 48 px interaction-target floor and 56 px Touch Assistance target;
- maps existing Contacts compatibility tokens onto the V1/V1.1 roles so feature-specific Contacts styles remain coherent during migration;
- keeps semantic success, warning, and critical state colors separate from atmospheric expression;
- keeps reading and explicit-decision surfaces solid while allowing restrained Glaze treatment for navigation, search, and transient control chrome;
- includes explicit Light, Dark, and Deep Dark mappings plus system dark-mode fallback;
- ensures system dark-mode fallback applies only when no explicit appearance is selected so explicit Deep Dark is not overridden by OS preference;
- preserves Reduced Transparency, Increased Contrast, Forced Colors, Reduced Motion, keyboard focus, safe-area reachability, and responsive form-factor behavior; and
- introduces no remote stylesheet, font, image, script, or presentation dependency.

## CI enforcement

`frontend/scripts/validate-glaze-ui.mjs` validates the exact currently pinned V1.1 authority revision, document activation, optical tokens, semantic separation, material rule, appearance mappings and explicit-appearance precedence, interaction-target floors, accessibility fallbacks, import ordering, application identity, and absence of remote presentation dependencies.

`frontend/scripts/validate-form-factors.mjs` keeps the existing Mobile, Narrow Tablet, Roomier Tablet, Desktop, and Wide Desktop composition checks while treating the older form-factor files as structural history resolved by the V1.1 layer. It no longer treats the older 46 px action rule as the effective current target; V1.1 resolves current interactive controls to a 48 px minimum.

## Remaining acceptance gates

Before GoreeCloud Contacts can claim GLAZE UI V1.1 conformance, current exact-revision evidence must still cover, as applicable:

- corrected immutable Stable GLAZE release and explicit Contacts re-pin;
- fresh source/CI validation on the corrected Stable pin;
- rendered visual/optical acceptance;
- keyboard and accessibility acceptance;
- Increased Contrast and Forced Colors behavior;
- Reduced Motion and Reduced Transparency behavior;
- 200% text/responsive reflow behavior;
- supported Mobile, Tablet, Desktop, and Wide Desktop form factors;
- representative-device/browser interaction acceptance;
- application-specific production boundary and release approval; and
- any additional evidence required by the current GoreeCloud Platform Contract and Glaze UI consumer-governance records.

Until those gates are complete, `goreecloud.platform.yaml` keeps Glaze UI at `applicable-migration-required` and overall platform conformance remains `nonconformant`.
