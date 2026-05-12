import type { Driver, DriverStanding, Race, Team } from '../types'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
  return res.json() as Promise<T>
}

export const getDrivers = () => get<Driver[]>('/drivers')
export const getDriver = (id: number) => get<Driver>(`/drivers/${id}`)
export const getTeams = () => get<Team[]>('/teams')
export const getCalendar = () => get<Race[]>('/calendar')
export const getDriverStandings = () => get<DriverStanding[]>('/standings/drivers')
