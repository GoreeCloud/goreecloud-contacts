import { useMemo, useState, type ChangeEvent } from 'react'

import type { ContactSummary } from './api.ts'
import DuplicateTools from './DuplicateTools.tsx'
import {
  exportAddressBookVcf,
  exportContactVcf,
  importVcf,
  previewVcf,
  type VcfImportPreview,
} from './vcfApi.ts'

import './vcf-tools.css'

const MAX_VCF_FILE_BYTES = 5_000_000

type Props = {
  selectedBookHref: string
  selectedBookName: string
  contacts: ContactSummary[]
  writeEnabled: boolean
  onImported: () => void
}

function saveDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export default function VcfTools({
  selectedBookHref,
  selectedBookName,
  contacts,
  writeEnabled,
  onImported,
}: Props) {
  const [exportHref, setExportHref] = useState('')
  const [vcfText, setVcfText] = useState('')
  const [fileName, setFileName] = useState('')
  const [preview, setPreview] = useState<VcfImportPreview | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const selectedIndices = useMemo(
    () => Array.from(selected).sort((a, b) => a - b),
    [selected],
  )

  async function runExportAddressBook() {
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const download = await exportAddressBookVcf(selectedBookHref)
      saveDownload(download.blob, download.filename)
      setMessage(`Exported ${selectedBookName}.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to export address book.')
    } finally {
      setBusy(false)
    }
  }

  async function runExportContact() {
    const contact = contacts.find((item) => item.href === exportHref)
    if (!contact) {
      setError('Choose a contact to export.')
      return
    }

    setBusy(true)
    setError('')
    setMessage('')
    try {
      const download = await exportContactVcf(contact)
      saveDownload(download.blob, download.filename)
      setMessage(`Exported ${contact.formatted_name}.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to export contact.')
    } finally {
      setBusy(false)
    }
  }

  async function readFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    setPreview(null)
    setSelected(new Set())
    setMessage('')
    setError('')

    if (!file) {
      setFileName('')
      setVcfText('')
      return
    }
    if (file.size > MAX_VCF_FILE_BYTES) {
      setFileName('')
      setVcfText('')
      setError('VCF import files are limited to 5 MB in Phase 4B.')
      event.target.value = ''
      return
    }

    try {
      setFileName(file.name)
      setVcfText(await file.text())
    } catch {
      setFileName('')
      setVcfText('')
      setError('Unable to read the selected VCF file.')
    }
  }

  async function runPreview() {
    if (!vcfText) {
      setError('Choose a VCF file before previewing.')
      return
    }

    setBusy(true)
    setError('')
    setMessage('')
    try {
      const result = await previewVcf(vcfText)
      setPreview(result)
      setSelected(new Set(result.items.filter((item) => item.valid).map((item) => item.index)))
      setMessage(
        `Previewed ${result.total} record${result.total === 1 ? '' : 's'}: ` +
          `${result.valid} valid, ${result.invalid} invalid.`,
      )
    } catch (caught) {
      setPreview(null)
      setSelected(new Set())
      setError(caught instanceof Error ? caught.message : 'Unable to preview the VCF file.')
    } finally {
      setBusy(false)
    }
  }

  async function runImport() {
    if (!writeEnabled) {
      setError('The CardDAV write safety gate must be explicitly enabled before import.')
      return
    }
    if (!preview || selectedIndices.length === 0) {
      setError('Select at least one valid previewed contact to import.')
      return
    }

    setBusy(true)
    setError('')
    setMessage('')
    try {
      const result = await importVcf(
        selectedBookHref,
        vcfText,
        selectedIndices,
      )
      setMessage(
        `Imported ${result.imported_count} contact${result.imported_count === 1 ? '' : 's'} ` +
          `into ${selectedBookName}.`,
      )
      setVcfText('')
      setFileName('')
      setPreview(null)
      setSelected(new Set())
      onImported()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to import the selected contacts.')
    } finally {
      setBusy(false)
    }
  }

  function toggleSelection(index: number) {
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  return (
    <>
      <section className="vcf-tools" aria-label="VCF import and export">
        <div className="vcf-tools-heading">
          <div>
            <p className="eyebrow">Portable contacts · Phase 4B</p>
            <h3>VCF import and export</h3>
            <p className="muted">
              Export stays available in read-only mode. Import requires an explicit preview,
              destination address book, selected records, and the CardDAV write safety gate.
            </p>
          </div>
          <span className="vcf-destination">{selectedBookName}</span>
        </div>

        {error ? <div className="inline-error" role="alert">{error}</div> : null}
        {message ? <div className="vcf-success" role="status">{message}</div> : null}

        <div className="vcf-tools-grid">
          <div className="vcf-tool-panel">
            <h4>Export</h4>
            <p className="muted">
              Download the selected address book or one contact as standards-based VCF.
            </p>
            <button
              type="button"
              className="secondary-button"
              disabled={busy}
              onClick={() => void runExportAddressBook()}
            >
              Export address book
            </button>

            <label>
              Single contact
              <select
                value={exportHref}
                onChange={(event) => setExportHref(event.target.value)}
              >
                <option value="">Choose a contact…</option>
                {contacts.map((contact) => (
                  <option key={contact.href} value={contact.href}>
                    {contact.formatted_name}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="secondary-button"
              disabled={busy || !exportHref}
              onClick={() => void runExportContact()}
            >
              Export selected contact
            </button>
          </div>

          <div className="vcf-tool-panel">
            <h4>Import</h4>
            <p className="muted">
              Choose a VCF file up to 5 MB. Previewing never writes to CardDAV.
            </p>
            <label>
              VCF file
              <input
                type="file"
                accept=".vcf,text/vcard,text/x-vcard"
                onChange={(event) => void readFile(event)}
              />
            </label>
            {fileName ? <p className="vcf-file-name">{fileName}</p> : null}
            <button
              type="button"
              className="secondary-button"
              disabled={busy || !vcfText}
              onClick={() => void runPreview()}
            >
              Preview VCF
            </button>
          </div>
        </div>

        {preview ? (
          <div className="vcf-preview">
            <div className="vcf-preview-heading">
              <div>
                <h4>Import preview</h4>
                <p className="muted">
                  Valid records are selected by default. Invalid records cannot be imported.
                </p>
              </div>
              <button
                type="button"
                className="primary-button"
                disabled={busy || !writeEnabled || selectedIndices.length === 0}
                onClick={() => void runImport()}
              >
                {busy ? 'Working…' : `Import selected (${selectedIndices.length})`}
              </button>
            </div>

            {!writeEnabled ? (
              <p className="privacy-note">
                Import remains disabled while the write safety gate is active.
              </p>
            ) : null}

            <div className="vcf-preview-list">
              {preview.items.map((item) => (
                <article
                  key={item.index}
                  className={`vcf-preview-item ${item.valid ? '' : 'invalid'}`}
                >
                  <label className="vcf-select">
                    <input
                      type="checkbox"
                      checked={selected.has(item.index)}
                      disabled={!item.valid || busy}
                      onChange={() => toggleSelection(item.index)}
                    />
                    <span>Record {item.index + 1}</span>
                  </label>
                  <div className="vcf-preview-copy">
                    <strong>{item.formatted_name ?? 'Invalid vCard'}</strong>
                    <small>
                      {[item.version ? `vCard ${item.version}` : '', item.emails[0] ?? '']
                        .filter(Boolean)
                        .join(' · ')}
                    </small>
                    {item.warnings.map((warning) => (
                      <p className="vcf-warning" key={warning}>{warning}</p>
                    ))}
                    {item.errors.map((itemError) => (
                      <p className="vcf-error" key={itemError}>{itemError}</p>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      <DuplicateTools
        selectedBookHref={selectedBookHref}
        selectedBookName={selectedBookName}
        writeEnabled={writeEnabled}
        onMerged={onImported}
      />
    </>
  )
}
