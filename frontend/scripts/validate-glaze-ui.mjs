import { readFile } from 'node:fs/promises'

const [
  mainSource,
  glazeSource,
  glazeV11Source,
  accessibilitySource,
  indexSource,
  canonicalIconSource,
  webIconSource,
  manifestSource,
] = await Promise.all([
  readFile(new URL('../src/main.tsx', import.meta.url), 'utf8'),
  readFile(new URL('../src/glaze.css', import.meta.url), 'utf8'),
  readFile(new URL('../src/glaze-v1.1.css', import.meta.url), 'utf8'),
  readFile(new URL('../src/glaze-accessibility.css', import.meta.url), 'utf8'),
  readFile(new URL('../index.html', import.meta.url), 'utf8'),
  readFile(new URL('../../artwork/contacts-icon.svg', import.meta.url), 'utf8'),
  readFile(new URL('../public/contacts-icon.svg', import.meta.url), 'utf8'),
  readFile(new URL('../public/manifest.webmanifest', import.meta.url), 'utf8'),
])

const manifest = JSON.parse(manifestSource)
const manifestIcon = Array.isArray(manifest.icons)
  ? manifest.icons.find((icon) => icon?.src === '/contacts-icon.svg')
  : undefined

const legacyRefinementImport = "import './glaze-form-factor-refinements.css'"
const v11Import = "import './glaze-v1.1.css'"

