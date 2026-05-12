import { useEffect, useState } from 'react'
import { getDriverStandings } from '../services/api'
import type { DriverStanding } from '../types'

function positionStyle(pos: number): string {
  if (pos === 1) return 'text-yellow-400 font-bold'
  if (pos === 2) return 'text-gray-300 font-semibold'
  if (pos === 3) return 'text-amber-600 font-semibold'
  return 'text-gray-500'
}

function positionBg(pos: number): string {
  if (pos === 1) return 'bg-yellow-400/10 border-l-2 border-yellow-400'
  if (pos === 2) return 'bg-gray-300/5 border-l-2 border-gray-400'
  if (pos === 3) return 'bg-amber-600/10 border-l-2 border-amber-600'
  return ''
}

function StandingRow({ entry }: { entry: DriverStanding }) {
  return (
    <div
      className={`flex items-center gap-4 px-5 py-3.5 border-b border-gray-800 last:border-0 hover:bg-gray-800/40 transition-colors duration-150 ${positionBg(entry.position)}`}
    >
      <span className={`w-7 text-right text-sm shrink-0 ${positionStyle(entry.position)}`}>
        {entry.position}
      </span>

      <div className="flex-1 min-w-0">
        <p className="text-white font-medium text-sm truncate">{entry.driver}</p>
        <p className="text-gray-500 text-xs truncate mt-0.5">{entry.team}</p>
      </div>

      <div className="text-right shrink-0">
        <p className="text-white font-bold text-sm">{entry.points} <span className="text-gray-500 font-normal text-xs">pts</span></p>
        <p className="text-gray-600 text-xs mt-0.5">{entry.wins} {entry.wins === 1 ? 'win' : 'wins'}</p>
      </div>
    </div>
  )
}

function SkeletonRow() {
  return (
    <div className="flex items-center gap-4 px-5 py-3.5 border-b border-gray-800 last:border-0 animate-pulse">
      <div className="h-3 w-5 bg-gray-800 rounded shrink-0" />
      <div className="flex-1">
        <div className="h-4 bg-gray-800 rounded w-2/5 mb-1" />
        <div className="h-3 bg-gray-800 rounded w-1/4" />
      </div>
      <div className="h-4 w-14 bg-gray-800 rounded" />
    </div>
  )
}

export default function Standings() {
  const [standings, setStandings] = useState<DriverStanding[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getDriverStandings()
      .then(setStandings)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="page-enter">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Driver Standings</h1>
        <p className="text-gray-400 mt-1">2025 Formula 1 World Championship.</p>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-4 px-5 py-3 border-b border-gray-700 bg-gray-800/50">
          <span className="w-7 text-right text-xs text-gray-500 uppercase tracking-wider shrink-0">Pos</span>
          <span className="flex-1 text-xs text-gray-500 uppercase tracking-wider">Driver</span>
          <span className="text-xs text-gray-500 uppercase tracking-wider shrink-0">Points</span>
        </div>

        {loading && Array.from({ length: 8 }, (_, i) => <SkeletonRow key={i} />)}

        {error && (
          <div className="p-8 text-center">
            <p className="text-red-400 font-medium">Failed to load standings</p>
            <p className="text-gray-500 text-sm mt-1">{error}</p>
            <p className="text-gray-600 text-xs mt-2">Make sure the backend is running on port 8000.</p>
          </div>
        )}

        {standings && standings.map(entry => (
          <StandingRow key={entry.position} entry={entry} />
        ))}
      </div>
    </div>
  )
}
