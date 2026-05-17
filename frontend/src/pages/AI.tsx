import { useEffect, useRef, useState } from 'react'
import { askAI, getAIHistory, getAIUsage } from '../services/api'
import { useAuth } from '../context/AuthContext'
import type { AIHistoryItem, AIResponse, AIUsage } from '../types'

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function UsageBar({ usage }: { usage: AIUsage }) {
  const pct = Math.round((usage.requests_today / usage.daily_limit) * 100)
  const barColor =
    pct >= 90 ? 'bg-red-500' : pct >= 60 ? 'bg-amber-500' : 'bg-emerald-500'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-600 shrink-0 font-mono tabular-nums">
        {usage.requests_today} / {usage.daily_limit} today
      </span>
    </div>
  )
}

function HistoryItem({ item }: { item: AIHistoryItem }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="border-b border-gray-800 last:border-0">
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full text-left px-5 py-4 hover:bg-gray-800/40 transition-colors duration-150"
      >
        <div className="flex items-start justify-between gap-4">
          <p className="text-sm text-gray-300 leading-snug line-clamp-2 flex-1">
            {item.prompt}
          </p>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className={`w-4 h-4 text-gray-600 shrink-0 mt-0.5 transition-transform duration-200 ${
              expanded ? 'rotate-180' : ''
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
        <p className="text-xs text-gray-700 font-mono mt-1">
          {formatDateTime(item.created_at)}
        </p>
      </button>

      {expanded && (
        <div className="px-5 pb-4">
          <div className="bg-gray-800/50 border border-gray-700/40 rounded-xl px-4 py-3">
            <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
              {item.response ?? 'No response recorded.'}
            </p>
            {item.model_name && (
              <p className="text-[11px] text-gray-700 font-mono mt-3">{item.model_name}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function SkeletonHistory() {
  return (
    <div className="animate-pulse px-5 py-4 border-b border-gray-800">
      <div className="h-3.5 bg-gray-800 rounded w-3/4 mb-2" />
      <div className="h-3 bg-gray-800 rounded w-1/4" />
    </div>
  )
}

export default function AIAssistant() {
  const { token } = useAuth()

  const [prompt, setPrompt] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [latestResponse, setLatestResponse] = useState<AIResponse | null>(null)

  const [history, setHistory] = useState<AIHistoryItem[] | null>(null)
  const [historyLoading, setHistoryLoading] = useState(true)

  const [usage, setUsage] = useState<AIUsage | null>(null)

  const responseRef = useRef<HTMLDivElement>(null)

  // Load history and usage on mount
  useEffect(() => {
    if (!token) return
    Promise.all([getAIHistory(token), getAIUsage(token)])
      .then(([h, u]) => {
        setHistory(h)
        setUsage(u)
      })
      .catch(() => setHistory([]))
      .finally(() => setHistoryLoading(false))
  }, [token])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = prompt.trim()
    if (!trimmed || !token) return

    setSubmitting(true)
    setSubmitError(null)

    try {
      const response = await askAI(token, trimmed)
      setLatestResponse(response)
      setPrompt('')

      // Prepend to history and refresh usage without a second round-trip
      setHistory(prev => [
        {
          id: response.id,
          prompt: response.prompt,
          response: response.response,
          request_type: response.request_type,
          created_at: response.created_at,
          model_name: null,
        },
        ...(prev ?? []),
      ])
      setUsage(prev =>
        prev
          ? {
              ...prev,
              requests_today: prev.requests_today + 1,
              remaining: Math.max(0, prev.remaining - 1),
            }
          : prev,
      )

      // Scroll response into view
      setTimeout(() => responseRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setSubmitting(false)
    }
  }

  const limitReached = usage !== null && usage.remaining === 0

  return (
    <div className="page-enter max-w-2xl">
      {/* Header */}
      <div className="mb-8">
        <p className="text-red-500 text-xs font-semibold tracking-widest uppercase mb-3">
          AI Race Assistant
        </p>
        <h1 className="text-3xl font-bold text-white">Ask the Grid</h1>
        <p className="text-gray-400 mt-1">
          Ask questions about your favourites, standings, and upcoming sessions.
          The assistant only uses your GridPulse data — it won't invent results.
        </p>
      </div>

      {/* Usage bar */}
      {usage && (
        <div className="mb-6">
          <UsageBar usage={usage} />
        </div>
      )}

      {/* Limit warning */}
      {limitReached && (
        <div className="mb-6 px-4 py-3 bg-amber-950/40 border border-amber-800/40 rounded-xl">
          <p className="text-amber-400 text-sm font-medium">Daily limit reached</p>
          <p className="text-amber-600 text-xs mt-0.5">
            You've used all {usage?.daily_limit} requests for today. Come back tomorrow.
          </p>
        </div>
      )}

      {/* Input form */}
      <form onSubmit={handleSubmit} className="mb-8">
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden focus-within:border-gray-600 transition-colors duration-200">
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e)
            }}
            placeholder="Ask about standings, your favourite drivers, upcoming sessions…"
            rows={4}
            disabled={submitting || limitReached}
            className="w-full bg-transparent text-white text-sm placeholder-gray-600 px-5 pt-4 pb-3 resize-none focus:outline-none disabled:opacity-40"
          />
          <div className="flex items-center justify-between px-4 pb-3 pt-1 border-t border-gray-800">
            <span className="text-xs text-gray-700">⌘ + Enter to submit</span>
            <button
              type="submit"
              disabled={submitting || !prompt.trim() || limitReached}
              className="flex items-center gap-2 bg-red-600 hover:bg-red-500 disabled:bg-gray-800 disabled:text-gray-600 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors duration-200"
            >
              {submitting ? (
                <>
                  <svg
                    className="w-4 h-4 animate-spin"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12" cy="12" r="10"
                      stroke="currentColor" strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8v8H4z"
                    />
                  </svg>
                  Analysing…
                </>
              ) : (
                'Ask'
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Submit error */}
      {submitError && (
        <div className="mb-6 px-4 py-3 bg-red-950/50 border border-red-800/50 rounded-xl">
          <p className="text-red-400 text-sm">{submitError}</p>
        </div>
      )}

      {/* Latest response */}
      {latestResponse && (
        <div ref={responseRef} className="mb-10">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2 h-2 rounded-full bg-red-500 shrink-0" />
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
              Response
            </p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl px-5 py-4">
            <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
              {latestResponse.response}
            </p>
            <p className="text-xs text-gray-700 font-mono mt-4">
              {formatDateTime(latestResponse.created_at)}
            </p>
          </div>
        </div>
      )}

      {/* History */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
          Recent Questions
        </p>

        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          {historyLoading && (
            <>
              <SkeletonHistory />
              <SkeletonHistory />
              <SkeletonHistory />
            </>
          )}

          {!historyLoading && history?.length === 0 && (
            <div className="px-5 py-10 text-center">
              <p className="text-gray-500 text-sm">No questions yet.</p>
              <p className="text-gray-700 text-xs mt-1">
                Your question history will appear here.
              </p>
            </div>
          )}

          {history && history.length > 0 && (
            <>
              {history.slice(0, 20).map(item => (
                <HistoryItem key={item.id} item={item} />
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