const requirements = [
  {
    ok: mainSource.includes("import './glaze.css'"),
    message: 'frontend/src/main.tsx must load the historical Contacts Glaze foundation.',
  },
  {
    ok: mainSource.includes("import './glaze-accessibility.css'"),
    message: 'frontend/src/main.tsx must load the Glaze accessibility layer.',
  },
  {
    ok: mainSource.includes(v11Import) &&
      mainSource.indexOf(v11Import) > mainSource.indexOf(legacyRefinementImport),
    message: 'The GLAZE UI V1.1 migration layer must load after the historical form-factor refinements.',
  },
  {
    ok: indexSource.includes('data-glaze-version="1.1"') &&
      indexSource.includes('data-glaze-density-profile="standard"'),
    message: 'The browser document must explicitly activate GLAZE UI V1.1 and a governed density profile.',
  },
  {
    ok: glazeV11Source.includes('GoreeCloud/goreecloud-glaze-ui@15cc76d2bcd4065552dc31c77145b63f34d9e7b2') &&
      glazeV11Source.includes('GLAZE UI V1.1 / 1.1.0 source migration layer'),
    message: 'The migration layer must identify the exact current Stable GLAZE UI V1.1 source authority.',
  },
  {
    ok: glazeV11Source.includes('--glz11-deep-teal: #0f6b6f;') &&
      glazeV11Source.includes('--glz11-soft-amber: #d9a35f;') &&
      glazeV11Source.includes('--glz11-radius-micro: 8px;') &&
      glazeV11Source.includes('--glz11-radius-control: 16px;') &&
      glazeV11Source.includes('--glz11-radius-container: 24px;') &&
      glazeV11Source.includes('--glz11-radius-hero: 32px;'),
    message: 'The V1.1 optical layer must retain the Stable Deep Teal/Soft Amber identity and 8/16/24/32 geometry references.',
  },
  {
    ok: glazeV11Source.includes('--glz11-target-min: 48px;') &&
      glazeV11Source.includes('[data-glz-touch-assistance="true"]') &&
      glazeV11Source.includes('--glz11-target-min: 56px;'),
    message: 'The V1.1 layer must enforce the 48px target floor and 56px touch-assistance target.',
  },
  {
    ok: glazeV11Source.includes('--glaze-success: var(--glz1-success);') &&
      glazeV11Source.includes('--glaze-warning: var(--glz1-warning);') &&
      glazeV11Source.includes('--glaze-danger: var(--glz1-critical);'),
    message: 'Protected semantic success/warning/critical roles must remain distinct from atmospheric color.',
  },
  {
    ok: glazeV11Source.includes('Reading and explicit-decision surfaces are solid') &&
      /\.notice,[\s\S]*?\.duplicate-tools\s*\{[\s\S]*?backdrop-filter:\s*none;/m.test(glazeV11Source),
    message: 'Reading and explicit-decision surfaces must be solid instead of introducing nested blur.',
  },
  {
    ok: glazeV11Source.includes('[data-glz-appearance="light"]') &&
      glazeV11Source.includes('[data-glz-appearance="dark"]') &&
      glazeV11Source.includes('[data-glz-appearance="deep-dark"]'),
    message: 'The V1.1 migration must include explicit Light, Dark, and Deep Dark appearance mappings.',
  },
  {
    ok: glazeV11Source.includes('@media (prefers-color-scheme: dark)') &&
      glazeV11Source.includes('html[data-glaze-version="1.1"]:not([data-glz-appearance])') &&
      !glazeV11Source.includes('html[data-glaze-version="1.1"]:not([data-glz-appearance="light"])'),
    message: 'System dark fallback must apply only when no explicit appearance is selected so explicit Deep Dark remains authoritative.',
  },
  {
    ok: glazeV11Source.includes('@media (prefers-reduced-transparency: reduce)') &&
      glazeV11Source.includes('@media (prefers-contrast: more)') &&
      glazeV11Source.includes('@media (forced-colors: active)'),
    message: 'The V1.1 migration must retain Reduced Transparency, Increased Contrast, and Forced Colors resilience.',
  },
  {
    ok: mainSource.includes('className="skip-link"') && mainSource.includes('href="#contacts"'),
    message: 'The application root must provide keyboard skip navigation to the contacts content.',
  },
  {
    ok: accessibilitySource.includes('.skip-link:focus-visible'),
    message: 'The keyboard skip link must become visible on focus.',
  },
  {
    ok: glazeSource.includes('--glaze-surface') && glazeSource.includes('--glaze-accent'),
    message: 'The historical Contacts layers must retain compatibility tokens consumed by existing feature styles.',
  },
  {
    ok: glazeV11Source.includes('--surface: var(--glaze-surface-strong)') &&
      glazeV11Source.includes('--border: var(--glaze-border)') &&
      glazeV11Source.includes('--muted: var(--glaze-muted)'),
    message: 'Feature-specific tools must remain connected to the V1.1 compatibility bridge.',
  },
  {
    ok: glazeSource.includes(':focus-visible'),
    message: 'Glaze UI must retain explicit keyboard focus-visible treatment.',
  },
  {
    ok: glazeSource.includes('@media (prefers-reduced-motion: reduce)') &&
      accessibilitySource.includes('@media (prefers-reduced-motion: reduce)'),
    message: 'The application must retain reduced-motion behavior.',
  },
  {
    ok: accessibilitySource.includes('@media (prefers-contrast: more)'),
    message: 'The Glaze accessibility layer must retain increased-contrast behavior.',
  },
  {
    ok: accessibilitySource.includes('@media (forced-colors: active)'),
    message: 'The Glaze accessibility layer must retain forced-colors fallback behavior.',
  },
  {
    ok: /@media \(max-width: 820px\)[\s\S]*?\.sidebar\s*\{[\s\S]*?display:\s*grid;/m.test(glazeSource),
    message: 'Small-screen Glaze UI must keep the primary sidebar controls available.',
  },
  {
    ok: !/@media \(max-width: 820px\)[\s\S]*?\.sidebar\s*\{[\s\S]*?display:\s*none;/m.test(glazeSource),
    message: 'Glaze UI must not hide the entire primary sidebar on small screens.',
  },
  {
    ok: indexSource.includes('name="color-scheme"') && indexSource.includes('light dark'),
    message: 'The document must declare light/dark color-scheme support.',
  },
  {
    ok: indexSource.includes('content="#f5f7fa"') && indexSource.includes('content="#0b0d11"'),
    message: 'Browser theme metadata must follow the V1 structural Light/Dark canvas values.',
  },
  {
    ok: indexSource.includes('name="referrer"') && indexSource.includes('content="no-referrer"'),
    message: 'The private application document must retain no-referrer browser metadata.',
  },
  {
    ok: indexSource.includes('name="robots"') &&
      indexSource.includes('noindex') &&
      indexSource.includes('nofollow') &&
      indexSource.includes('noarchive'),
    message: 'The private application document must retain no-index/no-archive crawler directives.',
  },
  {
    ok: !/(@import\s+url\(|url\(["']?https?:\/\/)/i.test(
      `${glazeSource}\n${glazeV11Source}\n${accessibilitySource}`,
    ),
    message: 'The Glaze UI layers must not introduce remote CSS/font/image dependencies.',
  },
  {
    ok: canonicalIconSource.includes('<title id="title">GoreeCloud Contacts</title>') &&
      canonicalIconSource.includes('viewBox="0 0 512 512"') &&
      canonicalIconSource.includes('address-book tile with a person silhouette'),
    message: 'The canonical Contacts SVG must retain its product identity metadata and 512-square vector contract.',
  },
  {
    ok: canonicalIconSource === webIconSource,
    message: 'The browser Contacts icon must remain byte-for-byte identical to artwork/contacts-icon.svg.',
  },
  {
    ok: indexSource.includes('rel="icon" type="image/svg+xml" href="/contacts-icon.svg"') &&
      indexSource.includes('rel="apple-touch-icon" href="/contacts-icon.svg"'),
    message: 'The browser document must continue using the canonical Contacts icon for application identity metadata.',
  },
  {
    ok: indexSource.includes('rel="manifest" href="/manifest.webmanifest"'),
    message: 'The browser document must retain the GoreeCloud Contacts web app manifest reference.',
  },
  {
    ok: manifest.name === 'GoreeCloud Contacts' &&
      manifest.short_name === 'Contacts' &&
      manifest.start_url === '/' &&
      manifest.scope === '/' &&
      manifest.display === 'standalone',
    message: 'The Contacts web app manifest must retain its canonical product identity and same-origin launch contract.',
  },
  {
    ok: manifestIcon?.type === 'image/svg+xml' &&
      manifestIcon?.sizes === 'any' &&
      typeof manifestIcon?.purpose === 'string' &&
      manifestIcon.purpose.includes('any') &&
      manifestIcon.purpose.includes('maskable'),
    message: 'The Contacts web app manifest must derive install icon metadata from /contacts-icon.svg.',
  },
]

const failures = requirements.filter((requirement) => !requirement.ok)

if (failures.length > 0) {
  for (const failure of failures) {
    console.error(`Glaze UI validation failed: ${failure.message}`)
  }
  process.exitCode = 1
} else {
  console.log(`GLAZE UI V1.1 source migration validation passed (${requirements.length} checks).`)
}
