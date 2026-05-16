import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getTeams, getFavoriteTeams, addFavoriteTeam, removeFavoriteTeam } from '../services/api'
import { useAuth } from '../context/AuthContext'
import type { Team } from '../types'

type FavStatus = 'idle' | 'loading' | 'error'

function TeamCard({
  team,
  isAuthenticated,
  token,
  initialFavorited,
}: {
  team: Team
  isAuthenticated: boolean
  token: string | null
  initialFavorited: boolean
}) {
  const [isFavorited, setIsFavorited] = useState(initialFavorited)
  const [favStatus, setFavStatus] = useState<FavStatus>('idle')
  const [favError, setFavError] = useState<string | null>(null)

  async function handleFavoriteToggle() {
    if (!token) return
    setFavStatus('loading')
    setFavError(null)
    try {
      if (isFavorited) {
        await removeFavoriteTeam(token, team.id)
        setIsFavorited(false)
      } else {
        await addFavoriteTeam(token, team.id)
        setIsFavorited(true)
      }
      setFavStatus('idle')
    } catch (e) {
      setFavStatus('error')
      setFavError(e instanceof Error ? e.message : 'Something went wrong')
    }
  }

  return (
    <div className={`bg-gray-900 border rounded-xl p-6 transition-all duration-200 hover:-translate-y-0.5
      ${isFavorited ? 'border-red-800/60' : 'border-gray-800 hover:border-red-500/70'}`}>
      {/* Colour accent bar */}
      <div className={`h-1 w-10 rounded-full mb-5 ${isFavorited ? 'bg-red-500' : 'bg-red-600'}`} />

      <h2 className="text-white font-bold text-xl leading-tight">{team.name}</h2>
      <p className="text-gray-500 text-sm mt-1">{team.constructor_name}</p>
      <p className="text-gray-700 text-xs mt-3">
        {team.base ?? 'Base location not available'}
      </p>

      {/* Favorite action */}
      <div className="mt-5 pt-4 border-t border-gray-800">
        {!isAuthenticated ? (
          <div>
            <Link
              to="/login"
              className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg border border-gray-700 text-gray-400 hover:border-gray-500 hover:text-white transition-colors duration-150 w-fit"
            >
              <span>☆</span>
              <span>Log in to favourite</span>
            </Link>
            <p className="text-xs text-gray-700 mt-1.5">Sign in to follow this team</p>
          </div>
        ) : (
          <div className="flex flex-col gap-1">
            <button
              onClick={handleFavoriteToggle}
              disabled={favStatus === 'loading'}
              className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg border transition-colors duration-150 w-fit disabled:opacity-40
                ${isFavorited
                  ? 'border-red-800 text-red-400 hover:bg-red-950/40'
                  : 'border-gray-700 text-gray-500 hover:border-gray-500 hover:text-white'
                }`}
            >
              <span>{isFavorited ? '★' : '☆'}</span>
              <span>
                {favStatus === 'loading'
                  ? isFavorited ? 'Removing…' : 'Adding…'
                  : isFavorited ? 'Favourited' : 'Add to Favourites'}
              </span>
            </button>
            {favStatus === 'error' && (
              <p className="text-xs text-red-400">{favError}</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 animate-pulse">
      <div className="h-1 w-10 bg-gray-800 rounded-full mb-5" />
      <div className="h-5 w-2/3 bg-gray-800 rounded mb-2" />
      <div className="h-3 w-1/2 bg-gray-800 rounded" />
      <div className="mt-5 pt-4 border-t border-gray-800">
        <div className="h-6 w-28 bg-gray-800 rounded" />
      </div>
    </div>
  )
}

export default function Teams() {
  const { isAuthenticated, token } = useAuth()
  const [teams, setTeams] = useState<Team[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [favoritedTeamIds, setFavoritedTeamIds] = useState<Set<number>>(new Set())

  useEffect(() => {
    getTeams()
      .then(setTeams)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!token) return
    getFavoriteTeams(token)
      .then(favorites => {
        setFavoritedTeamIds(new Set(favorites.map(f => f.team_id)))
      })
      .catch(() => {})
  }, [token])

  return (
    <div className="page-enter">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Teams</h1>
        <p className="text-gray-400 mt-1">All 11 constructors on the 2026 Formula 1 grid.</p>
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
          {teams.map(team => (
            <TeamCard
              key={team.id}
              team={team}
              isAuthenticated={isAuthenticated}
              token={token}
              initialFavorited={favoritedTeamIds.has(team.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
