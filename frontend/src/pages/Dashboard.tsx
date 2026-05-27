import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getDashboard } from '../services/api'
import { useAuth } from '../context/AuthContext'
import type { Dashboard } from '../types'

function SectionHeading({ title, linkTo, linkLabel }: { title: string; linkTo?: string; linkLabel?: string }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-white font-semibold text-lg">{title}</h2>
      {linkTo && (
        <Link to={linkTo} className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
          {linkLabel ?? 'View all'} →
        </Link>
      )}
    </div>
  )
}

function EmptyState({ message, linkTo, linkLabel }: {
  message: string
  linkTo?: string
  linkLabel?: string
}) {
  return (
    <div className="border border-dashed border-gray-800 rounded-xl px-6 py-8 text-center">
      <p className="text-gray-500 text-sm">{message}</p>
      {linkTo && (
        <Link
          to={linkTo}
          className="inline-block mt-4 text-xs font-medium text-white bg-gray-800 hover:bg-gray-700 border border-gray-700 hover:border-gray-600 px-4 py-1.5 rounded-lg transition-colors duration-150"
        >
          {linkLabel ?? 'Go there'} →
        </Link>
      )}
    </div>
  )
}

function SkeletonBlock({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-3">
          <div className="h-4 w-4 bg-gray-800 rounded-full shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="h-3 bg-gray-800 rounded w-2/3" />
            <div className="h-3 bg-gray-800 rounded w-1/3" />
          </div>
        </div>
      ))}
    </div>
  )
}

const SESSION_COLORS: Record<string, string> = {
  fp1: 'bg-blue-500',
  fp2: 'bg-blue-500',
  fp3: 'bg-blue-500',
  sprint_qualifying: 'bg-yellow-500',
  sprint: 'bg-orange-500',
  qualifying: 'bg-purple-500',
  race: 'bg-red-500',
}

function driverAlertIcon(type: string): { color: string; badge: string; icon: JSX.Element } {
  switch (type) {
    case 'favorite_driver_fastest_lap':
      return {
        color: 'text-purple-400',
        badge: 'Fastest lap',
        icon: (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
        ),
      }
    case 'favorite_driver_strategy':
      return {
        color: 'text-orange-400',
        badge: 'Strategy',
        icon: (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <circle cx="12" cy="12" r="9" />
            <circle cx="12" cy="12" r="3.5" />
          </svg>
        ),
      }
    case 'favorite_driver_rc_mention':
      return {
        color: 'text-yellow-400',
        badge: 'Race control',
        icon: (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 3v18" />
            <path d="M4 3h14l-3.5 4.5L18 12H4" />
          </svg>
        ),
      }
    case 'favorite_driver_lap_comparison':
      return {
        color: 'text-slate-400',
        badge: 'Lap note',
        icon: (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        ),
      }
    default:
      return {
        color: 'text-amber-500',
        badge: '',
        icon: (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
        ),
      }
  }
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  })
}

