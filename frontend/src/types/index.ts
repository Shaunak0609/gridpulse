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
  auth_provider: string
  profile_picture_url: string | null
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

export interface Session {
  id: number
  race_id: number
  session_type: string
  session_name: string
  start_time: string | null
  end_time: string | null
  timezone: string | null
}

export interface Reminder {
  id: number
  user_id: number
  race_id: number | null
  session_id: number | null
  title: string
  reminder_time: string
  sent: boolean
  created_at: string
}

export interface ReminderCreate {
  title: string
  reminder_time: string
  race_id?: number
  session_id?: number
}

export interface FavoriteDriver {
  id: number
  user_id: number
  driver_id: number
  created_at: string
  driver: {
    id: number
    code: string
    full_name: string
    nationality: string | null
    driver_number: number | null
    team: {
      id: number
      name: string
      constructor_name: string
      base: string | null
    } | null
  }
}

export interface FavoriteTeam {
  id: number
  user_id: number
  team_id: number
  created_at: string
  team: {
    id: number
    name: string
    constructor_name: string
    base: string | null
  }
}

export interface Dashboard {
  user: {
    id: number
    email: string
    username: string | null
  }
  favorite_drivers: FavoriteDriver[]
  favorite_teams: FavoriteTeam[]
  upcoming_sessions: Session[]
  upcoming_reminders: Reminder[]
  recent_notifications: Notification[]
}

export interface EmailPreferences {
  email_notifications_enabled: boolean
  calendar_email_reminders_enabled: boolean
  favorite_driver_email_alerts_enabled: boolean
}

export interface NotificationPreferences {
  favorite_driver_notifications_enabled: boolean
  favorite_driver_email_alerts_enabled: boolean
}

export interface Notification {
  id: number
  user_id: number
  type: string
  title: string
  message: string | null
  read: boolean
  created_at: string
  related_race_id: number | null
  related_driver_id: number | null
}
