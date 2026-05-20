import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getSessionDashboard } from '../services/api'
import { useAuth } from '../context/AuthContext'
import type {
  SessionDashboard,
  DashboardDriverSummary,
  DashboardStintSummary,
  DashboardKeyEvent,
  DashboardRCMessage,
  DashboardLapStats,
} from '../types'

// ─── Formatters ───────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return 'Date TBC'
  return new Date(iso).toLocaleDateString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

// ─── Compound badge ───────────────────────────────────────────────────────────

const COMPOUND_STYLES: Record<string, string> = {
  SOFT:         'bg-red-950 text-red-300 border-red-800',
  MEDIUM:       'bg-yellow-950 text-yellow-300 border-yellow-800',
  HARD:         'bg-gray-800 text-gray-200 border-gray-600',
  INTERMEDIATE: 'bg-green-950 text-green-300 border-green-800',
  WET:          'bg-blue-950 text-blue-300 border-blue-800',
}

const COMPOUND_ORDER = ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']

function CompoundBadge({ compound }: { compound: string | null }) {
  if (!compound) return <span className="text-gray-600">—</span>
  const style = COMPOUND_STYLES[compound] ?? 'bg-gray-800 text-gray-400 border-gray-700'
  return (
    <span className={`text-xs font-mono px-1.5 py-0.5 rounded border ${style}`}>
      {compound}
    </span>
  )
}

// ─── Flag badge ───────────────────────────────────────────────────────────────

const FLAG_STYLES: Record<string, string> = {
  GREEN:           'bg-green-950 text-green-300',
  YELLOW:          'bg-yellow-950 text-yellow-300',
  'DOUBLE YELLOW': 'bg-yellow-950 text-yellow-200',
  RED:             'bg-red-950 text-red-300',
  CHEQUERED:       'bg-gray-800 text-gray-300',
  'SAFETY CAR':    'bg-orange-950 text-orange-300',
}

