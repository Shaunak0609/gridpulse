import type { AuthUser, Driver, DriverStanding, LoginPayload, Race, SignupPayload, Team, TokenResponse } from '../types'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// ─── Helpers ────────────────────────────────────────────────────────────────

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
  return res.json() as Promise<T>
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  // Parse the response body regardless of status so we can surface the
  // backend's error message (e.g. "An account with that email already exists.")
  const data = await res.json()
  if (!res.ok) {
    throw new Error(data?.detail ?? `Request failed with status ${res.status}`)
  }
  return data as T
}

// ─── F1 endpoints ───────────────────────────────────────────────────────────

export const getDrivers = () => get<Driver[]>('/drivers')
export const getDriver = (id: number) => get<Driver>(`/drivers/${id}`)
export const getTeams = () => get<Team[]>('/teams')
export const getCalendar = () => get<Race[]>('/calendar')
export const getDriverStandings = () => get<DriverStanding[]>('/standings/drivers')

// ─── Auth endpoints ──────────────────────────────────────────────────────────

export const signup = (payload: SignupPayload) =>
  post<AuthUser>('/auth/signup', payload)

export const login = (payload: LoginPayload) =>
  post<TokenResponse>('/auth/login', payload)

export const getCurrentUser = (token: string) => {
  return fetch(`${API_BASE}/users/me`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to fetch user')
    return data as AuthUser
  })
}
