import { readFile } from 'node:fs/promises'

const [mainSource, foundationSource, indexSource, packageSource] = await Promise.all([
  readFile(new URL('../src/main.tsx', import.meta.url), 'utf8'),
  readFile(new URL('../src/glaze-v1.3-foundation.css', import.meta.url), 'utf8'),
  readFile(new URL('../index.html', import.meta.url), 'utf8'),
  readFile(new URL('../package.json', import.meta.url), 'utf8'),
])

const packageJson = JSON.parse(packageSource)
const v11Import = "import './glaze-v1.1.css'"
const v13FoundationImport = "import './glaze-v1.3-foundation.css'"
const stableAnchor = 'fc7cc91d2eace8da2371371c2855c24cbcb326a1'

const requirements = [
  {
    ok: mainSource.includes(v13FoundationImport) &&
      mainSource.indexOf(v13FoundationImport) > mainSource.indexOf(v11Import),
    message: 'The bounded V1.3 foundation must load after the currently active V1.1 layer.',
  },
  {
    ok: indexSource.includes('data-glaze-version="1.1"') &&
      !indexSource.includes('data-glaze-version="1.3"') &&
      !indexSource.includes('data-glaze-target-version="1.3"'),
    message: 'This tranche must not activate a V1.3 root or target marker before fresh whole-shell acceptance.',
  },
  {
    ok: foundationSource.includes('GLAZE UI V1.3 / 1.3.0 Adaptive Resonance foundation') &&
      foundationSource.includes(`GoreeCloud/goreecloud-glaze-ui@${stableAnchor}`),
    message: 'The staged foundation must identify V1.3.0 and its exact Stable integration anchor.',
  },
  {
    ok: foundationSource.includes('data-glaze-version="1.1" runtime contract') &&
      foundationSource.includes('fresh whole-shell rendered acceptance'),
    message: 'The source must retain an explicit non-activation and fresh-acceptance boundary.',
  },
  {
    ok: foundationSource.includes('V1.3 inherits the V1.2 neutral/frosted rendering foundation') &&
      foundationSource.includes('--glz13-frost-white: #f4f8fa;') &&
      foundationSource.includes('--glz13-base-glass: rgba(255, 255, 255, 0.58);'),
    message: 'The foundation must retain the inherited V1.2/V1.3 Stable neutral material source markers.',
  },
  {
    ok: foundationSource.includes('html[data-glaze-target-version="1.3"]') &&
      !foundationSource.includes('html[data-glaze-version="1.3"]'),
    message: 'V1.3 styles must remain isolated behind the staged target selector in this tranche.',
  },
  {
    ok: foundationSource.includes('wallpaper/environment sampling') &&
      foundationSource.includes('remote dynamic color') &&
      foundationSource.includes('contextual intelligence') &&
      foundationSource.includes('Personalization persistence') &&
      foundationSource.includes('System Shell authority'),
    message: 'The V1.3 adaptive-authority exclusions must remain explicit.',
  },
  {
    ok: foundationSource.includes('--glaze-success: var(--glz1-success);') &&
      foundationSource.includes('--glaze-warning: var(--glz1-warning);') &&
      foundationSource.includes('--glaze-danger: var(--glz1-critical);') &&
      foundationSource.includes('--glaze-focus: var(--glz1-focus);'),
    message: 'Protected semantic and focus roles must remain authoritative during staging.',
  },
  {
    ok: foundationSource.includes('@media (prefers-reduced-transparency: reduce)') &&
      foundationSource.includes('@media (prefers-contrast: more)') &&
      foundationSource.includes('@media (forced-colors: active)'),
    message: 'The staged foundation must carry resilience fallbacks before activation.',
  },
  {
    ok: !/(@import\s+url\(|url\(["']?https?:\/\/)/i.test(foundationSource),
    message: 'The staged V1.3 foundation must not introduce remote CSS, font, or image dependencies.',
  },
  {
    ok: packageJson.scripts?.['validate:ui']?.includes('validate-glaze-v1.3-foundation.mjs'),
    message: 'The Contacts UI validation command must run the V1.3 staging gate.',
  },
]

const failures = requirements.filter((requirement) => !requirement.ok)

if (failures.length > 0) {
  for (const failure of failures) {
    console.error(`GLAZE UI V1.3 foundation validation failed: ${failure.message}`)
  }
  process.exitCode = 1
} else {
  console.log(`GLAZE UI V1.3 bounded foundation validation passed (${requirements.length} checks).`)
}
