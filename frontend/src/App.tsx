import { useEffect, useState, type FormEvent } from 'react'
import { createNote, deleteNote, getVersion, listNotes, updateNote, type Note } from './api'
import './App.css'

const dateFormat = new Intl.DateTimeFormat('hu-HU', { dateStyle: 'medium', timeStyle: 'short' })

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Ismeretlen hiba'
}

function App() {
  const [notes, setNotes] = useState<Note[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [version, setVersion] = useState<string | null>(null)

  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    listNotes()
      .then(setNotes)
      .catch((e: unknown) => setError(errorMessage(e)))
      .finally(() => setLoading(false))

    getVersion()
      .then(setVersion)
      .catch(() => setVersion(null))
  }, [])

  function resetForm() {
    setTitle('')
    setBody('')
    setEditingId(null)
  }

  function startEdit(note: Note) {
    setEditingId(note.id)
    setTitle(note.title)
    setBody(note.body)
    setError(null)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!title.trim()) return

    setSaving(true)
    setError(null)
    try {
      if (editingId === null) {
        const created = await createNote({ title, body })
        setNotes((current) => [...current, created])
      } else {
        const updated = await updateNote(editingId, { title, body })
        setNotes((current) => current.map((n) => (n.id === updated.id ? updated : n)))
      }
      resetForm()
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: number) {
    setError(null)
    try {
      await deleteNote(id)
      setNotes((current) => current.filter((n) => n.id !== id))
      if (editingId === id) resetForm()
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  return (
    <main className="page">
      <header>
        <h1>Jegyzetek</h1>
      </header>

      <form className="card form" onSubmit={handleSubmit}>
        <label>
          Cím
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={200}
            required
          />
        </label>
        <label>
          Szöveg
          <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={3} />
        </label>
        <div className="actions">
          <button type="submit" disabled={saving || !title.trim()}>
            {editingId === null ? 'Hozzáadás' : 'Mentés'}
          </button>
          {editingId !== null && (
            <button type="button" className="secondary" onClick={resetForm}>
              Mégse
            </button>
          )}
        </div>
      </form>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <p className="muted">Betöltés…</p>
      ) : notes.length === 0 ? (
        <p className="muted">Még nincs jegyzet.</p>
      ) : (
        <ul className="notes">
          {notes.map((note) => (
            <li key={note.id} className={`card note${editingId === note.id ? ' editing' : ''}`}>
              <div className="note-head">
                <h2>{note.title}</h2>
                <time dateTime={note.created_at}>
                  {dateFormat.format(new Date(note.created_at))}
                </time>
              </div>
              {note.body && <p>{note.body}</p>}
              <div className="actions">
                <button type="button" className="secondary" onClick={() => startEdit(note)}>
                  Szerkesztés
                </button>
                <button type="button" className="danger" onClick={() => handleDelete(note.id)}>
                  Törlés
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <footer className="muted">Backend verzió: {version ?? 'nem elérhető'}</footer>
    </main>
  )
}

export default App
