import {
  ApiError,
  type ContactDetail,
  type ContactSummary,
  type ContactWritePayload,
} from './api.ts'

export type DuplicateSignal = {
  kind: 'uid' | 'email' | 'phone' | 'name' | 'organization' | 'title'
  value: string
}

export type DuplicateCandidate = {
  left: ContactSummary
  right: ContactSummary
  score: number
  confidence: 'high' | 'medium' | 'low'
  signals: DuplicateSignal[]
}

export type DuplicateScan = {
  candidate_count: number
  candidates: DuplicateCandidate[]
}

export type DuplicateFieldConflict = {
  field: string
  primary_value: string
  duplicate_value: string
}

export type DuplicateMergePreview = {
  primary: ContactDetail
  duplicate: ContactDetail
  proposed: ContactWritePayload
  conflicts: DuplicateFieldConflict[]
}

export type DuplicateMergeResult = {
  merged: ContactDetail
  deleted_href: string
}

function formatDetail(detail: unknown): string | null {
  if (typeof detail === 'string' && detail.trim()) {
    return detail.trim()
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (!item || typeof item !== 'object') {
          return null
        }
        const record = item as Record<string, unknown>
        return typeof record.msg === 'string' ? record.msg.trim() : null
      })
      .filter((message): message is string => Boolean(message))
    return messages.length ? messages.join(' ') : null
  }

  return null
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
    },
  })

  if (!response.ok) {
    let message = `Request failed with HTTP ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: unknown }
      message = formatDetail(payload.detail) ?? message
    } catch {
      // Keep the HTTP status fallback for non-JSON responses.
    }
    throw new ApiError(response.status, message)
  }

  return (await response.json()) as T
}

export function scanDuplicates(addressBookHref: string): Promise<DuplicateScan> {
  const params = new URLSearchParams({ address_book_href: addressBookHref })
  return requestJson<DuplicateScan>(`/api/carddav/duplicates?${params.toString()}`)
}

export function previewDuplicateMerge(
  addressBookHref: string,
  primaryHref: string,
  duplicateHref: string,
): Promise<DuplicateMergePreview> {
  return requestJson<DuplicateMergePreview>('/api/carddav/duplicates/preview', {
    method: 'POST',
    body: JSON.stringify({
      address_book_href: addressBookHref,
      primary_href: primaryHref,
      duplicate_href: duplicateHref,
    }),
  })
}

export function mergeDuplicates(
  addressBookHref: string,
  preview: DuplicateMergePreview,
  merged: ContactWritePayload,
): Promise<DuplicateMergeResult> {
  if (!preview.primary.etag || !preview.duplicate.etag) {
    throw new ApiError(
      409,
      'Both reviewed contacts require current ETags before a duplicate merge can run.',
    )
  }

  return requestJson<DuplicateMergeResult>('/api/carddav/duplicates/merge', {
    method: 'POST',
    body: JSON.stringify({
      address_book_href: addressBookHref,
      primary_href: preview.primary.href,
      primary_etag: preview.primary.etag,
      duplicate_href: preview.duplicate.href,
      duplicate_etag: preview.duplicate.etag,
      merged,
    }),
  })
}
