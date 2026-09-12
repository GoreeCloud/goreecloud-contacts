import { useMemo, useState } from 'react'

import type { ContactWritePayload } from './api.ts'
import {
  mergeDuplicates,
  previewDuplicateMerge,
  scanDuplicates,
  type DuplicateCandidate,
  type DuplicateFieldConflict,
  type DuplicateMergePreview,
  type DuplicateSignal,
} from './duplicateApi.ts'

import './duplicate-tools.css'

type Props = {
  selectedBookHref: string
  selectedBookName: string
  writeEnabled: boolean
  onMerged: () => void
}

type ConflictChoice = 'primary' | 'duplicate'
type ConflictChoices = Record<string, ConflictChoice>

function signalLabel(signal: DuplicateSignal): string {
  switch (signal.kind) {
    case 'uid':
      return `Same UID: ${signal.value}`
    case 'email':
      return `Same email: ${signal.value}`
    case 'phone':
      return `Same phone: ${signal.value}`
    case 'name':
      return `Same name: ${signal.value}`
    case 'organization':
      return `Same organization: ${signal.value}`
    case 'title':
      return `Same title: ${signal.value}`
  }
}

function clonePayload(payload: ContactWritePayload): ContactWritePayload {
  return {
    ...payload,
    structured_name: { ...payload.structured_name },
    emails: [...payload.emails],
    phones: [...payload.phones],
    addresses: payload.addresses.map((address) => ({
      ...address,
      types: [...address.types],
    })),
    websites: [...payload.websites],
    categories: [...payload.categories],
  }
}

function applyConflictChoice(
  payload: ContactWritePayload,
  conflict: DuplicateFieldConflict,
  choice: ConflictChoice,
): void {
  const value = choice === 'duplicate' ? conflict.duplicate_value : conflict.primary_value

  if (conflict.field.startsWith('structured_name.')) {
    const field = conflict.field.slice('structured_name.'.length) as keyof ContactWritePayload['structured_name']
    payload.structured_name[field] = value
    return
  }

  switch (conflict.field) {
    case 'formatted_name':
      payload.formatted_name = value
      break
    case 'organization':
      payload.organization = value || null
      break
    case 'title':
      payload.title = value || null
      break
    case 'birthday':
      payload.birthday = value || null
      break
    case 'note':
      payload.note = value || null
      break
    case 'photo':
      payload.photo = value || null
      break
  }
}

function candidateKey(candidate: DuplicateCandidate): string {
  return [candidate.left.href, candidate.right.href].sort().join('::')
}

function contactSummaryLines(contact: DuplicateCandidate['left']): string[] {
  return [
    contact.emails[0] ?? '',
    contact.phones[0] ?? '',
    [contact.title, contact.organization].filter(Boolean).join(' · '),
  ].filter(Boolean)
}