export default function Dashboard() {
  const { token } = useAuth()
  const [data, setData] = useState<Dashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    getDashboard(token)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [token])

  if (loading) {
    return (
      <div className="page-enter space-y-10">
        <div className="animate-pulse">
          <div className="h-8 w-48 bg-gray-800 rounded mb-2" />
          <div className="h-4 w-64 bg-gray-800 rounded" />
        </div>
        <SkeletonBlock rows={2} />
        <SkeletonBlock rows={2} />
        <SkeletonBlock rows={3} />
        <SkeletonBlock rows={3} />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="page-enter">
        <div className="bg-gray-900 border border-red-900/50 rounded-xl p-10 text-center">
          <p className="text-red-400 font-medium">Failed to load dashboard</p>
          <p className="text-gray-500 text-sm mt-1">{error ?? 'Unknown error'}</p>
        </div>
      </div>
    )
  }

  const { user, favorite_drivers, favorite_teams, upcoming_sessions, upcoming_reminders, recent_notifications } = data

  const DRIVER_UPDATE_TYPES = new Set([
    'favorite_driver_standing',
    'favorite_driver_wins',
    'favorite_driver_fastest_lap',
    'favorite_driver_strategy',
    'favorite_driver_rc_mention',
    'favorite_driver_lap_comparison',
  ])

  const driverUpdates = recent_notifications
    .filter(n => DRIVER_UPDATE_TYPES.has(n.type))
    .slice(0, 4)
  const otherNotifs = recent_notifications
    .filter(n => !DRIVER_UPDATE_TYPES.has(n.type))
    .slice(0, 3)

  return (
    <div className="page-enter space-y-10">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">
          Welcome back, {user.username ?? user.email.split('@')[0]}
        </h1>
        <p className="text-gray-500 mt-1 text-sm">Your personalised F1 overview.</p>
      </div>

      {/* Favourite Drivers */}
      <section>
        <SectionHeading title="Favourite Drivers" linkTo="/drivers" linkLabel="Browse drivers" />
        {favorite_drivers.length === 0 ? (
          <EmptyState
            message="You haven't favourited any drivers yet. Go to the Drivers page, open a driver, and tap the star."
            linkTo="/drivers"
            linkLabel="Browse drivers"
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {favorite_drivers.map(fav => (
              <Link
                key={fav.id}
                to={`/drivers/${fav.driver.id}`}
                className="bg-gray-900 border border-gray-800 hover:border-red-500/50 rounded-xl p-4 flex items-center gap-4 transition-colors"
              >
                <span className="text-red-500 font-black text-2xl font-mono w-8 text-right leading-none opacity-70 shrink-0">
                  {fav.driver.driver_number ?? '—'}
                </span>
                <div className="min-w-0">
                  <p className="text-white font-semibold text-sm truncate">{fav.driver.full_name}</p>
                  <p className="text-gray-500 text-xs truncate">{fav.driver.team?.name ?? 'No team'}</p>
                </div>
                <span className="ml-auto text-red-500 text-sm">★</span>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Driver Updates */}
      <section>
        <SectionHeading title="Driver Updates" linkTo="/notifications" linkLabel="All notifications" />
        {driverUpdates.length === 0 ? (
          <EmptyState
            message="No driver updates yet. Favourite a driver and updates will appear here when standings or session alerts are available."
            linkTo="/drivers"
            linkLabel="Browse drivers"
          />
        ) : (
          <div className="space-y-2">
            {driverUpdates.map(notif => {
              const { color, badge, icon } = driverAlertIcon(notif.type)
              return (
                <div
                  key={notif.id}
                  className={`border rounded-xl p-4 flex items-start gap-3 transition-colors ${
                    notif.read
                      ? 'bg-gray-900 border-gray-800 opacity-60'
                      : 'bg-gray-900 border-gray-800'
                  }`}
                >
                  <span className={`mt-0.5 shrink-0 ${notif.read ? 'text-gray-700' : color}`}>
                    {icon}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className={`text-sm font-medium ${notif.read ? 'text-gray-400' : 'text-white'}`}>
                      {notif.title}
                      {badge && !notif.read && (
                        <span className="ml-2 text-[10px] font-semibold uppercase tracking-wide text-gray-500 border border-gray-700 px-1.5 py-0.5 rounded align-middle">
                          {badge}
                        </span>
                      )}
                    </p>
                    {notif.message && (
                      <p className="text-gray-500 text-xs mt-0.5 leading-relaxed">{notif.message}</p>
                    )}
                  </div>
                  {!notif.read && (
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500 mt-1.5 shrink-0" />
                  )}
                </div>
              )
            })}
          </div>
        )}
      </section>

      {/* Favourite Teams */}
      <section>
        <SectionHeading title="Favourite Teams" linkTo="/teams" linkLabel="Browse teams" />
        {favorite_teams.length === 0 ? (
          <EmptyState
            message="You haven't favourited any teams yet. Go to the Teams page and tap the star on any constructor."
            linkTo="/teams"
            linkLabel="Browse teams"
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {favorite_teams.map(fav => (
              <div
                key={fav.id}
                className="bg-gray-900 border border-red-800/40 rounded-xl p-4 flex items-center gap-4"
              >
                <div className="h-1 w-6 rounded-full bg-red-500 shrink-0" />
                <div className="min-w-0">
                  <p className="text-white font-semibold text-sm truncate">{fav.team.name}</p>
                  <p className="text-gray-500 text-xs truncate">{fav.team.constructor_name}</p>
                </div>
                <span className="ml-auto text-red-500 text-sm">★</span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Upcoming Sessions */}
      <section>
        <SectionHeading title="Upcoming Sessions" linkTo="/calendar" linkLabel="Full calendar" />
        {upcoming_sessions.length === 0 ? (
          <EmptyState
            message="No upcoming sessions are scheduled right now."
            linkTo="/calendar"
            linkLabel="View calendar"
          />
        ) : (
          <div className="space-y-2">
            {upcoming_sessions.map(session => (
              <div
                key={session.id}
                className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-4"
              >
                <span className={`h-2 w-2 rounded-full shrink-0 ${SESSION_COLORS[session.session_type] ?? 'bg-gray-500'}`} />
                <div className="min-w-0 flex-1">
                  <p className="text-white text-sm font-medium truncate">{session.session_name}</p>
                  <p className="text-gray-500 text-xs">{formatDateTime(session.start_time)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Upcoming Reminders */}
      <section>
        <SectionHeading title="Upcoming Reminders" linkTo="/reminders" linkLabel="All reminders" />
        {upcoming_reminders.length === 0 ? (
          <EmptyState
            message="No upcoming reminders. Open the Race Calendar, expand any race, and set a reminder for a session."
            linkTo="/calendar"
            linkLabel="Open calendar"
          />
        ) : (
          <div className="space-y-2">
            {upcoming_reminders.map(reminder => (
              <div
                key={reminder.id}
                className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-4"
              >
                <span className="text-gray-600 text-base">🔔</span>
                <div className="min-w-0 flex-1">
                  <p className="text-white text-sm font-medium truncate">{reminder.title}</p>
                  <p className="text-gray-500 text-xs">{formatDateTime(reminder.reminder_time)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* AI Race Assistant shortcut */}
      <section>
        <Link
          to="/ai"
          className="group flex items-center gap-4 bg-gray-900 border border-gray-800 hover:border-red-500/40 rounded-xl px-5 py-4 transition-colors duration-200"
        >
          <div className="shrink-0 w-9 h-9 flex items-center justify-center rounded-lg bg-gray-800 group-hover:bg-red-950/60 transition-colors duration-200">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2l2 7h7l-5.5 4 2 7L12 16l-5.5 4 2-7L3 9h7z" />
            </svg>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-white text-sm font-semibold">AI Race Assistant</p>
            <p className="text-gray-500 text-xs mt-0.5">Ask questions about standings, sessions, and your favourites</p>
          </div>
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-gray-700 group-hover:text-gray-400 shrink-0 transition-colors duration-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      </section>

      {/* Recent Notifications — only shown when non-driver notifications exist */}
      {otherNotifs.length > 0 && (
        <section>
          <SectionHeading title="Recent Notifications" linkTo="/notifications" linkLabel="All notifications" />
          <div className="space-y-2">
            {otherNotifs.map(notif => (
              <div
                key={notif.id}
                className={`border rounded-xl p-4 flex items-start gap-4 transition-colors ${
                  notif.read ? 'bg-gray-900 border-gray-800' : 'bg-gray-900 border-red-900/40'
                }`}
              >
                <span className={`h-2 w-2 rounded-full mt-1.5 shrink-0 ${notif.read ? 'bg-gray-700' : 'bg-red-500'}`} />
                <div className="min-w-0">
                  <p className="text-white text-sm font-medium">{notif.title}</p>
                  {notif.message && <p className="text-gray-500 text-xs mt-0.5">{notif.message}</p>}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
