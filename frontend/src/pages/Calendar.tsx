import { useEffect, useState } from 'react'
import { getCalendar } from '../services/api'
import type { Race } from '../types'

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'TBC'
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function isPast(dateStr: string | null): boolean {
  if (!dateStr) return false
  return new Date(dateStr) < new Date()
}

function isNext(race: Race, allRaces: Race[]): boolean {
  const upcoming = allRaces.find(r => !isPast(r.start_date))
  return upcoming?.id === race.id
}

function RaceRow({ race, allRaces }: { race: Race; allRaces: Race[] }) {
  const past = isPast(race.start_date)
  const next = isNext(race, allRaces)

  return (
    <div
      className={`flex items-center gap-4 px-5 py-4 border-b border-gray-800 last:border-0 transition-colors duration-150
        ${past ? 'opacity-40' : 'hover:bg-gray-800/50'}`}
    >
      {/* Round badge */}
      <span className="text-gray-600 text-xs font-mono w-7 shrink-0 text-right">
        R{race.round}
      </span>

      {/* Race info */}
      <div className="flex-1 min-w-0">
        <p className={`font-semibold text-sm truncate ${past ? 'text-gray-400' : 'text-white'}`}>
          {race.name}
        </p>
        <p className="text-gray-600 text-xs truncate mt-0.5">{race.circuit_name ?? race.country ?? '—'}</p>
      </div>

      {/* Status / date */}
      <div className="text-right shrink-0">
        {next && (
          <span className="text-xs bg-red-600 text-white px-2 py-0.5 rounded-full font-medium block mb-1">
            Next Race
          </span>
        )}
        <p className={`text-xs font-mono ${past ? 'text-gray-600' : 'text-gray-400'}`}>
          {formatDate(race.start_date)}
        </p>
      </div>
    </div>
  )
}

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

export default function Calendar() {
  const [races, setRaces] = useState<Race[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getCalendar()
      .then(setRaces)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="page-enter">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Race Calendar</h1>
        <p className="text-gray-400 mt-1">The full 2025 Formula 1 season schedule.</p>
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

        {races && races.map(race => (
          <RaceRow key={race.id} race={race} allRaces={races} />
        ))}
      </div>
    </div>
  )
}
