import { useEffect, useMemo, useState, type FormEvent } from 'react'

import {
  ApiError,
  createContact,
  deleteContact,
  getAddressBooks,
  getAuthSession,
  getCardDavStatus,
  getContact,
  getContacts,
  getHealth,
  login,
  logout,
  updateContact,
  type AddressBook,
  type AuthSession,
  type ContactDetail,
  type ContactSummary,
  type ContactWritePayload,
  type Health,
  type PostalAddress,
  type StructuredName,
} from './api.ts'

import './milestone2.css'

type LoadState = 'idle' | 'loading' | 'ready' | 'error'
type FilterMode = 'all' | 'favorites'
type EditorState =
  | { mode: 'create' }
  | { mode: 'edit'; contact: ContactDetail }
  | null

const EMPTY_STRUCTURED_NAME: StructuredName = {
  family_name: '',
  given_name: '',
  additional_names: '',
  honorific_prefixes: '',
  honorific_suffixes: '',
}

const EMPTY_ADDRESS: PostalAddress = {
  types: [],
  po_box: '',
  extended_address: '',
  street_address: '',
  locality: '',
  region: '',
  postal_code: '',
  country: '',
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [writeEnabled, setWriteEnabled] = useState(false)
  const [authSession, setAuthSession] = useState<AuthSession | null>(null)
  const [addressBooks, setAddressBooks] = useState<AddressBook[]>([])
  const [selectedBook, setSelectedBook] = useState<string>('')
  const [contacts, setContacts] = useState<ContactSummary[]>([])
  const [selectedContact, setSelectedContact] = useState<ContactDetail | null>(null)
  const [query, setQuery] = useState('')
  const [filterMode, setFilterMode] = useState<FilterMode>('all')
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
        setSelectedContact(null)
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

    return contacts.filter((contact) => {
      if (filterMode === 'favorites' && !contact.favorite) {
        return false
      }

      if (!needle) {
        return true
      }

      const haystack = [
        contact.formatted_name,
        contact.organization ?? '',
        contact.title ?? '',
        ...contact.categories,
        ...contact.emails,
        ...contact.phones,
      ]
        .join(' ')
        .toLocaleLowerCase()

      return haystack.includes(needle)
    })
  }, [contacts, filterMode, query])

  const favoriteCount = useMemo(
    () => contacts.filter((contact) => contact.favorite).length,
    [contacts],
  )

  function resetAuthenticatedState() {
    setAuthSession({ authenticated: false, username: null, expires_at: null })
    setAddressBooks([])
    setSelectedBook('')
    setContacts([])
    setSelectedContact(null)
    setEditor(null)
    setQuery('')
    setFilterMode('all')
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
    setSelectedContact(null)
    setEditor(null)
  }

  async function openContact(contact: ContactSummary) {
    setError('')
    try {
      const detail = await getContact(contact.href)
      setSelectedContact(detail)
      setEditor(null)
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        resetAuthenticatedState()
        setError('Your session expired. Sign in again to continue.')
        return
      }
      setError(caught instanceof Error ? caught.message : 'Unable to load contact')
    }
  }

  async function beginEdit(contact: ContactSummary) {
    if (!writeEnabled) {
      return
    }

    setError('')
    try {
      const detail = await getContact(contact.href)
      setSelectedContact(null)
      setEditor({ mode: 'edit', contact: detail })
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        resetAuthenticatedState()
        setError('Your session expired. Sign in again to continue.')
        return
      }
      setError(caught instanceof Error ? caught.message : 'Unable to load contact')
    }
  }

  function mutationCompleted() {
    setEditor(null)
    setSelectedContact(null)
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
            onClick={() => {
              setSelectedContact(null)
              setEditor({ mode: 'create' })
            }}
          >
            + Create contact
          </button>

          <nav aria-label="Contact navigation" className="contact-navigation">
            <button
              type="button"
              className={`nav-item ${filterMode === 'all' ? 'active' : ''}`}
              onClick={() => setFilterMode('all')}
            >
              Contacts
              <span>{contacts.length}</span>
            </button>
            <button
              type="button"
              className={`nav-item ${filterMode === 'favorites' ? 'active' : ''}`}
              onClick={() => setFilterMode('favorites')}
            >
              Favorites
              <span>{favoriteCount}</span>
            </button>
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
              <p className="eyebrow">CardDAV · Milestone 4</p>
              <h2>{filterMode === 'favorites' ? 'Favorites' : 'Contacts'}</h2>
            </div>
            <input
              aria-label="Search contacts"
              className="search"
              type="search"
              placeholder="Search names, organizations, categories…"
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
                Reads and expanded contact details are available, but mutations remain
                blocked until <code>CARDDAV_WRITE_ENABLED=true</code> is set in an approved
                test or production environment.
              </p>
            </div>
          ) : null}

          {error ? (
            <div className="notice error" role="alert">
              <h3>Unable to complete the request</h3>
              <p>{error}</p>
            </div>
          ) : null}

          {selectedContact ? (
            <ContactDetailCard
              contact={selectedContact}
              writeEnabled={writeEnabled}
              onClose={() => setSelectedContact(null)}
              onEdit={() => {
                setEditor({ mode: 'edit', contact: selectedContact })
                setSelectedContact(null)
              }}
            />
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
              <div className="empty-state">
                {filterMode === 'favorites' ? 'No favorite contacts found.' : 'No contacts found.'}
              </div>
            ) : (
              filteredContacts.map((contact) => (
                <article className="contact-row" key={contact.href}>
                  <div className="name-cell">
                    <div className="avatar" aria-hidden="true">
                      {initials(contact.formatted_name)}
                    </div>
                    <div className="contact-primary">
                      <strong>
                        {contact.favorite ? <span className="favorite-star">★</span> : null}
                        {contact.formatted_name}
                      </strong>
                      {contact.organization || contact.title ? (
                        <small>
                          {[contact.title, contact.organization].filter(Boolean).join(' · ')}
                        </small>
                      ) : null}
                    </div>
                  </div>
                  <span>{contact.emails[0] ?? '—'}</span>
                  <span>{contact.phones[0] ?? '—'}</span>
                  <span className="row-actions">
                    <button
                      type="button"
                      className="row-action"
                      onClick={() => void openContact(contact)}
                    >
                      View
                    </button>
                    <button
                      type="button"
                      className="row-action"
                      disabled={!writeEnabled || !contact.etag}
                      onClick={() => void beginEdit(contact)}
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
        <p className="eyebrow">Secure session</p>
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

function ContactDetailCard({
  contact,
  writeEnabled,
  onClose,
  onEdit,
}: {
  contact: ContactDetail
  writeEnabled: boolean
  onClose: () => void
  onEdit: () => void
}) {
  const displayPhoto = contact.photo?.startsWith('data:image/') ? contact.photo : null

  return (
    <section className="detail-card" aria-label={`Contact details for ${contact.formatted_name}`}>
      <div className="editor-heading">
        <div className="detail-heading-copy">
          {displayPhoto ? (
            <img className="detail-photo" src={displayPhoto} alt="" />
          ) : (
            <div className="avatar detail-avatar" aria-hidden="true">
              {initials(contact.formatted_name)}
            </div>
          )}
          <div>
            <p className="eyebrow">Contact details</p>
            <h3>
              {contact.favorite ? <span className="favorite-star">★</span> : null}
              {contact.formatted_name}
            </h3>
            {contact.title || contact.organization ? (
              <p className="muted">
                {[contact.title, contact.organization].filter(Boolean).join(' · ')}
              </p>
            ) : null}
          </div>
        </div>
        <div className="detail-actions">
          <button type="button" className="text-button" onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className="primary-button"
            disabled={!writeEnabled || !contact.etag}
            onClick={onEdit}
          >
            Edit
          </button>
        </div>
      </div>

      <div className="detail-grid">
        <DetailGroup title="Email" values={contact.emails} />
        <DetailGroup title="Phone" values={contact.phones} />
        <DetailGroup title="Websites" values={contact.websites} />
        <DetailGroup title="Categories" values={contact.categories} />
        {contact.birthday ? <DetailValue title="Birthday" value={contact.birthday} /> : null}
        {contact.addresses.map((address, index) => (
          <DetailValue
            key={`${address.street_address}-${index}`}
            title={`Address${address.types.length ? ` · ${address.types.join(', ')}` : ''}`}
            value={formatAddress(address)}
          />
        ))}
      </div>

      {contact.note ? (
        <div className="detail-note">
          <strong>Notes</strong>
          <p>{contact.note}</p>
        </div>
      ) : null}

      {contact.has_photo && !displayPhoto ? (
        <p className="muted privacy-note">
          This contact has a photo reference. External photo loading is disabled by default.
        </p>
      ) : null}
    </section>
  )
}

function DetailGroup({ title, values }: { title: string; values: string[] }) {
  if (values.length === 0) {
    return null
  }

  return <DetailValue title={title} value={values.join('\n')} />
}

function DetailValue({ title, value }: { title: string; value: string }) {
  return (
    <div className="detail-value">
      <strong>{title}</strong>
      <span>{value}</span>
    </div>
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
  const [structuredName, setStructuredName] = useState<StructuredName>(
    contact?.structured_name ?? { ...EMPTY_STRUCTURED_NAME },
  )
  const [emails, setEmails] = useState(contact?.emails.join('\n') ?? '')
  const [phones, setPhones] = useState(contact?.phones.join('\n') ?? '')
  const [organization, setOrganization] = useState(contact?.organization ?? '')
  const [title, setTitle] = useState(contact?.title ?? '')
  const [addresses, setAddresses] = useState<PostalAddress[]>(
    contact?.addresses.length ? contact.addresses : [],
  )
  const [birthday, setBirthday] = useState(contact?.birthday ?? '')
  const [websites, setWebsites] = useState(contact?.websites.join('\n') ?? '')
  const [note, setNote] = useState(contact?.note ?? '')
  const [categories, setCategories] = useState(contact?.categories.join('\n') ?? '')
  const [favorite, setFavorite] = useState(contact?.favorite ?? false)
  const [photo, setPhoto] = useState(contact?.photo ?? '')
  const [busy, setBusy] = useState(false)
  const [mutationError, setMutationError] = useState('')

  function updateStructuredName(field: keyof StructuredName, value: string) {
    setStructuredName((current) => ({ ...current, [field]: value }))
  }

  function addAddress() {
    setAddresses((current) => [...current, { ...EMPTY_ADDRESS, types: [] }])
  }

  function removeAddress(index: number) {
    setAddresses((current) => current.filter((_, itemIndex) => itemIndex !== index))
  }

  function updateAddressField(
    index: number,
    field: Exclude<keyof PostalAddress, 'types'>,
    value: string,
  ) {
    setAddresses((current) =>
      current.map((address, itemIndex) =>
        itemIndex === index ? { ...address, [field]: value } : address,
      ),
    )
  }

  function updateAddressTypes(index: number, value: string) {
    setAddresses((current) =>
      current.map((address, itemIndex) =>
        itemIndex === index
          ? {
              ...address,
              types: value
                .split(',')
                .map((item) => item.trim())
                .filter(Boolean),
            }
          : address,
      ),
    )
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setMutationError('')

    const payload: ContactWritePayload = {
      formatted_name: name.trim(),
      structured_name: trimStructuredName(structuredName),
      emails: splitLines(emails),
      phones: splitLines(phones),
      organization: emptyToNull(organization),
      title: emptyToNull(title),
      addresses: addresses.map(trimAddress).filter(addressHasValue),
      birthday: emptyToNull(birthday),
      websites: splitLines(websites),
      note: emptyToNull(note),
      categories: splitLines(categories),
      favorite,
      photo: emptyToNull(photo),
    }

    if (!payload.formatted_name) {
      setMutationError('A contact display name is required.')
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
    <form className="editor-card expanded-editor" onSubmit={submit}>
      <div className="editor-heading">
        <div>
          <p className="eyebrow">CardDAV · Expanded model</p>
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

      <fieldset className="editor-section">
        <legend>Identity</legend>
        <label>
          Display name
          <input
            required
            maxLength={512}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>

        <div className="editor-grid name-grid">
          <label>
            Given name
            <input
              maxLength={512}
              value={structuredName.given_name}
              onChange={(event) => updateStructuredName('given_name', event.target.value)}
            />
          </label>
          <label>
            Family name
            <input
              maxLength={512}
              value={structuredName.family_name}
              onChange={(event) => updateStructuredName('family_name', event.target.value)}
            />
          </label>
          <label>
            Additional names
            <input
              maxLength={512}
              value={structuredName.additional_names}
              onChange={(event) => updateStructuredName('additional_names', event.target.value)}
            />
          </label>
          <label>
            Honorific prefix
            <input
              maxLength={512}
              value={structuredName.honorific_prefixes}
              onChange={(event) => updateStructuredName('honorific_prefixes', event.target.value)}
            />
          </label>
          <label>
            Honorific suffix
            <input
              maxLength={512}
              value={structuredName.honorific_suffixes}
              onChange={(event) => updateStructuredName('honorific_suffixes', event.target.value)}
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="editor-section">
        <legend>Communication</legend>
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
          <label>
            Websites
            <textarea
              rows={3}
              placeholder="One URL per line"
              value={websites}
              onChange={(event) => setWebsites(event.target.value)}
            />
          </label>
          <label>
            Categories
            <textarea
              rows={3}
              placeholder="One category per line"
              value={categories}
              onChange={(event) => setCategories(event.target.value)}
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="editor-section">
        <legend>Work and personal details</legend>
        <div className="editor-grid">
          <label>
            Organization
            <input
              maxLength={1024}
              value={organization}
              onChange={(event) => setOrganization(event.target.value)}
            />
          </label>
          <label>
            Title
            <input
              maxLength={1024}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>
          <label>
            Birthday
            <input
              placeholder="YYYY-MM-DD"
              maxLength={64}
              value={birthday}
              onChange={(event) => setBirthday(event.target.value)}
            />
          </label>
          <label>
            Photo URI
            <input
              placeholder="data:image/... or approved URI"
              value={photo}
              onChange={(event) => setPhoto(event.target.value)}
            />
          </label>
        </div>
        <label className="favorite-toggle">
          <input
            type="checkbox"
            checked={favorite}
            onChange={(event) => setFavorite(event.target.checked)}
          />
          Favorite contact
        </label>
      </fieldset>

      <fieldset className="editor-section">
        <legend>Postal addresses</legend>
        <div className="address-list">
          {addresses.map((address, index) => (
            <div className="address-editor" key={index}>
              <div className="address-editor-heading">
                <strong>Address {index + 1}</strong>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => removeAddress(index)}
                >
                  Remove
                </button>
              </div>
              <div className="editor-grid">
                <label>
                  Types
                  <input
                    placeholder="home, work"
                    value={address.types.join(', ')}
                    onChange={(event) => updateAddressTypes(index, event.target.value)}
                  />
                </label>
                <label>
                  Street
                  <input
                    value={address.street_address}
                    onChange={(event) => updateAddressField(index, 'street_address', event.target.value)}
                  />
                </label>
                <label>
                  Extended address
                  <input
                    value={address.extended_address}
                    onChange={(event) => updateAddressField(index, 'extended_address', event.target.value)}
                  />
                </label>
                <label>
                  P.O. box
                  <input
                    value={address.po_box}
                    onChange={(event) => updateAddressField(index, 'po_box', event.target.value)}
                  />
                </label>
                <label>
                  City / locality
                  <input
                    value={address.locality}
                    onChange={(event) => updateAddressField(index, 'locality', event.target.value)}
                  />
                </label>
                <label>
                  State / region
                  <input
                    value={address.region}
                    onChange={(event) => updateAddressField(index, 'region', event.target.value)}
                  />
                </label>
                <label>
                  Postal code
                  <input
                    value={address.postal_code}
                    onChange={(event) => updateAddressField(index, 'postal_code', event.target.value)}
                  />
                </label>
                <label>
                  Country
                  <input
                    value={address.country}
                    onChange={(event) => updateAddressField(index, 'country', event.target.value)}
                  />
                </label>
              </div>
            </div>
          ))}
        </div>
        <button type="button" className="secondary-button" onClick={addAddress}>
          + Add address
        </button>
      </fieldset>

      <fieldset className="editor-section">
        <legend>Notes</legend>
        <label>
          Notes
          <textarea
            rows={5}
            maxLength={10000}
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
        </label>
      </fieldset>

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

function emptyToNull(value: string): string | null {
  const normalized = value.trim()
  return normalized || null
}

function trimStructuredName(value: StructuredName): StructuredName {
  return {
    family_name: value.family_name.trim(),
    given_name: value.given_name.trim(),
    additional_names: value.additional_names.trim(),
    honorific_prefixes: value.honorific_prefixes.trim(),
    honorific_suffixes: value.honorific_suffixes.trim(),
  }
}

function trimAddress(value: PostalAddress): PostalAddress {
  return {
    types: value.types.map((item) => item.trim()).filter(Boolean),
    po_box: value.po_box.trim(),
    extended_address: value.extended_address.trim(),
    street_address: value.street_address.trim(),
    locality: value.locality.trim(),
    region: value.region.trim(),
    postal_code: value.postal_code.trim(),
    country: value.country.trim(),
  }
}

function addressHasValue(value: PostalAddress): boolean {
  return [
    value.po_box,
    value.extended_address,
    value.street_address,
    value.locality,
    value.region,
    value.postal_code,
    value.country,
  ].some(Boolean)
}

function formatAddress(value: PostalAddress): string {
  return [
    value.po_box,
    value.extended_address,
    value.street_address,
    value.locality,
    value.region,
    value.postal_code,
    value.country,
  ]
    .filter(Boolean)
    .join(', ')
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}
