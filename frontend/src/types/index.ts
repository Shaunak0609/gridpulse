export interface Driver {
  id: number
  code: string
  full_name: string
  nationality: string | null
  driver_number: number | null
  team: string | null
}

export interface Team {
  id: number
  name: string
  constructor_name: string
  base: string | null
}

export interface Race {
  id: number
  season: number
  round: number
  name: string
  circuit_name: string | null
  country: string | null
  start_date: string | null
}

export interface DriverStanding {
  position: number
  driver: string
  team: string
  points: number
  wins: number
  podiums: number
}

export interface AuthUser {
  id: number
  email: string
  username: string | null
  timezone: string | null
}

export interface SignupPayload {
  email: string
  password: string
  username?: string
  timezone?: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}
