import { readFile } from 'node:fs/promises'

const [mainSource, glazeSource, indexSource] = await Promise.all([
  readFile(new URL('../src/main.tsx', import.meta.url), 'utf8'),
  readFile(new URL('../src/glaze.css', import.meta.url), 'utf8'),
  readFile(new URL('../index.html', import.meta.url), 'utf8'),
])

const requirements = [
  {
    ok: mainSource.includes("import './glaze.css'"),
    message: 'frontend/src/main.tsx must load the Glaze UI foundation.',
  },
  {
    ok: glazeSource.includes('--glaze-surface') && glazeSource.includes('--glaze-accent'),
    message: 'Glaze UI must retain shared surface and accent design tokens.',
  },
  {
    ok: glazeSource.includes('--surface: var(--glaze-surface-strong)') &&
      glazeSource.includes('--border: var(--glaze-border)') &&
      glazeSource.includes('--muted: var(--glaze-muted)'),
    message: 'Feature-specific tools must remain connected to shared Glaze compatibility tokens.',
  },
  {
    ok: glazeSource.includes(':focus-visible'),
    message: 'Glaze UI must retain explicit keyboard focus-visible treatment.',
  },
  {
    ok: glazeSource.includes('@media (prefers-reduced-motion: reduce)'),
    message: 'Glaze UI must retain reduced-motion behavior.',
  },
  {
    ok: glazeSource.includes('@media (prefers-reduced-transparency: reduce)'),
    message: 'Glaze UI must retain reduced-transparency fallback behavior.',
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
    ok: !/(@import\s+url\(|url\(["']?https?:\/\/)/i.test(glazeSource),
    message: 'The Glaze UI foundation must not introduce third-party CSS/font/image dependencies.',
  },
]

const failures = requirements.filter((requirement) => !requirement.ok)

if (failures.length > 0) {
  for (const failure of failures) {
    console.error(`Glaze UI validation failed: ${failure.message}`)
  }
  process.exitCode = 1
} else {
  console.log(`Glaze UI validation passed (${requirements.length} checks).`)
}
