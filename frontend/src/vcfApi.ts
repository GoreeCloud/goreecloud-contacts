import { ApiError, type ContactSummary } from './api.ts'

export type VcfImportPreviewItem = {
  index: number
  valid: boolean
  version: string | null
  uid: string | null
  formatted_name: string | null
  emails: string[]
  phones: string[]
  warnings: string[]
  errors: string[]
}

export type VcfImportPreview = {
  total: number
  valid: number
  invalid: number
  items: VcfImportPreviewItem[]
}

export type VcfImportResult = {
  imported_count: number
  items: Array<{
    index: number
    href: string
    etag: string | null
    uid: string | null
    formatted_name: string
  }>
}

type Download = {
  blob: Blob
  filename: string
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
        return typeof record.msg === 'string' ? record.msg : null
      })
      .filter((message): message is string => Boolean(message))
    return messages.length ? messages.join(' ') : null
  }

  return null
}

async function throwApiError(response: Response): Promise<never> {
  let message = `Request failed with HTTP ${response.status}`
  try {
    const payload = (await response.json()) as { detail?: unknown }
    message = formatDetail(payload.detail) ?? message
  } catch {
    // Keep the HTTP status fallback for non-JSON responses.
  }
  throw new ApiError(response.status, message)
}

function filenameFromDisposition(disposition: string | null, fallback: string): string {
  if (!disposition) {
    return fallback
  }
  return disposition.match(/filename="([^"]+)"/i)?.[1] ?? fallback
}

async function downloadRequest(path: string, fallback: string): Promise<Download> {
  const response = await fetch(path, {
    credentials: 'include',
    headers: { Accept: 'text/vcard' },
  })

  if (!response.ok) {
    return throwApiError(response)
  }

  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(
      response.headers.get('content-disposition'),
      fallback,
    ),
  }
}

export function exportContactVcf(contact: ContactSummary): Promise<Download> {
  const params = new URLSearchParams({ href: contact.href })
  return downloadRequest(
    `/api/carddav/contact/export?${params.toString()}`,
    'contact.vcf',
  )
}

export function exportAddressBookVcf(
  addressBookHref: string,
): Promise<Download> {
  const params = new URLSearchParams({ address_book_href: addressBookHref })
  return downloadRequest(
    `/api/carddav/address-book/export?${params.toString()}`,
    'address-book.vcf',
  )
}

export async function previewVcf(vcfText: string): Promise<VcfImportPreview> {
  const response = await fetch('/api/carddav/import/preview', {
    method: 'POST',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ vcf_text: vcfText }),
  })

  if (!response.ok) {
    return throwApiError(response)
  }
  return (await response.json()) as VcfImportPreview
}

export async function importVcf(
  addressBookHref: string,
  vcfText: string,
  selectedIndices: number[],
): Promise<VcfImportResult> {
  const response = await fetch('/api/carddav/import', {
    method: 'POST',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      address_book_href: addressBookHref,
      vcf_text: vcfText,
      selected_indices: selectedIndices,
    }),
  })

  if (!response.ok) {
    return throwApiError(response)
  }
  return (await response.json()) as VcfImportResult
}
