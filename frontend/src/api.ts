export type Health = {
  status: string
  service: string
  environment: string
}

export type CardDavStatus = {
  configured: boolean
  read_only: boolean
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

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    headers: {
      Accept: 'application/json',
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

    throw new Error(message)
  }

  return (await response.json()) as T
}

export function getHealth(): Promise<Health> {
  return getJson<Health>('/api/health')
}

export function getCardDavStatus(): Promise<CardDavStatus> {
  return getJson<CardDavStatus>('/api/carddav/status')
}

export function getAddressBooks(): Promise<AddressBook[]> {
  return getJson<AddressBook[]>('/api/carddav/address-books')
}

export function getContacts(addressBookHref: string): Promise<ContactSummary[]> {
  const params = new URLSearchParams({ address_book_href: addressBookHref })
  return getJson<ContactSummary[]>(`/api/carddav/contacts?${params.toString()}`)
}
