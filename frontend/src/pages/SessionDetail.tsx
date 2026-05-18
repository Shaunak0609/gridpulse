import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  getSession,
  getSessionLaps,
  getSessionStints,
  getSessionRaceControl,
  getSessionWeather,
} from '../services/api'
import type { Lap, RaceControlMessage, SessionDetail, Stint, WeatherSample } from '../types'

// ─── Formatters ───────────────────────────────────────────────────────────────

function formatLapTime(seconds: number | null): string {
  if (seconds == null) return '—'
  const mins = Math.floor(seconds / 60)
  const secs = (seconds % 60).toFixed(3).padStart(6, '0')
  return mins > 0 ? `${mins}:${secs}` : `${secs}s`
}

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatSessionDate(iso: string | null): string {
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
  GREEN:          'bg-green-950 text-green-300',
  YELLOW:         'bg-yellow-950 text-yellow-300',
  'DOUBLE YELLOW':'bg-yellow-950 text-yellow-200',
  RED:            'bg-red-950 text-red-300',
  SC:             'bg-orange-950 text-orange-300',
  VSC:            'bg-orange-950 text-orange-200',
  CHEQUERED:      'bg-gray-800 text-gray-300',
}

function FlagBadge({ flag }: { flag: string | null }) {
  if (!flag) return null
  const style = FLAG_STYLES[flag] ?? 'bg-gray-800 text-gray-400'
  return (
    <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${style}`}>
      {flag}
    </span>
  )
}

// ─── Section card ─────────────────────────────────────────────────────────────

function SectionCard({
  title,
  count,
  empty,
  children,
}: {
  title: string
  count: number
  empty: boolean
  children: React.ReactNode
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-white">{title}</h2>
        <span className="text-xs font-mono text-gray-500">
          {count === 0 ? 'no data' : `${count} rows`}
        </span>
      </div>
      {empty ? (
        <div className="px-5 py-6 text-center">
          <p className="text-sm text-gray-600">No data synced yet.</p>
          <p className="text-xs text-gray-700 mt-1">
            Run <code className="text-gray-500">python scripts/sync_openf1_session.py --session-key &lt;key&gt;</code>
          </p>
        </div>
      ) : (
        children
      )}
    </div>
  )
}

// ─── Laps section ─────────────────────────────────────────────────────────────

function LapsSection({ laps }: { laps: Lap[] }) {
  // Group by driver, compute per-driver stats
  const byDriver: Record<number, Lap[]> = {}
  for (const lap of laps) {
    if (!byDriver[lap.driver_number]) byDriver[lap.driver_number] = []
    byDriver[lap.driver_number].push(lap)
  }

  const driverRows = Object.entries(byDriver)
    .map(([driverNum, driverLaps]) => {
      const racingLaps = driverLaps.filter(l => !l.is_pit_out_lap && l.lap_duration != null)
      const fastest = racingLaps.length
        ? Math.min(...racingLaps.map(l => l.lap_duration!))
        : null
      return {
        driverNumber: Number(driverNum),
        lapCount: driverLaps.length,
        fastest,
        pitOuts: driverLaps.filter(l => l.is_pit_out_lap).length,
      }
    })
    .sort((a, b) => (a.fastest ?? Infinity) - (b.fastest ?? Infinity))

  return (
    <SectionCard title="Laps" count={laps.length} empty={laps.length === 0}>
      <div className="px-5 py-3 border-b border-gray-800/50">
        <p className="text-xs text-gray-500">
          {laps.length} laps across {driverRows.length} drivers
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-800 text-gray-600 uppercase tracking-wider">
              <th className="px-5 py-2 text-left font-medium">Driver #</th>
              <th className="px-5 py-2 text-right font-medium">Laps</th>
              <th className="px-5 py-2 text-right font-medium">Fastest Lap</th>
              <th className="px-5 py-2 text-right font-medium">Pit-Out Laps</th>
            </tr>
          </thead>
          <tbody>
            {driverRows.map(row => (
              <tr key={row.driverNumber} className="border-b border-gray-800/40 last:border-0 hover:bg-gray-800/20">
                <td className="px-5 py-2 font-mono text-white">{row.driverNumber}</td>
                <td className="px-5 py-2 text-right text-gray-400">{row.lapCount}</td>
                <td className="px-5 py-2 text-right font-mono text-gray-300">
                  {formatLapTime(row.fastest)}
                </td>
                <td className="px-5 py-2 text-right text-gray-600">{row.pitOuts || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  )
}

// ─── Stints section ───────────────────────────────────────────────────────────

function StintsSection({ stints }: { stints: Stint[] }) {
  return (
    <SectionCard title="Stints" count={stints.length} empty={stints.length === 0}>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-800 text-gray-600 uppercase tracking-wider">
              <th className="px-5 py-2 text-left font-medium">Driver #</th>
              <th className="px-5 py-2 text-left font-medium">Stint</th>
              <th className="px-5 py-2 text-left font-medium">Compound</th>
              <th className="px-5 py-2 text-right font-medium">Laps</th>
              <th className="px-5 py-2 text-right font-medium">Tyre Age</th>
            </tr>
          </thead>
          <tbody>
            {stints.map(stint => (
              <tr key={stint.id} className="border-b border-gray-800/40 last:border-0 hover:bg-gray-800/20">
                <td className="px-5 py-2 font-mono text-white">{stint.driver_number}</td>
                <td className="px-5 py-2 text-gray-500">{stint.stint_number ?? '—'}</td>
                <td className="px-5 py-2">
                  <CompoundBadge compound={stint.compound} />
                </td>
                <td className="px-5 py-2 text-right text-gray-400 font-mono">
                  {stint.lap_start != null && stint.lap_end != null
                    ? `${stint.lap_start}→${stint.lap_end}`
                    : (stint.lap_start ?? '—')}
                </td>
                <td className="px-5 py-2 text-right text-gray-600">
                  {stint.tyre_age_at_start != null ? `+${stint.tyre_age_at_start}` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  )
}

// ─── Race control section ─────────────────────────────────────────────────────

function RaceControlSection({ messages }: { messages: RaceControlMessage[] }) {
  return (
    <SectionCard title="Race Control" count={messages.length} empty={messages.length === 0}>
      <div className="divide-y divide-gray-800/50">
        {messages.map(msg => (
          <div key={msg.id} className="px-5 py-2.5 flex items-start gap-3 hover:bg-gray-800/20">
            <span className="font-mono text-gray-600 text-xs shrink-0 w-20 pt-0.5">
              {formatTime(msg.date)}
            </span>
            <span className="text-gray-600 text-xs shrink-0 w-12 pt-0.5 text-right">
              {msg.lap_number != null ? `Lap ${msg.lap_number}` : ''}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-300 leading-snug">{msg.message}</p>
              {msg.driver_number != null && (
                <p className="text-xs text-gray-600 mt-0.5">Driver #{msg.driver_number}</p>
              )}
            </div>
            <div className="shrink-0">
              <FlagBadge flag={msg.flag} />
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  )
}

// ─── Weather section ──────────────────────────────────────────────────────────

function WeatherSection({ samples }: { samples: WeatherSample[] }) {
  const withData = samples.filter(s => s.air_temperature != null)
  const airTemps = withData.map(s => s.air_temperature!)
  const trackTemps = samples.filter(s => s.track_temperature != null).map(s => s.track_temperature!)
  const hadRain = samples.some(s => s.rainfall === true)

  const avg = (arr: number[]) =>
    arr.length ? (arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(1) : '—'

  const statItems = [
    { label: 'Air Temp (avg)', value: airTemps.length ? `${avg(airTemps)} °C` : '—' },
    { label: 'Air Temp (range)', value: airTemps.length ? `${Math.min(...airTemps).toFixed(1)}–${Math.max(...airTemps).toFixed(1)} °C` : '—' },
    { label: 'Track Temp (avg)', value: trackTemps.length ? `${avg(trackTemps)} °C` : '—' },
    { label: 'Rainfall', value: hadRain ? 'Yes' : 'No' },
    { label: 'Samples', value: samples.length },
  ]

  return (
    <SectionCard title="Weather" count={samples.length} empty={samples.length === 0}>
      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-px bg-gray-800/50 border-b border-gray-800">
        {statItems.map(item => (
          <div key={item.label} className="bg-gray-900 px-4 py-3">
            <p className="text-gray-600 text-xs mb-0.5">{item.label}</p>
            <p className={`text-sm font-mono font-medium ${item.label === 'Rainfall' && hadRain ? 'text-blue-400' : 'text-gray-300'}`}>
              {item.value}
            </p>
          </div>
        ))}
      </div>
      {/* Sample readings table */}
      <div className="overflow-x-auto max-h-64 overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-gray-900 z-10">
            <tr className="border-b border-gray-800 text-gray-600 uppercase tracking-wider">
              <th className="px-5 py-2 text-left font-medium">Time</th>
              <th className="px-5 py-2 text-right font-medium">Air °C</th>
              <th className="px-5 py-2 text-right font-medium">Track °C</th>
              <th className="px-5 py-2 text-right font-medium">Humidity %</th>
              <th className="px-5 py-2 text-right font-medium">Wind m/s</th>
              <th className="px-5 py-2 text-right font-medium">Rain</th>
            </tr>
          </thead>
          <tbody>
            {samples.map(s => (
              <tr key={s.id} className="border-b border-gray-800/30 last:border-0 hover:bg-gray-800/20">
                <td className="px-5 py-1.5 font-mono text-gray-500">{formatTime(s.date)}</td>
                <td className="px-5 py-1.5 text-right text-gray-300">{s.air_temperature?.toFixed(1) ?? '—'}</td>
                <td className="px-5 py-1.5 text-right text-gray-400">{s.track_temperature?.toFixed(1) ?? '—'}</td>
                <td className="px-5 py-1.5 text-right text-gray-500">{s.humidity?.toFixed(0) ?? '—'}</td>
                <td className="px-5 py-1.5 text-right text-gray-500">{s.wind_speed?.toFixed(1) ?? '—'}</td>
                <td className="px-5 py-1.5 text-right">
                  {s.rainfall ? (
                    <span className="text-blue-400">Yes</span>
                  ) : (
                    <span className="text-gray-700">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  )
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div>
        <div className="h-3 w-24 bg-gray-800 rounded mb-6" />
        <div className="h-8 w-64 bg-gray-800 rounded mb-2" />
        <div className="h-4 w-48 bg-gray-800 rounded" />
      </div>
      {Array.from({ length: 4 }, (_, i) => (
        <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl h-40" />
      ))}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SessionDetail() {
  const { id } = useParams<{ id: string }>()
  const sessionId = Number(id)

  const [session, setSession] = useState<SessionDetail | null>(null)
  const [laps, setLaps] = useState<Lap[]>([])
  const [stints, setStints] = useState<Stint[]>([])
  const [raceControl, setRaceControl] = useState<RaceControlMessage[]>([])
  const [weather, setWeather] = useState<WeatherSample[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionId) return
    setLoading(true)
    Promise.all([
      getSession(sessionId),
      getSessionLaps(sessionId),
      getSessionStints(sessionId),
      getSessionRaceControl(sessionId),
      getSessionWeather(sessionId),
    ])
      .then(([sess, lapsData, stintsData, rcData, weatherData]) => {
        setSession(sess)
        setLaps(lapsData)
        setStints(stintsData)
        setRaceControl(rcData)
        setWeather(weatherData)
      })
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load session'))
      .finally(() => setLoading(false))
  }, [sessionId])

  if (loading) {
    return (
      <div className="page-enter">
        <LoadingSkeleton />
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="page-enter">
        <Link to="/calendar" className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
          ← Calendar
        </Link>
        <div className="mt-8 text-center">
          <p className="text-red-400 font-medium">Session not found</p>
          <p className="text-gray-600 text-sm mt-1">{error}</p>
        </div>
      </div>
    )
  }

  const hasSyncedData = session.openf1_session_key != null

  return (
    <div className="page-enter space-y-6">
      {/* Back link */}
      <Link to="/calendar" className="text-xs text-gray-600 hover:text-gray-400 transition-colors inline-block">
        ← Calendar
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{session.session_name}</h1>
          <p className="text-gray-400 text-sm mt-0.5">
            {session.race_name}
            {session.circuit_short_name && ` · ${session.circuit_short_name}`}
            {session.country_name && `, ${session.country_name}`}
          </p>
          <p className="text-gray-600 text-xs mt-1 font-mono">
            {formatSessionDate(session.start_time)}
          </p>
        </div>
        <div className="text-right shrink-0">
          {hasSyncedData ? (
            <span className="text-xs bg-green-950 text-green-400 border border-green-800 px-2 py-1 rounded-full">
              Data synced
            </span>
          ) : (
            <span className="text-xs bg-gray-800 text-gray-500 border border-gray-700 px-2 py-1 rounded-full">
              Not synced
            </span>
          )}
        </div>
      </div>

      {/* Data sections */}
      <LapsSection laps={laps} />
      <StintsSection stints={stints} />
      <RaceControlSection messages={raceControl} />
      <WeatherSection samples={weather} />
    </div>
  )
}
