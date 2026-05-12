import { useEffect, useState } from 'react'
import { getTeams } from '../services/api'
import type { Team } from '../types'

function TeamCard({ team }: { team: Team }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-red-500/70 transition-all duration-200 hover:-translate-y-0.5">
      {/* Colour accent bar */}
      <div className="h-1 w-10 bg-red-600 rounded-full mb-5" />
      <h2 className="text-white font-bold text-xl leading-tight">{team.name}</h2>
      <p className="text-gray-500 text-sm mt-1">{team.constructor_name}</p>
      <p className="text-gray-700 text-xs mt-3">
        {team.base ?? 'Base location not available'}
      </p>
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 animate-pulse">
      <div className="h-1 w-10 bg-gray-800 rounded-full mb-5" />
      <div className="h-5 w-2/3 bg-gray-800 rounded mb-2" />
      <div className="h-3 w-1/2 bg-gray-800 rounded" />
    </div>
  )
}

export default function Teams() {
  const [teams, setTeams] = useState<Team[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getTeams()
      .then(setTeams)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="page-enter">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Teams</h1>
        <p className="text-gray-400 mt-1">All 10 constructors on the 2025 Formula 1 grid.</p>
      </div>

      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {Array.from({ length: 6 }, (_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {error && (
        <div className="bg-gray-900 border border-red-900/50 rounded-xl p-8 text-center">
          <p className="text-red-400 font-medium">Failed to load teams</p>
          <p className="text-gray-500 text-sm mt-1">{error}</p>
          <p className="text-gray-600 text-xs mt-2">Make sure the backend is running on port 8000.</p>
        </div>
      )}

      {teams && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {teams.map(team => <TeamCard key={team.id} team={team} />)}
        </div>
      )}
    </div>
  )
}
