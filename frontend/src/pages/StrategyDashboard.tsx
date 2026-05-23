import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getSessionStrategy } from '../services/api'
import { useAuth } from '../context/AuthContext'
import type {
  StrategyDashboard,
  StrategyCompoundUsage,
  StrategyDriverSummary,
  StrategyPitWindow,
  StrategyRaceControlContext,
  StrategyWeatherContext,
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
  YELLOW:          'bg-yellow-950 text-yellow-300',
  'DOUBLE YELLOW': 'bg-yellow-950 text-yellow-200',
  RED:             'bg-red-950 text-red-300',
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

// ─── Strategy insights section ────────────────────────────────────────────────

function StrategyInsightsSection({ insights }: { insights: string[] }) {
  if (insights.length === 0) return null

  const isLimited = insights.some(s => s.startsWith('Strategy insights are limited') || s.startsWith('No stint data'))

  return (
    <div
      className={`rounded-xl border px-5 py-4 ${
        isLimited
          ? 'bg-amber-950/20 border-amber-800/40'
          : 'bg-gray-900 border-gray-800'
      }`}
    >
      <h2 className="text-sm font-semibold text-white mb-3">Strategy Insights</h2>
      <ul className="space-y-2">
        {insights.map((insight, i) => (
          <li key={i} className="flex items-start gap-2.5">
            <span className="text-red-500 text-xs mt-0.5 shrink-0">•</span>
            <span className="text-gray-300 text-xs leading-relaxed">{insight}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

// ─── Compound usage section ───────────────────────────────────────────────────

function CompoundUsageSection({ usage }: { usage: StrategyCompoundUsage[] }) {
  const sorted = [
    ...COMPOUND_ORDER.filter(c => usage.some(u => u.compound === c)).map(
      c => usage.find(u => u.compound === c)!
    ),
    ...usage.filter(u => !COMPOUND_ORDER.includes(u.compound)),
  ]

  return (
    <SectionCard
      title="Compound Usage"
      badge={`${usage.length} compound${usage.length !== 1 ? 's' : ''}`}
      empty={usage.length === 0}
      emptyMessage="No compound data available."
    >
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-px bg-gray-800/50">
        {sorted.map(cu => (
          <div key={cu.compound} className="bg-gray-900 px-4 py-4">
            <CompoundBadge compound={cu.compound} />
            <p className="text-gray-200 text-sm font-mono font-medium mt-2">
              {cu.stint_count} stints
            </p>
            <p className="text-gray-500 text-xs mt-0.5">
              {cu.driver_count} driver{cu.driver_count !== 1 ? 's' : ''}
            </p>
            {cu.avg_stint_laps != null && (
              <p className="text-gray-600 text-xs mt-0.5 font-mono">
                avg {cu.avg_stint_laps} laps
              </p>
            )}
          </div>
        ))}
      </div>
    </SectionCard>
  )
}

// ─── Stop count section ───────────────────────────────────────────────────────

function StopCountSection({ groups }: { groups: Record<string, string[]> }) {
  const keys = Object.keys(groups)
    .map(Number)
    .sort((a, b) => a - b)

  if (keys.length === 0) return null

  return (
    <SectionCard
      title="Pit Stop Summary"
      badge={`${keys.length} strategy group${keys.length !== 1 ? 's' : ''}`}
      empty={false}
      emptyMessage=""
    >
      <div className="divide-y divide-gray-800/40">
        {keys.map(stops => {
          const drivers = groups[String(stops)]
          return (
            <div key={stops} className="px-5 py-3 flex items-baseline gap-3">
              <span className="text-white font-mono font-bold text-sm w-16 shrink-0">
                {stops} stop{stops !== 1 ? 's' : ''}
              </span>
              <span className="text-gray-400 text-xs leading-relaxed">
                {drivers.join(', ')}
              </span>
            </div>
          )
        })}
      </div>
    </SectionCard>
  )
}

// ─── Driver strategy section ──────────────────────────────────────────────────

function CompoundSequence({ sequence }: { sequence: string[] }) {
  if (sequence.length === 0) return <span className="text-gray-600 text-xs">No compound data</span>
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {sequence.map((compound, i) => (
        <span key={i} className="flex items-center gap-1">
          <CompoundBadge compound={compound} />
          {i < sequence.length - 1 && (
            <span className="text-gray-700 text-xs">→</span>
          )}
        </span>
      ))}
    </div>
  )
}

function DriverStrategyCard({ driver }: { driver: StrategyDriverSummary }) {
  const isFav = driver.is_favourite

  return (
    <div
      className={`rounded-xl border overflow-hidden ${
        isFav
          ? 'border-red-800/60 bg-red-950/10'
          : 'border-gray-800 bg-gray-900'
      }`}
    >
      {/* Driver header */}
      <div
        className={`px-5 py-3 flex items-center justify-between gap-3 border-b ${
          isFav ? 'border-red-800/40 bg-red-950/20' : 'border-gray-800'
        }`}
      >
        <div className="flex items-center gap-2 min-w-0">
          {isFav && <FavStar />}
          <span className={`font-semibold text-sm ${isFav ? 'text-white' : 'text-gray-200'}`}>
            {driver.driver_name}
          </span>
          <span className="text-gray-600 font-mono text-xs shrink-0">#{driver.driver_number}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs font-mono text-gray-500">
            {driver.stop_count} stop{driver.stop_count !== 1 ? 's' : ''}
          </span>
          {driver.longest_stint_laps != null && (
            <span className="text-xs font-mono text-gray-600">
              · longest {driver.longest_stint_laps}L
            </span>
          )}
        </div>
      </div>

      {/* Compound sequence */}
      <div className="px-5 py-2.5 border-b border-gray-800/50 flex items-center gap-2">
        <span className="text-xs text-gray-600 shrink-0">Strategy:</span>
        <CompoundSequence sequence={driver.compound_sequence} />
      </div>

      {/* Stint table */}
      {driver.stints.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-600 uppercase tracking-wider border-b border-gray-800/50">
                <th className="px-5 py-2 text-left font-medium">Stint</th>
                <th className="px-5 py-2 text-left font-medium">Compound</th>
                <th className="px-5 py-2 text-left font-medium">Laps</th>
                <th className="px-5 py-2 text-right font-medium">Length</th>
                <th className="px-5 py-2 text-right font-medium">Tyre age</th>
              </tr>
            </thead>
            <tbody>
              {driver.stints.map((stint, i) => {
                const stintLabel = stint.stint_number != null ? `S${stint.stint_number}` : `S${i + 1}`
                const lapRange =
                  stint.lap_start != null && stint.lap_end != null
                    ? `L${stint.lap_start}–${stint.lap_end}`
                    : stint.lap_start != null
                      ? `L${stint.lap_start}+`
                      : '—'
                const age =
                  stint.tyre_age_at_start != null && stint.tyre_age_at_start > 0
                    ? `${stint.tyre_age_at_start}L old`
                    : 'new'
                const isLongest =
                  driver.longest_stint_laps != null &&
                  stint.stint_laps === driver.longest_stint_laps

                return (
                  <tr
                    key={i}
                    className={`border-b border-gray-800/30 last:border-0 ${
                      isLongest ? 'bg-gray-800/20' : ''
                    }`}
                  >
                    <td className="px-5 py-2 font-mono text-gray-500">{stintLabel}</td>
                    <td className="px-5 py-2">
                      <CompoundBadge compound={stint.compound} />
                    </td>
                    <td className="px-5 py-2 font-mono text-gray-400">{lapRange}</td>
                    <td className="px-5 py-2 text-right font-mono">
                      {stint.stint_laps != null ? (
                        <span className={isLongest ? 'text-amber-400' : 'text-gray-400'}>
                          {stint.stint_laps}L{isLongest && ' ↑'}
                        </span>
                      ) : (
                        <span className="text-gray-700">—</span>
                      )}
                    </td>
                    <td className="px-5 py-2 text-right font-mono text-gray-500">{age}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function DriverStrategiesSection({ strategies }: { strategies: StrategyDriverSummary[] }) {
  // Favourite drivers first, then by driver number
  const sorted = [...strategies].sort((a, b) => {
    if (a.is_favourite !== b.is_favourite) return a.is_favourite ? -1 : 1
    return a.driver_number - b.driver_number
  })

  return (
    <SectionCard
      title="Driver Strategies"
      badge={`${strategies.length} drivers`}
      empty={strategies.length === 0}
      emptyMessage="No stint data has been synced for this session yet."
    >
      <div className="p-4 space-y-3">
        {sorted.map(driver => (
          <DriverStrategyCard key={driver.driver_number} driver={driver} />
        ))}
      </div>
    </SectionCard>
  )
}

// ─── Pit windows section ──────────────────────────────────────────────────────

function PitWindowsSection({ windows }: { windows: StrategyPitWindow[] }) {
  return (
    <SectionCard
      title="Pit Windows"
      badge={`${windows.length} window${windows.length !== 1 ? 's' : ''}`}
      empty={windows.length === 0}
      emptyMessage="No pit window data available — requires stint lap ranges."
    >
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-600 uppercase tracking-wider border-b border-gray-800">
              <th className="px-5 py-2.5 text-left font-medium">Window</th>
              <th className="px-5 py-2.5 text-left font-medium">Lap range</th>
              <th className="px-5 py-2.5 text-right font-medium">Drivers</th>
            </tr>
          </thead>
          <tbody>
            {windows.map(pw => (
              <tr
                key={pw.window_number}
                className="border-b border-gray-800/40 last:border-0 hover:bg-gray-800/10 transition-colors"
              >
                <td className="px-5 py-2.5 font-mono text-gray-400">
                  Window {pw.window_number}
                </td>
                <td className="px-5 py-2.5 font-mono text-gray-300">
                  {pw.lap_min === pw.lap_max
                    ? `Lap ${pw.lap_min}`
                    : `Laps ${pw.lap_min}–${pw.lap_max}`}
                </td>
                <td className="px-5 py-2.5 text-right font-mono text-gray-500">
                  {pw.driver_count} driver{pw.driver_count !== 1 ? 's' : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="px-5 py-2 text-xs text-gray-700 border-t border-gray-800/50">
        Windows are clusters of pit laps within 6 laps of each other. Not official timing data.
      </p>
    </SectionCard>
  )
}

// ─── Strategy race control section ────────────────────────────────────────────

function rcEventContextNote(flag: string | null, message: string): string | null {
  const f = (flag ?? '').toUpperCase()
  const m = message.toUpperCase()
  if (f === 'SAFETY CAR' || m.includes('SAFETY CAR DEPLOYED'))
    return 'may have affected pit stop timing for multiple drivers'
  if (m.includes('SAFETY CAR IN THE PIT LANE') || m.includes('SAFETY CAR ENDING'))
    return 'may have prompted drivers to pit before the restart'
  if (m.includes('VSC') || m.includes('VIRTUAL SAFETY CAR'))
    return 'may have affected pit stop decision-making'
  if (f === 'RED' || m.includes('RED FLAG'))
    return 'may have prompted a strategy reset — pit stops under red flags are permitted'
  if (m.includes('PIT LANE OPEN'))
    return 'pit lane open — could be relevant to when drivers chose to stop'
  if (m.includes('PIT LANE CLOSED'))
    return 'pit lane closed — drivers could not stop during this period'
  if (m.includes('RISK OF RAIN') || m.includes('WEATHER'))
    return 'could be relevant to compound selection'
  if (m.includes('RETIRED'))
    return 'retirement may have prompted strategic reactions from other teams'
  if (f === 'YELLOW' || f === 'DOUBLE YELLOW')
    return 'yellow flag conditions may have affected pit stop timing'
  return null
}

function StrategyRCSection({ rc }: { rc: StrategyRaceControlContext }) {
  return (
    <SectionCard
      title="Strategy-Relevant Race Control"
      badge={`${rc.total_strategy_events} events`}
      empty={rc.events.length === 0}
      emptyMessage="No strategy-relevant race control messages for this session."
    >
      <div className="divide-y divide-gray-800/40">
        {rc.events.map((ev, i) => {
          const note = rcEventContextNote(ev.flag, ev.message)
          return (
            <div
              key={i}
              className="px-5 py-2.5 flex items-start gap-3 hover:bg-gray-800/10 transition-colors"
            >
              <span className="text-gray-600 text-xs font-mono shrink-0 w-14 pt-0.5 text-right">
                {ev.lap_number != null ? `Lap ${ev.lap_number}` : ''}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-300 leading-snug">{ev.message}</p>
                {note && (
                  <p className="text-xs text-gray-600 mt-0.5 italic">↳ {note}</p>
                )}
              </div>
              {ev.flag && (
                <div className="shrink-0">
                  <FlagBadge flag={ev.flag} />
                </div>
              )}
            </div>
          )
        })}
      </div>
      <p className="px-5 py-2 text-xs text-gray-700 border-t border-gray-800/50">
        Filtered to safety cars, virtual safety cars, red flags, pit lane status, weather
        warnings, and retirements. Context notes describe potential strategy relevance
        — they do not confirm a causal link to any driver decision.
      </p>
    </SectionCard>
  )
}

// ─── Strategy weather section ─────────────────────────────────────────────────

function StrategyWeatherSection({ weather }: { weather: StrategyWeatherContext }) {
  const rangeStats = [
    {
      label: 'Rain during session',
      value: weather.had_rain ? 'Yes' : 'No',
      highlight: weather.had_rain,
    },
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
      label: 'Weather readings',
      value: weather.sample_count.toLocaleString(),
    },
  ]

  const hasLatest =
    weather.latest_air_temp != null ||
    weather.latest_track_temp != null ||
    weather.latest_rainfall != null

  const latestStats = [
    weather.latest_air_temp != null && {
      label: 'Air temp (latest)',
      value: `${weather.latest_air_temp} °C`,
    },
    weather.latest_track_temp != null && {
      label: 'Track temp (latest)',
      value: `${weather.latest_track_temp} °C`,
    },
    weather.latest_rainfall != null && {
      label: 'Rainfall (latest)',
      value: weather.latest_rainfall ? 'Yes' : 'No',
      highlight: weather.latest_rainfall,
    },
  ].filter(Boolean) as { label: string; value: string; highlight?: boolean }[]

  // Describe track temp variance cautiously
  const trackVariance =
    weather.track_min != null && weather.track_max != null
      ? weather.track_max - weather.track_min
      : null

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-white">Weather &amp; Conditions</h2>
        <span className="text-xs font-mono text-gray-500">
          {weather.sample_count} readings
        </span>
      </div>

      {/* Session range */}
      <div className="px-5 py-2 border-b border-gray-800/50">
        <p className="text-xs text-gray-600 uppercase tracking-wider">Session range</p>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-gray-800/50">
        {rangeStats.map(s => (
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

      {/* Latest reading */}
      {hasLatest && (
        <>
          <div className="px-5 py-2 border-t border-gray-800/50">
            <p className="text-xs text-gray-600 uppercase tracking-wider">Latest reading</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-px bg-gray-800/50">
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

      {/* Wet tyre drivers */}
      {weather.wet_tyre_drivers.length > 0 && (
        <div className="px-5 py-3 border-t border-gray-800/50 flex items-baseline gap-2">
          <span className="text-xs text-blue-400 shrink-0">Wet tyres used by:</span>
          <span className="text-xs text-gray-300">{weather.wet_tyre_drivers.join(', ')}</span>
        </div>
      )}

      {/* Rain or significant track variance note */}
      {(weather.had_rain || (trackVariance != null && trackVariance >= 10)) && (
        <div className="px-5 py-2.5 border-t border-gray-800/50 space-y-1">
          {weather.had_rain && (
            <p className="text-xs text-gray-600 italic">
              Rain was recorded — conditions may have been relevant to compound selection.
            </p>
          )}
          {trackVariance != null && trackVariance >= 10 && (
            <p className="text-xs text-gray-600 italic">
              Track temperature varied by {Math.round(trackVariance)}°C — significant changes
              could be relevant to tyre behaviour.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div>
        <div className="h-3 w-24 bg-gray-800 rounded mb-6" />
        <div className="h-8 w-80 bg-gray-800 rounded mb-2" />
        <div className="h-4 w-56 bg-gray-800 rounded mb-1" />
        <div className="h-3 w-40 bg-gray-800 rounded" />
      </div>
      <div className="grid grid-cols-3 sm:grid-cols-5 gap-px bg-gray-800/50 border border-gray-800 rounded-xl overflow-hidden">
        {[0, 1, 2, 3, 4].map(i => (
          <div key={i} className="bg-gray-900 h-20" />
        ))}
      </div>
      {[0, 1, 2, 3, 4].map(i => (
        <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl h-36" />
      ))}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function StrategyDashboardPage() {
  const { id } = useParams<{ id: string }>()
  const sessionId = Number(id)
  const { token, loading: authLoading } = useAuth()

  const [strategy, setStrategy] = useState<StrategyDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Wait for auth to resolve before fetching so the token state is final.
  useEffect(() => {
    if (authLoading || !sessionId) return
    setLoading(true)
    setError(null)
    getSessionStrategy(sessionId, token)
      .then(setStrategy)
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

  if (error || !strategy) {
    return (
      <div className="page-enter">
        <Link
          to="/calendar"
          className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
        >
          ← Calendar
        </Link>
        <div className="mt-8 text-center">
          <p className="text-red-400 font-medium">Strategy data not found</p>
          {error && <p className="text-gray-600 text-sm mt-1">{error}</p>}
        </div>
      </div>
    )
  }

  const {
    session_id,
    session_name,
    session_type,
    race_name,
    circuit_short_name,
    country_name,
    start_time,
    is_synced,
    has_stint_data,
    has_rc_data,
    has_weather_data,
    compound_usage,
    driver_strategies,
    stop_count_groups,
    pit_windows,
    race_control,
    weather,
    insights,
  } = strategy

  return (
    <div className="page-enter space-y-6">

      {/* Navigation */}
      <div className="flex items-center gap-4 text-xs">
        <Link to="/calendar" className="text-gray-600 hover:text-gray-400 transition-colors">
          ← Calendar
        </Link>
        <Link
          to={`/sessions/${session_id}/dashboard`}
          className="text-gray-600 hover:text-gray-400 transition-colors ml-auto"
        >
          Session dashboard →
        </Link>
        <Link
          to={`/sessions/${session_id}/analytics`}
          className="text-gray-600 hover:text-purple-400 transition-colors"
        >
          Analytics →
        </Link>
      </div>

      {/* Session header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs text-gray-600 uppercase tracking-wider mb-1 font-mono">
            Strategy Dashboard
          </p>
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

      {/* Not-synced notice */}
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

      {/* No stint data notice — synced session but tyres not available */}
      {is_synced && !has_stint_data && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl px-5 py-4">
          <p className="text-gray-400 text-sm font-medium">No tyre strategy data available</p>
          <p className="text-gray-600 text-xs mt-1">
            This session was synced but no stint or compound data was returned by OpenF1.
            Strategy sections below will show empty states.
          </p>
        </div>
      )}

      {/* Rule-based insights */}
      <StrategyInsightsSection insights={insights} />

      {/* Compound usage */}
      <CompoundUsageSection usage={compound_usage} />

      {/* Pit stop summary */}
      {has_stint_data && (
        <StopCountSection groups={stop_count_groups} />
      )}

      {/* Driver strategies — the main section */}
      <DriverStrategiesSection strategies={driver_strategies} />

      {/* Pit windows */}
      {has_stint_data && (
        <PitWindowsSection windows={pit_windows} />
      )}

      {/* Strategy race control */}
      {has_rc_data ? (
        <StrategyRCSection rc={race_control} />
      ) : (
        <SectionCard
          title="Strategy-Relevant Race Control"
          empty
          emptyMessage="No race control messages have been synced for this session."
        />
      )}

      {/* Weather */}
      {has_weather_data && weather ? (
        <StrategyWeatherSection weather={weather} />
      ) : (
        <SectionCard
          title="Weather &amp; Conditions"
          empty
          emptyMessage="No weather data has been synced for this session."
        />
      )}

      {/* Footnote */}
      <p className="text-xs text-center text-gray-700 pb-2">
        Strategy data is derived from OpenF1 stint records. Pit windows are approximated from
        stint transitions — not official timing data.
        {session_type === 'race' || session_type === 'sprint' ? '' : (
          ' Pit stop counts are less meaningful for non-race sessions.'
        )}
      </p>

    </div>
  )
}
