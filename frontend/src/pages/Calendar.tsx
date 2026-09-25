import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  getCalendar, getReminders, createReminder, getRaceSessions,
  getFavoriteDrivers, getFavoriteTeams,
} from '../services/api'
import { useAuth } from '../context/AuthContext'
import type { Race, Session } from '../types'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'TBC'
  // date-only strings are UTC midnight — force UTC to avoid off-by-one for users west of UTC
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

function formatSessionTime(isoStr: string | null): string {
  if (!isoStr) return 'TBA'
  return new Date(isoStr).toLocaleString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  })
}

function isPast(dateStr: string | null): boolean {
  if (!dateStr) return false
  return new Date(dateStr) < new Date()
}

function isSessionPast(isoStr: string | null): boolean {
  if (!isoStr) return false
  return new Date(isoStr) < new Date()
}

function isNext(race: Race, allRaces: Race[]): boolean {
  const upcoming = allRaces.find(r => !isPast(r.start_date))
  return upcoming?.id === race.id
}

const SESSION_COLORS: Record<string, string> = {
  fp1:              'bg-slate-600',
  fp2:              'bg-slate-600',
  fp3:              'bg-slate-600',
  sprint_qualifying: 'bg-orange-500',
  sprint:           'bg-orange-500',
  qualifying:       'bg-yellow-500',
  race:             'bg-red-600',
}

const PODIUM_STYLE: Record<number, string> = {
  1: 'text-yellow-400',
  2: 'text-gray-300',
  3: 'text-amber-600',
}

// ─── SessionPanel ────────────────────────────────────────────────────────────

type SessionReminderStatus = 'idle' | 'loading' | 'success' | 'error'