export default function DuplicateTools({
  selectedBookHref,
  selectedBookName,
  writeEnabled,
  onMerged,
}: Props) {
  const [candidates, setCandidates] = useState<DuplicateCandidate[]>([])
  const [scanned, setScanned] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [review, setReview] = useState<DuplicateMergePreview | null>(null)
  const [choices, setChoices] = useState<ConflictChoices>({})

  const resolvedPayload = useMemo(() => {
    if (!review) {
      return null
    }

    const payload = clonePayload(review.proposed)
    for (const conflict of review.conflicts) {
      applyConflictChoice(payload, conflict, choices[conflict.field] ?? 'primary')
    }
    return payload
  }, [choices, review])

  async function runScan(options?: { quiet?: boolean }) {
    setBusy(true)
    setError('')
    if (!options?.quiet) {
      setMessage('')
    }

    try {
      const result = await scanDuplicates(selectedBookHref)
      setCandidates(result.candidates)
      setScanned(true)
      if (!options?.quiet) {
        setMessage(
          result.candidate_count === 0
            ? `No duplicate candidates found in ${selectedBookName}.`
            : `Found ${result.candidate_count} duplicate candidate${result.candidate_count === 1 ? '' : 's'} in ${selectedBookName}.`,
        )
      }
      return result
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to scan for duplicate contacts.')
      return null
    } finally {
      setBusy(false)
    }
  }

  async function beginReview(
    candidate: DuplicateCandidate,
    primaryHref: string,
  ) {
    const primary = candidate.left.href === primaryHref ? candidate.left : candidate.right
    const duplicate = candidate.left.href === primaryHref ? candidate.right : candidate.left

    setBusy(true)
    setError('')
    setMessage('')
    try {
      const result = await previewDuplicateMerge(
        selectedBookHref,
        primary.href,
        duplicate.href,
      )
      setReview(result)
      setChoices(
        Object.fromEntries(
          result.conflicts.map((conflict) => [conflict.field, 'primary']),
        ) as ConflictChoices,
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to preview the duplicate merge.')
    } finally {
      setBusy(false)
    }
  }

  async function swapPrimary() {
    if (!review) {
      return
    }

    setBusy(true)
    setError('')
    setMessage('')
    try {
      const result = await previewDuplicateMerge(
        selectedBookHref,
        review.duplicate.href,
        review.primary.href,
      )
      setReview(result)
      setChoices(
        Object.fromEntries(
          result.conflicts.map((conflict) => [conflict.field, 'primary']),
        ) as ConflictChoices,
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to swap the primary contact.')
    } finally {
      setBusy(false)
    }
  }

  async function runMerge() {
    if (!writeEnabled) {
      setError('The CardDAV write safety gate must be explicitly enabled before merging duplicates.')
      return
    }
    if (!review || !resolvedPayload) {
      setError('Review a duplicate candidate before merging.')
      return
    }

    setBusy(true)
    setError('')
    setMessage('')
    try {
      const result = await mergeDuplicates(
        selectedBookHref,
        review,
        resolvedPayload,
      )
      setReview(null)
      setChoices({})
      onMerged()
      const refreshed = await runScan({ quiet: true })
      setMessage(
        `Merged into ${result.merged.formatted_name} and removed the reviewed duplicate.` +
          (refreshed ? ` ${refreshed.candidate_count} candidate${refreshed.candidate_count === 1 ? '' : 's'} remain.` : ''),
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to merge the reviewed duplicate contacts.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="duplicate-tools" aria-label="Duplicate contact review">
      <div className="duplicate-tools-heading">
        <div>
          <p className="eyebrow">Contact quality · Phase 4C</p>
          <h3>Duplicate detection and merge</h3>
          <p className="muted">
            Scan is read-only. GoreeCloud suggests possible matches, but you choose the
            surviving contact, review conflicts, and explicitly approve every merge.
          </p>
        </div>
        <div className="duplicate-heading-actions">
          <span className="duplicate-destination">{selectedBookName}</span>
          <button
            type="button"
            className="secondary-button"
            disabled={busy}
            onClick={() => void runScan()}
          >
            {busy ? 'Working…' : 'Scan for duplicates'}
          </button>
        </div>
      </div>

      {error ? <div className="inline-error" role="alert">{error}</div> : null}
      {message ? <div className="duplicate-success" role="status">{message}</div> : null}

      {review && resolvedPayload ? (
        <div className="duplicate-review">
          <div className="duplicate-review-heading">
            <div>
              <h4>Review merge</h4>
              <p className="muted">
                <strong>{review.primary.formatted_name}</strong> will survive. The other
                resource is deleted only after the survivor is conditionally updated.
              </p>
            </div>
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => void swapPrimary()}
            >
              Swap primary
            </button>
          </div>

          <div className="duplicate-review-pair">
            <article>
              <span className="duplicate-role primary">Survives</span>
              <strong>{review.primary.formatted_name}</strong>
              <small>{review.primary.emails[0] ?? review.primary.phones[0] ?? 'No email or phone'}</small>
            </article>
            <article>
              <span className="duplicate-role duplicate">Removed after merge</span>
              <strong>{review.duplicate.formatted_name}</strong>
              <small>{review.duplicate.emails[0] ?? review.duplicate.phones[0] ?? 'No email or phone'}</small>
            </article>
          </div>

          {review.conflicts.length ? (
            <div className="duplicate-conflicts">
              <h5>Choose conflicting values</h5>
              {review.conflicts.map((conflict) => (
                <label className="duplicate-conflict" key={conflict.field}>
                  <span>{conflict.field.replace('structured_name.', 'Name · ').replaceAll('_', ' ')}</span>
                  <select
                    value={choices[conflict.field] ?? 'primary'}
                    disabled={busy}
                    onChange={(event) =>
                      setChoices((current) => ({
                        ...current,
                        [conflict.field]: event.target.value as ConflictChoice,
                      }))
                    }
                  >
                    <option value="primary">Keep primary: {conflict.primary_value}</option>
                    <option value="duplicate">Use duplicate: {conflict.duplicate_value}</option>
                  </select>
                </label>
              ))}
            </div>
          ) : (
            <p className="privacy-note">No conflicting scalar fields require a choice.</p>
          )}

          <div className="duplicate-proposal">
            <h5>Proposed result</h5>
            <dl>
              <div><dt>Name</dt><dd>{resolvedPayload.formatted_name}</dd></div>
              <div><dt>Emails</dt><dd>{resolvedPayload.emails.join(', ') || '—'}</dd></div>
              <div><dt>Phones</dt><dd>{resolvedPayload.phones.join(', ') || '—'}</dd></div>
              <div><dt>Organization</dt><dd>{resolvedPayload.organization || '—'}</dd></div>
              <div><dt>Categories</dt><dd>{resolvedPayload.categories.join(', ') || '—'}</dd></div>
            </dl>
            <p className="privacy-note">
              Unsupported raw vCard properties from both reviewed resources are preserved
              where possible. The survivor keeps its UID. Current ETags are rechecked before
              any write so a changed contact cannot be merged from stale review state.
            </p>
          </div>

          {!writeEnabled ? (
            <p className="privacy-note">
              Review remains available in read-only mode. Merge stays disabled while the
              write safety gate is active.
            </p>
          ) : null}

          <div className="duplicate-review-actions">
            <button
              type="button"
              className="secondary-button"
              disabled={busy}
              onClick={() => {
                setReview(null)
                setChoices({})
              }}
            >
              Cancel review
            </button>
            <button
              type="button"
              className="primary-button"
              disabled={busy || !writeEnabled}
              onClick={() => void runMerge()}
            >
              {busy ? 'Working…' : 'Merge reviewed contacts'}
            </button>
          </div>
        </div>
      ) : null}

      {scanned && !review ? (
        <div className="duplicate-candidates">
          {candidates.length === 0 ? (
            <div className="duplicate-empty">No duplicate candidates were found.</div>
          ) : (
            candidates.map((candidate) => (
              <article className="duplicate-candidate" key={candidateKey(candidate)}>
                <div className="duplicate-candidate-heading">
                  <div>
                    <span className={`duplicate-confidence ${candidate.confidence}`}>
                      {candidate.confidence} confidence · {candidate.score}/100
                    </span>
                    <div className="duplicate-signals">
                      {candidate.signals.map((signal, index) => (
                        <span key={`${signal.kind}-${signal.value}-${index}`}>
                          {signalLabel(signal)}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="duplicate-pair">
                  {[candidate.left, candidate.right].map((contact) => (
                    <div className="duplicate-contact" key={contact.href}>
                      <strong>{contact.formatted_name}</strong>
                      {contactSummaryLines(contact).map((line) => <small key={line}>{line}</small>)}
                      <button
                        type="button"
                        className="secondary-button"
                        disabled={busy}
                        onClick={() => void beginReview(candidate, contact.href)}
                      >
                        Keep this contact
                      </button>
                    </div>
                  ))}
                </div>
              </article>
            ))
          )}
        </div>
      ) : null}
    </section>
  )
}
