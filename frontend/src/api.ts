// A backend /notes végpontjainak típusos kliense. Minden hívás relatív /api/
// útvonalra megy: a fürtben az nginx, fejlesztéskor a Vite továbbítja.

export interface Note {
  id: number
  title: string
  body: string
  created_at: string
}

export interface NoteInput {
  title: string
  body: string
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })

  if (!response.ok) {
    // A backend hibánál {"error": "..."} alakú JSON-t ad; ha mégsem (pl. az
    // nginx 502-t ad, mert a backend nem fut), a státuszkódból írunk üzenetet.
    const payload = (await response.json().catch(() => null)) as { error?: string } | null
    throw new ApiError(response.status, payload?.error ?? `HTTP ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export async function listNotes(): Promise<Note[]> {
  const data = await request<{ notes: Note[] }>('/notes')
  return data.notes
}

export function createNote(input: NoteInput): Promise<Note> {
  return request<Note>('/notes', { method: 'POST', body: JSON.stringify(input) })
}

export function updateNote(id: number, input: NoteInput): Promise<Note> {
  return request<Note>(`/notes/${id}`, { method: 'PUT', body: JSON.stringify(input) })
}

export function deleteNote(id: number): Promise<void> {
  return request<void>(`/notes/${id}`, { method: 'DELETE' })
}

// A backend a buildkor beégetett commit SHA-t adja vissza (APP_VERSION).
// A felületen megjelenítve látszik, melyik verzió fut éppen a fürtben.
export async function getVersion(): Promise<string> {
  const data = await request<{ version: string }>('/version')
  return data.version
}
