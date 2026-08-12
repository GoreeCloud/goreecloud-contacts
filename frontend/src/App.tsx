import { useEffect, useMemo, useState } from 'react'

import {
  getAddressBooks,
  getCardDavStatus,
  getContacts,
  getHealth,
  type AddressBook,
  type ContactSummary,
  type Health,
} from './api.ts'

type LoadState = 'idle' | 'loading' | 'ready' | 'error'

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [addressBooks, setAddressBooks] = useState<AddressBook[]>([])
  const [selectedBook, setSelectedBook] = useState<string>('')
  const [contacts, setContacts] = useState<ContactSummary[]>([])
  const [query, setQuery] = useState('')
  const [state, setState] = useState<LoadState>('loading')
  const [error, setError] = useState<string>('')

  useEffect(() => {
    let cancelled = false

    async function bootstrap() {
      setState('loading')
      setError('')

      try {
        const [healthResult, statusResult] = await Promise.all([
          getHealth(),
          getCardDavStatus(),
        ])

        if (cancelled) {
          return
        }

        setHealth(healthResult)
        setConfigured(statusResult.configured)

        if (!statusResult.configured) {
          setState('ready')
          return
        }

        const books = await getAddressBooks()
        if (cancelled) {
          return
        }

        setAddressBooks(books)

        if (books.length > 0) {
          setSelectedBook(books[0].href)
        }

        setState('ready')
      } catch (caught) {
        if (cancelled) {
          return
        }

        setError(caught instanceof Error ? caught.message : 'Unknown error')
        setState('error')
      }
    }

    void bootstrap()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    async function loadContacts() {
      if (!selectedBook) {
        setContacts([])
        return
      }

      setState('loading')
      setError('')

      try {
        const result = await getContacts(selectedBook)
        if (!cancelled) {
          setContacts(result)
          setState('ready')
        }
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : 'Unknown error')
          setState('error')
        }
      }
    }

    void loadContacts()

    return () => {
      cancelled = true
    }
  }, [selectedBook])

  const filteredContacts = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase()

    if (!needle) {
      return contacts
    }

    return contacts.filter((contact) => {
      const haystack = [
        contact.formatted_name,
        ...contact.emails,
        ...contact.phones,
      ]
        .join(' ')
        .toLocaleLowerCase()

      return haystack.includes(needle)
    })
  }, [contacts, query])

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">GoreeCloud</p>
          <h1>Contacts</h1>
        </div>
        <div className="backend-status" aria-live="polite">
          <span
            className={`status-dot ${health?.status === 'ok' ? 'online' : ''}`}
          />
          {health?.status === 'ok' ? 'Backend online' : 'Connecting'}
        </div>
      </header>

      <main className="workspace">
        <aside className="sidebar">
          <button type="button" className="create-button" disabled>
            + Create contact
          </button>

          <nav aria-label="Contact navigation">
            <a className="nav-item active" href="#contacts">
              Contacts
              <span>{contacts.length}</span>
            </a>
          </nav>

          <div className="sidebar-section">
            <p className="section-label">Address books</p>
            {addressBooks.length === 0 ? (
              <p className="muted">No address books loaded.</p>
            ) : (
              addressBooks.map((book) => (
                <button
                  type="button"
                  className={`book-button ${
                    selectedBook === book.href ? 'selected' : ''
                  }`}
                  key={book.href}
                  onClick={() => setSelectedBook(book.href)}
                >
                  {book.display_name}
                </button>
              ))
            )}
          </div>

          <div className="read-only-badge">Read-only milestone</div>
        </aside>

        <section className="content" id="contacts">
          <div className="content-header">
            <div>
              <p className="eyebrow">CardDAV</p>
              <h2>Contacts</h2>
            </div>
            <input
              aria-label="Search contacts"
              className="search"
              type="search"
              placeholder="Search contacts"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>

          {configured === false ? (
            <div className="notice">
              <h3>CardDAV connection is not configured yet</h3>
              <p>
                Copy <code>.env.example</code> to <code>.env</code> locally and
                provide an approved test Radicale account. Credentials stay
                outside Git.
              </p>
            </div>
          ) : null}

          {error ? (
            <div className="notice error" role="alert">
              <h3>Unable to load CardDAV data</h3>
              <p>{error}</p>
            </div>
          ) : null}

          <div className="table-card" aria-busy={state === 'loading'}>
            <div className="contact-row table-heading">
              <span>Name</span>
              <span>Email</span>
              <span>Phone</span>
            </div>

            {state === 'loading' ? (
              <div className="empty-state">Loading…</div>
            ) : filteredContacts.length === 0 ? (
              <div className="empty-state">
                {configured === false
                  ? 'Configure a test CardDAV account to begin.'
                  : 'No contacts found.'}
              </div>
            ) : (
              filteredContacts.map((contact) => (
                <article className="contact-row" key={contact.href}>
                  <div className="name-cell">
                    <div className="avatar" aria-hidden="true">
                      {initials(contact.formatted_name)}
                    </div>
                    <strong>{contact.formatted_name}</strong>
                  </div>
                  <span>{contact.emails[0] ?? '—'}</span>
                  <span>{contact.phones[0] ?? '—'}</span>
                </article>
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  )
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}