function FlagBadge({ flag }: { flag: string | null }) {
  if (!flag) return null
  const style = FLAG_STYLES[flag] ?? 'bg-gray-800 text-gray-400'
  return (
    <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${style}`}>{flag}</span>
  )
}

// ─── Favourite star ────────────────────────────────────────────────────────────

function FavStar() {
  return (
    <span className="text-red-500 text-sm leading-none shrink-0" title="Favourite driver">
      ★
    </span>
  )
}

// ─── Section card ─────────────────────────────────────────────────────────────

function SectionCard({
  title,
  badge,
  empty,
  emptyMessage,
  children,
}: {
  title: string
  badge?: string
  empty: boolean
  emptyMessage: string
  children?: React.ReactNode
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-white">{title}</h2>
        {badge && <span className="text-xs font-mono text-gray-500">{badge}</span>}
      </div>
      {empty ? (
        <div className="px-5 py-8 text-center">
          <p className="text-sm text-gray-600">{emptyMessage}</p>
        </div>
      ) : (
        children
      )}
    </div>
  )
}

// ─── Lap stats section ────────────────────────────────────────────────────────

function LapStatsSection({ stats }: { stats: DashboardLapStats }) {
  const items = [
    { label: 'Total lap rows', value: stats.total_rows.toLocaleString() },
    { label: 'Drivers with data', value: stats.driver_count },
    { label: 'Max lap number', value: stats.max_lap ?? '—' },
  ]
  return (
    <div className="grid grid-cols-3 gap-px bg-gray-800/50">
      {items.map(item => (
        <div key={item.label} className="bg-gray-900 px-4 py-3">
          <p className="text-gray-600 text-xs mb-0.5">{item.label}</p>
          <p className="text-sm font-mono font-medium text-gray-200">{item.value}</p>
        </div>
      ))}
    </div>
  )
}

// ─── Finishing order section ──────────────────────────────────────────────────

function FinishingOrderSection({ entries }: { entries: DashboardDriverSummary[] }) {
  return (
    <SectionCard
      title="Finishing Order"
      badge={`${entries.length} drivers`}
      empty={entries.length === 0}
      emptyMessage="No lap data — finishing order cannot be derived for this session."
    >
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-800 text-gray-600 uppercase tracking-wider">
              <th className="px-5 py-2.5 text-left font-medium w-12">Pos</th>
              <th className="px-5 py-2.5 text-left font-medium">Driver</th>
              <th className="px-5 py-2.5 text-right font-medium">Max Lap</th>
              <th className="px-5 py-2.5 text-right font-medium">Gap</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(entry => (
              <tr
                key={entry.driver_number}
                className={`border-b border-gray-800/40 last:border-0 transition-colors ${
                  entry.is_favourite
                    ? 'bg-red-950/20 hover:bg-red-950/30'
                    : 'hover:bg-gray-800/20'
                }`}
              >
                <td className="px-5 py-2.5">
                  <span
                    className={`font-mono font-bold ${
                      entry.position <= 3 ? 'text-yellow-400' : 'text-gray-500'
                    }`}
                  >
                    P{entry.position}
                  </span>
                </td>
                <td className="px-5 py-2.5">
                  <div className="flex items-center gap-2">
                    {entry.is_favourite && <FavStar />}
                    <span
                      className={`font-medium ${
                        entry.is_favourite ? 'text-white' : 'text-gray-300'
                      }`}
                    >
                      {entry.driver_name}
                    </span>
                    <span className="text-gray-600 font-mono">#{entry.driver_number}</span>
                  </div>
                </td>
                <td className="px-5 py-2.5 text-right font-mono text-gray-400">
                  {entry.max_lap}
                </td>
                <td className="px-5 py-2.5 text-right font-mono">
                  {entry.laps_behind === 0 ? (
                    <span className="text-green-400">Lead</span>
                  ) : (
                    <span className="text-gray-500">
                      +{entry.laps_behind} lap{entry.laps_behind !== 1 ? 's' : ''}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="px-5 py-2 text-xs text-gray-700 border-t border-gray-800/50">
        Derived from lap timing data — not official results. Post-race penalties are not reflected.
      </p>
    </SectionCard>
  )
}

// ─── Tyre strategy section ────────────────────────────────────────────────────

function TyreStrategySection({
  compoundOverview,
  stintSummary,
}: {
  compoundOverview: Record<string, number>
  stintSummary: DashboardStintSummary[]
}) {
  const sortedCompounds = [
    ...COMPOUND_ORDER.filter(c => c in compoundOverview),
    ...Object.keys(compoundOverview).filter(c => !COMPOUND_ORDER.includes(c)),
  ]

  return (
    <SectionCard
      title="Tyre Strategy"
      badge={`${stintSummary.length} drivers`}
      empty={stintSummary.length === 0}
      emptyMessage="No stint data stored for this session."
    >
      {sortedCompounds.length > 0 && (
        <div className="px-5 py-3 flex items-center gap-3 flex-wrap border-b border-gray-800/50">
          <span className="text-xs text-gray-600 shrink-0">Compounds used:</span>
          {sortedCompounds.map(compound => (
            <span key={compound} className="flex items-center gap-1.5">
              <CompoundBadge compound={compound} />
              <span className="text-gray-500 text-xs font-mono">
                {compoundOverview[compound]}×
              </span>
            </span>
          ))}
        </div>
      )}
      <div className="divide-y divide-gray-800/40">
        {stintSummary.map(driver => (
          <div
            key={driver.driver_number}
            className={`px-5 py-3 ${driver.is_favourite ? 'bg-red-950/20' : ''}`}
          >
            <div className="flex items-center gap-2 mb-2">
              {driver.is_favourite && <FavStar />}
              <span
                className={`text-xs font-semibold ${
                  driver.is_favourite ? 'text-white' : 'text-gray-300'
                }`}
              >
                {driver.driver_name}
              </span>
              <span className="text-gray-600 text-xs font-mono">#{driver.driver_number}</span>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {driver.stints.map((stint, i) => {
                const stintLabel = stint.stint_number != null ? `S${stint.stint_number}` : `S${i + 1}`
                const lapRange =
                  stint.lap_start != null && stint.lap_end != null
                    ? `L${stint.lap_start}–${stint.lap_end}`
                    : stint.lap_start != null
                      ? `L${stint.lap_start}+`
                      : null
                const age =
                  stint.tyre_age_at_start != null && stint.tyre_age_at_start > 0
                    ? `${stint.tyre_age_at_start}L old`
                    : 'new'
                return (
                  <div
                    key={i}
                    className="flex items-center gap-1.5 bg-gray-800/60 rounded px-2 py-1"
                  >
                    <span className="text-gray-600 text-xs font-mono">{stintLabel}</span>
                    <CompoundBadge compound={stint.compound} />
                    {lapRange && (
                      <span className="text-gray-500 text-xs font-mono">{lapRange}</span>
                    )}
                    <span className="text-gray-600 text-xs">({age})</span>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  )
}

// ─── Race control section ─────────────────────────────────────────────────────

function RaceControlSection({
  keyEvents,
  messages,
  total,
  blueFlagCount,
  omittedCount,
}: {
  keyEvents: DashboardKeyEvent[]
  messages: DashboardRCMessage[]
  total: number
  blueFlagCount: number
  omittedCount: number
}) {
  const noteParts: string[] = []
  if (blueFlagCount > 0) noteParts.push(`${blueFlagCount} blue-flag lapping messages excluded`)
  if (omittedCount > 0) noteParts.push(`${omittedCount} routine messages omitted`)

  return (
    <SectionCard
      title="Race Control"
      badge={`${total} total messages`}
      empty={keyEvents.length === 0 && messages.length === 0}
      emptyMessage="No race control messages stored for this session."
    >
      {keyEvents.length > 0 && (
        <div className="px-5 py-3 border-b border-gray-800/50">
          <p className="text-xs text-gray-600 uppercase tracking-wider mb-2.5">Key events</p>
          <div className="space-y-1.5">
            {keyEvents.map((ev, i) => (
              <div key={i} className="flex items-baseline gap-2">
                <span className="text-red-500 text-xs shrink-0">•</span>
                <span className="text-gray-300 text-xs">{ev.label}</span>
                {ev.lap_number != null && (
                  <span className="text-gray-600 text-xs font-mono">lap {ev.lap_number}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="divide-y divide-gray-800/40">
        {messages.map((msg, i) => (
          <div
            key={i}
            className="px-5 py-2.5 flex items-start gap-3 hover:bg-gray-800/10 transition-colors"
          >
            <span className="text-gray-600 text-xs font-mono shrink-0 w-14 pt-0.5 text-right">
              {msg.lap_number != null ? `Lap ${msg.lap_number}` : ''}
            </span>
            <p className="text-xs text-gray-300 leading-snug flex-1 min-w-0">{msg.message}</p>
            {msg.flag && (
              <div className="shrink-0">
                <FlagBadge flag={msg.flag} />
              </div>
            )}
          </div>
        ))}
      </div>
      {noteParts.length > 0 && (
        <p className="px-5 py-2 text-xs text-gray-700 border-t border-gray-800/50">
          {noteParts.join('; ')}
        </p>
      )}
    </SectionCard>
  )
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function windCompass(degrees: number | null): string {
  if (degrees === null) return ''
  const labels = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
  return labels[Math.round(degrees / 45) % 8]
}

// ─── Weather section ──────────────────────────────────────────────────────────

function WeatherSection({ weather }: { weather: NonNullable<SessionDashboard['weather']> }) {
  const latest = weather.latest_sample

  // Latest-reading stat cells — only include fields that have a value
  const latestStats: { label: string; value: string; highlight?: boolean }[] = []
  if (latest) {
    if (latest.air_temperature != null)
      latestStats.push({ label: 'Air temp', value: `${latest.air_temperature} °C` })
    if (latest.track_temperature != null)
      latestStats.push({ label: 'Track temp', value: `${latest.track_temperature} °C` })
    if (latest.humidity != null)
      latestStats.push({ label: 'Humidity', value: `${latest.humidity}%` })
    latestStats.push({
      label: 'Rainfall',
      value: latest.rainfall ? 'Yes' : 'No',
      highlight: latest.rainfall ?? false,
    })
    if (latest.wind_speed != null) {
      const dir = latest.wind_direction != null
        ? ` ${windCompass(latest.wind_direction)}`
        : ''
      latestStats.push({ label: 'Wind', value: `${latest.wind_speed} m/s${dir}` })
    }
  }

  // Session-range cells
  const rangeStats = [
    {
      label: 'Air temp range',
      value:
        weather.air_min != null && weather.air_max != null
          ? `${weather.air_min}–${weather.air_max} °C`
          : '—',
    },
    {
      label: 'Track temp range',
      value:
        weather.track_min != null && weather.track_max != null
          ? `${weather.track_min}–${weather.track_max} °C`
          : '—',
    },
    {
      label: 'Rain during session',
      value: weather.had_rain ? 'Yes' : 'No',
    },
    {
      label: 'Samples stored',
      value: weather.sample_count.toLocaleString(),
    },
  ]

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-white">Weather</h2>
        <span className="text-xs font-mono text-gray-500">{weather.sample_count} readings</span>
      </div>

      {/* Latest reading */}
      {latestStats.length > 0 && (
        <>
          <div className="px-5 py-2 border-b border-gray-800/50">
            <p className="text-xs text-gray-600 uppercase tracking-wider">Latest reading</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-px bg-gray-800/50 border-b border-gray-800">
            {latestStats.map(s => (
              <div key={s.label} className="bg-gray-900 px-4 py-3">
                <p className="text-gray-600 text-xs mb-0.5">{s.label}</p>
                <p
                  className={`text-sm font-mono font-medium ${
                    s.highlight ? 'text-blue-400' : 'text-gray-200'
                  }`}
                >
                  {s.value}
                </p>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Session range */}
      <div className="px-5 py-2 border-b border-gray-800/50">
        <p className="text-xs text-gray-600 uppercase tracking-wider">Session range</p>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-gray-800/50">
        {rangeStats.map(s => (
          <div key={s.label} className="bg-gray-900 px-4 py-3">
            <p className="text-gray-600 text-xs mb-0.5">{s.label}</p>
            <p className="text-sm font-mono font-medium text-gray-200">{s.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div>
        <div className="h-3 w-24 bg-gray-800 rounded mb-6" />
        <div className="h-8 w-72 bg-gray-800 rounded mb-2" />
        <div className="h-4 w-52 bg-gray-800 rounded mb-1" />
        <div className="h-3 w-40 bg-gray-800 rounded" />
      </div>
      <div className="grid grid-cols-3 gap-px bg-gray-800/50 border border-gray-800 rounded-xl overflow-hidden">
        {[0, 1, 2].map(i => (
          <div key={i} className="bg-gray-900 h-14" />
        ))}
      </div>
      {[0, 1, 2, 3].map(i => (
        <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl h-40" />
      ))}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SessionDashboardPage() {
  const { id } = useParams<{ id: string }>()
  const sessionId = Number(id)
  const { token, loading: authLoading } = useAuth()

  const [dashboard, setDashboard] = useState<SessionDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Wait for auth to resolve before fetching so the correct token is used once.
  // This prevents a double-fetch (anonymous then authed) on initial page load.
  useEffect(() => {
    if (authLoading || !sessionId) return
    setLoading(true)
    setError(null)
    getSessionDashboard(sessionId, token)
      .then(setDashboard)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [sessionId, token, authLoading])

  if (loading || authLoading) {
    return (
      <div className="page-enter">
        <LoadingSkeleton />
      </div>
    )
  }

  if (error || !dashboard) {
    return (
      <div className="page-enter">
        <Link to="/calendar" className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
          ← Calendar
        </Link>
        <div className="mt-8 text-center">
          <p className="text-red-400 font-medium">Dashboard not found</p>
          {error && <p className="text-gray-600 text-sm mt-1">{error}</p>}
        </div>
      </div>
    )
  }

  const {
    session_name,
    session_type,
    race_name,
    circuit_short_name,
    country_name,
    start_time,
    is_synced,
    has_lap_data,
    has_stint_data,
    has_rc_data,
    has_weather_data,
    lap_stats,
    finishing_order,
    compound_overview,
    stint_summary,
    race_control,
    weather,
  } = dashboard

  // Finishing order is only meaningful for race and sprint sessions.
  const isRaceOrSprint = session_type === 'race' || session_type === 'sprint'

  return (
    <div className="page-enter space-y-6">

      {/* Navigation */}
      <div className="flex items-center gap-4 text-xs">
        <Link to="/calendar" className="text-gray-600 hover:text-gray-400 transition-colors">
          ← Calendar
        </Link>
        <Link
          to={`/sessions/${sessionId}`}
          className="text-gray-600 hover:text-gray-400 transition-colors ml-auto"
        >
          Raw session data →
        </Link>
      </div>

      {/* Session header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{session_name}</h1>
          <p className="text-gray-400 text-sm mt-0.5">
            {race_name}
            {circuit_short_name && ` · ${circuit_short_name}`}
            {country_name && `, ${country_name}`}
          </p>
          <p className="text-gray-600 text-xs mt-1 font-mono">{formatDate(start_time)}</p>
        </div>
        <div className="shrink-0">
          {is_synced ? (
            <span className="text-xs bg-green-950 text-green-400 border border-green-800 px-2.5 py-1 rounded-full">
              Synced
            </span>
          ) : (
            <span className="text-xs bg-gray-800 text-gray-500 border border-gray-700 px-2.5 py-1 rounded-full">
              Not synced
            </span>
          )}
        </div>
      </div>

      {/* Not-synced notice — explains why all sections below will be empty */}
      {!is_synced && (
        <div className="bg-amber-950/30 border border-amber-800/40 rounded-xl px-5 py-4">
          <p className="text-amber-400 text-sm font-medium">No historical data available</p>
          <p className="text-amber-600/70 text-xs mt-1 leading-relaxed">
            This session has not been synced from OpenF1. Run{' '}
            <code className="text-amber-500/80 font-mono">
              python scripts/sync_openf1_session.py --session-key &lt;key&gt;
            </code>{' '}
            to ingest lap, stint, race control, and weather data.
          </p>
        </div>
      )}

      {/* Lap summary */}
      <SectionCard
        title="Lap Summary"
        badge={has_lap_data ? `${lap_stats.total_rows.toLocaleString()} rows` : undefined}
        empty={!has_lap_data}
        emptyMessage="No lap data stored for this session."
      >
        <LapStatsSection stats={lap_stats} />
      </SectionCard>

      {/* Finishing order — race and sprint sessions only */}
      {isRaceOrSprint && (
        <FinishingOrderSection entries={finishing_order} />
      )}

      {/* Tyre strategy */}
      <TyreStrategySection
        compoundOverview={compound_overview}
        stintSummary={stint_summary}
      />

      {/* Race control */}
      <RaceControlSection
        keyEvents={race_control.key_events}
        messages={race_control.messages}
        total={race_control.total}
        blueFlagCount={race_control.blue_flag_count}
        omittedCount={race_control.omitted_count}
      />

      {/* Weather */}
      {has_weather_data && weather ? (
        <WeatherSection weather={weather} />
      ) : (
        <SectionCard
          title="Weather"
          empty
          emptyMessage="No weather data stored for this session."
        />
      )}

    </div>
  )
}
