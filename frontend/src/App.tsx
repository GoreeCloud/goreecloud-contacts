import { useEffect, useMemo, useState, type FormEvent } from 'react'

import {
  ApiError,
  createContact,
  deleteContact,
  getAddressBooks,
  getAuthSession,
  getCardDavStatus,
  getContacts,
  getHealth,
  login,
  logout,
  updateContact,
  type AddressBook,
  type AuthSession,
  type ContactSummary,
  type ContactWritePayload,
  type Health,
} from './api.ts'

import './milestone2.css'

type LoadState = 'idle' | 'loading' | 'ready' | 'error'
type EditorState =
  | { mode: 'create' }
  | { mode: 'edit'; contact: ContactSummary }
  | null

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [writeEnabled, setWriteEnabled] = useState(false)
  const [authSession, setAuthSession] = useState<AuthSession | null>(null)
  const [addressBooks, setAddressBooks] = useState<AddressBook[]>([])
  const [selectedBook, setSelectedBook] = useState<string>('')
  const [contacts, setContacts] = useState<ContactSummary[]>([])
  const [query, setQuery] = useState('')
  const [state, setState] = useState<LoadState>('loading')
  const [error, setError] = useState<string>('')
  const [editor, setEditor] = useState<EditorState>(null)
  const [refreshCounter, setRefreshCounter] = useState(0)

  const authenticated = authSession?.authenticated === true

  useEffect(() => {
    let cancelled = false

    async function bootstrap() {
      setState('loading')
      setError('')

      try {
        const [healthResult, statusResult, sessionResult] = await Promise.all([
          getHealth(),
          getCardDavStatus(),
          getAuthSession(),
        ])

        if (cancelled) {
          return
        }

        setHealth(healthResult)
        setConfigured(statusResult.configured)
        setWriteEnabled(statusResult.write_enabled)
        setAuthSession(sessionResult)

        if (!statusResult.configured || !sessionResult.authenticated) {
          setState('ready')
          return
        }

        const books = await getAddressBooks()
        if (cancelled) {
          return
        }

        setAddressBooks(books)
        setSelectedBook(books[0]?.href ?? '')
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
      if (!authenticated || !selectedBook) {
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
        if (cancelled) {
          return
        }

        if (caught instanceof ApiError && caught.status === 401) {
          resetAuthenticatedState()
          setError('Your session expired. Sign in again to continue.')
          setState('ready')
          return
        }

        setError(caught instanceof Error ? caught.message : 'Unknown error')
        setState('error')
      }
    }

    void loadContacts()

    return () => {
      cancelled = true
    }
  }, [authenticated, selectedBook, refreshCounter])

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

  function resetAuthenticatedState() {
    setAuthSession({ authenticated: false, username: null, expires_at: null })
    setAddressBooks([])
    setSelectedBook('')
    setContacts([])
    setEditor(null)
    setQuery('')
  }

  async function signedIn(session: AuthSession) {
    setAuthSession(session)
    setState('loading')
    setError('')

    try {
      const books = await getAddressBooks()
      setAddressBooks(books)
      setSelectedBook(books[0]?.href ?? '')
      setState('ready')
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        resetAuthenticatedState()
      }
      setError(caught instanceof Error ? caught.message : 'Unable to load address books')
      setState('error')
      throw caught
    }
  }

  async function signOut() {
    try {
      await logout()
    } finally {
      resetAuthenticatedState()
      setError('')
      setState('ready')
    }
  }

  function chooseBook(href: string) {
    setSelectedBook(href)
    setEditor(null)
  }

  function mutationCompleted() {
    setEditor(null)
    setRefreshCounter((value) => value + 1)
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">GoreeCloud</p>
          <h1>Contacts</h1>
        </div>
        <div className="topbar-actions">
          {authenticated ? (
            <div className="account-controls">
              <span>{authSession.username}</span>
              <button type="button" className="text-button" onClick={() => void signOut()}>
                Sign out
              </button>
            </div>
          ) : null}
          <div className="backend-status" aria-live="polite">
            <span
              className={`status-dot ${health?.status === 'ok' ? 'online' : ''}`}
            />
            {health?.status === 'ok' ? 'Backend online' : 'Connecting'}
          </div>
        </div>
      </header>

      <main className="workspace">
        <aside className="sidebar">
          <button
            type="button"
            className="create-button"
            disabled={!authenticated || !writeEnabled || !selectedBook}
            onClick={() => setEditor({ mode: 'create' })}
          >
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
            {!authenticated ? (
              <p className="muted">Sign in to load your address books.</p>
            ) : addressBooks.length === 0 ? (
              <p className="muted">No address books loaded.</p>
            ) : (
              addressBooks.map((book) => (
                <button
                  type="button"
                  className={`book-button ${
                    selectedBook === book.href ? 'selected' : ''
                  }`}
                  key={book.href}
                  onClick={() => chooseBook(book.href)}
                >
                  {book.display_name}
                </button>
              ))
            )}
          </div>

          <div className={`mode-badge ${writeEnabled ? 'write-enabled' : ''}`}>
            {writeEnabled ? 'Conditional writes enabled' : 'Read-only safety mode'}
          </div>
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
              disabled={!authenticated}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>

          {configured === false ? (
            <div className="notice">
              <h3>CardDAV connection is not configured yet</h3>
              <p>
                Set <code>CARDDAV_BASE_URL</code> in the protected local environment.
                User credentials are entered at sign-in and are not stored in Git.
              </p>
            </div>
          ) : null}

          {configured && !authenticated ? (
            <LoginCard onSignedIn={signedIn} />
          ) : null}

          {configured && authenticated && !writeEnabled ? (
            <div className="notice">
              <h3>Write safety gate is active</h3>
              <p>
                Reads are available, but create, update, and delete remain
                blocked until <code>CARDDAV_WRITE_ENABLED=true</code> is set in
                the protected local environment.
              </p>
            </div>
          ) : null}

          {error ? (
            <div className="notice error" role="alert">
              <h3>Unable to complete the request</h3>
              <p>{error}</p>
            </div>
          ) : null}

          {editor && selectedBook && authenticated && writeEnabled ? (
            <ContactEditor
              editor={editor}
              addressBookHref={selectedBook}
              onCancel={() => setEditor(null)}
              onSaved={mutationCompleted}
            />
          ) : null}

          <div className="table-card" aria-busy={state === 'loading'}>
            <div className="contact-row table-heading">
              <span>Name</span>
              <span>Email</span>
              <span>Phone</span>
              <span>Actions</span>
            </div>

            {state === 'loading' ? (
              <div className="empty-state">Loading…</div>
            ) : !authenticated ? (
              <div className="empty-state">Sign in to view contacts.</div>
            ) : filteredContacts.length === 0 ? (
              <div className="empty-state">No contacts found.</div>
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
                  <span>
                    <button
                      type="button"
                      className="row-action"
                      disabled={!writeEnabled || !contact.etag}
                      onClick={() => setEditor({ mode: 'edit', contact })}
                    >
                      Edit
                    </button>
                  </span>
                </article>
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  )
}

function LoginCard({
  onSignedIn,
}: {
  onSignedIn: (session: AuthSession) => Promise<void>
}) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [loginError, setLoginError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoginError('')

    if (!username.trim() || !password) {
      setLoginError('A CardDAV username and password are required.')
      return
    }

    setBusy(true)
    try {
      const session = await login(username.trim(), password)
      setPassword('')
      await onSignedIn(session)
    } catch (caught) {
      setLoginError(caught instanceof Error ? caught.message : 'Unable to sign in')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="login-card" onSubmit={submit}>
      <div>
        <p className="eyebrow">Milestone 3</p>
        <h3>Sign in to Radicale</h3>
        <p className="muted">
          Your password is sent only to the GoreeCloud Contacts backend for CardDAV
          authentication and is never stored in the browser session cookie.
        </p>
      </div>

      {loginError ? (
        <div className="inline-error" role="alert">
          {loginError}
        </div>
      ) : null}

      <label>
        Username
        <input
          autoComplete="username"
          required
          maxLength={256}
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />
      </label>

      <label>
        Password
        <input
          autoComplete="current-password"
          required
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </label>

      <div className="login-actions">
        <button type="submit" className="primary-button" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </div>
    </form>
  )
}

function ContactEditor({
  editor,
  addressBookHref,
  onCancel,
  onSaved,
}: {
  editor: Exclude<EditorState, null>
  addressBookHref: string
  onCancel: () => void
  onSaved: () => void
}) {
  const contact = editor.mode === 'edit' ? editor.contact : null
  const [name, setName] = useState(contact?.formatted_name ?? '')
  const [emails, setEmails] = useState(contact?.emails.join('\n') ?? '')
  const [phones, setPhones] = useState(contact?.phones.join('\n') ?? '')
  const [busy, setBusy] = useState(false)
  const [mutationError, setMutationError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setMutationError('')

    const payload: ContactWritePayload = {
      formatted_name: name.trim(),
      emails: splitLines(emails),
      phones: splitLines(phones),
    }

    if (!payload.formatted_name) {
      setMutationError('A contact name is required.')
      return
    }

    setBusy(true)

    try {
      if (contact) {
        if (!contact.etag) {
          throw new Error('This contact has no ETag and cannot be updated safely.')
        }
        await updateContact(contact.href, contact.etag, payload)
      } else {
        await createContact(addressBookHref, payload)
      }

      onSaved()
    } catch (caught) {
      setMutationError(
        caught instanceof Error ? caught.message : 'Unable to save contact',
      )
    } finally {
      setBusy(false)
    }
  }

  async function removeContact() {
    if (!contact) {
      return
    }

    if (!contact.etag) {
      setMutationError('This contact has no ETag and cannot be deleted safely.')
      return
    }

    if (!window.confirm(`Delete ${contact.formatted_name}?`)) {
      return
    }

    setBusy(true)
    setMutationError('')

    try {
      await deleteContact(contact.href, contact.etag)
      onSaved()
    } catch (caught) {
      setMutationError(
        caught instanceof Error ? caught.message : 'Unable to delete contact',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="editor-card" onSubmit={submit}>
      <div className="editor-heading">
        <div>
          <p className="eyebrow">CardDAV</p>
          <h3>{contact ? 'Edit contact' : 'Create contact'}</h3>
        </div>
        <button type="button" className="text-button" onClick={onCancel}>
          Close
        </button>
      </div>

      {mutationError ? (
        <div className="inline-error" role="alert">
          {mutationError}
        </div>
      ) : null}

      <label>
        Name
        <input
          required
          maxLength={512}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </label>

      <div className="editor-grid">
        <label>
          Email addresses
          <textarea
            rows={3}
            placeholder="One email address per line"
            value={emails}
            onChange={(event) => setEmails(event.target.value)}
          />
        </label>
        <label>
          Phone numbers
          <textarea
            rows={3}
            placeholder="One phone number per line"
            value={phones}
            onChange={(event) => setPhones(event.target.value)}
          />
        </label>
      </div>

      <div className="editor-actions">
        {contact ? (
          <button
            type="button"
            className="danger-button"
            disabled={busy}
            onClick={() => void removeContact()}
          >
            Delete
          </button>
        ) : (
          <span />
        )}

        <div>
          <button
            type="button"
            className="secondary-button"
            disabled={busy}
            onClick={onCancel}
          >
            Cancel
          </button>
          <button type="submit" className="primary-button" disabled={busy}>
            {busy ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </form>
  )
}

function splitLines(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}
