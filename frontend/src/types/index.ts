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

export interface AIResponse {
  id: number
  prompt: string
  response: string | null
  request_type: string
  created_at: string
}

export interface AIHistoryItem {
  id: number
  prompt: string
  response: string | null
  request_type: string
  created_at: string
  model_name: string | null
}

export interface AIUsage {
  requests_today: number
  daily_limit: number
  remaining: number
}

export interface SessionDetail {
  id: number
  race_id: number
  session_type: string
  session_name: string
  start_time: string | null
  end_time: string | null
  timezone: string | null
  circuit_short_name: string | null
  country_name: string | null
  openf1_session_key: number | null
  race_name: string | null
}

export interface Lap {
  id: number
  session_id: number
  driver_number: number
  lap_number: number
  lap_duration: number | null
  duration_sector_1: number | null
  duration_sector_2: number | null
  duration_sector_3: number | null
  is_pit_out_lap: boolean
  date_start: string | null
}

export interface Stint {
  id: number
  session_id: number
  driver_number: number
  stint_number: number | null
  compound: string | null
  lap_start: number | null
  lap_end: number | null
  tyre_age_at_start: number | null
}

export interface RaceControlMessage {
  id: number
  session_id: number
  date: string | null
  lap_number: number | null
  category: string | null
  message: string
  flag: string | null
  scope: string | null
  sector: number | null
  driver_number: number | null
}

export interface WeatherSample {
  id: number
  session_id: number
  date: string | null
  air_temperature: number | null
  track_temperature: number | null
  humidity: number | null
  rainfall: boolean | null
  wind_speed: number | null
  wind_direction: number | null
}

// ─── Session Dashboard ───────────────────────────────────────────────────────
// Mirrors app/schemas/session_dashboard.py — SessionDashboardResponse

export interface DashboardLapStats {
  total_rows: number
  driver_count: number
  max_lap: number | null
}

export interface DashboardDriverSummary {
  position: number
  driver_number: number
  driver_name: string
  max_lap: number
  laps_behind: number
  is_favourite: boolean
}

export interface DashboardStintEntry {
  stint_number: number | null
  compound: string | null
  lap_start: number | null
  lap_end: number | null
  tyre_age_at_start: number | null
}

export interface DashboardStintSummary {
  driver_number: number
  driver_name: string
  stints: DashboardStintEntry[]
  is_favourite: boolean
}

export interface DashboardKeyEvent {
  label: string
  lap_number: number | null
}

export interface DashboardRCMessage {
  lap_number: number | null
  flag: string | null
  message: string
}

export interface DashboardRaceControlSummary {
  key_events: DashboardKeyEvent[]
  messages: DashboardRCMessage[]
  total: number
  blue_flag_count: number
  omitted_count: number
}

export interface DashboardWeatherSummary {
  air_min: number | null
  air_max: number | null
  track_min: number | null
  track_max: number | null
  had_rain: boolean
  sample_count: number
}

export interface SessionDashboard {
  session_id: number
  session_name: string
  session_type: string
  race_name: string
  circuit_short_name: string | null
  country_name: string | null
  start_time: string | null
  is_synced: boolean
  has_lap_data: boolean
  has_stint_data: boolean
  has_rc_data: boolean
  has_weather_data: boolean
  lap_stats: DashboardLapStats
  finishing_order: DashboardDriverSummary[]
  compound_overview: Record<string, number>
  stint_summary: DashboardStintSummary[]
  race_control: DashboardRaceControlSummary
  weather: DashboardWeatherSummary | null
}
