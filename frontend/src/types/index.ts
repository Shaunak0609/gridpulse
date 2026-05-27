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
  related_session_id: number | null
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

export interface DashboardLatestWeatherSample {
  air_temperature: number | null
  track_temperature: number | null
  humidity: number | null       // percentage 0–100, rounded to whole number
  rainfall: boolean | null
  wind_speed: number | null     // metres per second
  wind_direction: number | null // degrees: 0 = N, 90 = E, 180 = S, 270 = W
}

export interface DashboardWeatherSummary {
  air_min: number | null
  air_max: number | null
  track_min: number | null
  track_max: number | null
  had_rain: boolean
  sample_count: number
  latest_sample: DashboardLatestWeatherSample | null
}

// ─── Strategy Dashboard ──────────────────────────────────────────────────────
// Mirrors app/schemas/strategy_dashboard.py — StrategyDashboardResponse

export interface StrategyCompoundUsage {
  compound: string
  stint_count: number
  driver_count: number
  avg_stint_laps: number | null
}

export interface StrategyStintSummary {
  stint_number: number | null
  compound: string | null
  lap_start: number | null
  lap_end: number | null
  tyre_age_at_start: number | null
  stint_laps: number | null
}

export interface StrategyDriverSummary {
  driver_number: number
  driver_name: string
  stop_count: number
  compound_sequence: string[]
  stints: StrategyStintSummary[]
  longest_stint_laps: number | null
  is_favourite: boolean
}

export interface StrategyPitWindow {
  window_number: number
  lap_min: number
  lap_max: number
  driver_count: number
}

export interface StrategyRCEvent {
  lap_number: number | null
  flag: string | null
  message: string
}

export interface StrategyRaceControlContext {
  events: StrategyRCEvent[]
  total_strategy_events: number
}

export interface StrategyWeatherContext {
  had_rain: boolean
  wet_tyre_drivers: string[]
  air_min: number | null
  air_max: number | null
  track_min: number | null
  track_max: number | null
  sample_count: number
  latest_air_temp: number | null
  latest_track_temp: number | null
  latest_rainfall: boolean | null
}

export interface StrategyDashboard {
  session_id: number
  session_name: string
  session_type: string
  race_name: string
  circuit_short_name: string | null
  country_name: string | null
  start_time: string | null
  is_synced: boolean
  has_stint_data: boolean
  has_lap_data: boolean
  has_rc_data: boolean
  has_weather_data: boolean
  compound_usage: StrategyCompoundUsage[]
  driver_strategies: StrategyDriverSummary[]
  // JSON object keys are always strings; backend int keys (1, 2) become "1", "2"
  stop_count_groups: Record<string, string[]>
  pit_windows: StrategyPitWindow[]
  race_control: StrategyRaceControlContext
  weather: StrategyWeatherContext | null
  insights: string[]
}

// ─── Advanced Analytics ──────────────────────────────────────────────────────
// Mirrors app/schemas/analytics.py

export interface AnalyticsDriverSummary {
  driver_number: number
  driver_name: string
  lap_count: number
  timed_lap_count: number
  fastest_lap: number | null
  average_lap: number | null
  best_s1: number | null
  best_s2: number | null
  best_s3: number | null
  is_favourite: boolean
}

export interface AnalyticsCompoundUsage {
  compound: string
  avg_lap_time: number | null
  fastest_lap_time: number | null
  driver_count: number
  sample_lap_count: number
}

export interface AnalyticsStintEntry {
  driver_number: number
  driver_name: string
  stint_number: number | null
  compound: string | null
  lap_start: number | null
  lap_end: number | null
  avg_lap_time: number | null
  laps_counted: number
  is_favourite: boolean
}

export interface AnalyticsTireSummary {
  compound_pace: AnalyticsCompoundUsage[]
  stint_pace: AnalyticsStintEntry[]
  has_compound_pace: boolean
}

export interface AnalyticsTeammateComparison {
  team_name: string
  driver_a_number: number
  driver_a_name: string
  driver_a_fastest: number | null
  driver_a_avg: number | null
  driver_b_number: number
  driver_b_name: string
  driver_b_fastest: number | null
  driver_b_avg: number | null
  fastest_delta: number | null
  avg_delta: number | null
}

export interface AnalyticsRaceContext {
  rc_total: number
  safety_car_laps: number[]
  red_flag_laps: number[]
}

export interface AnalyticsWeather {
  air_temperature: number | null
  track_temperature: number | null
  humidity: number | null
  rainfall: boolean | null
  wind_speed: number | null
}

export interface SessionAnalytics {
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
  has_compound_pace: boolean
  session_fastest_lap: number | null
  session_fastest_driver: string | null
  session_avg_lap: number | null
  driver_pace: AnalyticsDriverSummary[]
  tire_analytics: AnalyticsTireSummary
  teammate_comparisons: AnalyticsTeammateComparison[]
  race_context: AnalyticsRaceContext
  weather: AnalyticsWeather | null
  data_note: string | null
}

export interface DriverComparisonAnalytics {
  driver_a: AnalyticsDriverSummary
  driver_b: AnalyticsDriverSummary
  fastest_delta: number | null
  avg_delta: number | null
  driver_a_stints: AnalyticsStintEntry[]
  driver_b_stints: AnalyticsStintEntry[]
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
