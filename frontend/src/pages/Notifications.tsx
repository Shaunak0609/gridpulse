import { useEffect, useState } from 'react'
import { getNotifications, markNotificationRead, deleteNotification } from '../services/api'
import { useAuth } from '../context/AuthContext'
import type { Notification } from '../types'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  })
}

// ─── Type config ──────────────────────────────────────────────────────────────

// Each notification type maps to an icon variant, badge label, and color set.
// The icon is rendered differently when the notification is already read (dimmed).

type IconVariant = 'star' | 'bolt' | 'tire' | 'flag' | 'warning' | 'bell' | 'dot'

interface TypeConfig {
  icon: IconVariant
  iconColor: string   // Tailwind text-* class when unread
  badge: string
  badgeClass: string  // full badge Tailwind classes
}

function getTypeConfig(type: string): TypeConfig {
  switch (type) {
    case 'favorite_driver_standing':
      return {
        icon: 'star',
        iconColor: 'text-amber-500',
        badge: 'Driver update',
        badgeClass: 'text-amber-600 bg-amber-950/60 border-amber-900/50',
      }
    case 'favorite_driver_wins':
      return {
        icon: 'star',
        iconColor: 'text-amber-500',
        badge: 'Race wins',
        badgeClass: 'text-amber-600 bg-amber-950/60 border-amber-900/50',
      }
    case 'favorite_driver_fastest_lap':
      return {
        icon: 'bolt',
        iconColor: 'text-purple-400',
        badge: 'Fastest lap',
        badgeClass: 'text-purple-400 bg-purple-950/60 border-purple-900/50',
      }
    case 'favorite_driver_strategy':
      return {
        icon: 'tire',
        iconColor: 'text-orange-400',
        badge: 'Strategy',
        badgeClass: 'text-orange-400 bg-orange-950/60 border-orange-900/50',
      }
    case 'favorite_driver_rc_mention':
      return {
        icon: 'flag',
        iconColor: 'text-yellow-400',
        badge: 'Race control',
        badgeClass: 'text-yellow-500 bg-yellow-950/60 border-yellow-900/50',
      }
    case 'favorite_driver_lap_comparison':
      return {
        icon: 'warning',
        iconColor: 'text-slate-400',
        badge: 'Lap note',
        badgeClass: 'text-slate-400 bg-slate-800/60 border-slate-700/50',
      }
    case 'reminder_created':
      return {
        icon: 'bell',
        iconColor: 'text-blue-400',
        badge: 'Reminder',
        badgeClass: 'text-blue-400 bg-blue-950/60 border-blue-900/50',
      }
    default:
      return {
        icon: 'dot',
        iconColor: 'text-red-500',
        badge: '',
        badgeClass: '',
      }
  }
}

// ─── SVG icons ────────────────────────────────────────────────────────────────

function StarIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  )
}

function BoltIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
    </svg>
  )
}

function TireIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="3.5" />
    </svg>
  )
}

function FlagIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 3v18" />
      <path d="M4 3h14l-3.5 4.5L18 12H4" />
    </svg>
  )
}

function WarningIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  )
}

function BellIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 01-3.46 0" />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v6M14 11v6" />
      <path d="M9 6V4h6v2" />
    </svg>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function NotificationIcon({ type, read }: { type: string; read: boolean }) {
  const config = getTypeConfig(type)
  const colorClass = read ? 'text-gray-600' : config.iconColor

  if (config.icon === 'dot') {
    return (
      <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${read ? 'bg-gray-700' : 'bg-red-500'}`} />
    )
  }

  const iconMap: Record<string, JSX.Element> = {
    star: <StarIcon />,
    bolt: <BoltIcon />,
    tire: <TireIcon />,
    flag: <FlagIcon />,
    warning: <WarningIcon />,
    bell: <BellIcon />,
  }

  return (
    <span className={`mt-0.5 shrink-0 ${colorClass}`}>
      {iconMap[config.icon]}
    </span>
  )
}

function NotificationBadge({ type }: { type: string }) {
  const { badge, badgeClass } = getTypeConfig(type)
  if (!badge) return null
  return (
    <span className={`inline-block align-middle text-[10px] font-semibold uppercase tracking-wide border px-1.5 py-0.5 rounded ml-2 ${badgeClass}`}>
      {badge}
    </span>
  )
}

function NotificationRow({
  notification,
  onMarkRead,
  onDelete,
}: {
  notification: Notification
  onMarkRead: (id: number) => void
  onDelete: (id: number) => void
}) {
  const [busy, setBusy] = useState(false)

  function handleMarkRead() {
    setBusy(true)
    onMarkRead(notification.id)
  }

  function handleDelete() {
    setBusy(true)
    onDelete(notification.id)
  }

  return (
    <div
      className={`flex items-start gap-4 px-5 py-4 border-b border-gray-800 last:border-0 transition-colors duration-150
        ${notification.read ? 'opacity-50' : 'hover:bg-gray-800/50'}`}
    >
      {/* Type icon */}
      <NotificationIcon type={notification.type} read={notification.read} />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className={`font-semibold text-sm ${notification.read ? 'text-gray-400' : 'text-white'}`}>
          {notification.title}
          <NotificationBadge type={notification.type} />
        </p>
        {notification.message && (
          <p className="text-gray-500 text-xs mt-0.5 leading-relaxed break-words">{notification.message}</p>
        )}
        <p className="text-gray-700 text-xs font-mono mt-1">{formatDateTime(notification.created_at)}</p>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 shrink-0">
        {!notification.read && (
          <button
            onClick={handleMarkRead}
            disabled={busy}
            className="text-xs text-gray-500 hover:text-white border border-gray-800 hover:border-gray-600 px-2.5 py-1 rounded-lg transition-colors duration-150 disabled:opacity-40"
          >
            Mark read
          </button>
        )}
        <button
          onClick={handleDelete}
          disabled={busy}
          className="text-gray-600 hover:text-red-400 transition-colors duration-150 disabled:opacity-40"
          aria-label="Delete notification"
        >
          <TrashIcon />
        </button>
      </div>
    </div>
  )
}

function SkeletonRow() {
  return (
    <div className="flex items-start gap-4 px-5 py-4 border-b border-gray-800 last:border-0 animate-pulse">
      <div className="mt-1.5 w-2 h-2 rounded-full bg-gray-800 shrink-0" />
      <div className="flex-1">
        <div className="h-4 bg-gray-800 rounded w-2/5 mb-1.5" />
        <div className="h-3 bg-gray-800 rounded w-3/5 mb-1" />
        <div className="h-3 bg-gray-800 rounded w-1/4" />
      </div>
      <div className="h-6 w-20 bg-gray-800 rounded-lg" />
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Notifications() {
  const { token } = useAuth()
  const [notifications, setNotifications] = useState<Notification[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    getNotifications(token)
      .then(setNotifications)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [token])

  async function handleMarkRead(id: number) {
    if (!token) return
    try {
      const updated = await markNotificationRead(token, id)
      setNotifications(prev => prev?.map(n => (n.id === id ? updated : n)) ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to mark as read')
    }
  }

  async function handleDelete(id: number) {
    if (!token) return
    try {
      await deleteNotification(token, id)
      setNotifications(prev => prev?.filter(n => n.id !== id) ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete notification')
    }
  }

  const unreadCount = notifications?.filter(n => !n.read).length ?? 0

  return (
    <div className="page-enter max-w-2xl">
      {/* Header */}
      <div className="mb-8">
        <p className="text-red-500 text-xs font-semibold tracking-widest uppercase mb-3">
          Account
        </p>
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-white">Notifications</h1>
          {unreadCount > 0 && (
            <span className="text-xs bg-red-600 text-white font-semibold px-2 py-0.5 rounded-full">
              {unreadCount}
            </span>
          )}
        </div>
        <p className="text-gray-400 mt-1">Activity and updates for your account.</p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-6 px-4 py-3 bg-red-950/50 border border-red-800/50 rounded-xl">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* List */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {loading && Array.from({ length: 4 }, (_, i) => <SkeletonRow key={i} />)}

        {!loading && notifications?.length === 0 && (
          <div className="px-5 py-12 text-center">
            <p className="text-gray-400 font-medium">No notifications yet</p>
            <p className="text-gray-600 text-sm mt-1">
              Notifications appear here when you create reminders, favourite a driver, or generate session alerts.
            </p>
          </div>
        )}

        {notifications?.map(notification => (
          <NotificationRow
            key={notification.id}
            notification={notification}
            onMarkRead={handleMarkRead}
            onDelete={handleDelete}
          />
        ))}
      </div>
    </div>
  )
}