function SessionPanel({
  raceId,
  raceName,
  token,
  isAuthenticated,
  remindedSessionIds,
}: {
  raceId: number
  raceName: string
  token: string | null
  isAuthenticated: boolean
  remindedSessionIds: Set<number>
}) {
  const [sessions, setSessions] = useState<Session[] | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [sessionReminderStatus, setSessionReminderStatus] = useState<Record<number, SessionReminderStatus>>({})
  const [sessionReminderErrors, setSessionReminderErrors] = useState<Record<number, string>>({})

  useEffect(() => {
    getRaceSessions(raceId)
      .then(setSessions)
      .catch(() => setLoadError(true))
  }, [raceId])

  async function handleSessionReminder(session: Session) {
    if (!token) return
    setSessionReminderStatus(prev => ({ ...prev, [session.id]: 'loading' }))
    try {
      await createReminder(token, {
        title: `${raceName} – ${session.session_name}`,
        reminder_time: session.start_time ?? new Date().toISOString(),
        session_id: session.id,
      })
      setSessionReminderStatus(prev => ({ ...prev, [session.id]: 'success' }))
    } catch (e) {
      setSessionReminderStatus(prev => ({ ...prev, [session.id]: 'error' }))
      setSessionReminderErrors(prev => ({
        ...prev,
        [session.id]: e instanceof Error ? e.message : 'Failed',
      }))
    }
  }

  if (loadError) {
    return (
      <div className="px-5 pb-4 pt-1">
        <p className="text-xs text-gray-600">Session data unavailable.</p>
      </div>
    )
  }

  if (!sessions) {
    return (
      <div className="px-5 pb-4 pt-1 space-y-2">
        {Array.from({ length: 5 }, (_, i) => (
          <div key={i} className="flex items-center gap-3 animate-pulse">
            <div className="h-2 w-2 rounded-full bg-gray-800 shrink-0" />
            <div className="h-3 bg-gray-800 rounded w-24" />
            <div className="h-3 bg-gray-800 rounded w-36 ml-auto" />
          </div>
        ))}
      </div>
    )
  }

  if (sessions.length === 0) {
    return (
      <div className="px-5 pb-4 pt-1">
        <p className="text-xs text-gray-600">No sessions found for this race.</p>
      </div>
    )
  }

  return (
    <div className="px-5 pb-4 pt-1 border-t border-gray-800/60">
      <div className="space-y-1 mt-2">
        {sessions.map(session => {
          const past = isSessionPast(session.start_time)
          const dotColor = SESSION_COLORS[session.session_type] ?? 'bg-gray-600'
          const status = remindedSessionIds.has(session.id)
            ? 'success'
            : (sessionReminderStatus[session.id] ?? 'idle')
          const errMsg = sessionReminderErrors[session.id]

          return (
            <div
              key={session.id}
              className="flex items-center gap-3 py-1.5"
            >
              {/* Session type dot */}
              <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${dotColor}`} />

              {/* Session name — links to detail page for past sessions */}
              {past ? (
                <Link
                  to={`/sessions/${session.id}`}
                  className="text-xs font-medium w-28 shrink-0 text-gray-300 hover:text-white transition-colors underline-offset-2 hover:underline"
                >
                  {session.session_name}
                </Link>
              ) : (
                <span className="text-xs font-medium w-28 shrink-0 text-gray-300">
                  {session.session_name}
                </span>
              )}

              {/* Time — converted to the viewer's local timezone automatically */}
              <span className="text-xs text-gray-400 font-mono flex-1">
                {formatSessionTime(session.start_time)}
              </span>

              {/* Reminder button — upcoming sessions only */}
              {!past && session.start_time && (
                <div className="shrink-0 w-28 text-right">
                  {!isAuthenticated ? (
                    <Link
                      to="/login"
                      className="text-xs text-gray-700 hover:text-gray-500 transition-colors"
                    >
                      Log in
                    </Link>
                  ) : status === 'success' ? (
                    <span className="text-xs text-green-500">Reminder set ✓</span>
                  ) : status === 'error' ? (
                    <span className="text-xs text-red-400">{errMsg}</span>
                  ) : (
                    <button
                      onClick={() => handleSessionReminder(session)}
                      disabled={status === 'loading'}
                      className="text-xs text-gray-600 hover:text-white border border-gray-800 hover:border-gray-600 px-2 py-0.5 rounded-md transition-colors duration-150 disabled:opacity-40"
                    >
                      {status === 'loading' ? 'Adding…' : '+ Remind'}
                    </button>
                  )}
                </div>
              )}

              {/* Dashboard, Strategy, and Analytics links for past sessions */}
              {past ? (
                <div className="shrink-0 w-32 text-right space-y-0.5">
                  <Link
                    to={`/sessions/${session.id}/dashboard`}
                    className="block text-xs text-gray-400 hover:text-red-400 transition-colors"
                  >
                    Dashboard →
                  </Link>
                  <Link
                    to={`/sessions/${session.id}/strategy`}
                    className="block text-xs text-gray-400 hover:text-orange-400 transition-colors"
                  >
                    Strategy →
                  </Link>
                  <Link
                    to={`/sessions/${session.id}/analytics`}
                    className="block text-xs text-gray-400 hover:text-purple-400 transition-colors"
                  >
                    Analytics →
                  </Link>
                </div>
              ) : !session.start_time ? (
                <div className="shrink-0 w-32" />
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── ResultTeaser ─────────────────────────────────────────────────────────────
// Quick podium + fastest-lap strip shown directly on a past race's collapsed
// card, so viewers don't have to expand/click through to see who won.

function ResultTeaser({
  race,
  favoriteDriverNames,
  favoriteTeamNames,
  highlightFavorites,
}: {
  race: Race
  favoriteDriverNames: Set<string>
  favoriteTeamNames: Set<string>
  highlightFavorites: boolean
}) {
  const teaser = race.teaser
  if (!teaser || (teaser.podium.length === 0 && !teaser.fastest_lap_driver)) return null

  function isFavorite(driverName: string, teamName: string | null): boolean {
    if (!highlightFavorites) return false
    return favoriteDriverNames.has(driverName) || (teamName !== null && favoriteTeamNames.has(teamName))
  }

  return (
    <div className="px-5 pb-3 -mt-1 flex flex-wrap items-center gap-x-5 gap-y-1.5">
      {teaser.podium.map(entry => (
        <span
          key={entry.position}
          className={`text-xs flex items-center gap-1.5 ${
            isFavorite(entry.driver_name, entry.team_name) ? 'text-red-400 font-semibold' : 'text-gray-500'
          }`}
        >
          <span className={`font-bold ${PODIUM_STYLE[entry.position] ?? 'text-gray-600'}`}>
            P{entry.position}
          </span>
          {entry.driver_name}
        </span>
      ))}
      {teaser.fastest_lap_driver && (
        <span
          className={`text-xs flex items-center gap-1.5 ${
            isFavorite(teaser.fastest_lap_driver, null) ? 'text-red-400 font-semibold' : 'text-gray-600'
          }`}
        >
          <span className="text-purple-400 font-bold">FL</span>
          {teaser.fastest_lap_driver}
          {teaser.fastest_lap_time && (
            <span className="text-gray-700 font-mono">{teaser.fastest_lap_time.toFixed(3)}s</span>
          )}
        </span>
      )}
    </div>
  )
}

// ─── RaceRow ──────────────────────────────────────────────────────────────────

type ReminderStatus = 'idle' | 'loading' | 'success' | 'error'

function RaceRow({
  race,
  allRaces,
  hasReminder,
  remindedSessionIds,
  favoriteDriverNames,
  favoriteTeamNames,
  highlightFavorites,
}: {
  race: Race
  allRaces: Race[]
  hasReminder: boolean
  remindedSessionIds: Set<number>
  favoriteDriverNames: Set<string>
  favoriteTeamNames: Set<string>
  highlightFavorites: boolean
}) {
  const { isAuthenticated, token } = useAuth()
  const past = isPast(race.start_date)
  const next = isNext(race, allRaces)
  const [reminderStatus, setReminderStatus] = useState<ReminderStatus>(hasReminder ? 'success' : 'idle')
  const [reminderError, setReminderError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)

  function toggleExpanded() {
    setExpanded(prev => !prev)
  }

  async function handleAddReminder() {
    if (!token) return
    setReminderStatus('loading')
    try {
      await createReminder(token, {
        title: `${race.name} – Race Day`,
        reminder_time: `${race.start_date}T09:00:00Z`,
        race_id: race.id,
      })
      setReminderStatus('success')
    } catch (e) {
      setReminderStatus('error')
      setReminderError(e instanceof Error ? e.message : 'Failed to create reminder')
    }
  }

  // Season-progress accent — a clear signal beyond just dimming, per race status.
  const accentClass = next
    ? 'border-l-2 border-red-500 bg-red-950/10'
    : past
      ? 'border-l-2 border-emerald-800/60'
      : 'border-l-2 border-transparent'

  return (
    <div className={`border-b border-gray-800 last:border-0 ${accentClass}`}>
      {/* Race header row — click anywhere in it to expand the session timeline */}
      <div
        role="button"
        tabIndex={0}
        onClick={toggleExpanded}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleExpanded() } }}
        className={`flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-gray-800/30 transition-colors duration-150 ${past ? 'opacity-70' : ''}`}
      >
        {/* Round badge */}
        <span className="text-gray-600 text-xs font-mono w-7 shrink-0 text-right">
          R{race.round}
        </span>

        {/* Race info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className={`font-semibold text-sm truncate ${past ? 'text-gray-400' : 'text-white'}`}>
              {race.name}
            </p>
            {race.is_sprint_weekend && (
              <span className="text-[10px] uppercase tracking-wide font-semibold text-orange-400 bg-orange-500/10 px-1.5 py-0.5 rounded">
                Sprint
              </span>
            )}
            <span className="text-[10px] uppercase tracking-wide text-gray-600 border border-gray-800 px-1.5 py-0.5 rounded">
              {race.circuit_type}
            </span>
          </div>
          <p className="text-gray-600 text-xs truncate mt-0.5">{race.circuit_name ?? race.country ?? '—'}</p>
        </div>

        {/* Status / date */}
        <div className="text-right shrink-0">
          {next && (
            <span className="text-xs bg-red-600 text-white px-2 py-0.5 rounded-full font-medium block mb-1">
              Next Race
            </span>
          )}
          {past && !next && (
            <span className="text-xs text-emerald-700 font-medium block mb-1">Completed</span>
          )}
          <p className={`text-xs font-mono ${past ? 'text-gray-600' : 'text-gray-400'}`}>
            {formatDate(race.start_date)}
          </p>
        </div>

        {/* Race-level reminder — stopPropagation so clicking it doesn't also toggle the row */}
        {!past && race.start_date ? (
          <div className="shrink-0 w-28 text-right" onClick={e => e.stopPropagation()}>
            {!isAuthenticated ? (
              <Link to="/login" className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
                Log in to remind
              </Link>
            ) : reminderStatus === 'success' ? (
              <span className="text-xs text-green-500">Reminder set ✓</span>
            ) : reminderStatus === 'error' ? (
              <span className="text-xs text-red-400">{reminderError}</span>
            ) : (
              <button
                onClick={handleAddReminder}
                disabled={reminderStatus === 'loading'}
                className="text-xs text-gray-500 hover:text-white border border-gray-800 hover:border-gray-600 px-2.5 py-1 rounded-lg transition-colors duration-150 disabled:opacity-40"
              >
                {reminderStatus === 'loading' ? 'Adding…' : '+ Reminder'}
              </button>
            )}
          </div>
        ) : (
          <div className="shrink-0 w-28" />
        )}

        {/* Expand indicator — purely visual now; the whole row above already toggles */}
        <span className="shrink-0 text-gray-700 p-1" aria-hidden="true">
          <svg
            className={`w-3.5 h-3.5 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
            fill="none" stroke="currentColor" strokeWidth={2.5}
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </div>

      {/* Result teaser — past races, shown while collapsed */}
      {past && !expanded && (
        <ResultTeaser
          race={race}
          favoriteDriverNames={favoriteDriverNames}
          favoriteTeamNames={favoriteTeamNames}
          highlightFavorites={highlightFavorites}
        />
      )}

      {/* Session panel — lazy rendered when expanded */}
      {expanded && (
        <SessionPanel
          raceId={race.id}
          raceName={race.name}
          token={token}
          isAuthenticated={isAuthenticated}
          remindedSessionIds={remindedSessionIds}
        />
      )}
    </div>
  )
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <div className="flex items-center gap-4 px-5 py-4 border-b border-gray-800 last:border-0 animate-pulse">
      <div className="h-3 w-6 bg-gray-800 rounded" />
      <div className="flex-1">
        <div className="h-4 bg-gray-800 rounded w-3/5 mb-1" />
        <div className="h-3 bg-gray-800 rounded w-2/5" />
      </div>
      <div className="h-3 w-20 bg-gray-800 rounded" />
    </div>
  )
}

// ─── Filters ──────────────────────────────────────────────────────────────────

type CircuitFilter = 'all' | 'street' | 'permanent'
type FormatFilter = 'all' | 'sprint' | 'standard'

function FilterButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`text-xs px-3 py-1.5 rounded-lg transition-colors duration-150 ${
        active ? 'bg-red-600 text-white font-medium' : 'text-gray-400 hover:text-white hover:bg-gray-800 border border-gray-800'
      }`}
    >
      {children}
    </button>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Calendar() {
  const { token, isAuthenticated } = useAuth()
  const [races, setRaces] = useState<Race[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [remindedRaceIds, setRemindedRaceIds] = useState<Set<number>>(new Set())
  const [remindedSessionIds, setRemindedSessionIds] = useState<Set<number>>(new Set())

  const [circuitFilter, setCircuitFilter] = useState<CircuitFilter>('all')
  const [formatFilter, setFormatFilter] = useState<FormatFilter>('all')
  const [highlightFavorites, setHighlightFavorites] = useState(true)
  const [favoriteDriverNames, setFavoriteDriverNames] = useState<Set<string>>(new Set())
  const [favoriteTeamNames, setFavoriteTeamNames] = useState<Set<string>>(new Set())

  useEffect(() => {
    getCalendar()
      .then(setRaces)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!token) return
    getReminders(token)
      .then(reminders => {
        const raceIds = new Set(
          reminders
            .filter(r => r.session_id === null)
            .map(r => r.race_id)
            .filter((id): id is number => id !== null)
        )
        const sessionIds = new Set(
          reminders
            .map(r => r.session_id)
            .filter((id): id is number => id !== null)
        )
        setRemindedRaceIds(raceIds)
        setRemindedSessionIds(sessionIds)
      })
      .catch(() => {})
  }, [token])

  useEffect(() => {
    if (!token) return
    Promise.all([getFavoriteDrivers(token), getFavoriteTeams(token)])
      .then(([drivers, teams]) => {
        setFavoriteDriverNames(new Set(drivers.map(d => d.driver.full_name)))
        setFavoriteTeamNames(new Set(teams.map(t => t.team.name)))
      })
      .catch(() => {})
  }, [token])

  const filteredRaces = useMemo(() => {
    if (!races) return null
    return races.filter(r => {
      if (circuitFilter !== 'all' && r.circuit_type !== circuitFilter) return false
      if (formatFilter === 'sprint' && !r.is_sprint_weekend) return false
      if (formatFilter === 'standard' && r.is_sprint_weekend) return false
      return true
    })
  }, [races, circuitFilter, formatFilter])

  const completedCount = races?.filter(r => isPast(r.start_date)).length ?? 0
  const totalCount = races?.length ?? 0
  const progressPct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0
  const hasFavorites = favoriteDriverNames.size > 0 || favoriteTeamNames.size > 0

  return (
    <div className="page-enter">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white">Race Calendar</h1>
        <p className="text-gray-400 mt-1">The full 2026 Formula 1 season schedule.</p>
      </div>

      {/* Season progress */}
      {totalCount > 0 && (
        <div className="mb-6">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-1.5">
            <span>{completedCount} of {totalCount} races completed</span>
            <span>{progressPct}%</span>
          </div>
          <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-red-600 rounded-full transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <span className="text-xs text-gray-600 mr-1">Circuit:</span>
        <FilterButton active={circuitFilter === 'all'} onClick={() => setCircuitFilter('all')}>All</FilterButton>
        <FilterButton active={circuitFilter === 'street'} onClick={() => setCircuitFilter('street')}>Street</FilterButton>
        <FilterButton active={circuitFilter === 'permanent'} onClick={() => setCircuitFilter('permanent')}>Permanent</FilterButton>

        <span className="text-xs text-gray-600 ml-3 mr-1">Weekend:</span>
        <FilterButton active={formatFilter === 'all'} onClick={() => setFormatFilter('all')}>All</FilterButton>
        <FilterButton active={formatFilter === 'sprint'} onClick={() => setFormatFilter('sprint')}>Sprint</FilterButton>
        <FilterButton active={formatFilter === 'standard'} onClick={() => setFormatFilter('standard')}>Standard</FilterButton>

        {isAuthenticated && hasFavorites && (
          <label className="flex items-center gap-1.5 text-xs text-gray-400 ml-3 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={highlightFavorites}
              onChange={e => setHighlightFavorites(e.target.checked)}
              className="accent-red-600"
            />
            Highlight my favourites
          </label>
        )}
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {loading && Array.from({ length: 8 }, (_, i) => <SkeletonRow key={i} />)}

        {error && (
          <div className="p-8 text-center">
            <p className="text-red-400 font-medium">Failed to load calendar</p>
            <p className="text-gray-500 text-sm mt-1">{error}</p>
            <p className="text-gray-600 text-xs mt-2">Make sure the backend is running on port 8000.</p>
          </div>
        )}

        {filteredRaces && filteredRaces.length === 0 && !loading && (
          <div className="p-8 text-center">
            <p className="text-gray-400 font-medium">No races match these filters.</p>
          </div>
        )}

        {filteredRaces && races && filteredRaces.map(race => (
          <RaceRow
            key={race.id}
            race={race}
            allRaces={races}
            hasReminder={remindedRaceIds.has(race.id)}
            remindedSessionIds={remindedSessionIds}
            favoriteDriverNames={favoriteDriverNames}
            favoriteTeamNames={favoriteTeamNames}
            highlightFavorites={highlightFavorites}
          />
        ))}
      </div>
    </div>
  )
}
