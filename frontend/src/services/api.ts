import type { AIHistoryItem, AIResponse, AIUsage, AuthUser, Dashboard, Driver, DriverStanding, EmailPreferences, FavoriteDriver, FavoriteTeam, LoginPayload, Notification, NotificationPreferences, Race, Reminder, ReminderCreate, Session, SignupPayload, Team, TokenResponse } from '../types'

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

// ─── Session endpoints ───────────────────────────────────────────────────────

export const getUpcomingSessions = (limit = 10) =>
  get<Session[]>(`/sessions/upcoming?limit=${limit}`)

export const getRaceSessions = (raceId: number) =>
  get<Session[]>(`/races/${raceId}/sessions`)

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

// ─── Reminder endpoints ──────────────────────────────────────────────────────

export const getReminders = (token: string): Promise<Reminder[]> =>
  fetch(`${API_BASE}/reminders`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to fetch reminders')
    return data as Reminder[]
  })

export const createReminder = (token: string, payload: ReminderCreate): Promise<Reminder> =>
  fetch(`${API_BASE}/reminders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to create reminder')
    return data as Reminder
  })

export const deleteReminder = (token: string, id: number): Promise<void> =>
  fetch(`${API_BASE}/reminders/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  }).then(res => {
    if (!res.ok) throw new Error('Failed to delete reminder')
  })

// ─── Notification endpoints ──────────────────────────────────────────────────

export const getNotifications = (token: string): Promise<Notification[]> =>
  fetch(`${API_BASE}/notifications`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to fetch notifications')
    return data as Notification[]
  })

export const markNotificationRead = (token: string, id: number): Promise<Notification> =>
  fetch(`${API_BASE}/notifications/${id}/read`, {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}` },
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to mark notification as read')
    return data as Notification
  })

export const deleteNotification = (token: string, id: number): Promise<void> =>
  fetch(`${API_BASE}/notifications/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  }).then(res => {
    if (!res.ok) throw new Error('Failed to delete notification')
  })

// ─── Email preference endpoints ──────────────────────────────────────────────

export const getEmailPreferences = (token: string): Promise<EmailPreferences> =>
  fetch(`${API_BASE}/users/me/email-preferences`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to fetch email preferences')
    return data as EmailPreferences
  })

export const updateEmailPreferences = (
  token: string,
  payload: Partial<EmailPreferences>,
): Promise<EmailPreferences> =>
  fetch(`${API_BASE}/users/me/email-preferences`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to update email preferences')
    return data as EmailPreferences
  })

export const getNotificationPreferences = (token: string): Promise<NotificationPreferences> =>
  fetch(`${API_BASE}/users/me/notification-preferences`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to fetch notification preferences')
    return data as NotificationPreferences
  })

export const updateNotificationPreferences = (
  token: string,
  payload: Partial<NotificationPreferences>,
): Promise<NotificationPreferences> =>
  fetch(`${API_BASE}/users/me/notification-preferences`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to update notification preferences')
    return data as NotificationPreferences
  })

export const sendTestEmail = (token: string): Promise<{ message: string }> =>
  fetch(`${API_BASE}/email/test`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to send test email')
    return data as { message: string }
  })

// ─── Favorite endpoints ──────────────────────────────────────────────────────

export const getFavoriteDrivers = (token: string): Promise<FavoriteDriver[]> =>
  fetch(`${API_BASE}/me/favorites/drivers`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to fetch favourite drivers')
    return data as FavoriteDriver[]
  })

export const addFavoriteDriver = (token: string, driverId: number): Promise<FavoriteDriver> =>
  fetch(`${API_BASE}/me/favorites/drivers/${driverId}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to add favourite driver')
    return data as FavoriteDriver
  })

export const removeFavoriteDriver = (token: string, driverId: number): Promise<void> =>
  fetch(`${API_BASE}/me/favorites/drivers/${driverId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  }).then(res => {
    if (!res.ok) throw new Error('Failed to remove favourite driver')
  })

export const getFavoriteTeams = (token: string): Promise<FavoriteTeam[]> =>
  fetch(`${API_BASE}/me/favorites/teams`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to fetch favourite teams')
    return data as FavoriteTeam[]
  })

export const addFavoriteTeam = (token: string, teamId: number): Promise<FavoriteTeam> =>
  fetch(`${API_BASE}/me/favorites/teams/${teamId}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to add favourite team')
    return data as FavoriteTeam
  })

export const removeFavoriteTeam = (token: string, teamId: number): Promise<void> =>
  fetch(`${API_BASE}/me/favorites/teams/${teamId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  }).then(res => {
    if (!res.ok) throw new Error('Failed to remove favourite team')
  })

// ─── Dashboard endpoint ──────────────────────────────────────────────────────

export const getDashboard = (token: string): Promise<Dashboard> =>
  fetch(`${API_BASE}/me/dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to fetch dashboard')
    return data as Dashboard
  })

// ─── AI Race Assistant endpoints ─────────────────────────────────────────────

export const askAI = (token: string, prompt: string, request_type = 'general'): Promise<AIResponse> =>
  fetch(`${API_BASE}/ai/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ prompt, request_type }),
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to get AI response')
    return data as AIResponse
  })

export const getAIHistory = (token: string): Promise<AIHistoryItem[]> =>
  fetch(`${API_BASE}/ai/history`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to fetch AI history')
    return data as AIHistoryItem[]
  })

export const getAIUsage = (token: string): Promise<AIUsage> =>
  fetch(`${API_BASE}/ai/usage`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(async res => {
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail ?? 'Failed to fetch AI usage')
    return data as AIUsage
  })
