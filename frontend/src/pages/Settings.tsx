import { useEffect, useState } from 'react'
import { getEmailPreferences, updateEmailPreferences, sendTestEmail } from '../services/api'
import { useAuth } from '../context/AuthContext'
import type { EmailPreferences } from '../types'

// ─── Toggle component ────────────────────────────────────────────────────────

function Toggle({
  enabled,
  onChange,
  disabled = false,
}: {
  enabled: boolean
  onChange: (value: boolean) => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!enabled)}
      disabled={disabled}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200
        ${enabled ? 'bg-red-600' : 'bg-gray-700'}
        ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer hover:opacity-90'}`}
      aria-pressed={enabled}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-200
          ${enabled ? 'translate-x-6' : 'translate-x-1'}`}
      />
    </button>
  )
}

// ─── Setting row ─────────────────────────────────────────────────────────────

function SettingRow({
  label,
  description,
  enabled,
  onChange,
  disabled = false,
}: {
  label: string
  description: string
  enabled: boolean
  onChange: (value: boolean) => void
  disabled?: boolean
}) {
  return (
    <div className={`flex items-center justify-between gap-6 py-4 border-b border-gray-800 last:border-0
      ${disabled ? 'opacity-50' : ''}`}>
      <div className="min-w-0">
        <p className="text-sm font-medium text-white">{label}</p>
        <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{description}</p>
      </div>
      <Toggle enabled={enabled} onChange={onChange} disabled={disabled} />
    </div>
  )
}

// ─── Skeleton ────────────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <div className="flex items-center justify-between gap-6 py-4 border-b border-gray-800 last:border-0 animate-pulse">
      <div className="flex-1">
        <div className="h-4 bg-gray-800 rounded w-2/5 mb-1.5" />
        <div className="h-3 bg-gray-800 rounded w-3/5" />
      </div>
      <div className="h-6 w-11 bg-gray-800 rounded-full shrink-0" />
    </div>
  )
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function Settings() {
  const { token, user } = useAuth()
  const [prefs, setPrefs] = useState<EmailPreferences | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [testStatus, setTestStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')
  const [testMessage, setTestMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    getEmailPreferences(token)
      .then(setPrefs)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [token])

  async function handleToggle(field: keyof EmailPreferences, value: boolean) {
    if (!token || !prefs) return
    setSaveError(null)

    // Optimistic update — update UI immediately before the request completes
    setPrefs(prev => prev ? { ...prev, [field]: value } : prev)

    try {
      const updated = await updateEmailPreferences(token, { [field]: value })
      setPrefs(updated)
    } catch (e) {
      // Revert on failure
      setPrefs(prev => prev ? { ...prev, [field]: !value } : prev)
      setSaveError(e instanceof Error ? e.message : 'Failed to save setting')
    }
  }

  async function handleTestEmail() {
    if (!token) return
    setTestStatus('sending')
    setTestMessage(null)
    try {
      const res = await sendTestEmail(token)
      setTestStatus('sent')
      setTestMessage(res.message)
    } catch (e) {
      setTestStatus('error')
      setTestMessage(e instanceof Error ? e.message : 'Failed to send test email')
    }
  }

  const masterOn = prefs?.email_notifications_enabled ?? false

  return (
    <div className="page-enter max-w-lg">
      {/* Header */}
      <div className="mb-8">
        <p className="text-red-500 text-xs font-semibold tracking-widest uppercase mb-3">
          Account
        </p>
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-1 text-sm">Manage your notification preferences.</p>
      </div>

      {/* Load error */}
      {error && (
        <div className="mb-6 px-4 py-3 bg-red-950/50 border border-red-800/50 rounded-xl">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Save error */}
      {saveError && (
        <div className="mb-4 px-4 py-3 bg-red-950/50 border border-red-800/50 rounded-xl">
          <p className="text-red-400 text-sm">{saveError}</p>
        </div>
      )}

      {/* Email notifications card */}
      <div className="mb-6">
        <p className="text-gray-500 text-xs font-semibold uppercase tracking-widest mb-3 px-1">
          Email Notifications
        </p>
        <div className="bg-gray-900 border border-gray-800 rounded-2xl px-6 py-2">
          {loading ? (
            <>
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
            </>
          ) : prefs ? (
            <>
              <SettingRow
                label="Email notifications"
                description="Master switch. Turn this on to receive any emails from GridPulse."
                enabled={prefs.email_notifications_enabled}
                onChange={v => handleToggle('email_notifications_enabled', v)}
              />
              <SettingRow
                label="Race reminders"
                description="Send me an email before races I have added a reminder for."
                enabled={prefs.calendar_email_reminders_enabled}
                onChange={v => handleToggle('calendar_email_reminders_enabled', v)}
                disabled={!masterOn}
              />
              <SettingRow
                label="Favourite driver alerts"
                description="Notify me about results and updates for my favourite drivers. Coming soon."
                enabled={prefs.favorite_driver_email_alerts_enabled}
                onChange={v => handleToggle('favorite_driver_email_alerts_enabled', v)}
                disabled={!masterOn}
              />
            </>
          ) : null}
        </div>
        {!loading && prefs && !masterOn && (
          <p className="text-gray-600 text-xs mt-2 px-1">
            Enable email notifications above to configure individual settings.
          </p>
        )}
      </div>

      {/* Test email section */}
      {prefs && masterOn && (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl px-6 py-5">
          <p className="text-sm font-medium text-white mb-0.5">Send a test email</p>
          <p className="text-xs text-gray-500 mb-4">
            Sends a test email to <span className="text-gray-400">{user?.email}</span> to confirm delivery is working.
          </p>
          <button
            onClick={handleTestEmail}
            disabled={testStatus === 'sending'}
            className="text-sm text-gray-300 hover:text-white border border-gray-700 hover:border-gray-500 px-4 py-2 rounded-lg transition-colors duration-150 disabled:opacity-40"
          >
            {testStatus === 'sending' ? 'Sending…' : 'Send test email'}
          </button>
          {testMessage && (
            <p className={`text-xs mt-3 ${testStatus === 'sent' ? 'text-green-500' : 'text-red-400'}`}>
              {testMessage}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
