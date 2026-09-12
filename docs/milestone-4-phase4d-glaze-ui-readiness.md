# Milestone 4 Phase 4D — Glaze UI and Responsive Readiness

## Purpose

This increment aligns the GoreeCloud Contacts browser interface with the GoreeCloud Glaze UI design language while preserving the existing CardDAV, authentication, privacy, and conditional-write boundaries.

It is deliberately a presentation and interface-resilience layer. It does not change Radicale authority, CardDAV resource semantics, ETag conflict handling, session storage, CSRF enforcement, VCF portability, or duplicate-merge mutation ordering.

## Glaze UI foundation

The frontend loads `src/glaze.css` after the existing application styles. The file provides a shared token layer for:

- light and dark appearance through operating-system preference;
- layered and selectively translucent surfaces;
- rounded controls and containers;
- restrained shadows and depth;
- purposeful ambient gradients;
- semantic accent, success, warning, and danger colors;
- visible keyboard focus;
- touch-target improvements;
- reduced-motion behavior;
- reduced-transparency fallback behavior;
- responsive small-screen layout.

The compatibility tokens `--surface`, `--border`, and `--muted` map existing VCF and duplicate-management components into the same Glaze foundation rather than allowing those feature areas to develop a separate visual system.

## Mobile navigation correction

Before this increment, the existing `max-width: 820px` rule set changed the workspace to one column and set `.sidebar { display: none; }`.

Because the sidebar contains more than decorative desktop navigation, hiding it also removed these controls from small-screen users:

- Create contact;
- Contacts/Favorites filtering;
- address-book selection;
- the read-only/write-enabled safety-state indicator.

The Glaze layer overrides that behavior. On small screens, the sidebar becomes a normal compact section above the main contact content. Core functions therefore remain available without adding a second mobile-only state model or duplicating authorization logic.

## Accessibility and interaction controls

The Glaze layer provides explicit `:focus-visible` treatment for buttons, links, inputs, textareas, and selects. A keyboard `Skip to contacts` link allows users to bypass repeated top-level interface controls and reach the existing contacts content region directly.

On coarse-pointer devices, interactive controls receive a minimum touch-oriented height. Reduced-motion preference removes nonessential transitions and animations. Reduced-transparency preference replaces translucent application surfaces with solid surfaces and disables backdrop filtering.

The dedicated `glaze-accessibility.css` layer additionally supports:

- increased-contrast preference with stronger focus treatment;
- forced-colors/high-contrast environments using system colors rather than relying on translucent or decorative surfaces;
- removal of nonessential glass effects and shadows when forced colors are active;
- explicit system-color treatment for the backend status indicator and primary interactive surfaces.

These controls preserve the Glaze identity while giving readability and assistive-technology compatibility priority over decorative treatment.

The existing semantic form labels, alert roles, `aria-live` backend status, and disabled mutation controls remain unchanged.

## Browser privacy metadata

The application document now declares:

- `Referrer-Policy` equivalent browser metadata through `meta name="referrer" content="no-referrer"` so ordinary browser navigation does not disclose the Contacts page URL as a referrer;
- `robots` directives requesting `noindex`, `nofollow`, `noarchive`, `nosnippet`, and `noimageindex` for the private application interface.

These are privacy-by-default defense-in-depth controls. Crawler directives are not access controls and do not replace private DNS, NetBird authorization, Caddy publication rules, authentication, or firewall policy.

## Privacy and dependency boundary

The Glaze UI layer is completely self-hosted. It introduces no analytics, advertising, external fonts, remote CSS, remote images, or third-party browser scripts.

External contact-photo behavior remains governed by the existing application logic. This presentation change does not cause remote photo references to be fetched automatically.

## Automated guard

`frontend/scripts/validate-glaze-ui.mjs` is a dependency-free source validator executed by CI through `npm run validate:ui`.

It verifies that:

- the Glaze foundation and accessibility layer remain loaded;
- keyboard skip navigation remains present and focus-visible;
- shared Glaze surface/accent tokens remain defined;
- feature-specific compatibility tokens remain connected to Glaze;
- keyboard focus-visible styling remains present;
- reduced-motion handling remains present;
- reduced-transparency fallback remains present;
- increased-contrast handling remains present;
- forced-colors handling remains present;
- the small-screen sidebar remains available rather than being hidden;
- light/dark document color-scheme support remains declared;
- no-referrer browser metadata remains declared;
- private no-index/no-archive crawler directives remain declared;
- the Glaze stylesheets do not introduce remote CSS/font/image dependencies.

This validator does not replace browser acceptance testing. It prevents accidental removal of agreed source-level design, accessibility, and browser-privacy requirements during later refactoring.

## Related source hardening

During this Phase 4D review, the production input-bound work was also reconciled so the primary CardDAV and VCF-export query parameters use the same shared href/ETag limits as the duplicate workflow. That change is documented separately in `production-readiness-input-bounds.md` because it is a security/readiness correction rather than a presentation feature.

## Production-readiness boundary

This increment improves source-level product readiness but does not approve production deployment.

The following remain separate acceptance gates:

- isolated Phase 4C live duplicate/merge acceptance and cleanup;
- target-runtime session persistence and worker validation;
- production secret injection and rotation evidence;
- backup and restore testing;
- private DNS/Caddy/NetBird/firewall publication validation;
- production logging/redaction and server-level request controls;
- actual monitoring and alert delivery;
- upgrade and rollback rehearsal;
- production-representative browser acceptance, including small-screen and high-contrast visual validation;
- DAVx5 coexistence and conflict testing;
- portability acceptance;
- controlled production-family onboarding.

## Acceptance criteria

This increment is source-complete only when the exact branch head passes all existing backend and frontend checks plus the Glaze UI validation step. Browser visual acceptance remains required before stable production approval.
