export type Health = {
  status: string
  service: string
  environment: string
}

export type CardDavStatus = {
  configured: boolean
  read_only: boolean
  write_enabled: boolean
}

export type AuthSession = {
  authenticated: boolean
  username: string | null
  expires_at: string | null
}

export type AddressBook = {
  href: string
  display_name: string
}

export type StructuredName = {
  family_name: string
  given_name: string
  additional_names: string
  honorific_prefixes: string
  honorific_suffixes: string
}

export type PostalAddress = {
  types: string[]
  po_box: string
  extended_address: string
  street_address: string
  locality: string
  region: string
  postal_code: string
  country: string
}

export type ContactSummary = {
  href: string
  etag: string | null
  uid: string | null
  formatted_name: string
  emails: string[]
  phones: string[]
  organization: string | null
  title: string | null
  categories: string[]
  favorite: boolean
  has_photo: boolean
}

export type ContactDetail = ContactSummary & {
  structured_name: StructuredName
  addresses: PostalAddress[]
  birthday: string | null
  websites: string[]
  note: string | null
  photo: string | null
}

export type ContactWritePayload = {
  formatted_name: string
  structured_name: StructuredName
  emails: string[]
  phones: string[]
  organization: string | null
  title: string | null
  addresses: PostalAddress[]
  birthday: string | null
  websites: string[]
  note: string | null
  categories: string[]
  favorite: boolean
  photo: string | null
}

export type ContactDeleteResponse = {
  deleted: boolean
  href: string
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function formatErrorDetail(detail: unknown): string | null {
  if (typeof detail === 'string') {
    const normalized = detail.trim()
    return normalized || null
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (!item || typeof item !== 'object') {
          return null
        }

        const record = item as Record<string, unknown>
        const message = typeof record.msg === 'string' ? record.msg.trim() : ''
        if (!message) {
          return null
        }

        const location = Array.isArray(record.loc)
          ? record.loc
              .map((part) => String(part))
              .filter((part) => !['body', 'query', 'path'].includes(part))
              .join('.')
          : ''

        return location ? `${location}: ${message}` : message
      })
      .filter((message): message is string => Boolean(message))

    if (messages.length) {
      return messages.join(' ')
    }
  }

  if (detail && typeof detail === 'object') {
    const message = (detail as Record<string, unknown>).msg
    if (typeof message === 'string' && message.trim()) {
      return message.trim()
    }
  }

  return null
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(path, {
    ...init,
    cache: 'no-store',
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
      message = formatErrorDetail(payload.detail) ?? message
    } catch {
      // Keep the HTTP status message when the response is not JSON.
    }

    throw new ApiError(response.status, message)
  }

  return (await response.json()) as T
}

export function getHealth(): Promise<Health> {
  return requestJson<Health>('/api/health')
}

export function getCardDavStatus(): Promise<CardDavStatus> {
  return requestJson<CardDavStatus>('/api/carddav/status')
}

export function getAuthSession(): Promise<AuthSession> {
  return requestJson<AuthSession>('/api/auth/session')
}

export function login(username: string, password: string): Promise<AuthSession> {
  return requestJson<AuthSession>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function logout(): Promise<AuthSession> {
  return requestJson<AuthSession>('/api/auth/logout', { method: 'POST' })
}

export function getAddressBooks(): Promise<AddressBook[]> {
  return requestJson<AddressBook[]>('/api/carddav/address-books')
}

export function getContacts(addressBookHref: string): Promise<ContactSummary[]> {
  const params = new URLSearchParams({ address_book_href: addressBookHref })
  return requestJson<ContactSummary[]>(`/api/carddav/contacts?${params.toString()}`)
}

export function getContact(href: string): Promise<ContactDetail> {
  const params = new URLSearchParams({ href })
  return requestJson<ContactDetail>(`/api/carddav/contact?${params.toString()}`)
}

export function createContact(
  addressBookHref: string,
  payload: ContactWritePayload,
): Promise<ContactDetail> {
  const params = new URLSearchParams({ address_book_href: addressBookHref })
  return requestJson<ContactDetail>(`/api/carddav/contacts?${params.toString()}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateContact(
  href: string,
  etag: string,
  payload: ContactWritePayload,
): Promise<ContactDetail> {
  const params = new URLSearchParams({ href, etag })
  return requestJson<ContactDetail>(`/api/carddav/contact?${params.toString()}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteContact(
  href: string,
  etag: string,
): Promise<ContactDeleteResponse> {
  const params = new URLSearchParams({ href, etag })
  return requestJson<ContactDeleteResponse>(`/api/carddav/contact?${params.toString()}`, {
    method: 'DELETE',
  })
}
