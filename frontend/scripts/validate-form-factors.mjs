import { readFile } from 'node:fs/promises'

const [mainSource, formFactorSource] = await Promise.all([
  readFile(new URL('../src/main.tsx', import.meta.url), 'utf8'),
  readFile(new URL('../src/glaze-form-factors.css', import.meta.url), 'utf8'),
])

const requirements = [
  {
    ok: mainSource.includes("import './glaze-form-factors.css'"),
    message: 'The Contacts client must load the Glaze UI 1.4 form-factor layer.',
  },
  {
    ok: formFactorSource.includes('Glaze UI 1.4.0 current-Stable'),
    message: 'The form-factor layer must identify the current Stable Glaze UI 1.4.0 contract.',
  },
  {
    ok: formFactorSource.includes('@media (max-width: 599px)') &&
      formFactorSource.includes('position: fixed;') &&
      formFactorSource.includes('--contacts-mobile-action-offset'),
    message: 'Mobile must provide a Compact reachability-first composition with a lower action zone.',
  },
  {
    ok: formFactorSource.includes("content: 'Email'") &&
      formFactorSource.includes("content: 'Phone'") &&
      formFactorSource.includes('.table-card .contact-row:not(.table-heading)'),
    message: 'Mobile must transform the desktop contact table into labeled contact cards.',
  },
  {
    ok: formFactorSource.includes('@media (min-width: 600px) and (max-width: 1023px)') &&
      formFactorSource.includes('grid-template-columns: 204px minmax(0, 1fr);') &&
      formFactorSource.includes('grid-template-columns: repeat(2, minmax(0, 1fr));'),
    message: 'Tablet must use a persistent touch navigation pane and intentionally expanded card canvas.',
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
    ok: formFactorSource.includes('@media (prefers-reduced-transparency: reduce)') &&
      formFactorSource.includes('@media (forced-colors: active)'),
    message: 'Form-factor layouts must retain transparency and forced-colors resilience.',
  },
  {
    ok: !/(@import\s+url\(|url\(["']?https?:\/\/)/i.test(formFactorSource),
    message: 'The form-factor layer must not introduce third-party presentation dependencies.',
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
