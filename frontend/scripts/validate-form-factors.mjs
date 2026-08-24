import { readFile } from 'node:fs/promises'

const [
  mainSource,
  accessibilitySource,
  formFactorSource,
  refinementSource,
  vcfSource,
  duplicateSource,
] = await Promise.all([
  readFile(new URL('../src/main.tsx', import.meta.url), 'utf8'),
  readFile(new URL('../src/glaze-accessibility.css', import.meta.url), 'utf8'),
  readFile(new URL('../src/glaze-form-factors.css', import.meta.url), 'utf8'),
  readFile(new URL('../src/glaze-form-factor-refinements.css', import.meta.url), 'utf8'),
  readFile(new URL('../src/vcf-tools.css', import.meta.url), 'utf8'),
  readFile(new URL('../src/duplicate-tools.css', import.meta.url), 'utf8'),
])

const featureToolSource = `${vcfSource}\n${duplicateSource}`

const requirements = [
  {
    ok: mainSource.includes("import './glaze-accessibility.css'") &&
      mainSource.includes("import './glaze-form-factors.css'") &&
      mainSource.includes("import './glaze-form-factor-refinements.css'"),
    message: 'The Contacts client must load the Glaze accessibility and both 1.4 form-factor layers.',
  },
  {
    ok: mainSource.includes('className="skip-link"') &&
      mainSource.includes('href="#contacts"') &&
      accessibilitySource.includes('.skip-link:focus-visible'),
    message: 'Keyboard users must retain a visible skip path to the Contacts workspace.',
  },
  {
    ok: accessibilitySource.includes('.contact-row:not(.table-heading):focus-within') &&
      accessibilitySource.includes('.editor-section:focus-within') &&
      accessibilitySource.includes('.address-editor:focus-within') &&
      accessibilitySource.includes('.detail-card:focus-within') &&
      accessibilitySource.includes('.login-card:focus-within') &&
      accessibilitySource.includes('.vcf-tools:focus-within') &&
      accessibilitySource.includes('.duplicate-tools:focus-within'),
    message: 'Dense Contacts workflows must preserve visible group-level keyboard focus orientation.',
  },
  {
    ok: accessibilitySource.includes('scroll-margin-top: 104px;') &&
      accessibilitySource.includes('scroll-margin-bottom: calc(164px + env(safe-area-inset-bottom));'),
    message: 'Focused workflow groups must remain clear of sticky Desktop chrome and Compact lower navigation.',
  },
  {
    ok: accessibilitySource.includes('@media (forced-colors: active)') &&
      accessibilitySource.includes('border: 2px solid Highlight;') &&
      accessibilitySource.includes('@media (prefers-reduced-motion: reduce)') &&
      accessibilitySource.includes('transition: none;'),
    message: 'Keyboard focus-group treatment must remain visible in forced colors and calm under reduced motion.',
  },
  {
    ok: formFactorSource.includes('Glaze UI 1.4.0 current-Stable'),
    message: 'The form-factor layer must identify the current Stable Glaze UI 1.4.0 contract.',
  },
  {
    ok: refinementSource.includes('@media (max-width: 719px)') &&
      refinementSource.includes('.contact-navigation') &&
      refinementSource.includes('position: fixed;') &&
      refinementSource.includes('env(safe-area-inset-bottom)'),
    message: 'Compact Mobile must provide a true lower reachability navigation zone with safe-area handling.',
  },
  {
    ok: refinementSource.includes("content: 'Email'") &&
      refinementSource.includes("content: 'Phone'") &&
      refinementSource.includes('.table-card .contact-row:not(.table-heading)'),
    message: 'Compact Mobile must transform the desktop contact table into labeled contact cards.',
  },
  {
    ok: refinementSource.includes('.empty-state {\n  grid-column: 1 / -1;') &&
      refinementSource.includes('.notice code {\n  overflow-wrap: anywhere;') &&
      refinementSource.includes('.empty-state {\n    padding: 28px 16px;') &&
      refinementSource.includes('border: 1px dashed var(--glaze-border-strong);'),
    message: 'Loading, empty, and notice states must span the active contact canvas and remain Compact-readable.',
  },
  {
    ok: refinementSource.includes('.login-card {') &&
      refinementSource.includes('.login-card input {') &&
      refinementSource.includes('.login-actions .primary-button {') &&
      refinementSource.includes('min-height: 48px;'),
    message: 'Compact sign-in must use a full-width, touch-sized single-task form.',
  },
  {
    ok: refinementSource.includes('.account-controls {') &&
      refinementSource.includes('grid-template-columns: minmax(0, 1fr) auto;') &&
      refinementSource.includes('.account-controls > span {') &&
      refinementSource.includes('text-overflow: ellipsis;') &&
      refinementSource.includes('.backend-status {'),
    message: 'Compact account and backend state must remain bounded, readable, and touch-friendly.',
  },
  {
    ok: refinementSource.includes('.detail-card,') &&
      refinementSource.includes('.editor-card,') &&
      refinementSource.includes('background: var(--glaze-surface);') &&
      refinementSource.includes('border-color: var(--glaze-border);'),
    message: 'Contact detail and editor surfaces must use the current Glaze material token system.',
  },
  {
    ok: refinementSource.includes('.detail-actions {') &&
      refinementSource.includes('.editor-actions > div {') &&
      refinementSource.includes('min-height: 46px;') &&
      refinementSource.includes('.editor-actions .danger-button'),
    message: 'Compact contact detail and editor actions must remain touch-sized and reachability-oriented.',
  },
  {
    ok: refinementSource.includes('@media (min-width: 720px) and (max-width: 839px)') &&
      refinementSource.includes('grid-template-columns: 192px minmax(0, 1fr);') &&
      refinementSource.includes('.editor-grid,\n  .detail-grid,\n  .name-grid {\n    grid-template-columns: 1fr;') &&
      refinementSource.includes('.login-card {\n    width: 100%;\n    max-width: none;'),
    message: 'Narrow Tablet must retain a touch navigation pane while keeping auth and detail/editor workflows comfortably single-column.',
  },
  {
    ok: refinementSource.includes('@media (min-width: 840px) and (max-width: 1023px)') &&
      refinementSource.includes('.detail-grid,\n  .editor-grid {\n    grid-template-columns: repeat(2, minmax(0, 1fr));'),
    message: 'Roomier Tablet must intentionally expand contact detail and editor forms to two columns.',
  },
  {
    ok: formFactorSource.includes('@media (min-width: 1024px) and (max-width: 1439px)') &&
      formFactorSource.includes('grid-template-columns: 252px minmax(0, 1fr);'),
    message: 'Desktop must use a persistent productivity workspace composition.',
  },
  {
    ok: formFactorSource.includes('@media (min-width: 1440px)') &&
      formFactorSource.includes('grid-template-columns: 288px minmax(0, 1fr);') &&
      formFactorSource.includes('width: min(100%, 1600px);'),
    message: 'Wide Desktop must expand the workspace without unbounded content stretching.',
  },
  {
    ok: vcfSource.includes('@media (max-width: 719px)') &&
      vcfSource.includes('@media (min-width: 720px) and (max-width: 839px)') &&
      vcfSource.includes('var(--glaze-surface)') &&
      vcfSource.includes('var(--glaze-border)'),
    message: 'VCF tools must follow Glaze tokens and the Compact/Narrow-Tablet composition contract.',
  },
  {
    ok: duplicateSource.includes('@media (max-width: 719px)') &&
      duplicateSource.includes('@media (min-width: 720px) and (max-width: 839px)') &&
      duplicateSource.includes('var(--glaze-surface)') &&
      duplicateSource.includes('var(--glaze-border)'),
    message: 'Duplicate review must follow Glaze tokens and the Compact/Narrow-Tablet composition contract.',
  },
  {
    ok: !/#(?:fff(?:fff)?|f9fafb|e5e7eb|6b7280)\b/i.test(featureToolSource),
    message: 'VCF and duplicate-review presentation must not regress to the legacy hard-coded light palette.',
  },
  {
    ok: formFactorSource.includes('@media (prefers-reduced-transparency: reduce)') &&
      refinementSource.includes('@media (prefers-reduced-transparency: reduce) {') &&
      refinementSource.includes('@media (prefers-reduced-transparency: reduce) and (max-width: 719px)') &&
      vcfSource.includes('@media (prefers-reduced-transparency: reduce)') &&
      duplicateSource.includes('@media (prefers-reduced-transparency: reduce)') &&
      formFactorSource.includes('@media (forced-colors: active)') &&
      refinementSource.includes('@media (forced-colors: active) {') &&
      refinementSource.includes('.login-card,') &&
      refinementSource.includes('.account-controls,') &&
      refinementSource.includes('.backend-status,') &&
      refinementSource.includes('.empty-state {') &&
      refinementSource.includes('@media (forced-colors: active) and (max-width: 719px)') &&
      vcfSource.includes('@media (forced-colors: active)') &&
      duplicateSource.includes('@media (forced-colors: active)'),
    message: 'Form-factor, feedback, authentication, detail/editor, and workflow surfaces must retain transparency and forced-colors resilience.',
  },
  {
    ok: !/(@import\s+url\(|url\(["']?https?:\/\/)/i.test(
      `${accessibilitySource}\n${formFactorSource}\n${refinementSource}\n${featureToolSource}`,
    ),
    message: 'The accessibility, form-factor, and workflow layers must not introduce third-party presentation dependencies.',
  },
]

const failures = requirements.filter((requirement) => !requirement.ok)

if (failures.length > 0) {
  for (const failure of failures) {
    console.error(`Glaze UI form-factor validation failed: ${failure.message}`)
  }
  process.exitCode = 1
} else {
  console.log(`Glaze UI 1.4 form-factor validation passed (${requirements.length} checks).`)
}
