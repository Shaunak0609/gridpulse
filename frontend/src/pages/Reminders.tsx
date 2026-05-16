import { useEffect, useState } from 'react'
import { getReminders, deleteReminder } from '../services/api'
import { useAuth } from '../context/AuthContext'
import type { Reminder } from '../types'

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

function isUpcoming(dateStr: string): boolean {
  return new Date(dateStr) > new Date()
}

// Derive a short session label and dot colour from the reminder title.
// Titles for session reminders follow the format "Race Name – Session Name".
function getSessionLabel(title: string): string {
  const parts = title.split(' – ')
  return parts.length > 1 ? parts[parts.length - 1] : title
}

const SESSION_DOT_COLORS: Record<string, string> = {
  'Practice 1':        'bg-slate-500',
  'Practice 2':        'bg-slate-500',
  'Practice 3':        'bg-slate-500',
  'Sprint Qualifying': 'bg-orange-500',
  'Sprint':            'bg-orange-500',
  'Qualifying':        'bg-yellow-500',
  'Race':              'bg-red-500',
}

function ReminderRow({
  reminder,
  onDelete,
}: {
  reminder: Reminder
  onDelete: (id: number) => void
}) {
  const [deleting, setDeleting] = useState(false)
  const upcoming = isUpcoming(reminder.reminder_time)
  const isSession = reminder.session_id !== null
  const sessionLabel = isSession ? getSessionLabel(reminder.title) : null
  const dotColor = reminder.sent
    ? 'bg-gray-700'
    : isSession
    ? (SESSION_DOT_COLORS[sessionLabel ?? ''] ?? 'bg-gray-500')
    : upcoming
    ? 'bg-red-500'
    : 'bg-gray-700'

  async function handleDelete() {
    setDeleting(true)
    onDelete(reminder.id)
  }

  return (
    <div
      className={`flex items-center gap-4 px-5 py-4 border-b border-gray-800 last:border-0 transition-colors duration-150
        ${upcoming ? 'hover:bg-gray-800/50' : 'opacity-50'}`}
    >
      {/* Status dot */}
      <span className={`w-2 h-2 rounded-full shrink-0 ${dotColor}`} />

      {/* Reminder info */}
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-sm text-white truncate">{reminder.title}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <p className="text-gray-500 text-xs font-mono">
            {formatDateTime(reminder.reminder_time)}
          </p>
        </div>
      </div>

      {/* Type badge */}
      {isSession && sessionLabel ? (
        <span className="text-xs text-gray-500 border border-gray-800 px-2 py-0.5 rounded-full shrink-0 hidden sm:inline">
          {sessionLabel}
        </span>
      ) : reminder.race_id && !isSession ? (
        <span className="text-xs text-gray-600 border border-gray-800 px-2 py-0.5 rounded-full shrink-0 hidden sm:inline">
          Race
        </span>
      ) : null}

      {/* Sent badge */}
      {reminder.sent && (
        <span className="text-xs text-gray-600 border border-gray-800 px-2 py-0.5 rounded-full shrink-0">
          Sent
        </span>
      )}

      {/* Delete button */}
      <button
        onClick={handleDelete}
        disabled={deleting}
        className="text-gray-600 hover:text-red-400 transition-colors duration-150 shrink-0 disabled:opacity-40"
        aria-label="Delete reminder"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="w-4 h-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="3 6 5 6 21 6" />
          <path d="M19 6l-1 14H6L5 6" />
          <path d="M10 11v6M14 11v6" />
          <path d="M9 6V4h6v2" />
        </svg>
      </button>
    </div>
  )
}

function SkeletonRow() {
  return (
    <div className="flex items-center gap-4 px-5 py-4 border-b border-gray-800 last:border-0 animate-pulse">
      <div className="w-2 h-2 rounded-full bg-gray-800 shrink-0" />
      <div className="flex-1">
        <div className="h-4 bg-gray-800 rounded w-2/5 mb-1" />
        <div className="h-3 bg-gray-800 rounded w-1/4" />
      </div>
      <div className="h-3 w-8 bg-gray-800 rounded" />
    </div>
  )
}

export default function Reminders() {
  const { token } = useAuth()
  const [reminders, setReminders] = useState<Reminder[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    getReminders(token)
      .then(setReminders)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [token])

  async function handleDelete(id: number) {
    if (!token) return
    try {
      await deleteReminder(token, id)
      setReminders(prev => prev?.filter(r => r.id !== id) ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete reminder')
    }
  }

  return (
    <div className="page-enter max-w-2xl">
      {/* Header */}
      <div className="mb-8">
        <p className="text-red-500 text-xs font-semibold tracking-widest uppercase mb-3">
          Account
        </p>
        <h1 className="text-3xl font-bold text-white">Reminders</h1>
        <p className="text-gray-400 mt-1">Your scheduled race reminders.</p>
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

        {!loading && reminders?.length === 0 && (
          <div className="px-5 py-12 text-center">
            <p className="text-gray-400 font-medium">No reminders yet</p>
            <p className="text-gray-600 text-sm mt-1">
              You can create reminders from the Race Calendar.
            </p>
          </div>
        )}

        {reminders &&
          reminders.map(reminder => (
            <ReminderRow key={reminder.id} reminder={reminder} onDelete={handleDelete} />
          ))}
      </div>
    </div>
  )
}
