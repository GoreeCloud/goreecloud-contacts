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

export type ContactSummary = {
  href: string
  etag: string | null
  uid: string | null
  formatted_name: string
  emails: string[]
  phones: string[]
}

export type ContactWritePayload = {
  formatted_name: string
  emails: string[]
  phones: string[]
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

async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
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
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) {
        message = payload.detail
      }
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

export function createContact(
  addressBookHref: string,
  payload: ContactWritePayload,
): Promise<ContactSummary> {
  const params = new URLSearchParams({ address_book_href: addressBookHref })
  return requestJson<ContactSummary>(`/api/carddav/contacts?${params.toString()}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateContact(
  href: string,
  etag: string,
  payload: ContactWritePayload,
): Promise<ContactSummary> {
  const params = new URLSearchParams({ href, etag })
  return requestJson<ContactSummary>(`/api/carddav/contact?${params.toString()}`, {
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
